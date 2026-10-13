//=============================================================================
// tb_div_done_rate.v  (ANALYSIS-ONLY, sibling of tb_awb_live_ratio.v)
//   问题：awb.v 把 divider 的 .start 接成 I_tvalid_r1（一个「电平」而不是单拍脉冲），
//         真实 ISP 的 valid 图案是 1,1,0 循环（2/3 占空）。要判断 AWB 到底是
//         「每个有效像素都拿到一个新比值」还是「每 50 拍才更新一次」，必须先量出
//         门级 divider 的 done 在一个 start 周期里有几个上升沿。
//
//   测法1 EXP0..2：单拍 start 脉冲     -> 量 start 到 done 拉高的精确延迟。
//   测法2 DUTY    ：start = 1,1,0 循环 4000 拍 -> 数 done 高电平拍数与上升沿数。
//=============================================================================
`timescale 1ns/1ps

module tb_div_done_rate;

    reg clk = 0;
    always #8.3335 clk = ~clk;    // 60 MHz

    reg         rst;
    reg         start;
    reg  [31:0] den;
    reg  [47:0] num;
    wire [47:0] quotient;
    wire [31:0] remainder;
    wire        done;

    divider u_div (
        .clk (clk), .rst (rst), .start (start),
        .denominator (den), .numerator (num),
        .done (done), .quotient (quotient), .remainder (remainder)
    );

    integer cyc;
    always @(posedge clk) cyc <= cyc + 1;

    // ---- done 统计（复位清零，测量窗口内累计） -----------------------------
    reg     done_d;
    integer done_hi;
    integer done_rise;
    integer first_done_cyc;
    reg     meas_en = 0;

    always @(posedge clk) begin
        done_d <= done;
        if (rst || !meas_en) begin
            done_hi <= 0; done_rise <= 0; first_done_cyc <= -1;
        end else begin
            if (done) begin
                done_hi <= done_hi + 1;
                if (first_done_cyc < 0) first_done_cyc <= cyc;
            end
            if (done & ~done_d) done_rise <= done_rise + 1;
        end
    end

    integer k;

    initial begin
        rst = 1; start = 0; den = 32'd80; num = 48'd100 << 16; cyc = 0;
        repeat (10) @(posedge clk);
        rst = 0;
        repeat (5)  @(posedge clk);

        $display("================================================================");
        $display(" TD divider (level_nu=50, pipline): done rate vs start pattern");
        $display(" den=80 num=(100<<16)  expect quotient=0x%h (%0d)",
                 (48'd100<<16)/80, (48'd100<<16)/80);
        $display("================================================================");

        //---- 测法1：单拍 start 脉冲 -> 精确延迟 ----------------------------
        for (k = 0; k < 3; k = k + 1) begin
            @(negedge clk); rst = 1; start = 0;
            repeat (5) @(posedge clk);
            rst = 0;
            repeat (3) @(posedge clk);
            cyc = 0;
            meas_en = 1;
            @(negedge clk); start = 1;
            @(negedge clk); start = 0;
            repeat (100) @(posedge clk);
            meas_en = 0;
            @(negedge clk);
            $display("EXP%0d single-cycle pulse : first_done_cyc=%0d  done_hi=%0d  done_rise=%0d  quotient=0x%h (%0d)",
                     k, first_done_cyc, done_hi, done_rise, quotient, quotient);
        end

        //---- 测法2：1,1,0 占空 4000 拍 -------------------------------------
        @(negedge clk); rst = 1; start = 0;
        repeat (5) @(posedge clk);
        rst = 0;
        repeat (3) @(posedge clk);
        cyc = 0;
        meas_en = 1;
        $display("--- driving start as 1,1,0 for 4000 cycles ---");
        for (k = 0; k < 4000; k = k + 1) begin
            @(negedge clk);
            start = ((k % 3) != 2) ? 1'b1 : 1'b0;
        end
        @(negedge clk); start = 0;
        repeat (200) @(posedge clk);
        meas_en = 0;
        @(negedge clk);
        $display("DUTY  1,1,0 for 4000 cycles : done_hi=%0d  done_rise=%0d  (done_hi/4000=%0d%%)  first_done_cyc=%0d  quotient=0x%h (%0d)",
                 done_hi, done_rise, (done_hi*100)/4000, first_done_cyc, quotient, quotient);
        if (done_hi >= 3900)
            $display("   -> VERDICT: done is HIGH ON EVERY CYCLE -> gain register updates on EVERY valid pixel");
        else if (done_hi > 0)
            $display("   -> VERDICT: done pulses only %0d times in 4000 cycles", done_hi);
        else
            $display("   -> VERDICT: done NEVER pulses under 1,1,0 !");

        $display("======== DIV DONE ========");
        $finish;
    end

    initial begin
        #2000000;
        $display("*** TIMEOUT ***");
        $finish;
    end

endmodule
