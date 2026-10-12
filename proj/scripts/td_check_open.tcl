# TD 无头工程检查：只做语法/接口分析，不综合、不产生中间产物
# 用法(注意路径必须用正斜杠)：
#   Start-Process -FilePath 'E:\TD\bin\td_commands_prompt.exe' `
#     -ArgumentList 'E:/FPGA/proj/scripts/td_check_open.tcl' -RedirectStandardOutput <日志> -PassThru
# 期望输出：PRJ-1401 : Successfully analyzed 46 source files.
# 注意：会打印 7 条 PRJ-9210 "XML 不存在" 的假告警，可忽略。

set prj "E:/FPGA/proj/baseline/lab3/td_project/camera_to_dsi_display.al"

if { [catch { open_project $prj } e] } {
    puts "### OPEN_FAILED $e"
    exit
}
puts "### OPEN_OK"
catch { export_files "E:/FPGA/proj/logs/our_filelist.txt" -absolute_mode }
puts "### FILELIST_DONE"
catch { close_project }
puts "### DONE"
exit
