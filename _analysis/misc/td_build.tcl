#=====================================================================
# td_build.tcl —— TD 6.2.1 批处理：综合 + 布局布线 + 出比特流
#   用法（Windows）：
#     "source E:/FPGA/_analysis/td_build.tcl`nexit" | E:\TD\bin\td_commands_prompt.exe
#   注意：TD 的 Tcl 会把反斜杠当转义符 ⇒ 脚本里一律用正斜杠 "/"
#=====================================================================
open_project E:/FPGA/proj/baseline/lab3/td_project/camera_to_dsi_display.al
puts "TD-BUILD: project opened"

reset_runs {syn_1 phy_1}
puts "TD-BUILD: runs reset"

launch_runs {syn_1 phy_1} -jobs 2
puts "TD-BUILD: runs launched (syn_1 -> gate, phy_1 -> bitgen)"

wait_run -quiet syn_1
puts "TD-BUILD: syn_1 finished"

wait_run -quiet phy_1
puts "TD-BUILD: phy_1 finished"

save_best_bits
puts "TD-BUILD: best bits saved to best_result/"

close_project
puts "TD-BUILD: ALL DONE"
exit
