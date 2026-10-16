2026-10-14_无调试中枢版_v2   (Tang Dynasty v6.2.168116 / PH1P35MDG324)

产物
  camera_to_dsi_display.bit    1789539 B  md5 BCC685D935EC04DB72AF123FC2D65D55
  构建时刻 2026-10-14 23:33:59

相对 v1 (md5 606273F214BAFC3D25FFB576D7EEBE79) 的两处修正
  1) td_project/camera_to_dsi_display.al  补进 lsc.v（CompileOrder 57，紧接 ae_ctrl.v 的 56）
     在此之前 lsc.v 只存在于 run 目录的 .prj 里。.prj 是 TD 命令行的输入，.al 是 TD 图形
     界面的输入 —— 只要用 GUI 打开工程保存一次，.prj 会按 .al 重写，lsc.v 就会凭空消失，
     LSC 静默失效且不报任何错（WNS 正 / 0 违例 / bit 正常生成）。
  2) td_project/camera_to_dsi_display.sdc  删除已失效的
       set_false_path -from [get_clocks {config_inst.cwc_tck_o}]
     该时钟属于已被移除的 ChipWatcher 调试中枢，留着会报
       USR-8130 CRITICAL-WARNING: No clock match the pattern
     本次构建已不再出现该告警。

RTL 一行未改。本版与 v1 在功能上完全等价。

资源对照
                        有中枢(板上)   v1      本版 v2
  #slices              19157 90.30%  18376 86.61%  17774 83.78%
  #lut6                  --          16699 78.71%  16143 76.09%
  #slice reg (FF)      19813 46.69%  14990 35.33%  14961 35.26%
  #eram                 60   55.56%   51   47.22%   51   47.22%
  #dsp                   8           8            8
  Setup WNS            +81 ps      +109 ps      +102 ps   TNS 0  违例 0
  Hold  WNS            +20 ps      +20 ps       +20 ps    TNS 0  违例 0
  Wire length          5001728     4592128      4270352
  累计回收 1383 slice(6.52pp) + 9 ERAM + 4852 FF

未决事项（交给后续版本）
  QSPI 固化未做 —— 赛题解析 slide26 硬性要求「最终提交设计必须固化在开发板上，
  上电即可运行，无需再使用PC下载」。属通过/不通过级别。
  另：「下载后几分钟变暗约10倍」尚未做连续 15 分钟长跑验证。
