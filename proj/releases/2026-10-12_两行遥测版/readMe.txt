2026-10-12 两行遥测版（OSD 第 1+2 行诊断）
=========================================
生成时间 : 2026-10-12 22:33:47
顶层     : design_top_wrapper
器件     : PH1P35MDG324 speed 3
Setup    : WNS +63ps  TNS 0  违例 0
Hold     : WNS +20ps  TNS 0  违例 0
线长     : 5026592
#slices  : 18253 / 21216 = 86.03%
#lut6    : 15641 / 21216 = 73.72%
#reg     : 19465
#RAMs    : 60      （判据：掉到 12 就是 ISP 链被扫掉）
#DSPs    : 8       （判据：必须是 8）
#eram    : 60 / 108 = 55.56%

camera_to_dsi_display.bit           1789539 B  md5 79c6832556dda860814e4b5a94514215
camera_to_dsi_display_compress.bit  1441777 B  md5 8d1fa8424f7c4b956d90fe3a1bcc9f9d

本版包含
--------
1. 活档 awb.v 四路修复：四个 4px 通道全部参与累加（原先只累加通道 0）；
   去掉每帧把增益复位成 1.000x（原写法让每帧前半段等于没有白平衡）；
   sum_* 初值 1 -> 0。
2. OSD 两行遥测（橙色，仅诊断用）：
   第 1 行  AE<gi2>S<st1>M<ml2>W<gr4>B<gb4>
   第 2 行  F<can><frm><req><aec><cam>T<settle2>N<gi_next2>D<gi_dec2>U<gi_inc2>
   位置：第 1 行内部坐标 (376,152)，第 2 行 (376,164)，均在 1280x720 内部坐标系。
   采集图是 1920x1080，屏幕位置 = 内部坐标 x 1.5。

第 1 行字段
-----------
pos 0-1   'AE'
pos 2-3   增益索引（十六进制） 00=1.000x  40=4.000x  7F=15.750x
pos 4     'S'
pos 5     状态 0=等配置/表下载中 1=稳定计时中 2=闭环运行 3=冻结
pos 6     'M'
pos 7-8   实测帧均值（十六进制），目标 TARGET_MEAN=70 -> 0x46
pos 9     'W'
pos 10-13 AWB R 增益（十六进制），0x1000 = 1.000x
pos 14    'B'
pos 15-18 AWB B 增益（十六进制）

第 2 行字段
-----------
pos 0     'F' 以下 5 位是 AE 决策链的 5 个使能位，1/0
pos 1     can_act        S_can_act
pos 2     frame_ok       S_frame_ok（本帧像素数 > NOM_PIX/2）
pos 3     req_pend       S_req_pend
pos 4     ae_cfg_done    I_ae_cfg_done
pos 5     cam_cfg_done   I_cam_cfg_done
pos 6     'T'
pos 7-8   settle 计数（十六进制，满值 60 = 0x3C）
pos 9     'N'
pos 10-11 gi_next（十六进制，7 位索引）
pos 12    'D'
pos 13-14 gi_dec（本帧要减的档数，十六进制）
pos 15    'U'
pos 16-17 gi_inc（本帧要加的档数，十六进制）

判读要点
--------
- 第 2 行 5 个使能位是定位「AE 不动」的钥匙：
  全是 1 而 gi 仍不变 -> 决策说不需要动（看 D/U 两位是否为 0）；
  某一位是 0 -> 就是那一位把 AE 锁死了。
- 若 D=0 且 U=0，说明 AE 认为亮度已在死区（目标 70 +- 4.76%）。
- 若 U 非 0 但第 1 行的 AE 不变，问题在下发路径（req_pend / 表握手）。

上板注意
--------
- 必须断电重启后再烧，让 ae_ctrl 复位到 GAIN_IDX_INIT = 0x40。
- SW4 上 = AE 闭环运行；SW4 下 = AE 冻结在当前档。
- 首次上电画面会偏暗约 1/4，是 AE 起始档位（4.000x）的预期行为。

回滚
----
烧 proj/releases/2026-10-12_OSD遥测版/camera_to_dsi_display.bit
   （md5 af25c9b559898eb677241f729a997614）
再往前：proj/releases/2026-10-12_AE修正版/camera_to_dsi_display.bit
   （md5 4c75078a4c31b091a3e015dde4854b59）
