//=============================================================================
// [HDR-2026-10-12] tb_ae_stat.v —— ae_stat 的 Testbench  v2
// 用法（在 run 目录里）：
//   vlib work
//   vlog <repo>/proj/baseline/lab3/user_source/hdl_source/isp/ae_stat.v tb_ae_stat.v
//   vsim -c -do "run -all; quit -f" tb_ae_stat
//-----------------------------------------------------------------------------
// 帧的建模方式（与真实硬件一致）：
//   send_frame() —— NBEAT 拍，每拍 tvalid=1，第 0 拍 tuser=1（帧首与首个有效拍重合）
//   flush()      —— 1 拍 tuser=1 / tvalid=0，把刚结束的那一帧"发布"到 O_*
//   ⇒ 要看第 N 帧的统计，必须 send_frame(N) 之后再 flush()
//-----------------------------------------------------------------------------
// 覆盖判据：
//   CASE 1 复位后输出全 0
//   CASE 2 恒定色帧 R=200/G=100/B=50：Σ(Y*256) 与 TB 独立公式逐拍累加值完全一致
//   CASE 3 高光帧 R=G=B=255：hi == 全部像素，lo == 0
//   CASE 4 暗部帧 R=G=B=3  ：lo == 全部像素，hi == 0
//   CASE 5 混合帧（4 像素 mx = 255/100/5/100）：hi == NBEAT, lo == NBEAT
//   CASE 6 tgl 在 send_frame 时翻转、flush 时再翻回去
//   CASE 7 tvalid 拉低的那一拍不计入（cnt 少 4、sum 少一份）
// ★踩坑：所有输出采样必须 `@(posedge clk); #1;` —— DUT 用 NBA 更新，
//   只写 @(posedge clk) 会读到上一拍（tb_blc_template.v 上踩过一次）。
//=============================================================================

