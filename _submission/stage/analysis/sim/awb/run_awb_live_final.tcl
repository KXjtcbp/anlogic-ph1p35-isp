# =============================================================================
# run_awb_live_final.tcl
#   最终取证脚本。与 run_awb_live_pristine.tcl 相同，只做两件事：
#     1. 被测 RTL 用冻结副本 awb_pristine_b60eb85.v（git b60eb85/HEAD，22055 B）
#        —— 因为工作区里的 awb.v 在本轮仿真期间被另一路改了，钉住快照才可复现；
#     2. 每次删掉 work 重建，保证不会误加载上一次编译进库里的 awb。
#   用法（在 _analysis\sim\awb 下）：
#       vsim -c -do run_awb_live_final.tcl
# =============================================================================
set ROOT  "D:/harness/fpga/fpgacnds"
set AL    "E:/anlu/sim_release/common"
set SIM   "$ROOT/_analysis/sim/awb"
set HDL   "$ROOT/proj/baseline/lab3/user_source/hdl_source"
set DIVIP "$ROOT/proj/baseline/lab3/user_source/ip_source/divider"

puts "=== FINAL RUN : pristine RTL awb_pristine_b60eb85.v (22055 B, git b60eb85) ==="

if {[file exists work]} { file delete -force work }
vlib work

vlog "$SIM/glbl.v" \
     "$AL/al_map_basic.v" "$AL/al_map_lut.v" "$AL/al_map_adder.v" "$AL/al_map_seq.v"
vlog "$DIVIP/divider_gate.v"
vlog "$SIM/sim_blk_mem_gen_awb_delay_signal.v"
vlog "$HDL/signal_delay.v"
vlog "$SIM/awb_pristine_b60eb85.v"
vlog "$SIM/tb_awb_live_ratio.v"

vsim -c -nolog -L work work.tb_awb_live_ratio work.glbl -do "run -all; quit -f"
