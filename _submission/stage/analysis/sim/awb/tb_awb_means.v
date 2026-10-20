//=============================================================================
// tb_awb_means.v -- does the stock AWB actually deliver a neutral frame?
//
// Stimulus: an entire frame of one constant colour, R=80 G=100 B=90
//           => input  R/G = 0.800, B/G = 0.900
//
// Gray-world AWB must output R/G = 1.000, B/G = 1.000.
// We accumulate the real output bytes over the last frame and report the ratio,
// so this measures the BLOCK'S ACTUAL behaviour, not what the code looks like.
//=============================================================================
`timescale 1ns/1ps

module tb_awb_means;

  localparam W   = 256;
  localparam H   = 8;
  localparam BPL = W/4;                 // 64 beats per line
  localparam NFRAME = 4;

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

  localparam [23:0] PX = {8'h50, 8'h64, 8'h5A};   // R=80 G=100 B=90
  localparam [95:0] TD = {PX, PX, PX, PX};

  awb #(.IMG_HEIGHT(H), .IMG_WIDTH(W)) dut (
      .I_clk (clk), .I_rst_n(rst_n), .I_tlast(tlast), .I_tuser(tuser),
      .I_tdata(tdata), .I_tvalid(tvalid), .I_tready(tready),
      .O_tlast(o_tlast), .O_tuser(o_tuser), .O_tdata(o_tdata),
      .O_tvalid(o_tvalid), .O_tready(o_tready)
  );

  // ---- measurement accumulators (widths sized for W*H pixels) --------------
  integer inR, inG, inB;        // input  sums, one frame
  integer ouR, ouG, ouB;        // output sums, one frame
  integer nout;
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

  task report;
    input [8*20:1] tag;
    begin
      $display("%0s  in : R/G=%.4f B/G=%.4f   (inR=%0d inG=%0d inB=%0d)",
               tag, inR*1.0/inG, inB*1.0/inG, inR, inG, inB);
      if (nout > 0)
        $display("%0s  out: R/G=%.4f B/G=%.4f   (ouR=%0d ouG=%0d ouB=%0d  n=%0d)  gainR=%h gainB=%h",
                 tag, ouR*1.0/ouG, ouB*1.0/ouG, ouR, ouG, ouB, nout,
                 dut.in_r_r1, dut.in_b_r1);
    end
  endtask

  integer f, i;
  initial begin
    inR=0; inG=0; inB=0; ouR=0; ouG=0; ouB=0; nout=0;

    rst_n = 0;
    repeat (10) @(negedge clk);
    rst_n = 1;
    repeat (5)  @(negedge clk);

    for (f = 0; f < NFRAME; f = f + 1) begin
      // clear the per-frame accumulators at the start of every frame
      inR=0; inG=0; inB=0; ouR=0; ouG=0; ouB=0; nout=0;

      for (i = 0; i < H; i = i + 1) begin
        repeat (60) @(negedge clk);
        tdata  = TD;
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
      // let the pipeline drain
      repeat (120) @(negedge clk);
      $display("--- frame %0d ---", f);
      report("  ");
    end

    $display("");
    $display("======== VERDICT ========");
    if (nout == 0) begin
      $display("*** NO OUTPUT DATA AT ALL - O_tvalid never asserted ***");
    end else if (ouR*1.0/ouG > 0.995 && ouR*1.0/ouG < 1.005 &&
                 ouB*1.0/ouG > 0.995 && ouB*1.0/ouG < 1.005) begin
      $display("*** AWB WORKS: output frame is neutral (R/G and B/G within 0.5%% of 1.0) ***");
    end else begin
      $display("*** AWB UNDER-CORRECTS: output R/G=%.4f B/G=%.4f, target 1.0000 ***",
               ouR*1.0/ouG, ouB*1.0/ouG);
    end
    $finish;
  end

  initial begin
    #8000000;
    $display("*** TIMEOUT ***");
    $finish;
  end

endmodule