`timescale 1ns/1ps

module tb_ae_stat;

    localparam integer NBEAT = 64;      // 每帧拍数（不需要是真实的 230400）
    localparam integer NPIX  = NBEAT*4;

    reg         clk = 0;
    reg         rst_n = 0;
    reg         tvalid = 0;
    reg         tuser = 0;
    reg  [95:0] tdata = 96'd0;

    wire [39:0] o_sum;
    wire [31:0] o_cnt;
    wire [31:0] o_hi;
    wire [31:0] o_lo;
    wire        o_tgl;

    integer errors = 0;

    ae_stat #(
        .NOM_PIX   (32'd230400),
        .HI_THRESH (8'd250),
        .LO_THRESH (8'd8)
    ) dut (
        .I_clk       (clk),
        .I_rst_n     (rst_n),
        .I_tvalid    (tvalid),
        .I_tuser     (tuser),
        .I_tdata     (tdata),
        .O_luma_sum  (o_sum),
        .O_pix_cnt   (o_cnt),
        .O_hi_cnt    (o_hi),
        .O_lo_cnt    (o_lo),
        .O_frame_tgl (o_tgl)
    );

    always #8.333 clk = ~clk;           // 约 60 MHz（ISP 域实测 16.668ns）

    //-------------------------------------------------------------------------
    // TB 侧独立参考模型（故意不复用 DUT 的任何函数）
    //-------------------------------------------------------------------------
    function [17:0] ref_beat_luma;      // 4 像素的 Σ(Y*256)，用真正的乘法
        input [7:0] r0, g0, b0, r1, g1, b1, r2, g2, b2, r3, g3, b3;
        begin
            ref_beat_luma = 77*(r0+r1+r2+r3) + 150*(g0+g1+g2+g3) + 29*(b0+b1+b2+b3);
        end
    endfunction

    function [7:0] ref_max3;
        input [7:0] a, b, c;
        reg   [7:0] m;
        begin
            m = (a > b) ? a : b;
            ref_max3 = (m > c) ? m : c;
        end
    endfunction

    function [95:0] pack4;
        input [7:0] r0, g0, b0, r1, g1, b1, r2, g2, b2, r3, g3, b3;
        begin
            pack4 = { r3, g3, b3, r2, g2, b2, r1, g1, b1, r0, g0, b0 };
        end
    endfunction

    //-------------------------------------------------------------------------
    // 发一帧：NBEAT 拍，第 0 拍 tuser=1 & tvalid=1（帧首与首个有效拍重合）
    //   drop_at >= 0 时把那一拍的 tvalid 拉低
    //-------------------------------------------------------------------------
    task send_frame;
        input [95:0] pat;
        input integer drop_at;
        integer i;
        begin
            for (i = 0; i < NBEAT; i = i + 1) begin
                @(negedge clk);
                tdata  = pat;
                tuser  = (i == 0)     ? 1'b1 : 1'b0;
                tvalid = (i == drop_at)? 1'b0 : 1'b1;
                @(posedge clk);
            end
            @(negedge clk);
            tuser = 1'b0; tvalid = 1'b0; tdata = 96'd0;
            @(posedge clk);
        end
    endtask

    // 发布刚结束的那一帧（1 拍 tuser=1 / tvalid=0）
    task flush;
        begin
            @(negedge clk);
            tuser = 1'b1; tvalid = 1'b0; tdata = 96'd0;
            @(posedge clk);
            @(negedge clk);
            tuser = 1'b0;
            @(posedge clk);
        end
    endtask

    //-------------------------------------------------------------------------
    // 一帧的期望值（用 TB 的参考模型算）
    //-------------------------------------------------------------------------
    reg [39:0] e_sum;
    reg [31:0] e_cnt, e_hi, e_lo;
    integer    k;
    reg [7:0]  rr, gg, bb;

    // 对"恒色帧 + 指定丢拍位置"求期望；nhi/nlo 传 1 表示该色 mx>=250 / mx<=8
    task expect_const;
        input [7:0] R, G, B;
        input integer drop_at;
        begin
            e_sum = 40'd0; e_cnt = 32'd0; e_hi = 32'd0; e_lo = 32'd0;
            for (k = 0; k < NBEAT; k = k + 1) begin
                if (k != drop_at) begin
                    e_sum = e_sum + ref_beat_luma(R,G,B, R,G,B, R,G,B, R,G,B);
                    e_cnt = e_cnt + 32'd4;
                    if (ref_max3(R,G,B) >= 250) e_hi = e_hi + 32'd4;
                    if (ref_max3(R,G,B) <=   8) e_lo = e_lo + 32'd4;
                end
            end
        end
    endtask

    task check;
        input [8*24:1] label;
        begin
            @(posedge clk); #1;
            if (o_sum !== e_sum || o_cnt !== e_cnt || o_hi !== e_hi || o_lo !== e_lo) begin
                $display("[%0s] FAIL  sum got=%0d exp=%0d | cnt got=%0d exp=%0d | hi got=%0d exp=%0d | lo got=%0d exp=%0d",
                         label, o_sum, e_sum, o_cnt, e_cnt, o_hi, e_hi, o_lo, e_lo);
                errors = errors + 1;
            end else
                $display("[%0s] ok    sum=%0d cnt=%0d hi=%0d lo=%0d", label, o_sum, o_cnt, o_hi, o_lo);
        end
    endtask

    reg tgl_a, tgl_b;
    localparam [95:0] CONST = { 8'd200,8'd100,8'd50,  8'd200,8'd100,8'd50,  8'd200,8'd100,8'd50,  8'd200,8'd100,8'd50  };
    localparam [95:0] WHITE = { 8'd255,8'd255,8'd255, 8'd255,8'd255,8'd255, 8'd255,8'd255,8'd255, 8'd255,8'd255,8'd255 };
    localparam [95:0] DARK  = { 8'd3,8'd3,8'd3,       8'd3,8'd3,8'd3,       8'd3,8'd3,8'd3,       8'd3,8'd3,8'd3       };
    localparam [95:0] MIXED = { 8'd100,8'd100,8'd100, 8'd5,8'd5,8'd5,       8'd100,8'd100,8'd100, 8'd255,8'd255,8'd255 };

    initial begin
        // ---------------- CASE 1: 复位 ----------------
        rst_n = 0; tvalid = 0; tuser = 0; tdata = 0;
        repeat (5) @(posedge clk); #1;
        if (o_sum !== 40'd0 || o_cnt !== 32'd0 || o_hi !== 32'd0 || o_lo !== 32'd0 || o_tgl !== 1'b0) begin
            $display("[CASE 1 reset] FAIL sum=%0d cnt=%0d hi=%0d lo=%0d tgl=%b", o_sum, o_cnt, o_hi, o_lo, o_tgl);
            errors = errors + 1;
        end else $display("[CASE 1 reset] ok    all zero, tgl=0");
        rst_n = 1;
        repeat (3) @(posedge clk);

        // ---------------- CASE 6a/6b: tgl 每次帧首翻转 ----------------
        tgl_a = o_tgl;
        send_frame(CONST, -1);
        tgl_b = o_tgl;
        if (tgl_b === tgl_a) begin
            $display("[CASE 6a tgl ] FAIL no toggle at frame start: stuck at %b", o_tgl); errors = errors + 1;
        end else $display("[CASE 6a tgl ] ok   frame-start toggle %b -> %b", tgl_a, tgl_b);
        flush();
        if (o_tgl === tgl_b) begin
            $display("[CASE 6b tgl ] FAIL no toggle at flush: stuck at %b", o_tgl); errors = errors + 1;
        end else $display("[CASE 6b tgl ] ok   flush toggle %b -> %b", tgl_b, o_tgl);

        // ---------------- CASE 2: 恒定色帧 ----------------
        send_frame(CONST, -1);
        flush();
        expect_const(200,100,50, -1);
        check("CASE 2 const ");

        // ---------------- CASE 3: 高光帧 ----------------
        send_frame(WHITE, -1);
        flush();
        expect_const(255,255,255, -1);
        check("CASE 3 white ");

        // ---------------- CASE 4: 暗部帧 ----------------
        send_frame(DARK, -1);
        flush();
        expect_const(3,3,3, -1);
        check("CASE 4 dark  ");

        // ---------------- CASE 5: 混合帧（mx = 100 / 5 / 100 / 255）----------------
        send_frame(MIXED, -1);
        flush();
        e_sum = 40'd0; e_cnt = NPIX; e_hi = 0; e_lo = 0;
        for (k = 0; k < NBEAT; k = k + 1) begin
            e_sum = e_sum + ref_beat_luma(255,255,255, 100,100,100, 5,5,5, 100,100,100);
            e_hi  = e_hi + 32'd1;      // 每拍只有 1 个像素的 mx 是 255 (>=250)
            e_lo  = e_lo + 32'd1;      // 每拍只有 1 个像素的 mx 是 5   (<=8)
        end
        check("CASE 5 mixed ");

        // ---------------- CASE 7: 丢一拍 ----------------
        send_frame(CONST, 7);
        flush();
        expect_const(200,100,50, 7);
        check("CASE 7 drop  ");

        // ---------------- 汇总 ----------------
        if (errors == 0) $display("\n  ALL PASS, errors=0");
        else             $display("\n  *** FAILED ***, errors=%0d", errors);
        $finish;
    end

    initial begin
        #2000000;
        $display("*** TIMEOUT ***"); $finish;
    end

endmodule
