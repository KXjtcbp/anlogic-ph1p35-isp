//=============================================================================
// [HDR-2026-10-12] 文件 : tb_ae_ctrl.v
// 模块 : tb_ae_ctrl   —— ae_ctrl.v 的 Testbench
// 用法 : vlib work
//        vlog ae_ctrl.v tb_ae_ctrl.v
//        vsim -c -do "run -all; quit -f" tb_ae_ctrl
// 说明 : 本 TB 不需要 glbl（ae_ctrl 不例化任何 IP 原语）。
//        TB 侧自带一个 uicfgcs500_720p 的 AE 表握手模型：
//          O_ae_req 单拍脉冲 -> I_ae_cfg_done 拉低 AE_DL_CYCLES 拍 -> 再拉高。
// 覆盖 : CASE1 复位默认值      CASE2 配置未完成时不动作
//        CASE3 稳定期不动作     CASE4 欠亮 -> 逐档加亮并收敛进死区
//        CASE5 高光护栏优先降档 CASE6 暗场景护栏阻止加亮
//        CASE7 冻结(I_ae_en=0)  CASE8 请求脉冲宽度必须恰好 1 拍
//=============================================================================
`timescale 1ns / 1ns

module tb_ae_ctrl;

    //-------------- 与 DUT 的 parameter 保持一致（TB 用小尺寸便于快速收敛）------
    localparam [7:0]  TGT       = 8'd70;
    localparam [31:0] NOM       = 32'd1048576;  // 2^20 ：使 DUT 的 >>20 回读有意义
    localparam [6:0]  GI_INIT   = 7'd64;        // 0x0F20 = 4.000x
    localparam [7:0]  SETTLE    = 8'd4;
    localparam [15:0] EXP       = 16'd1990;
    localparam integer AE_DL_CYCLES = 20;

    // TARGET_SUM = 2^20 * 70 = 73400320 ; DEADBAND = /21 = 3495253
    localparam [39:0] TSUM      = 40'd73400320;
    localparam [39:0] DBAND     = 40'd3495253;

    reg         clk = 0;
    reg         rst_n = 0;
    reg         ae_en = 1;
    reg         stat_tgl = 0;
    reg  [39:0] luma_sum = 0;
    reg  [31:0] pix_cnt = 0, hi_cnt = 0, lo_cnt = 0;
    reg         cam_cfg_done = 0;
    reg         ae_cfg_done  = 0;

    wire        ae_req;
    wire [15:0] exposure_time, analog_gain;
    wire [7:0]  meas_luma;
    wire [6:0]  gain_idx;
    wire [1:0]  state;

    integer errors = 0;
    integer req_n  = 0;
    reg     req_seen = 0;
    reg     req_stuck = 0;
    integer max_pulse = 0;
    integer cur_pulse = 0;

    //-------------- DUT -------------------------------------------------------
    ae_ctrl #(
        .TARGET_MEAN    (TGT),
        .NOM_PIX        (NOM),
        .EXPOSURE_FIXED (EXP),
        .GAIN_IDX_INIT  (GI_INIT),
        .SETTLE_FRAMES  (SETTLE)
    ) dut (
        .I_clk           (clk),
        .I_rst_n         (rst_n),
        .I_ae_en         (ae_en),
        .I_stat_tgl      (stat_tgl),
        .I_luma_sum      (luma_sum),
        .I_pix_cnt       (pix_cnt),
        .I_hi_cnt        (hi_cnt),
        .I_lo_cnt        (lo_cnt),
        .I_cam_cfg_done  (cam_cfg_done),
        .I_ae_cfg_done   (ae_cfg_done),
        .O_ae_req        (ae_req),
        .O_exposure_time (exposure_time),
        .O_analog_gain   (analog_gain),
        .O_meas_luma     (meas_luma),
        .O_gain_idx      (gain_idx),
        .O_state         (state)
    );

    //-------------- 时钟 -------------------------------------------------------
    always #10 clk = ~clk;          // 20 ns

    //-------------- 请求脉冲监测 ----------------------------------------------
    always @(posedge clk) begin
        if (ae_req) begin
            req_n = req_n + 1;
            cur_pulse = cur_pulse + 1;
            if (req_seen) req_stuck = 1;      // 连续两拍高 = 不是脉冲
            req_seen = 1;
            if (cur_pulse > max_pulse) max_pulse = cur_pulse;
        end else begin
            req_seen = 0;
            cur_pulse = 0;
        end
    end

    //-------------- uicfgcs500_720p 的 AE 表握手模型 --------------------------
    integer dl;
    always @(posedge clk) begin
        if (!rst_n) begin
            dl = 0;
            ae_cfg_done <= 1'b0;
        end else if (ae_req) begin
            dl = AE_DL_CYCLES;
            ae_cfg_done <= 1'b0;
        end else if (dl != 0) begin
            dl = dl - 1;
            if (dl == 1) ae_cfg_done <= 1'b1;
        end
    end

    //-------------- 一帧的统计值 ----------------------------------------------
    // 亮度模型：luma_sum = 当前增益索引 * 110  (gi=122..127 时落在 14000 附近)
    task do_frame(input [39:0] ls, input [31:0] hi, input [31:0] lo);
        begin
            luma_sum = ls;
            pix_cnt  = NOM;
            hi_cnt   = hi;
            lo_cnt   = lo;
            #200;
            stat_tgl = ~stat_tgl;       // 帧结束
            #1000;                      // 留足时间给下发模型
        end
    endtask

    // 用当前增益索引算出这一帧的亮度总和。
    // 亮度模型：mean(gi) = gi * 9 / 16  （gi=124 -> 69.75, gi=127 -> 71.4）
    //           luma_sum = mean * 2^20 = gi * 589824
    function [39:0] ls_of_gi(input [6:0] gi);
        begin
            ls_of_gi = gi * 40'd589824;
        end
    endfunction

    // TB 侧独立的"索引 -> 寄存器字节"参考模型（与 DUT 的 f_gain_bytes 同构，
    // 但不共用任何代码，用来抓 DUT 里查表写错的情况）
    function [7:0] exp_coarse(input [1:0] c);
        begin
            case (c)
                2'd0:    exp_coarse = 8'h03;
                2'd1:    exp_coarse = 8'h07;
                2'd2:    exp_coarse = 8'h0F;
                default: exp_coarse = 8'h1F;
            endcase
        end
    endfunction

    function [15:0] exp_gain_bytes(input [6:0] gi);
        reg [7:0] fine;
        begin
            fine = 8'h20 + {3'b000, gi[4:0]};
            exp_gain_bytes = {exp_coarse(gi[6:5]), fine};
        end
    endfunction

    task chk(input [255:0] name, input cond);
        begin
            if (cond) $display("  [OK]   %0s", name);
            else begin $display("  [FAIL] %0s", name); errors = errors + 1; end
        end
    endtask

    //==========================================================================
    integer i;
    reg [6:0] gi_before, gi_after;

    initial begin
        $display("=== tb_ae_ctrl start ===");

        //--------------------- CASE 1 : 复位默认值 ---------------------------
        rst_n = 0; #200; rst_n = 1; #100;
        $display("[CASE 1] reset defaults");
        chk("gain_idx resets to GAIN_IDX_INIT", gain_idx == GI_INIT);
        chk("analog_gain = 16'h0F20 (4.000x)", analog_gain == 16'h0F20);
        chk("exposure  = 1990",                exposure_time == 16'd1990);
        chk("state    = 0",                    state == 2'd0);
        chk("no request yet",                  req_n == 0);

        //--------------------- CASE 2 : 配置未完成 -> 不动作 -----------------
        $display("[CASE 2] cam_cfg_done=0 (no action)");
        cam_cfg_done = 0; ae_cfg_done = 0;
        for (i = 0; i < 20; i = i + 1) do_frame(40'd1000, 32'd0, 32'd0);  // 极暗
        chk("gain_idx unchanged", gain_idx == GI_INIT);
        chk("no request",         req_n == 0);

        //--------------------- CASE 3 : 稳定期不动作 -------------------------
        $display("[CASE 3] settle window (SETTLE_FRAMES=%0d)", SETTLE);
        cam_cfg_done = 1; ae_cfg_done = 1; #100;
        for (i = 0; i < SETTLE - 1; i = i + 1) do_frame(40'd1000, 32'd0, 32'd0);
        chk("still no request during settle", req_n == 0);
        chk("gain_idx still unchanged",       gain_idx == GI_INIT);
        chk("state == 1 (settling)",          state == 2'd1);

        //--------------------- CASE 4 : 欠亮 -> 加亮并收敛 -------------------
        $display("[CASE 4] under-exposed -> climb then converge");
        for (i = 0; i < 90; i = i + 1) begin
            do_frame(ls_of_gi(gain_idx), 32'd0, 32'd0);
        end
        $display("        final gain_idx=%0d  luma_sum=%0d  state=%0d  req_n=%0d",
                 gain_idx, ls_of_gi(gain_idx), state, req_n);
        chk("gain_idx climbed",                 gain_idx > GI_INIT);
        chk("converged inside dead-band",       (ls_of_gi(gain_idx) >= (TSUM-DBAND)) &&
                                                (ls_of_gi(gain_idx) <= (TSUM+DBAND)));
        chk("gain_idx in expected range 116..127", (gain_idx >= 7'd116) && (gain_idx <= 7'd127));
        chk("state == 2 (closed loop)",         state == 2'd2);
        chk("meas_luma plausible (65..85)",     (meas_luma >= 8'd65) && (meas_luma <= 8'd85));
        chk("requests were generated",          req_n > 10);

        //--------------------- CASE 5 : 高光护栏优先降档 ---------------------
        $display("[CASE 5] highlight guard overrides (hi_cnt=20 > 200/64=3)");
        gi_before = gain_idx;
        do_frame(TSUM, 32'd0, 32'd0);          // flush：先让上一用例的高光统计过去
        gi_before = gain_idx;
        for (i = 0; i < 4; i = i + 1) begin
            do_frame(TSUM, 32'd20000, 32'd0);  // 亮度在靶心 + 高光超限
            $display("        frame %0d : O_gain_idx=%0d (S_gi=%0d) step=%0d req_n=%0d",
                     i, gain_idx, dut.S_gi, dut.S_step_n, req_n);
        end
        gi_after = gain_idx;
        gi_after = gain_idx;
        $display("        gain_idx %0d -> %0d", gi_before, gi_after);
        chk("index decreased despite in-band brightness", gi_after < gi_before);

        //--------------------- CASE 6 : 暗场景护栏阻止加亮 -------------------
        $display("[CASE 6] low-light guard blocks brightening");
        do_frame(40'd1000000, 32'd0, 32'd300000);   // flush：先让上一用例的高光统计过去
        gi_before = gain_idx;
        for (i = 0; i < 8; i = i + 1) do_frame(40'd1000000, 32'd0, 32'd300000);
        gi_after = gain_idx;
        $display("        gain_idx %0d -> %0d", gi_before, gi_after);
        chk("index NOT increased", gi_after == gi_before);

        //--------------------- CASE 7 : 冻结 ---------------------------------
        $display("[CASE 7] freeze (I_ae_en=0)");
        ae_en = 0; #200;
        gi_before = gain_idx;
        for (i = 0; i < 12; i = i + 1) do_frame(40'd1000, 32'd0, 32'd0);
        gi_after = gain_idx;
        $display("        gain_idx %0d -> %0d  state=%0d", gi_before, gi_after, state);
        chk("index frozen",           gi_after == gi_before);
        chk("analog_gain frozen",     analog_gain == exp_gain_bytes(gi_before));
        chk("state == 3",             state == 2'd3);
        ae_en = 1; #200;

        //--------------------- CASE 8 : 请求脉冲宽度 -------------------------
        $display("[CASE 8] O_ae_req pulse width");
        $display("        total requests=%0d  max pulse width=%0d cycles", req_n, max_pulse);
        chk("every request is exactly 1 cycle wide", (req_stuck == 0) && (max_pulse == 1));

        //--------------------- 汇总 ------------------------------------------
        if (errors == 0) $display("*** ALL PASS, errors=0 ***");
        else             $display("*** FAILED, errors=%0d ***", errors);
        $display("=== tb_ae_ctrl end ===");
        $finish;
    end

    // 防跑飞
    initial begin
        #5_000_000;
        $display("*** TIMEOUT ***");
        $finish;
    end

endmodule
