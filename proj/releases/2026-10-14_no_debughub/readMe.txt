2026-10-14_无调试中枢版  (Tang Dynasty v6.2.168116 / PH1P35MDG324)

产物
  camera_to_dsi_display.bit            1789539 B  md5 606273F214BAFC3D25FFB576D7EEBE79
  camera_to_dsi_display_compress.bit   (见同目录)
  源       proj/baseline/lab3/td_project/camera_to_dsi_display_Runs/phy_1/
  构建时刻 2026-10-14 23:13:48

与上一版（2026-10-14_SW1-LSC旁路诊断版 (md5 e4dd994604843b011e7d07abce016070)）的唯一区别
  RTL 一行未改。改的是构建流程脚本：
    E:\FPGA\_analysis\misc\DefaultFlow_noCWC.tcl   （TD 原版 DefaultFlow.tcl 的副本，
        删掉了 opt_rtl_fun / opt_place_fun 里的 insert_debugger、
        以及 bitgen_fun 里的 setup_debugger，共 12 行）
    E:\FPGA\_analysis\misc\td_run_direct.ps1  的 $flow 改指向它

为什么必须改流程而不是删产物
  TD 的 DefaultFlow.tcl 会自己调 insert_debugger：
    第 126-129 行  opt_rtl_fun  （syn_1 阶段）
    第 163-165 行  opt_place_fun（phy_1 阶段）   <- 就是这一处把中枢补回来的
    第 228-231 行  bitgen_fun   （setup_debugger）
  insert_debugger 不带参数时无条件建一个默认 ChipWatcher 中枢（实例名 auto_created_cwc1）。
  删 <run>/cw/ 无效 —— cw/ 是它的产物，不是它的输入；phy 阶段会重新生成。

资源对照（route.qor / camera_to_dsi_display_phy.area）
                        上一版        本版        回收
  #slices            19157 90.30%  18376 86.61%   -781  -3.69pp
  #slice reg (FF)    19813 46.69%  14990 35.33%   -4823
  #eram              60    55.56%  51    47.22%   -9
  #lut6              (未记录)      16699 78.71%
  #RAMs / #DSPs      60 / 8        51 / 8
  Setup WNS          +81 ps        +109 ps  TNS 0  违例 0
  Hold  WNS          +20 ps        +20 ps   TNS 0  违例 0
  Wire length        5001728       4592128          -8.2%

副作用（必须记住）
  ChipWatcher 从此不可用。以后要用必须在 DefaultFlow_noCWC.tcl 里把这三处改回去，
  或用 TD 图形界面单次跑。原始流程脚本未改动，随时可还原。
