camera_to_dsi_display.bit            1789539 B  md5 aff63e6d8d5951d560ff41c883aa80b0
camera_to_dsi_display_compress.bit   1445489 B  md5 bb4fc0983262ee9b6e5a6b758fb8d893

生成时刻 2026-10-12 22:09:27   Tang Dynasty v6.2.168116   器件 PH1P35MDG324 speed3
顶层 design_top_wrapper

时序        Setup WNS +51ps / TNS 0 / 违例 S-EP 0
            Hold  WNS +20ps / TNS 0 / 违例 H-EP 0
资源        #slices 18769 (88.47%)   #lut6 16056/21216 (75.68%)   #reg 19420
            #RAMs 60   #DSPs 8   #eram 60/108 (55.56%)   线长 5242928

本版相对 2026-10-12_OSD遥测版（md5 af25c9b559898eb677241f729a997614）的唯一改动：
  活档 hdl_source/awb.v —— 自动白平衡从"只采 1/4 像素 + 每帧增益复位"改成"四路全采 + 跨帧保持"：
    1) rgb888_*_d[1..3] 与 rgb888_*_d0[1..3] 补齐赋值（原来只有 [0] 有驱动，[1..3] 悬空）
    2) rgb_sum[0..3] 四路各自算 R+G+B
    3) 累加改成先算四条组合增量 inc_r/inc_g/inc_b 再累加一次
       （同一 always 块里对同一 reg 多次非阻塞赋值只有最后一条生效，所以必须先合成）
    4) sum_* 复位初值 1 -> 0
    5) 增益复位条件去掉 I_tuser —— 原来每帧开头都把增益打回 1.000x，
       等于每帧前半段没有白平衡，且永远收敛不到稳态

回滚：烧 2026-10-12_OSD遥测版\camera_to_dsi_display.bit (md5 af25c9b559898eb677241f729a997614)
      或 2026-10-12_AE修正版\camera_to_dsi_display.bit (md5 4c75078a4c31b091a3e015dde4854b59)

注意：本版仍带橙色遥测行（hdmi_mixer 第 4 层 OSD），位置在屏幕 x[566..1000] y[228..240]（1920 空间），
      内容 AE<增益索引><状态>M<实测均值>W<AWB R增益>B<AWB B增益>，全部十六进制。
