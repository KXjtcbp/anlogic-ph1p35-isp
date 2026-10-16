本目录 = 2026-10-12 自动曝光（AE）首版
================================================================
来源：proj\baseline\lab3\td_project\camera_to_dsi_display_Runs\phy_1\
       （TD 命令行 syn_1 + phy_1 的原始输出，2026-10-12 19:24:36）

与上一版（_backup\20261012_bit_K45_0149，无 AE）相比，本版新增：
  1. isp/ae_stat.v   —— 帧亮度统计器（60MHz 域），统计点挂在 awb 之前
  2. isp/ae_ctrl.v   —— 自动曝光闭环控制器（24MHz 域），目标帧均值 70
  3. isp_top.v       —— 插入 u_ae_stat，并新增 5 个统计输出端口
  4. design_top_wrapper.v —— 用 ae_ctrl 替换 ae_set（ae_set 保留文件但不再例化）；
                         SW4 由「模拟增益选择」改为「AE 使能」
  5. uicfgcs500_720p.v —— rt_exposure / rt_analog_gain 由硬编码改为接 AE 输出
  6. camera_to_dsi_display.sdc —— 新增 MIPI_RX_BYTE_CLK -> pll_clk_24m 的
                         set_max_delay -datapath_only 20.000 约束

资源与时序（phy_1/route.qor + camera_to_dsi_display_phy.area，2026-10-12 19:24）
  Setup WNS +3 ps / TNS 0 / 违例 S-EP 0 ；Hold WNS +20 ps / TNS 0 / 违例 H-EP 0
  #slices 18132/21216 = 85.46%   #RAMs 60   #DSPs 8   #eram 60/108 = 55.56%
  #IO 68/160   #lut6 15426/21216 = 72.71%   #reg 19290
  AE 实测占用：u_ae_stat 391 LUT + 269 FF ；u_ae_ctrl 109 LUT + 163 FF ；0 ERAM / 0 DSP

烧写后应看到什么（首次上板验收）
  上电时模拟增益复位到 4.000x、数字增益 2.000x = 8.000x，比上一版的 31.500x 暗约 1/4，
  这是预期行为，不是坏了；约 1 秒后 AE 自动爬升，画面变亮。
  把 SW4 拨下 = AE 冻结在当前档；拨回上 = AE 重新闭环。

回滚
  烧 proj\releases\lab3_原厂_2026-09-10\ 那一份 = 回到厂商原始基线；
  烧 _backup\20261012_bit_K45_0149\camera_to_dsi_display.bit
  （md5 f4f9ce5ec969a7524bb0d5e609ca60d1）= 回到加 AE 之前的 K=45 版。

md5
  camera_to_dsi_display.bit                    1789539 B  57ce384dd79433dec0e5728511c7be8c
  camera_to_dsi_display_compress.bit           1443697 B  adb4cde8bc26e032f5e67394aa735bf8

对照：proj\releases\lab3_原厂_2026-09-10\camera_to_dsi_display.bit
      md5 与本次不同（那是 2026-09-10 的厂商 baseline）
