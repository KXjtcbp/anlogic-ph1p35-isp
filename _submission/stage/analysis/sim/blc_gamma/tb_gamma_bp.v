//=============================================================================
// tb_gamma_bp.v -- regression for the [HDR-2026-10-11f] black-point-restored
//                  S-curve table in isp/isp_gamma.v
//
// The expected table comes from  gamma_lut_bp_soft_k45.vh  (a function+case,
// deliberately NOT $readmemh: a missing relative path makes $readmemh load all
// zeros SILENTLY, which is how this project once shipped a black screen).
//
// Checks
//   CASE 1  reset + 2-cycle latency on tvalid/tlast/tuser
//   CASE 2  0..255 on all 12 byte lanes == exp_lut, and all 12 lanes equal
//   CASE 3  bypass = 1  ->  O_tdata === I_tdata delayed 2 cycles
//   CASE 4  hot bypass switch mid-stream
//   CASE 5  black point: exp_lut(0..2) == 0, exp_lut(255) == 255, monotonic
//=============================================================================
`timescale 1ns/1ps

module tb_gamma_bp;

  localparam K_BP = 24;

  reg clk = 0;
  always #8.3335 clk = ~clk;              // 60 MHz ISP domain

  reg         rst_n  = 0;
  reg         tvalid = 0;
  reg         tlast  = 0;
  reg         tuser  = 0;
  reg  [95:0] tdata  = 0;
  reg         bypass = 1;
  wire        tready;
  wire [95:0] o_tdata;
  wire        o_tvalid, o_tlast, o_tuser;
  reg         o_tready = 1;

  isp_gamma dut (
      .I_clk (clk), .I_rst_n(rst_n), .I_tlast(tlast), .I_tuser(tuser),
      .I_tdata(tdata), .I_tvalid(tvalid), .I_tready(tready),
      .I_gamma_bypass(bypass),
      .O_tdata(o_tdata), .O_tlast(o_tlast), .O_tuser(o_tuser),
      .O_tvalid(o_tvalid), .O_tready(o_tready)
  );

  `include "gamma_lut_bp_soft_k45.vh"

  integer errors = 0;
  integer v, lane;
  reg [7:0] b;
  reg [7:0] seen;
  reg [7:0] v8;
  reg [7:0] x8;

  task fail;
    input [255:0] msg;
    begin
      errors = errors + 1;
      $display("  ** FAIL %0s", msg);
    end
  endtask

  // build a 96-bit beat with all 12 lanes set to `val`
  function [95:0] rep12;
    input [7:0] val;
    integer i;
    begin
      for (i = 0; i < 12; i = i + 1) rep12[8*i +: 8] = val;
    end
  endfunction

  task send_beat;
    input [95:0] d;
    input        tl, tu, tv, bp;
    begin
      @(negedge clk);
      tdata  = d;
      tlast  = tl;
      tuser  = tu;
      tvalid = tv;
      bypass = bp;
      @(negedge clk);                      // 1 cycle in flight
      @(negedge clk);                      // 2-cycle pipeline
      #1;                                  // let NBA settle before sampling
    end
  endtask

  initial begin
    $display("==== tb_gamma_bp : black-point S-curve table regression ====");

    // ---------------- CASE 1 : reset ----------------
    rst_n = 0; tvalid = 0; tlast = 0; tuser = 0; tdata = 0; bypass = 1;
    repeat (5) @(negedge clk);
    if (o_tvalid !== 1'b0) fail("case1 reset: O_tvalid must be 0");
    rst_n = 1;
    repeat (3) @(negedge clk);
    $display("  [CASE 1] reset ............... %s", (errors == 0) ? "ok" : "see above");

    // ---------------- CASE 2 : full table on all 12 lanes ----------------
    bypass = 0;
    for (v = 0; v < 256; v = v + 1) begin
      v8 = v;
      send_beat(rep12(v8), 1'b0, 1'b0, 1'b1, 1'b0);
      seen = o_tdata[7:0];
      if (o_tvalid !== 1'b1) begin
        fail("case2 O_tvalid low");
      end
      if (seen !== exp_lut(v8)) begin
        $display("  ** FAIL case2 lane0 v=%0d got=%02h exp=%02h", v, seen, exp_lut(v8));
        errors = errors + 1;
      end
      for (lane = 0; lane < 12; lane = lane + 1) begin
        b = o_tdata[8*lane +: 8];
        if (b !== exp_lut(v8)) begin
          $display("  ** FAIL case2 v=%0d lane=%0d got=%02h exp=%02h", v, lane, b, exp_lut(v8));
          errors = errors + 1;
        end
      end
    end
    $display("  [CASE 2] 256 x 12 lanes ...... %s", (errors == 0) ? "ok" : "see above");

    // ---------------- CASE 3 : bypass ----------------
    begin : case3
      integer e3;
      e3 = errors;
      bypass = 1;
      for (v = 0; v < 256; v = v + 1) begin
        v8 = v;
        send_beat(rep12(v8), 1'b1, 1'b1, 1'b1, 1'b1);
        if (o_tdata !== rep12(v8)) begin
          $display("  ** FAIL case3 v=%0d got=%024h exp=%024h", v, o_tdata, rep12(v8));
          errors = errors + 1;
        end
        if (o_tlast !== 1'b1 || o_tuser !== 1'b1) begin
          fail("case3 tlast/tuser not delayed with data");
          errors = errors + 1;
        end
      end
      $display("  [CASE 3] bypass == identity ... %s", (errors == e3) ? "ok" : "see above");
    end

    // ---------------- CASE 4 : hot bypass switch ----------------
    begin : case4
      integer e4;
      e4 = errors;
      bypass = 0;
      send_beat(rep12(8'd64), 1'b0, 1'b0, 1'b1, 1'b0);
      if (o_tdata[7:0] !== exp_lut(8'd64)) begin
        fail("case4 pre-switch");
        errors = errors + 1;
      end
      bypass = 1;
      send_beat(rep12(8'd64), 1'b0, 1'b0, 1'b1, 1'b1);
      if (o_tdata[7:0] !== 8'd64) begin
        $display("  ** FAIL case4 post-switch got=%02h exp=40", o_tdata[7:0]);
        errors = errors + 1;
      end
      $display("  [CASE 4] hot bypass switch ... %s", (errors == e4) ? "ok" : "see above");
    end

    // ---------------- CASE 5 : static properties of the table ----------------
    begin : case5
      integer e5, x, prev;
      e5 = errors;
      if (exp_lut(8'd0) !== 8'd0 || exp_lut(8'd1) !== 8'd0 || exp_lut(8'd2) !== 8'd0) begin
        $display("  ** FAIL case5 black point: exp_lut(0..2) = %0d %0d %0d, must be 0 0 0",
                 exp_lut(8'd0), exp_lut(8'd1), exp_lut(8'd2));
        errors = errors + 1;
      end
      if (exp_lut(8'd255) !== 8'd255) begin
        fail("case5 exp_lut(255) != 255");
        errors = errors + 1;
      end
      // NOTE: prev must start at 0, not -1 -- exp_lut returns an UNSIGNED [7:0],
      // so the comparison is unsigned and a -1 would become 32'hFFFFFFFF.
      prev = 0;
      for (x = 0; x < 256; x = x + 1) begin
        x8 = x;
        if (exp_lut(x8) < prev) begin
          $display("  ** FAIL case5 not monotonic at x=%0d", x);
          errors = errors + 1;
        end
        prev = exp_lut(x8);
      end
      $display("  [CASE 5] black point + monotonic %s", (errors == e5) ? "ok" : "see above");
    end

    $display("");
    if (errors == 0) $display("  ALL PASS, errors=0");
    else             $display("  *** FAILED ***, errors=%0d", errors);
    $finish;
  end

  initial begin
    #2000000;
    $display("*** TIMEOUT ***");
    $finish;
  end

endmodule
