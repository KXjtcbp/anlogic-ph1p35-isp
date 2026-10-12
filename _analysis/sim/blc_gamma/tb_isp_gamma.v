//=============================================================================
// tb_isp_gamma.v —— isp_gamma.v 的功能自测（ModelSim）
//   ★所有 $display 一律用 ASCII，避免 ModelSim 控制台按 GBK 解码 UTF-8 变乱码
//
// 覆盖 5 件事：
//   1. 延迟必须是 2 拍（第 1 拍绝不能出数据、第 2 拍必须出）；
//   2. 全表比对：0..255 每个码值送 12 路同值字节，在第 2 拍比对 12 路输出
//      —— 与从 gamma_lut_p118_k125.hex 读出的黄金表逐点比对（256×12 = 3072 字节）；
//   3. 锚点抽查 + tlast/tuser 必须与数据同拍跟随；
//   4. 12 路独立查表（12 个互不相同的字节，检查位序/通道没有串位）；
//   5. 旁路：I_gamma_bypass=1 时 O_tdata 必须与 I_tdata 逐位相同（延迟仍 2 拍）。
//
// 运行（工作目录里必须有 gamma_lut_p118_k125.hex）：
//   vlib work
//   vlog isp_gamma.v tb_isp_gamma.v
//   vsim -c -do "run -all; quit -f" tb_isp_gamma
//=============================================================================
`timescale 1ns/1ns

module tb_isp_gamma;

    reg         clk = 0;
    reg         rst_n = 0;
    reg         i_tlast = 0, i_tuser = 0, i_tvalid = 0, i_bypass = 0;
    reg  [95:0] i_tdata = 0;
    wire [95:0] o_tdata;
    wire        o_tlast, o_tuser, o_tvalid, i_tready;
    reg         o_tready = 1;
    reg  [95:0] d_hold = 0;      // 保存当前 beat，供第 2 拍比对

    integer errors = 0;
    integer a, bad;

    reg [7:0]  gold [0:255];
    reg [95:0] expect96;
    reg [7:0]  g;

    always #5 clk = ~clk;      // 100 MHz

    isp_gamma u_dut (
        .I_clk          (clk      ),
        .I_rst_n        (rst_n    ),
        .I_tlast        (i_tlast  ),
        .I_tuser        (i_tuser  ),
        .I_tdata        (i_tdata  ),
        .I_tvalid       (i_tvalid ),
        .I_tready       (i_tready ),
        .I_gamma_bypass (i_bypass ),
        .O_tdata        (o_tdata  ),
        .O_tlast        (o_tlast  ),
        .O_tuser        (o_tuser  ),
        .O_tvalid       (o_tvalid ),
        .O_tready       (o_tready )
    );

    //---- 送 1 个 beat，返回时正好是「数据应出现在 O_tdata 上」的那一拍 ----
    //   时序：t=N 驱动 → posedge(N+1) 第1级采样 → posedge(N+2) 第2级输出
    //         任务在 t=N+2 返回（此时 O_tvalid=1、O_tdata=查表结果）
    task send_beat;
        input [95:0] d;
        input        tl, tu;
        begin
            @(negedge clk);          // t = N
            i_tdata  = d;
            i_tvalid = 1'b1;
            i_tlast  = tl;
            i_tuser  = tu;
            @(negedge clk);          // t = N+1
            i_tvalid = 1'b0;
            i_tlast  = 1'b0;
            i_tuser  = 1'b0;
            @(negedge clk);          // t = N+2  ← 输出有效拍
        end
    endtask

    function [95:0] same12;
        input [7:0] b;
        begin
            same12 = {b,b,b,b,b,b,b,b,b,b,b,b};
        end
    endfunction

    initial begin
        $readmemh("gamma_lut_p118_k125.hex", gold);
        $display("==== table load check: gold[0]=%02h gold[16]=%02h gold[64]=%02h gold[118]=%02h gold[200]=%02h gold[255]=%02h",
                 gold[0], gold[16], gold[64], gold[118], gold[200], gold[255]);
        if (gold[16] !== 8'h0a || gold[64] !== 8'h37 || gold[118] !== 8'h76 ||
            gold[200] !== 8'hd3 || gold[255] !== 8'hff) begin
            $display("** FAIL: golden table not loaded (gamma_lut_p118_k125.hex missing in work dir?)");
            errors = errors + 1;
        end

        //---- reset ----
        rst_n = 0;
        repeat (4) @(negedge clk);
        rst_n = 1;
        repeat (2) @(negedge clk);
        if (o_tvalid !== 1'b0) begin
            $display("** FAIL: O_tvalid should be 0 after reset, got %b", o_tvalid);
            errors = errors + 1;
        end

        //==== CASE 1: latency must be exactly 2 cycles ====
        @(negedge clk);                       // t = N
        i_tdata  = 96'h0000_0000_0000_0000_0001;
        i_tvalid = 1'b1;
        @(negedge clk);                       // t = N+1
        if (o_tvalid !== 1'b0) begin
            $display("** FAIL case1: O_tvalid high at cycle 1 (latency must be 2)");
            errors = errors + 1;
        end
        i_tvalid = 1'b0;
        @(negedge clk);                       // t = N+2
        if (o_tvalid !== 1'b1) begin
            $display("** FAIL case1: O_tvalid low at cycle 2");
            errors = errors + 1;
        end else if (o_tdata[7:0] !== gold[8'h01]) begin
            $display("** FAIL case1: O_tdata[7:0]=%02h expect %02h", o_tdata[7:0], gold[8'h01]);
            errors = errors + 1;
        end else
            $display("CASE1 PASS: fixed latency = 2 cycles, data=%02h", o_tdata[7:0]);
        repeat (2) @(negedge clk);

        //==== CASE 2: full table sweep, 256 x 12 bytes ====
        bad = 0;
        for (a = 0; a < 256; a = a + 1) begin
            g = gold[a];
            expect96 = {g,g,g,g,g,g,g,g,g,g,g,g};
            send_beat(same12(a[7:0]), 1'b0, 1'b0);
            if (o_tvalid !== 1'b1) begin
                if (bad < 5) $display("** FAIL case2 a=%0d: O_tvalid low", a);
                bad = bad + 1;
            end
            else if (o_tdata !== expect96) begin
                if (bad < 5) $display("** FAIL case2 a=%0d: O=%024h E=%024h", a, o_tdata, expect96);
                bad = bad + 1;
            end
        end
        if (bad == 0)
            $display("CASE2 PASS: full table 256 x 12 = 3072 bytes all match golden table");
        else begin
            $display("** FAIL case2: %0d mismatches", bad);
            errors = errors + bad;
        end

        //==== CASE 3: anchors + tlast/tuser follow ====
        $display("---- CASE3 anchors (in -> out, expect) ----");
        bad = 0;
        for (a = 0; a < 11; a = a + 1) begin
            case (a)
                0: g = 8'd0;   1: g = 8'd16;  2: g = 8'd32;  3: g = 8'd64;
                4: g = 8'd96;  5: g = 8'd118; 6: g = 8'd128; 7: g = 8'd160;
                8: g = 8'd200; 9: g = 8'd224; default: g = 8'd255;
            endcase
            send_beat(same12(g), 1'b1, 1'b1);
            $display("   %3d -> %3d (expect %3d)  o_tlast=%b o_tuser=%b",
                     g, o_tdata[7:0], gold[g], o_tlast, o_tuser);
            if (o_tdata[7:0] !== gold[g]) begin
                $display("** FAIL case3 anchor %0d value", g);
                bad = bad + 1;
            end
            if (o_tlast !== 1'b1 || o_tuser !== 1'b1) begin
                $display("** FAIL case3 anchor %0d: tlast/tuser did not follow at same cycle", g);
                bad = bad + 1;
            end
        end
        if (bad == 0) $display("CASE3 PASS: 11 anchors + tlast/tuser aligned");
        else begin errors = errors + bad; end

        //==== CASE 4: 12 independent lanes (byte order / channel crossing) ====
        expect96 = {gold[8'hb0],gold[8'ha0],gold[8'h90],gold[8'h80],gold[8'h70],gold[8'h60],
                    gold[8'h50],gold[8'h40],gold[8'h30],gold[8'h20],gold[8'h10],gold[8'h00]};
        send_beat({8'hb0,8'ha0,8'h90,8'h80,8'h70,8'h60,
                   8'h50,8'h40,8'h30,8'h20,8'h10,8'h00}, 1'b0, 1'b0);
        if (o_tdata !== expect96) begin
            $display("** FAIL case4: O=%024h E=%024h", o_tdata, expect96);
            errors = errors + 1;
        end else
            $display("CASE4 PASS: 12 different bytes mapped independently, bit order correct");

        //==== CASE 5: bypass ====
        d_hold = 96'h0123_4567_89ab_cdef_0011_2233;
        i_bypass = 1'b0;
        send_beat(d_hold, 1'b0, 1'b0);
        $display("   bypass=0: O_tdata=%024h (changed by table)", o_tdata);
        if (o_tdata === d_hold) begin
            $display("** WARN case5: bypass=0 left data unchanged (unexpected)");
        end
        i_bypass = 1'b1;
        send_beat(d_hold, 1'b0, 1'b0);
        if (o_tdata !== d_hold) begin
            $display("** FAIL case5: bypass=1 O=%024h expect %024h", o_tdata, d_hold);
            errors = errors + 1;
        end else
            $display("CASE5 PASS: bypass=1 passes data through (still 2 cycles latency), O=%024h", o_tdata);
        i_bypass = 1'b0;
        send_beat(96'd0, 1'b0, 1'b0);

        //==== summary ====
        $display("\n==== RESULT: errors=%0d ====", errors);
        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED");
        $finish;
    end

endmodule
