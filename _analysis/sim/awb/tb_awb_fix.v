//=============================================================================
// tb_awb_fix.v -- regression for the [HDR-2026-10-11f] AWB gain change
//
//   stock  : gain updated on every `done` pulse and reset on I_tuser
//            => RUNNING per-line gain, frame mean NOT normalised, line 0 wrong
//   patched: target gain tracked every `done` (clamped), applied gain updated
//            ONCE per frame on the tuser RISING EDGE, with damping
//
// Stimulus (W=256, H=8, 64 beats/line -- W must exceed signal_delay's 50-tap
//           per-line delay, otherwise rd_valid never asserts and there is no output)
//   MODE 0 : uniform R=G=B=100                              frame R/G = 1.0000
//   MODE 1 : split, lines 0..3 R=60, lines 4..7 R=140, G=B=100
//            -> frame INPUT mean R/G = 1.0000.  A frame-normalising AWB must
//               give output frame mean R/G = 1.0000.  Stock gave 1.3396 (+34%).
//               This is the decisive test and it does not depend on the divider
//               settling, because the correct target gain equals the reset value.
//   MODE 2 : uniform R=60 G=100 B=100 (R/G = 0.6), 12 frames, to watch the
//            damped gain ramp monotonically toward 1.6667
//=============================================================================
`timescale 1ns/1ps

module tb_awb_fix;

  localparam W     = 256;
  localparam H     = 8;
  localparam BPL   = W/4;      // 64 beats per line
  localparam BIDLE = 20;       // idle beats between lines (lets the divider settle)

  reg clk = 0;
  always #8.3335 clk = ~clk;   // ~60 MHz, same as the ISP domain

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

  integer inR, inG, inB, ouR, ouG, ouB, nout, j;

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

  // per-output-line accumulation (segmented by o_tlast / o_tuser)
  integer li;
  reg [31:0] lineR [0:15];
  reg [31:0] lineG [0:15];

  always @(posedge clk) if (o_tvalid) begin
    for (j = 0; j < 4; j = j + 1)
      if (li < 16) begin
        lineR[li] = lineR[li] + o_tdata[24*j+16 +: 8];
        lineG[li] = lineG[li] + o_tdata[24*j+ 8 +: 8];
      end
  end

  always @(posedge clk) if (o_tvalid && o_tlast) li = li + 1;
  always @(posedge clk) if (o_tvalid && o_tuser) begin
    for (j = 0; j < 16; j = j + 1) begin lineR[j] = 0; lineG[j] = 0; end
    li = 0;
  end

  // 96-bit beat = 4 pixels of {R[23:16], G[15:8], B[7:0]}
  function [95:0] mkword;
    input [7:0] r;
    begin
      mkword = {r, 8'h64, 8'h64, r, 8'h64, 8'h64, r, 8'h64, 8'h64, r, 8'h64, 8'h64};
    end
  endfunction

  integer mode, f, i, nf;
  reg [7:0] rr;

  initial begin
    for (j = 0; j < 16; j = j + 1) begin lineR[j] = 0; lineG[j] = 0; end
    inR=0; inG=0; inB=0; ouR=0; ouG=0; ouB=0; nout=0; li=0;

    rst_n = 0;
    repeat (10) @(negedge clk);
    rst_n = 1;
    repeat (5)  @(negedge clk);

    for (mode = 0; mode < 3; mode = mode + 1) begin
      nf = (mode == 2) ? 12 : 2;
      rst_n = 0;
      repeat (10) @(negedge clk);
      rst_n = 1;
      repeat (20) @(negedge clk);

      $display("");
      $display("======== MODE %0d ========", mode);
      if (mode == 0) $display("  control : uniform R=G=B=100            frame R/G = 1.0000");
      if (mode == 1) $display("  DECISIVE: lines0-3 R=60 / lines4-7 R=140 (G=B=100)  frame R/G = 1.0000");
      if (mode == 2) $display("  ramp    : uniform R=60 G=100 B=100      frame R/G = 0.6000, want gainR -> 1.6667");

      for (f = 0; f < nf; f = f + 1) begin
        inR=0; inG=0; inB=0; ouR=0; ouG=0; ouB=0; nout=0;

        for (i = 0; i < H; i = i + 1) begin
          if      (mode == 1) rr = (i < 4) ? 8'd60 : 8'd140;
          else if (mode == 0) rr = 8'd100;
          else                rr = 8'd60;

          tdata  = mkword(rr);
          tvalid = 1;
          tuser  = (i == 0);
          tlast  = 0;
          @(negedge clk);
          tuser  = 0;
          repeat (BPL - 2) @(negedge clk);
          tlast  = 1;
          @(negedge clk);
          tlast  = 0;
          tvalid = 0;
          repeat (BIDLE) @(negedge clk);
        end
        repeat (40) @(negedge clk);

        $display("--- mode %0d frame %0d : in R/G=%.4f B/G=%.4f | out R/G=%.4f B/G=%.4f n=%0d gainR=%h gainB=%h",
                 mode, f, inR*1.0/inG, inB*1.0/inG,
                 (ouG>0) ? ouR*1.0/ouG : 0.0, (ouG>0) ? ouB*1.0/ouG : 0.0,
                 nout, dut.in_r_r1, dut.in_b_r1);

        if (mode == 1) begin
          $display("      per-output-line R/G:");
          for (j = 0; j < 8; j = j + 1)
            if (lineG[j] > 0)
              $display("        line %0d : R/G=%.4f", j, lineR[j]*1.0/lineG[j]);
        end
      end
    end

    $display("");
    $display("======== VERDICT ========");
    $display("  MODE 1 must print out R/G = 1.0000  (stock implementation gave 1.3396).");
    $display("  MODE 2 gainR must ramp monotonically toward 1.6667 (damped, ~4-frame tau).");
    $display("  MODE 0 must stay at 1.0000.");
    $finish;
  end

  initial begin
    #40000000;
    $display("*** TIMEOUT ***");
    $finish;
  end

endmodule
