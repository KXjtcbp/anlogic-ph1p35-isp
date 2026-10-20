//==========================================================================
// tb_div_pattern.v
//   目的：判定 TD 除法器 IP（PH1_LOGIC_SEQ_DIV, level_nu=50, pipline）在
//         不同的 start 占空比下还能不能拉高 done。
//   动机：awb.v 把 start 接成 I_tvalid_r1（一个电平，不是单拍脉冲）。
//         真实 ISP 里 valid 图案是 "1,1,0" 循环（2/3 占空），
//         而历史 TB 用的是 64 拍连续 valid（近乎 100%）。
//         如果 done 在 2/3 占空下不再拉高，AWB 的 in_r_tgt 就永远停在
//         1.000x，白平衡等于没生效 —— 这就是要找的根因。
//   跑法：vsim -c -do "run -all; quit -f" glbl tb_div_pattern
//==========================================================================
`timescale 1ns/1ps

module tb_div_pattern;

    reg         clk = 0;
    reg         rst = 1;
    reg         start;          // 必须在例化之前声明，否则会被当成隐式 wire

    // 被除数 / 除数：故意取一个非平凡的比值 G/R = 1.25
    //   numerator  = sum_g << 16 = 100000 << 16
    //   denominator= sum_r       =  80000
    //   期望 quotient ≈ 1.25 * 65536 = 81920 = 0x14000
    localparam [31:0] DEN = 32'd80000;
    localparam [47:0] NUM = 48'd100000 << 16;

    wire [47:0] quotient;
    wire [31:0] remainder;
    wire        done;

    divider u_div (
        .clk         (clk        ),
        .rst         (rst        ),
        .start       (start      ),
        .denominator (DEN        ),
        .numerator   (NUM        ),
        .done        (done       ),
        .quotient    (quotient   ),
        .remainder   (remainder  )
    );

    //------------------------------------------------------------------------
    // start 图案发生器
    //   MODE 0 : 一直拉高（最宽松）
    //   MODE 1 : 64 拍高 / 20 拍低（历史 TB 的图案）
    //   MODE 2 : 1,1,0 循环（真实 ISP 的 2/3 占空）
    //   MODE 3 : 每 3 拍只有 1 拍高（1/3 占空，最苛刻）
    //------------------------------------------------------------------------
    reg [1:0] mode = 2'd0;
    integer   cyc  = 0;

    always @(*) begin
        case (mode)
            2'd0: start = 1'b1;
            2'd1: start = ((cyc % 84) < 64);
            2'd2: start = ((cyc % 3) != 2);
            default: start = ((cyc % 3) == 0);
        endcase
    end

    // 统计 done 脉冲
    integer donecnt;
    reg     done_d;
    always @(posedge clk) done_d <= done;
    wire    done_pulse = done & ~done_d;

    integer i;
    integer first_done_cyc;

    initial begin
        donecnt        = 0;
        first_done_cyc = -1;
    end

    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (rst) begin
            donecnt        <= 0;
            first_done_cyc <= -1;
        end else if (done_pulse) begin
            donecnt <= donecnt + 1;
            if (first_done_cyc < 0) first_done_cyc <= cyc;
        end
    end

    task run_mode(input [1:0] m, input [8*24-1:0] name);
        begin
            mode = m;
            rst  = 1;
            repeat (5) @(posedge clk);
            rst = 0;
            cyc = 0;
            repeat (4000) @(posedge clk);
            $display("MODE %0d [%0s] : donecnt=%0d  first_done_cyc=%0d  last quotient=0x%h (%0d)  expect 0x14000 (81920)",
                     m, name, donecnt, first_done_cyc, quotient, quotient);
            if (donecnt == 0)
                $display("        *** done NEVER pulsed -> AWB gain would stay 1.000x ***");
            else if (quotient !== 48'h14000)
                $display("        *** done pulsed but quotient WRONG ***");
            else
                $display("        ok");
            mode = 2'd0;
            rst  = 1;
            repeat (5) @(posedge clk);
        end
    endtask

    initial begin
        $display("================================================================");
        $display(" TD divider IP: does done survive a reduced-duty start ?");
        $display("================================================================");
        run_mode(2'd0, "start always high ");
        run_mode(2'd1, "start 64hi/20lo   ");
        run_mode(2'd2, "start 1,1,0 cycle ");
        run_mode(2'd3, "start 1-of-3      ");
        $display("================================================================");
        $display(" *** TB DONE ***");
        $finish;
    end

    always #8.333 clk = ~clk;   // 60 MHz

endmodule
