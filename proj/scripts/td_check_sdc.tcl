# ------------------------------------------------------------------
# 用途：验证 camera_to_dsi_display.sdc 里新加的
#       set_max_delay -datapath_only 约束确实被 TD 解析成 timing exception。
# 为什么需要 elaborate：read_sdc 要求先有工作模型（否则报
#       USR-8128 CRITICAL-WARNING: Please import a work model first.）。
# 为什么不用 -file：report_timing_exception 会顺带触发完整 update_timing，
#       在没有门级网表的阶段会 coredump，所以改成直接打到 stdout。
# 用法：E:\TD\bin\td_commands_prompt.exe E:/FPGA/proj/scripts/td_check_sdc.tcl
# 注意：Tcl 脚本路径必须用正斜杠；脚本本身不能带 BOM。
# ------------------------------------------------------------------
set prj_dir  {E:/FPGA/proj/baseline/lab3/td_project}
set top_name {design_top_wrapper}

proc sect {tag script} {
    set rc [catch {uplevel 1 $script} em]
    puts "### ${tag}_RC=$rc"
    if {$rc} { puts "### ${tag}_FAIL: $em" }
    return $rc
}

puts "### PROBE_START"
cd $prj_dir

sect IMPORT {import_device ph1_35p.db -package PH1P35MDG324 -speed 3}
sect OPEN   {open_project camera_to_dsi_display.al}
sect ELAB   {elaborate -top $top_name}
sect ADC    {read_adc ../user_source/constraints_source/pin.adc}
sect SDC    {read_sdc camera_to_dsi_display.sdc}
sect IPSDC  {read_sdc -ip ddr2 ../user_source/hdl_source/ph1p35_ddr/ddr2/src/sdc/ddr2.sdc}
puts "### --- set_max_delay constraints currently registered ---"
sect QUERY  {report_timing_exception}

puts "### PROBE_DONE"
exit 0
