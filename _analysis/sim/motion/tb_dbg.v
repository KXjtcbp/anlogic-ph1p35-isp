`timescale 1ns/1ps
module tb_dbg;
  reg clk=0,rstn=0,tv=0,tu=0,tl=0,bp=0; reg [95:0] td=0;
  motion_detect #(.STRICT2(1'b0)) dut(.I_clk(clk),.I_rst_n(rstn),.I_bypass(bp),
    .I_tdata(td),.I_tvalid(tv),.I_tuser(tu),.I_tlast(tl),
    .O_blk_mask(),.O_blk_cnt(),.O_motion_any(),.O_dbg_cur(),.O_dbg_prev());
  always #5 clk=~clk;
  function [95:0] p4(input [7:0] v); begin p4={v,v,v,v,v,v,v,v,v,v,v,v}; end endfunction
  integer y,b;
  initial begin
    rstn=0; #40 rstn=1; #20;
    for (y=0;y<240;y=y+1) for (b=0;b<320;b=b+1) begin
      @(negedge clk); tv=1; tu=(y==0&&b==0); tl=(b==319);
      td=p4((b<40)?8'd160:8'd100); @(posedge clk);
    end
    @(negedge clk); tv=0; @(posedge clk);
    $display("y=239 ?: S_acc[0]=%0d S_acc[1]=%0d S_acc[2]=%0d  (m=160 ?=1024000, m=100 ?=640000)",
             dut.S_acc[0], dut.S_acc[1], dut.S_acc[2]);
    $display("S_cur_k[0]=%0d S_cur_k[1]=%0d S_cur_k[2]=%0d (? 125 / 125 / 78)",
             dut.S_cur_k[0], dut.S_cur_k[1], dut.S_cur_k[2]);
    $display("prev[0][0]=%0d prev[0][1]=%0d prev[0][2]=%0d",
             dut.S_prev[0][0], dut.S_prev[0][1], dut.S_prev[0][2]);
    $finish;
  end
endmodule
