AWB 帧锁存版 —— 2026-10-13 00:05

=== 这一版改了什么 ===
1. hdl_source/awb.v：把"每来一个 done[0] 就用当时的运行求和比覆盖增益"改成
   "每帧只在帧末锁存一次"（帧锁存）。这是 2026-10-12 夜定位到的顶层色带病灶的修法。
2. isp/ae_ctrl.v：把 O_dbg2 改成寄存器输出（原来是从 S_* 直接组合跨到 24MHz 域，
   产生 1 条 set_max_delay 违例 7.835ns > 8.000ns 边缘余量）。

=== 上板要看什么 ===
- 画面顶部/底部的横向色带应当明显减轻或消失（这是本版唯一的目的）
- 两行橙色遥测仍在：第1行 AE<gi>S<st>M<ml>W<gr>B<gb>，第2行 F<can><frm><req><aec><cam>T<settle>N<next>D<dec>U<inc>
- 第1行 'W' 后面的 4 位 ÷4096 才是真实 R 增益；'B' 同理

=== QoR ===
Setup WNS +100ps / TNS 0 / 违例 0 ; Hold WNS +20ps / TNS 0 / 违例 0
Wire length 5266000 ; #slices 18289 (86.20%) ; #lut6 15777 (74.36%) ; #reg 19536
#RAMs 60 (判据：不能掉到 12) ; #DSPs 8 ; #eram 60/108 (55.56%)
black box 检查：0 条 HDL-8007

=== 文件 ===
camera_to_dsi_display.bit            1789539 B  md5 f933199d6defb46a4e7c9cc6a13c00d8
camera_to_dsi_display_compress.bit   1441393 B  md5 d054dd34d0aed60f0f1491cbdf90689a

=== 回滚 ===
proj/releases/2026-10-12_两行遥测版/camera_to_dsi_display.bit  md5 79c6832556dda860814e4b5a94514215
