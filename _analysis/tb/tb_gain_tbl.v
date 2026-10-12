//=============================================================================
// tb_gain_tbl.v  —— 2026-10-10c 增益改动端到端验证台
//
// 把 uicfgcs500_720p 真正跑一遍（含 uics500reg_720p60 / SC500GainTbl / uii2c），
// 在 iic_req 上抓取"实际会被写进传感器的 (地址,数据)"序列，对四种开关组合逐一验证：
//   ① 端口连接（I_gain_digital）—— elaboration/仿真即可暴露
//   ② REG_SIZE = 123、索引 0..122 一条不漏地下发
//   ③ 索引 115 的 stream-on 延时计数器确实被触发（表尾追加没破坏它）
//   ④ 模拟增益：SW4 上→3e08=1f/3e09=3f(15.750x)；下→0f/20(4.000x)
//      数字增益：SW3 上→3e06=01/3e07=80(2.000x)；下→00/80(1.000x)
//   ⑤ 0x4501 恰好写两条且都是 0xb4（测试图关闭），0x3e03 = 0x0b
//   ⑥ 曝光 3e00/3e01/3e02 = 00/7c/60 = 1990
//   ⑦ 无 I_ae_req 时 AE 表不下发；注入一次 I_ae_req 后 AE 表 **8 条**下发
//      （2026-10-10d：AE 表 5→8，新增 3e06/3e07 数字增益与 4501 运行时自检）
//   ⑧ ★运行时通路★ AE 表下发的曝光/增益必须跟当前开关一致，且 I_test_pattern=1 时
//      4501 写 0xbc（灰度测试图）、=0 时写 0xb4；init 表则永远写 0xb4。
//=============================================================================
`timescale 1ns / 1ps

module tb_gain_tbl;

    reg         clk     = 1'b0;
    reg         rst_n   = 1'b0;
    reg         ae_req  = 1'b0;
    reg  [15:0] exp_time = 16'd1990;
    reg  [15:0] ana_gain = 16'd80;
    reg         tp = 1'b0;
    reg         gh = 1'b0;
    reg         gd = 1'b0;
    wire        scl, sda, cfg_done, ae_done;

    uicfgcs500_720p #(.CLK_DIV(16'd3)) dut (
        .I_clk          (clk),
        .I_rst_n        (rst_n),
        .I_ae_req       (ae_req),
        .I_exposure_time(exp_time),
        .I_analog_gain  (ana_gain),
        .I_test_pattern (tp),
        .I_gain_high    (gh),
        .I_gain_digital (gd),
        .O_cam_scl      (scl),
        .IO_cam_sda     (sda),
        .O_cfg_done     (cfg_done),
        .O_ae_cfg_done  (ae_done)
    );

    always #5 clk = ~clk;                       // 100 MHz 快跑

    // ---- 抓写下发：线上字节序 = CAM_ID → 寄存器高字节 → 寄存器低字节 → 数据 ----
    reg [15:0] log_addr [0:255];
    reg [7:0]  log_data [0:255];
    reg [7:0]  log_id   [0:255];
    integer    nwr, ae_phase, n_delay_seen, errs, combos_done;
    reg [31:0] first_wr;
    reg        iic_req_d;
    wire       wr_stb = dut.iic_req && !iic_req_d;   // ★只在 iic_req 上升沿记一次

    always @(posedge clk) begin
        iic_req_d <= dut.iic_req;
        if (rst_n) begin
            if (dut.delay_cnt != 18'd0) n_delay_seen = n_delay_seen + 1;
            if (wr_stb && !$isunknown(dut.wr_data)) begin
                if (nwr == 0) first_wr = dut.wr_data;
                log_id  [nwr] = dut.wr_data[7:0];
                log_addr[nwr] = {dut.wr_data[15:8], dut.wr_data[23:16]};
                log_data[nwr] = dut.wr_data[31:24];
                if (ae_phase) $display("      AE WR addr=0x%04h data=0x%02h",
                                       log_addr[nwr], log_data[nwr]);
                nwr = nwr + 1;
            end
        end
    end

    function [7:0] last_data_of(input [15:0] a);
        integer k;
        begin
            last_data_of = 8'hxx;
            for (k = 0; k < nwr; k = k + 1)
                if (log_addr[k] == a) last_data_of = log_data[k];
        end
    endfunction

    function integer count_of(input [15:0] a, input [7:0] d);
        integer k, c;
        begin
            c = 0;
            for (k = 0; k < nwr; k = k + 1)
                if (log_addr[k] == a && log_data[k] == d) c = c + 1;
            count_of = c;
        end
    endfunction

    task expect(input cond, input [8*64:1] tag);
        begin
            if (cond) $display("  [PASS] %0s", tag);
            else begin $display("  [FAIL] %0s", tag); errs = errs + 1; end
        end
    endtask

    task run_one(input gh_i, input gd_i, input do_ae, input tp_i);
        begin
            gh = gh_i; gd = gd_i; tp = tp_i;
            rst_n = 1'b0;
            repeat (30) @(negedge clk);
            nwr = 0; n_delay_seen = 0; ae_phase = 0;
            rst_n = 1'b1;
            wait (cfg_done === 1'b1);
            repeat (5) @(negedge clk);

            $display("");
            $display("=== 组合 %0d : SW4(模拟高档)=%b  SW3(数字x2)=%b | 共 %0d 次 I2C 写 | REG_SIZE=%0d ===",
                     combos_done, gh, gd, nwr, dut.init_size);

            expect(dut.init_size === 9'd123, "REG_SIZE = 123");
            expect(nwr === 123,           "索引 0..122 共 123 条全部下发");
            expect(n_delay_seen > 0,      "索引 115 的 stream-on 延时计数器被触发过");
            expect(log_id[0] === 8'h6c,   "I2C 从机地址 = 0x6c");
            expect(count_of(16'h4501, 8'hb4) === 2 && count_of(16'h4501, 8'hbc) === 0,
                   "0x4501 两条都写 0xb4（测试图关闭）");
            expect(last_data_of(16'h3e03) === 8'h0b, "0x3e03 = 0x0b（AGC 位保留）");
            expect(last_data_of(16'h3e00) === 8'h00 && last_data_of(16'h3e01) === 8'h7c &&
                   last_data_of(16'h3e02) === 8'h60, "曝光 = 00/7c/60 = 1990（2*VTS-10 上限）");
            if (gh_i)
                expect(last_data_of(16'h3e08) === 8'h1f && last_data_of(16'h3e09) === 8'h3f,
                       "SW4上 -> 模拟增益 0x1f/0x3f = 15.750x");
            else
                expect(last_data_of(16'h3e08) === 8'h0f && last_data_of(16'h3e09) === 8'h20,
                       "SW4下 -> 模拟增益 0x0f/0x20 = 4.000x");
            if (gd_i)
                expect(last_data_of(16'h3e06) === 8'h01 && last_data_of(16'h3e07) === 8'h80,
                       "SW3上 -> 数字增益 0x01/0x80 = 2.000x");
            else
                expect(last_data_of(16'h3e06) === 8'h00 && last_data_of(16'h3e07) === 8'h80,
                       "SW3下 -> 数字增益 0x00/0x80 = 1.000x");
            expect(count_of(16'h3e06, 8'h00) + count_of(16'h3e06, 8'h01) == 1,
                   "0x3e06 只被写一次（表尾单条）");

            if (do_ae) begin
                ae_phase = 1;
                nwr = 0;
                @(negedge clk); ae_req = 1'b1; @(negedge clk); ae_req = 1'b0;
                repeat (5000) @(negedge clk);
                expect(nwr == 8, "注入 I_ae_req 后 AE 表 8 条下发");
                expect(last_data_of(16'h3e00) === 8'h00 && last_data_of(16'h3e01) === 8'h7c &&
                       last_data_of(16'h3e02) === 8'h60,
                       "运行时表曝光 = 00/7c/60 = 1990");
                if (gh_i)
                    expect(last_data_of(16'h3e08) === 8'h1f && last_data_of(16'h3e09) === 8'h3f,
                           "运行时表模拟增益跟随 SW4=1 -> 0x1f/0x3f = 15.750x");
                else
                    expect(last_data_of(16'h3e08) === 8'h0f && last_data_of(16'h3e09) === 8'h20,
                           "运行时表模拟增益跟随 SW4=0 -> 0x0f/0x20 = 4.000x");
                if (gd_i)
                    expect(last_data_of(16'h3e06) === 8'h01 && last_data_of(16'h3e07) === 8'h80,
                           "运行时表数字增益跟随 SW3=1 -> 0x01/0x80 = 2.000x");
                else
                    expect(last_data_of(16'h3e06) === 8'h00 && last_data_of(16'h3e07) === 8'h80,
                           "运行时表数字增益跟随 SW3=0 -> 0x00/0x80 = 1.000x");
                if (tp_i)
                    expect(last_data_of(16'h4501) === 8'hbc,
                           "I_test_pattern=1 -> 运行时表 4501 = 0xbc（灰度递增测试图，自检）");
                else
                    expect(last_data_of(16'h4501) === 8'hb4,
                           "I_test_pattern=0 -> 运行时表 4501 = 0xb4（正常图像）");
                ae_phase = 0;
            end
            combos_done = combos_done + 1;
        end
    endtask

    initial begin
        nwr = 0; ae_phase = 0; n_delay_seen = 0; errs = 0; combos_done = 0;
        $display("########## tb_gain_tbl 开始 ##########");
        run_one(1'b0, 1'b0, 1'b0, 1'b0);
        run_one(1'b0, 1'b1, 1'b0, 1'b0);
        run_one(1'b1, 1'b0, 1'b0, 1'b0);
        run_one(1'b1, 1'b1, 1'b1, 1'b0);
        run_one(1'b1, 1'b1, 1'b1, 1'b1);
        $display("");
        if (errs == 0) $display("########## 最终：全部 PASS ##########");
        else           $display("########## 最终：%0d 处 FAIL ##########", errs);
        $finish;
    end

    initial begin
        #400000000;   // 400 ms 仿真超时保护
        $display("########## 超时 ##########");
        $finish;
    end

endmodule
