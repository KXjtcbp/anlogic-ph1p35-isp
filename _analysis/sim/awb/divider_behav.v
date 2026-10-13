//=============================================================================
// divider_behav.v  --  FALLBACK ONLY
//   Behavioural stand-in for the Anlogic divider IP (divider.ipc:
//   numer_width=48, denom_width=32, level_nu=50, model_select=pipline
//   == fully pipelined, result every clock after LATENCY cycles).
//
//   Port list and parameter list are identical to divider_gate.v:
//     clk, rst(active-high), start, denominator[31:0], numerator[47:0],
//     quotient[47:0], done, remainder[31:0]
//     parameters PIPLE=50, S_DEN, S_NUM, W_DEN, W_NUM, W_REM
//
//   本文件只在 divider_gate.v 门级网表跑不动时才编入。若编入，报告中必须
//   明确声明「divider 是行为级替换」。
//=============================================================================
`timescale 1ns/1ps

module divider
  (
  input  wire        clk,
  input  wire [31:0] denominator,
  input  wire [47:0] numerator,
  input  wire        rst,
  input  wire        start,
  output wire        done,
  output wire [47:0] quotient,
  output wire [31:0] remainder
  );

  parameter PIPLE = 50;
  parameter S_DEN = "UNSIGNED";
  parameter S_NUM = "UNSIGNED";
  parameter W_DEN = 32;
  parameter W_NUM = 48;
  parameter W_REM = 32;

  localparam LAT = PIPLE;          // 50

  reg [47:0] q_s [0:63];
  reg [31:0] r_s [0:63];
  reg        v_s [0:63];

  integer i;

  // 组合除法：quotient = numerator / denominator（无符号），remainder = 余数
  reg [79:0] q_full;
  always @* begin
    if (denominator == 0) begin
      q_full = 80'h0;
    end else begin
      q_full = {32'd0, numerator} / {48'd0, denominator};
    end
  end

  always @(posedge clk) begin
    if (rst) begin
      for (i = 0; i < 64; i = i + 1) begin
        q_s[i] <= 48'd0;
        r_s[i] <= 32'd0;
        v_s[i] <= 1'b0;
      end
    end
    else begin
      q_s[0] <= q_full[47:0];
      r_s[0] <= numerator % (denominator == 0 ? 32'd1 : denominator);
      v_s[0] <= start;
      for (i = 1; i < 64; i = i + 1) begin
        q_s[i] <= q_s[i-1];
        r_s[i] <= r_s[i-1];
        v_s[i] <= v_s[i-1];
      end
    end
  end

  assign done      = (LAT < 64) ? v_s[LAT] : 1'b0;
  assign quotient  = (LAT < 64) ? q_s[LAT] : 48'd0;
  assign remainder = (LAT < 64) ? r_s[LAT] : 32'd0;

endmodule
