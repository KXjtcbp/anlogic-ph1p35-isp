# TD 命令行全流程构建脚本（一次进程内完成，不能用 reset_run —— 本版本无此 Tcl 命令）
# 用法:
#   Start-Process -FilePath 'E:\TD\bin\td_commands_prompt.exe' `
#     -ArgumentList <本文件的【正斜杠】路径> -RedirectStandardOutput <日志> -PassThru
# 注意: PowerShell 的 -ArgumentList 会吃掉反斜杠，调用时路径必须写成正斜杠。
# 作用: 打开整合工程 -> launch_runs(综合+实现) -> wait_run 等待 -> open_run -> save_best_bits
# 产出: camera_to_dsi_display_Runs\best_result\camera_to_dsi_display.bit 及各类报告

set prj "E:/FPGA/proj/baseline/lab3/td_project/camera_to_dsi_display.al"

puts "### STEP open_project"
if { [catch { open_project $prj } e] } {
    puts "### OPEN_FAILED $e"
    exit
}
puts "### OPEN_OK"

puts "### STEP launch_runs phy_1 -jobs 6"
set t0 [clock seconds]
if { [catch { launch_runs phy_1 -jobs 6 } e2] } {
    puts "### LAUNCH_FAILED $e2"
} else {
    puts "### LAUNCH_OK"
}

puts "### STEP wait_run phy_1 syn_1"
if { [catch { wait_run phy_1 syn_1 } e3] } {
    puts "### WAIT_FAILED $e3"
} else {
    puts "### WAIT_OK"
}
set t1 [clock seconds]
puts "### BUILD_SECONDS [expr {$t1 - $t0}]"

puts "### STEP open_run syn_1"
if { [catch { open_run syn_1 } e4] } { puts "### OPENRUN_SYN_FAILED $e4" } else {
    puts "### OPENRUN_SYN_OK"
    catch { report_area -file "E:/FPGA/proj/logs/our_syn.area" }
    catch { report_timing_summary -file "E:/FPGA/proj/logs/our_syn.timing" }
    catch { close_run }
}

puts "### STEP open_run phy_1"
if { [catch { open_run phy_1 } e5] } { puts "### OPENRUN_PHY_FAILED $e5" } else {
    puts "### OPENRUN_PHY_OK"
    catch { report_area -io_info -file "E:/FPGA/proj/logs/our_phy.area" }
    catch { report_timing_summary -file "E:/FPGA/proj/logs/our_phy.timing" }
    catch { report_timing_status -file "E:/FPGA/proj/logs/our_phy.ts" }
    catch { report_qor -step route -file "E:/FPGA/proj/logs/our_route.qor" }
    catch { report_clock_utilization -file "E:/FPGA/proj/logs/our_clock_utilization.txt" }
    catch { close_run }
}

puts "### STEP save_best_bits"
catch { save_best_bits } e6
puts "### SAVEBITS_MSG $e6"

catch { close_project }
puts "### DONE"
exit
