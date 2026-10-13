# =============================================================================
# run_div_rate.tcl —— 只跑 divider done 节奏那个 TB（AWB_TB=both 时第二段总是
#   不执行，先隔离成单独脚本，排除 TB 与 tcl 流程的相互影响）。
#   用法：vsim -c -do run_div_rate.tcl
# =============================================================================
set ROOT  "D:/harness/fpga/fpgacnds"
set AL    "E:/anlu/sim_release/common"
set SIM   "$ROOT/_analysis/sim/awb"
set DIVIP "$ROOT/proj/baseline/lab3/user_source/ip_source/divider"

if {[file exists work_div]} { file delete -force work_div }
vlib work_div
vmap work_div work_div

vlog -work work_div "$SIM/glbl.v" \
     "$AL/al_map_basic.v" "$AL/al_map_lut.v" "$AL/al_map_adder.v" "$AL/al_map_seq.v"
vlog -work work_div "$DIVIP/divider_gate.v"
vlog -work work_div "$SIM/tb_div_done_rate.v"

vsim -c -nolog -L work_div work_div.tb_div_done_rate work_div.glbl -do "run -all; quit -f"
