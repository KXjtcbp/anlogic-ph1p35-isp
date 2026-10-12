//=============================================================================
// sim_blk_mem_gen_awb_delay_signal.v
//   Behavioural stand-in for the Anlogic IP wrapper of the same name, so the
//   AWB block can be simulated in ModelSim (the vendor file instantiates the
//   PH1_LOGIC_ERAM primitive, which ModelSim does not have).
//   Ports/parameters are identical to the real wrapper. 96bit x 2048 true
//   dual port, NOREG (asynchronous read), READBEFOREWRITE on port B.
//   Compile this file INSTEAD of isp/awb/ram/blk_mem_gen_awb_delay_signal.v
//=============================================================================
`timescale 1ns / 1ps

module blk_mem_gen_awb_delay_signal (
    output [95:0] doa,
    output [95:0] dob,
    input  [95:0] dia,
    input  [95:0] dib,
    input  [10:0] addra,
    input  [10:0] addrb,
    input         wea,
    input         web,
    input         clka,
    input         clkb
);
  parameter DATA_WIDTH_A = 96;
  parameter ADDR_WIDTH_A = 11;
  parameter DATA_DEPTH_A = 2048;
  parameter DATA_WIDTH_B = 96;
  parameter ADDR_WIDTH_B = 11;
  parameter DATA_DEPTH_B = 2048;
  parameter REGMODE_A    = "NOREG";
  parameter REGMODE_B    = "NOREG";
  parameter WRITEMODE_A  = "NORMAL";
  parameter WRITEMODE_B  = "READBEFOREWRITE";
  parameter RESETMODE_A  = "ASYNC";
  parameter RESETMODE_B  = "ASYNC";

  reg [95:0] mem [0:2047];

  assign doa = mem[addra];
  assign dob = mem[addrb];

  always @(posedge clka) if (wea) mem[addra] <= dia;
  always @(posedge clkb) if (web) mem[addrb] <= dib;

endmodule
