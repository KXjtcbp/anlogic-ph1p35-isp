LSC 诊断图案版  2026-10-13 23:48

用途：一次性判断 LSC（lsc.v）到底有没有落到像素上、以及 x 坐标计数对不对。
用完请立刻换回正式版（见文末）。

与正式 LSC 版的唯一差别
  1) F_kh：左半屏 hidx 0..9（像素 0..639） k = 0 ；右半屏 hidx 10..19（像素 640..1279）k = 7
     => 屏幕正中应出现一条硬竖直分界
  2) F_kv：全部 0（先单独验 x，y 不参与）
  3) F_apply 增益临时从 g = 1 + k/64 提到 g = 1 + k/16
     k=7 时为 x1.4375 => 右半屏 R、B 各 +44%，明显偏品红

判别表
  左右完全一样、没有分界      -> LSC 没进通路（烧错版本）或 S_bx 恒 0
  右半屏品红、分界在正中      -> LSC 正常、x 计数正确
  整屏一样地品红              -> S_bx 卡在末拍
  分界明显不在正中            -> x 计数比例不对

烧写
  1. 断电重启（让 AE 增益与 LSC 一起复位）
  2. 四开关全上
  3. 对均匀白纸/白墙拍 1 张即可

md5
  camera_to_dsi_display.bit          16980DCDC16E3F325EDB25D67A3933EB
  camera_to_dsi_display_compress.bit DF4B617B36EDBF4BE976471AD0E2058B

QoR
  Setup WNS +100 ps / TNS 0 / 违例 0 ; Hold WNS +20 ps / 违例 0
  #slices 17947 (84.59%) ; #RAMs 60 ; #DSPs 8 ; 0 条 HDL-8007

回滚 / 换回正式版
  1. python E:\FPGA\_analysis\scripts\gen_lsc_diag.py --restore
  2. 重跑 _analysis\misc\td_run_direct.ps1 syn_1 phy_1
  正式 LSC 版已归档：proj\releases\2026-10-14_LSC版\  md5 F049225FF7640D03FD1833AC9CA2F2CC
