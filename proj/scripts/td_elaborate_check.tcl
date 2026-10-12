# TD 无头工程检查（加强版）：open_project -> 真正跑综合的 read_design 阶段
#
# 为什么需要这个脚本：
#   open_project 只做「语法/接口分析」，不做 elaborate 的寄存器驱动检查。
#   我曾经因此漏掉一个致命错误（HDL-8007 net 'f_heat.d[7]' is constantly
#   driven from multiple places），它只在真正 run（综合）时才报出来。
#   read_design 阶段会真正 elaborate，能在几分钟内提前抓出这类错误。
#
# 重要：本文件的换行/编码是无 BOM 的 UTF-8。
#   千万不要用 PowerShell 的 `Set-Content -Encoding UTF8` 生成 Tcl 脚本，
#   那会写入 BOM，TD 会把它读成 `invalid command name "锘縞atch"`。
#
# 用法（路径必须用正斜杠，Start-Process 的 ArgumentList 会吃掉反斜杠）：
#   Start-Process -FilePath 'E:\TD\bin\td_commands_prompt.exe' `
#     -ArgumentList 'E:/FPGA/proj/scripts/td_elaborate_check.tcl' `
#     -RedirectStandardOutput <日志> -PassThru -WindowStyle Hidden
#
# 判读：日志里出现 HDL-8007 / HDL-7215 / HDL-5369 / ERROR 就是有真错误。
#       出现 "### READ_DESIGN_OK" 才算通过。
#       7 条 PRJ-9210 "XML does not exist" 是本机已知假告警，可忽略。

set prj "E:/FPGA/proj/baseline/lab3/td_project/camera_to_dsi_display.al"

if { [catch { open_project $prj } e] } {
    puts "### OPEN_FAILED $e"
    exit
}
puts "### OPEN_OK"

if { [catch { launch_runs syn_1 -step read_design } e] } {
    puts "### LAUNCH_FAILED $e"
    catch { close_project }
    exit
}
puts "### LAUNCH_OK"

catch { wait_run syn_1 } e
puts "### WAIT_DONE $e"

catch { close_project }
puts "### DONE"
exit
