//=============================================================================
// tb_awb_zones.v -- does the stock AWB normalise the FRAME mean when the
//                   frame contains more than one colour zone?
//
// Hypothesis under test
//   awb.v accumulates sum_r/sum_g/sum_b from I_tuser to the end of frame and
//   updates gain on every `done` pulse.  That means the gain applied to line N
//   is derived from lines 0..N only -- a RUNNING (non-stationary) gain.
//   A running gain cannot in general normalise the frame MEAN.
//
// Stimulus (W=256, H=8, 64 beats/line)
//   mode 0 : uniform  R=60  G=100 B=100           (R/G = 0.600)
//   mode 1 : SPLIT    lines 0..3 R=60, lines 4..7 R=140
//                     frame input mean R/G = 1.000 -> a correct frame-latched
//                     gray-world AWB must output frame mean R/G = 1.000
//   mode 2 : uniform  R=140 G=100 B=100           (R/G = 1.400)
//
// Verdict
//   mode 1 output R/G ~ 1.00  -> AWB frame-normalises; running gain harmless
//   mode 1 output R/G >  1.05 -> AWB does NOT frame-normalise; running gain is
//                                the real cause of the residual colour cast
//=============================================================================
`timescale 1ns/1ps

module tb_awb_zones;

  localparam W      = 256;
  localparam H      = 8;
  localparam BPL    = W/4;              // 64 beats per line
  localparam NFRAME = 2;                // per mode

  reg clk = 0;
  always #8.3335 clk = ~clk;            // ~60 MHz

  reg         rst_n  = 0;
  reg         tuser  = 0;
  reg         tlast  = 0;
  reg         tvalid = 0;
  reg  [95:0] tdata  = 0;
  wire        tready;
  wire        o_tlast, o_tuser, o_tvalid;
  wire [95:0] o_tdata;
  reg         o_tready = 1;

  awb #(.IMG_HEIGHT(H), .IMG_WIDTH(W)) dut (
      .I_clk (clk), .I_rst_n(rst_n), .I_tlast(tlast), .I_tuser(tuser),
      .I_tdata(tdata), .I_tvalid(tvalid), .I_tready(tready),
      .O_tlast(o_tlast), .O_tuser(o_tuser), .O_tdata(o_tdata),
      .O_tvalid(o_tvalid), .O_tready(o_tready)
  );

  integer inR, inG, inB;
  integer ouR, ouG, ouB, nout;
  integer j;

  always @(posedge clk) if (tvalid) begin
    for (j = 0; j < 4; j = j + 1) begin
      inR = inR + tdata[24*j+16 +: 8];
      inG = inG + tdata[24*j+ 8 +: 8];
      inB = inB + tdata[24*j    +: 8];
    end
  end

  always @(posedge clk) if (o_tvalid) begin
    for (j = 0; j < 4; j = j + 1) begin
      ouR = ouR + o_tdata[24*j+16 +: 8];
      ouG = ouG + o_tdata[24*j+ 8 +: 8];
      ouB = ouB + o_tdata[24*j    +: 8];
    end
    nout = nout + 4;
  end

  // per-line output accumulation, segmented by o_tlast
  integer lR, lG, lB, ln;
  integer li;                           // current output line index
  reg [31:0] lineR [0:15];
  reg [31:0] lineG [0:15];

  always @(posedge clk) if (o_tvalid) begin
    for (j = 0; j < 4; j = j + 1) begin
      if (li < 16) begin
        lineR[li] = lineR[li] + o_tdata[24*j+16 +: 8];
        lineG[li] = lineG[li] + o_tdata[24*j+ 8 +: 8];
      end
    end
  end

  always @(posedge clk) if (o_tvalid && o_tlast) li = li + 1;
  always @(posedge clk) if (o_tvalid && o_tuser) begin
    for (j = 0; j < 16; j = j + 1) begin lineR[j] = 0; lineG[j] = 0; end
    li = 0;
  end

  // pixel word = {R[23:16], G[15:8], B[7:0]}; 4 pixels per 96-bit beat.
  // NOTE: the first attempt packed it as {8'h00, r, 8'h64} which put the varying
  // value in the GREEN slot and left R == 0 -- the whole R-channel test was
  // vacuous (inR = 0, gainR saturated at 0xfffff). Fixed to {r, 8'h64, 8'h64}.
  function [95:0] mkline;
    input [7:0] r;
    begin
      mkline = {r, 8'h64, 8'h64, r, 8'h64, 8'h64, r, 8'h64, 8'h64, r, 8'h64, 8'h64};
    end
  endfunction

  integer mode, f, i;
  reg [7:0] rr;

  initial begin
    for (j = 0; j < 16; j = j + 1) begin lineR[j] = 0; lineG[j] = 0; end
    inR=0; inG=0; inB=0; ouR=0; ouG=0; ouB=0; nout=0; li=0;

    rst_n = 0;
    repeat (10) @(negedge clk);
    rst_n = 1;
    repeat (5)  @(negedge clk);

    for (mode = 0; mode < 3; mode = mode + 1) begin
      // fresh reset per mode so accumulators/gains cannot carry over
      rst_n = 0;
      repeat (10) @(negedge clk);
      rst_n = 1;
      repeat (20) @(negedge clk);

      $display("");
      $display("================ MODE %0d ================", mode);
      if (mode == 1) $display("  split frame: lines 0-3 R=60, lines 4-7 R=140; frame mean R/G = 1.000");
      if (mode == 0) $display("  uniform R=100 G=100 B=100 (R/G = 1.000)  <- control");
      if (mode == 2) $display("  uniform R=60  G=100 B=100 (R/G = 0.600)");

      for (f = 0; f < NFRAME; f = f + 1) begin
        inR=0; inG=0; inB=0; ouR=0; ouG=0; ouB=0; nout=0;

        for (i = 0; i < H; i = i + 1) begin
          repeat (60) @(negedge clk);
          if (mode == 1) rr = (i < 4) ? 8'd60 : 8'd140;
          else if (mode == 0) rr = 8'd100;   // R=G=B=100 -> R/G = 1.000 (control)
          else rr = 8'd60;
          tdata  = mkline(rr);
          tvalid = 1;
          tuser  = (i == 0);
          tlast  = 0;
          repeat (BPL-1) @(negedge clk);
          tlast  = 1;
          @(negedge clk);
          tlast  = 0;
          tvalid = 0;
          tuser  = 0;
        end
        repeat (200) @(negedge clk);

        $display("--- mode %0d frame %0d ---", mode, f);
        $display("  in : R/G=%.4f B/G=%.4f  (inR=%0d inG=%0d inB=%0d)", inR*1.0/inG, inB*1.0/inG, inR, inG, inB);
        if (nout > 0) begin
          $display("  out: R/G=%.4f B/G=%.4f  (ouR=%0d ouG=%0d ouB=%0d n=%0d) gainR=%h gainB=%h",
                   ouR*1.0/ouG, ouB*1.0/ouG, ouR, ouG, ouB, nout, dut.in_r_r1, dut.in_b_r1);
          $display("  per-output-line R/G:");
          for (j = 0; j < 8; j = j + 1)
            if (lineG[j] > 0)
              $display("     line %0d : R/G=%.4f", j, lineR[j]*1.0/lineG[j]);
        end else $display("  out: NO DATA");
      end
    end

    $display("");
    $display("======== VERDICT ========");
    $display("  mode 1 (split, frame input R/G = 1.000) output R/G printed above.");
    $display("  A correct frame-normalising gray-world AWB gives 1.0000.");
    $display("  If it is clearly > 1.05 the gain is a RUNNING per-line gain and the");
    $display("  frame mean is NOT normalised -> that is a real (fixable) colour cast.");
    $finish;
  end

  initial begin
    #40000000;
    $display("*** TIMEOUT ***");
    $finish;
  end

endmodule
