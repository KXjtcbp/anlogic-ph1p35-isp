# 2026-10-15 运动检测 OSD 版

## 本次改了什么
1. `hdmi_mixer.v` 新增第 5 层 OSD：运动块边界描边（红色 COLOR_MOT_TEXT=24'hff2020），
   16 列 x 9 行、块尺寸 80x80，与 `motion_detect.v` 的 BEATS_PER_BLK=20*4px 对齐。
   块索引用 15+8 个比较器求和，块内偏移用 bx*80=(bx<<6)+(bx<<4) 还原 —— 全程零除法器、零 ERAM。
   优先级最低（不遮已有的遥测/CNT/MODE/logo）。
2. `hdmi_mixer.v` 新增 2 个输入端口 `I_mot_mask[143:0]` / `I_mot_cnt[7:0]`。
3. `design_top_wrapper.v` 的 `u_hdmi_mixer` 例化处接上 `S_mot_mask` / `S_mot_cnt`
   （`S_mot_mask` 等三根 wire 与 `u_isp_top` 侧在 10-15 早前那次已接好，见 :932-934 / :966-968）。

## 为什么必须接
`design_top_wrapper.v` 里 `S_mot_mask/S_mot_cnt/S_mot_any` 三根线在 10-15 早期版本已经接上
`u_isp_top`，但没有任何消费者 ⇒ TD 在 Optimize 阶段把整条 `u_motion_detect` 当冗余扫掉，
`gate.area`/`phy.area` 里搜不到它，bit 里没有运动逻辑。这次接上 OSD 后才真正进网表。

## 综合后判据（两道，都过）
- `syn_1\camera_to_dsi_display_gate.area` 搜 `u_motion_detect` = 1 命中
- `phy_1\camera_to_dsi_display_phy.area` 搜 `u_motion_detect` = 1 命中
  （`| u_motion_detect | motion_detect | 1015 | 320 | 1722 | 0 | 0 | 0 | 0 | 42 | 21 | 0 | 0 |`）
- 资源应当上升：`#slices` 13969 -> 15604（+1635）、`#lut6` 12941 -> 14271（+1330）

## QoR
Setup WNS +109 ps / TNS 0 / S-EP 0；Hold WNS +20 ps / TNS 0 / H-EP 0；线长 3887824
`#slices 15604 (73.55%)`、`#lut6 14271 (67.27%)`、`#reg 11186 (26.36%)`、`#eram 51/108`、`#dsp 10/40`

## 回滚点
`proj\releases\2026-10-15_wb_recip版\`（md5 3C619ABF75F2645323B299D4942334F6）
