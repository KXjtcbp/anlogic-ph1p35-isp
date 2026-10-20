//=============================================================================
// tb_blc.v —— mipi_to_raw_converter.v 黑电平扣除补丁的自测（ModelSim）
//   ASCII-only $display (ModelSim console is GBK; UTF-8 text shows as garbage)
//
// 校验内容：
//   1. 复位行为（O_raw_tdata=0 / O_raw_tvalid=0）；
//   2. bypass=0：逐点与手算锚点比对，另跑 0..1023 全量扫描与 TB 侧独立公式比对
//      —— 公式 (x > 56 ? x-56 : 0) + 2 再取 [9:2]；
//   3. bypass=1：必须等于 x 取 [9:2]（= 2026-10-09 之前的原始截断行为）；
//   4. 四个字段各自独立（4 个互不相同的值，确认位拼接次序 f0->[31:24] ... f3->[7:0]）；
//   5. tlast/tuser/tvalid 与数据同拍延迟 1；
//   6. tready 纯组合直通（I_raw_tready = O_raw_tready）。
//
// 运行：
//   vlog mipi_to_raw_converter.v tb_blc.v
//   vsim -c -do "run -all; quit -f" tb_blc
//=============================================================================
`timescale 1ns/1ns

module tb_blc;

    localparam [9:0] BL = 10'd56;

    reg         clk = 0, rst_n = 0;
    reg         bp = 0;
    reg  [39:0] d = 0;
    reg         tl = 0, tu = 0, tv = 0;
    wire [31:0] o_d;
    wire        o_tl, o_tu, o_tv, i_tr;
    reg         o_tr = 1;

    integer errors = 0;
    integer x, bad, e;

    always #5 clk = ~clk;      // 100 MHz

    mipi_to_raw_converter u_dut (
        .I_clk         (clk  ),
        .I_rst_n       (rst_n),
        .I_blk_bypass  (bp   ),
        .I_raw_tdata   (d    ),
        .I_raw_tdest   (10'd0),
        .I_raw_tlast   (tl   ),
        .I_raw_tvalid  (tv   ),
        .I_raw_tuser   (tu   ),
        .I_raw_tready  (i_tr ),
        .O_raw_tdata   (o_d  ),
        .O_raw_tlast   (o_tl ),
        .O_raw_tvalid  (o_tv ),
        .O_raw_tuser   (o_tu ),
        .O_raw_tready  (o_tr )
    );

    // TB 侧独立公式（与 RTL 分开写，互相印证）
    function [7:0] exp_blk;
        input [9:0] v;
        integer t;
        begin
            t = (v > BL) ? (v - BL) : 0;
            exp_blk = (t + 2) >> 2;
        end
    endfunction
    function [7:0] exp_raw;
        input [9:0] v;
        begin
            exp_raw = v >> 2;
        end
    endfunction
    function [31:0] pack4;
        input [9:0] f0, f1, f2, f3;
        reg [7:0] b0, b1, b2, b3;
        begin
            b0 = exp_blk(f0); b1 = exp_blk(f1); b2 = exp_blk(f2); b3 = exp_blk(f3);
            pack4 = {b0, b1, b2, b3};
        end
    endfunction

    // 送 1 拍，返回时输出已更新（1 拍延迟）
    task beat;
        input [39:0] dd;
        input        tl_i, tu_i;
        begin
            @(negedge clk);
            d = dd; tv = 1'b1; tl = tl_i; tu = tu_i;
            @(posedge clk); #1;         // 输出寄存器已更新
        end
    endtask

    initial begin
        //---- reset ----
        rst_n = 0; tv = 0; bp = 0;
        repeat (4) @(negedge clk);
        #1;
        if (o_d !== 32'd0 || o_tv !== 1'b0 || o_tl !== 1'b0 || o_tu !== 1'b0) begin
            $display("** FAIL reset: o_d=%08h o_tv=%b o_tl=%b o_tu=%b", o_d, o_tv, o_tl, o_tu);
            errors = errors + 1;
        end else
            $display("RESET OK: O_raw_tdata=0, O_raw_tvalid=0");
        rst_n = 1;
        repeat (2) @(negedge clk);

        //==== CASE 1: hand-computed anchors, bypass = 0 ====
        $display("---- CASE1 anchors (x -> out, hand-computed) ----");
        for (x = 0; x < 16; x = x + 1) begin
            case (x)
                0:  begin e = 10'd0;    beat({10'd0,10'd0,10'd0,10'd0},  1'b0,1'b0); end
                1:  begin e = 10'd1;    beat({10'd1,10'd1,10'd1,10'd1},  1'b0,1'b0); end
                2:  begin e = 10'd56;   beat({10'd56,10'd56,10'd56,10'd56}, 1'b0,1'b0); end
                3:  begin e = 10'd57;   beat({10'd57,10'd57,10'd57,10'd57}, 1'b0,1'b0); end
                4:  begin e = 10'd58;   beat({10'd58,10'd58,10'd58,10'd58}, 1'b0,1'b0); end
                5:  begin e = 10'd61;   beat({10'd61,10'd61,10'd61,10'd61}, 1'b0,1'b0); end
                6:  begin e = 10'd62;   beat({10'd62,10'd62,10'd62,10'd62}, 1'b0,1'b0); end
                7:  begin e = 10'd66;   beat({10'd66,10'd66,10'd66,10'd66}, 1'b0,1'b0); end
                8:  begin e = 10'd68;   beat({10'd68,10'd68,10'd68,10'd68}, 1'b0,1'b0); end
                9:  begin e = 10'd69;   beat({10'd69,10'd69,10'd69,10'd69}, 1'b0,1'b0); end
                10: begin e = 10'd70;   beat({10'd70,10'd70,10'd70,10'd70}, 1'b0,1'b0); end
                11: begin e = 10'd1000; beat({10'd1000,10'd1000,10'd1000,10'd1000}, 1'b0,1'b0); end
                12: begin e = 10'd1023; beat({10'd1023,10'd1023,10'd1023,10'd1023}, 1'b0,1'b0); end
                13: begin e = 10'd255;  beat({10'd255,10'd255,10'd255,10'd255}, 1'b0,1'b0); end
                14: begin e = 10'd63;   beat({10'd63,10'd63,10'd63,10'd63}, 1'b0,1'b0); end
                default: begin e = 10'd64; beat({10'd64,10'd64,10'd64,10'd64}, 1'b0,1'b0); end
            endcase
            $display("   %4d -> %3d (expect %3d)", e, o_d[7:0], exp_blk(e));
            if (o_d[7:0] !== exp_blk(e) || o_d[31:24] !== exp_blk(e) ||
                o_d[23:16] !== exp_blk(e) || o_d[15:8] !== exp_blk(e)) begin
                $display("** FAIL case1 x=%0d: O=%08h expect four bytes %02h", e, o_d, exp_blk(e));
                errors = errors + 1;
            end
        end
        $display("CASE1: %0d anchors checked", 16);
        // 单独点出几个关键值的实算值，便于人工核对
        $display("   hand-check: 57->0  58->1  62->2  66->3  70->4  1023->242(was x>>2=255)");

        //==== CASE 2: full 0..1023 sweep, all four fields ====
        bad = 0;
        bp = 1'b0;
        for (x = 0; x < 1024; x = x + 1) begin
            beat({x[9:0], x[9:0], x[9:0], x[9:0]}, 1'b0, 1'b0);
            if (o_d !== {exp_blk(x[9:0]),exp_blk(x[9:0]),exp_blk(x[9:0]),exp_blk(x[9:0])}) begin
                if (bad < 5) $display("** FAIL case2 x=%0d: O=%08h", x, o_d);
                bad = bad + 1;
            end
        end
        if (bad == 0) $display("CASE2 PASS: full sweep 0..1023 x 4 fields (4096 values) = (x-56+2)>>2 clamped at 0");
        else begin $display("** FAIL case2: %0d bad", bad); errors = errors + bad; end

        //==== CASE 3: bypass = 1 must reproduce pre-2026-10-09 truncation ====
        bad = 0;
        bp = 1'b1;
        for (x = 0; x < 1024; x = x + 1) begin
            beat({x[9:0], x[9:0], x[9:0], x[9:0]}, 1'b0, 1'b0);
            if (o_d !== {exp_raw(x[9:0]),exp_raw(x[9:0]),exp_raw(x[9:0]),exp_raw(x[9:0])}) begin
                if (bad < 5) $display("** FAIL case3 x=%0d: O=%08h", x, o_d);
                bad = bad + 1;
            end
        end
        if (bad == 0) $display("CASE3 PASS: bypass=1 => x>>2 exactly (old behaviour restored, e.g. 57->14, 1023->255)");
        else begin $display("** FAIL case3: %0d bad", bad); errors = errors + bad; end
        bp = 1'b0;

        //==== CASE 4: four independent fields, packing order ====
        beat({10'd1023, 10'd100, 10'd64, 10'd58}, 1'b0, 1'b0);
        if (o_d !== pack4(10'd58, 10'd64, 10'd100, 10'd1023)) begin
            $display("** FAIL case4: O=%08h expect %08h", o_d, pack4(10'd58,10'd64,10'd100,10'd1023));
            errors = errors + 1;
        end else
            $display("CASE4 PASS: f0->[31:24] f1->[23:16] f2->[15:8] f3->[7:0], independent; O=%08h", o_d);
        $display("   (1023,100,64,58) -> %02h %02h %02h %02h", o_d[31:24], o_d[23:16], o_d[15:8], o_d[7:0]);

        //==== CASE 5: flow control delay 1 + tready combinational ====
        //   驱动瞬间（还没到 posedge）输出必须保持旧值 => 证明没有组合直通；
        //   下一个 posedge 之后必须跟随 => 证明正好延迟 1 拍。
        //   先清空流控寄存器，避免读到上一个 beat 残留的 valid=1
        @(negedge clk); tv = 1'b0; tl = 1'b0; tu = 1'b0;
        @(posedge clk); #1;
        if (o_tv !== 1'b0 || o_tl !== 1'b0 || o_tu !== 1'b0) begin
            $display("** FAIL case5: flow registers did not clear (o_tv=%b o_tl=%b o_tu=%b)", o_tv, o_tl, o_tu);
            errors = errors + 1;
        end
        @(negedge clk); d = {10'd300,10'd300,10'd300,10'd300}; tv = 1'b1; tl = 1'b1; tu = 1'b1;
        #1;                       // 同一时刻、任何 posedge 之前
        if (o_tv !== 1'b0 || o_tl !== 1'b0 || o_tu !== 1'b0) begin
            $display("** FAIL case5a: flow signals changed combinationally (o_tv=%b o_tl=%b o_tu=%b)",
                     o_tv, o_tl, o_tu);
            errors = errors + 1;
        end
        @(posedge clk); #1;       // 1 拍之后
        if (o_tv !== 1'b1 || o_tl !== 1'b1 || o_tu !== 1'b1) begin
            $display("** FAIL case5a: flow signals o_tv=%b o_tl=%b o_tu=%b (expect 1/1/1 after 1 cycle)",
                     o_tv, o_tl, o_tu);
            errors = errors + 1;
        end else
            $display("CASE5a PASS: tlast/tuser/tvalid registered, exactly 1 cycle behind data");
        @(negedge clk); tv = 1'b0; tl = 1'b0; tu = 1'b0;
        o_tr = 1'b0; #1;
        if (i_tr !== 1'b0) begin
            $display("** FAIL case5b: I_raw_tready=%b didn't follow O_raw_tready=0", i_tr);
            errors = errors + 1;
        end else
            $display("CASE5b PASS: I_raw_tready = O_raw_tready (pure combinational passthrough)");
        o_tr = 1'b1;

        //==== summary ====
        $display("\n==== RESULT: errors=%0d ====", errors);
        if (errors == 0) $display("TEST PASSED");
        else             $display("TEST FAILED");
        $finish;
    end

endmodule
