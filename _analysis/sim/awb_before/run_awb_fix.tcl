#=============================================================================
# run_awb_fix.tcl -- 在独立 work 目录里对指定 awb.v 跑两帧 TB
#   Usage: vsim -c -do run_awb_fix.tcl     (CWD = 本目录)
#   Env  : AWB_DIV = gate (default) | behav
#          AWB_SRC = 被测 awb.v 路径（默认活档）
#          TB      = tb_awb_live_ratio_2f (default) | tb_awb_live_ratio
#=============================================================================
set ROOT  "D:/harness/fpga/fpgacnds"
set SIM   "$ROOT/_analysis/sim/awb"
set FIX   "$ROOT/_analysis/sim/awb_fix"
set AL    "E:/anlu/sim_release/common"
set HDL   "$ROOT/proj/baseline/lab3/user_source/hdl_source"
set DIVIP "$ROOT/proj/baseline/lab3/user_source/ip_source/divider"

if {![info exists env(AWB_DIV)]} { set env(AWB_DIV) gate }
if {![info exists env(AWB_SRC)]} { set env(AWB_SRC) "$HDL/awb.v" }
if {![info exists env(TB)]}      { set env(TB)      "tb_awb_live_ratio_2f"  }

puts "=== RUN   AWB_DIV=$env(AWB_DIV)   TB=$env(TB)"
puts "=== AWB   $env(AWB_SRC)"

vlib work

vlog "$SIM/glbl.v" \
     "$AL/al_map_basic.v" \
     "$AL/al_map_lut.v" \
     "$AL/al_map_adder.v" \
     "$AL/al_map_seq.v"

if {$env(AWB_DIV) eq "gate"} {
    puts "=== divider source: $DIVIP/divider_gate.v  (GATE NETLIST) ==="
    vlog "$DIVIP/divider_gate.v"
} else {
    puts "=== divider source: $SIM/divider_behav.v  (BEHAVIOURAL SUBSTITUTE) ==="
    vlog "$SIM/divider_behav.v"
}

vlog "$SIM/sim_blk_mem_gen_awb_delay_signal.v"
vlog "$HDL/signal_delay.v"
vlog "$env(AWB_SRC)"
vlog "$FIX/$env(TB).v"
vsim -c -nolog -L work work.$env(TB) work.glbl -do "run -all; quit -f"
