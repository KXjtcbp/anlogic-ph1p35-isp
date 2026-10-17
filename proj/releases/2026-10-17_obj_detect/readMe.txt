# 2026-10-17_obj_detect

## 这是什么
首个带「颜色目标检测」的正式基线（赛题 基础扩展项(2)）。
在 2026-10-17_baseline_p0_closed（6CB52C84）之上新增 obj_detect.v。

## 新增/改动
- 新建 `isp/obj_detect.v`：16 列 x 9 行 = 144 个 80x80 块；逐像素判「红色主导」
  （R>=80 且 R-G>=35 且 R-B>=35），块内命中 > 40 判为目标；只输出 144bit 掩码
  ⇒ 存储 18 B，零帧缓存、零 ERAM、零 DSP、零乘法器/除法器。
- `hdmi_mixer.v`：新增第 7 层 OSD（亮绿 24'h00ff40 块描边），复用第 5 层
  的块索引逻辑；+port I_obj_mask/I_obj_cnt。
- `isp_top.v`：例化 u_obj_detect（纯观察者），+3 端口。
- `design_top_wrapper.v`：接线；.I_obj_bypass(~S_mot_en)，SW3 关则两个功能一起清空。
- .al / syn_1.prj / phy_1.prj 登记 obj_detect.v。

## ★踩坑记录（第四次同类）
第一版 obj_detect.v 被 TD 在 RTL 优化阶段当无用逻辑删掉（rtl.area 只有 2 LUT）。
根因：块判决值取了 `*_nx`（下一拍值），而 `*_nx` 在块结束那拍被清成 0
⇒ 判决恒 0 ⇒ 掩码永不更新 ⇒ TD 判定整模块无消费者。
修法：① 新增 `S_acc*_fin = S_acc* + S_inc` 作为判决值；
      ② `S_blk_hit = S_col_last`（块结束无条件锁存，不再 & S_add）；
      ③ `O_obj_any <= (O_blk_mask != 0)` 改为由掩码组合产生。
TB `_analysis/sim/obj/tb_obj_detect.v` 验证：左半红右半黑 ⇒ 左 8 列 72 块全 1、
右半 0，两轮均 PASS。blk_cnt 计数项在 TB 里退化（S_lyc/S_bxc 相位），
但 OSD 只用 I_obj_mask，不影响画面。

## 时序与资源
Setup WNS +101 ps / TNS 0 / 违例 S-EP 0
Hold  WNS +20  ps / TNS 0 / 违例 H-EP 0
#slices 16414 (77.37%)  #lut6 15162 (71.46%)  #reg 11635
#eram 51/108 (47.22%)   #dsp 10/40 (25.00%)   #RAMs 51
u_obj_detect = 373 logic LUT / 272 ripple / 376 FF / 0 ERAM / 0 DSP（三份 area 报告均命中）

## 拨码映射（本版）
SW1=LSC 开关 / SW2=S 曲线开关 / SW3=运动检测+目标检测使能 / SW4=运动灵敏度

## 产物
camera_to_dsi_display.bit           1789539 B  md5 2132966F87D3A116960823B12C702F04
## 回滚点
2026-10-17_baseline_p0_closed  md5 6CB52C8463FB6E96A7EC7DE69AE6E754
