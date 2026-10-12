//=============================================================================
// tb_awb_probe.v  -- probe the stock AWB block: does the white-balance gain
//                    ever leave 1.0x, and does the divider 'done' ever pulse?
//
// Constant-colour stimulus: every pixel = R=80 G=100 B=90.
// A correct gray-world AWB must drive the gains to
//      gain_R = G/R = 1.250  -> Q16 = 0x14000
//      gain_B = G/B = 1.111  -> Q16 = 0x11C71
// and the output R/G/B to (100,100,100).
//=============================================================================
`timescale 1ns/1ps

module tb_awb_probe;

  localparam W   = 256;      // image width  (must be >= 4*48 so signal_delay works)
  localparam H   = 4;        // image height
  localparam BPL = W/4;      // beats per line = 64

  reg clk = 0;
  always #8.3335 clk = ~clk;          // ~60 MHz

  reg         rst_n  = 0;
  reg         tuser  = 0;
  reg         tlast  = 0;
  reg         tvalid = 0;
  reg  [95:0] tdata  = 0;
  wire        tready;
  wire        o_tlast, o_tuser, o_tvalid;
  wire [95:0] o_tdata;
  reg         o_tready = 1;

  // constant colour  R=0x50(80) G=0x64(100) B=0x5A(90)
  localparam [23:0] PX = {8'h50, 8'h64, 8'h5A};
  localparam [95:0] TD = {PX, PX, PX, PX};

  integer donecnt = 0;
  always @(posedge clk) if (dut.done[0]) donecnt = donecnt + 1;

  awb #(.IMG_HEIGHT(H), .IMG_WIDTH(W)) dut (
      .I_clk    (clk),
      .I_rst_n  (rst_n),
      .I_tlast  (tlast),
      .I_tuser  (tuser),
      .I_tdata  (tdata),
      .I_tvalid (tvalid),
      .I_tready (tready),
      .O_tlast  (o_tlast),
      .O_tuser  (o_tuser),
      .O_tdata  (o_tdata),
      .O_tvalid (o_tvalid),
      .O_tready (o_tready)
  );

  integer f, i;
  initial begin
    rst_n = 0;
    repeat (10) @(negedge clk);
    rst_n = 1;
    repeat (5)  @(negedge clk);

    $display("--- start: gainR=%h gainB=%h donecnt=%0d", dut.in_r_r1, dut.in_b_r1, donecnt);

    for (f = 0; f < 6; f = f + 1) begin
      for (i = 0; i < H; i = i + 1) begin
        // inter-line / inter-frame gap
        repeat (80) @(negedge clk);

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

        $display("f%0d l%0d | gainR=%h gainB=%h | sumR=%0d sumG=%0d sumB=%0d | done=%0d",
                 f, i, dut.in_r_r1, dut.in_b_r1,
                 dut.sum_r[0], dut.sum_g[0], dut.sum_b[0], donecnt);
      end
    end

    // let the last gain settle
    repeat (300) @(negedge clk);
    $display("--- end  : gainR=%h gainB=%h donecnt=%0d", dut.in_r_r1, dut.in_b_r1, donecnt);
    $display("    expect gainR=0x14000 (1.250x)  gainB=0x11c71 (1.111x)");
    if (dut.in_r_r1 == 20'h10000) $display("*** GAINS STUCK AT 1.0x ***");
    else                          $display("*** gains moved ***");
    $finish;
  end

  initial begin
    #4000000;
    $display("*** TIMEOUT ***");
    $finish;
  end

endmodule
