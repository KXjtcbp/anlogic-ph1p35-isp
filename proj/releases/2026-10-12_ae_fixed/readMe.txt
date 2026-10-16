AE 修正版 —— 2026-10-12 20:24 构建
================================================

【这一版修了什么】
上一版（2026-10-12_AE首版）的 AE 方向是反的：每帧都判"画面过亮"，把增益一路降到最低档。
上板现象是"拨上 SW4 之后画面越来越黑"。本版修掉三个 bug：

1. ae_ctrl.v 的亮度量纲差 256 倍（把 ae_stat 输出的 Σ(Y×256) 直接当成 ΣY 用）
   -> 恒判"过亮" -> 每帧降档。
   修法：S_lsum = {8'd0, S_luma_sum[39:8]}

2. ae_ctrl.v 的增益上限钳位失效（7 位求和先截断，钳位条件恒假）
   -> 爬到接近满档时跳回最低档并振荡（实测一帧从 116 掉到 4）。
   修法：先在 8 位上求和，再判溢出。

3. ae_ctrl.v 的"暗场景护栏"把加亮通道堵死（近黑 >25% 就停止加亮）
   本工程场景近黑占 65%~95%，该护栏恒真 -> AE 在本来就暗的场景里完全不加亮。
   修法：LO_GUARD_SHIFT 默认改为 0（关闭）；要恢复旧策略改回 2 即可。

Testbench 从 8 个 CASE 扩到 10 个，新增：
  CASE 9  量纲回归（断言 dut.S_lsum == TARGET_SUM）
  CASE 10 板上实测场景回归（用 A4 的真实数字，断言"必须加档"）
  CASE 6  反向重写（暗场景必须加亮）
结果：*** ALL PASS, errors=0 ***


【QoR】
  Setup WNS        95 ps     (上一版 +3 ps)
  Setup TNS         0        Num of violated S-EP   0
  Hold  WNS        20 ps     Num of violated H-EP   0
  Wire length      5028912
  #slices          18111  (85.36%)
  #RAMs               60    <- 必须保持 60；掉到 12 说明 ISP 链被当冗余扫掉了
  #DSPs                8
  #eram             60/108 (55.56%)
  #lut6          15296/21216 (72.10%)
  #reg              19268
  bitgen: 1061830 bits set as '1', frame number 3481 -> 3473


【上板现象（预期）】
- 开机默认 SW1/SW2/SW3/SW4 都拨上 = AE 闭环运行。
- 复位后模拟增益停在 4.000x（x SW3 数字 2.000x = 8.000x），画面偏暗；
  约 1 秒后 AE 开始爬升，几秒内会顶到满档 15.750x（x 2.000x = 31.500x）。
- 顶到满档后画面比开机时亮很多，但在宿舍这类暗场景里达不到目标帧均值 70
  —— 这是光照不足，不是 AE 故障。
- SW4 拨到下 = AE 冻结在当前档（画面亮度保持不变）；拨回上 = 继续闭环。


【回滚方法】
烧上一版：
  proj\releases\2026-10-12_AE首版\camera_to_dsi_display.bit
  md5 = 57ce384dd79433dec0e5728511c7be8c

再往前一版（无 AE，黑位 K=45）：
  _backup\20261012_bit_K45_0149\camera_to_dsi_display.bit
  md5 = f4f9ce5ec969a7524bb0d5e609ca60d1


【文件校验】
  camera_to_dsi_display.bit            1789539 B
    md5 = 4c75078a4c31b091a3e015dde4854b59
  camera_to_dsi_display_compress.bit   1442609 B
    md5 = 2c96716a056f281a6c6362092a722e40

构建时间 2026-10-12 20:24:21，工具 Tang Dynasty V6.2.168116，器件 PH1P35MDG324。
