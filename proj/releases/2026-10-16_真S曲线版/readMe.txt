# 2026-10-16 真 S 曲线版

## 本版内容
在 main 618c4c8 基础上综合，相对上一版 2026-10-15_运动灵敏度版（md5 BDB6C0E86B202FE7D9396587C0C361CC）**只改了色调曲线**：
- isp/isp_gamma.v：由「反 S (P=160, A=B=0.50) + 黑位恢复 K=45」换成 **真 S (P=128, A=1.15, B=1.10) + 黑位恢复 K=1**，来自组员 C 的 eature/curve-true-s-osd-params-v2（256 项表值已逐条核对）。
- osd_char_lib.v：同步取 v2，新增 '-' (0x2d) 与 '.' (0x2e) 两个字形（为尚未合入的参数行 OSD 预留）。
- 其余 RTL 一行未改。

## 曲线指标（256 级灰阶统计）
| 项 | 旧（反 S K=45） | 本版（真 S K=1） |
|---|---|---|
| p10 | 39 | 19 |
| p50 | 134 | 128 |
| p90 | 204 | 234 |
| p10-p90 跨度 | 165 | 215 |
| 中调斜率 (x=120..136) | 0.695 | 1.125 |
| 输出为 0 的输入码数 | 13 (x=0..12) | 3 (x=0..2) |
| 可达输出码 | 185 | 244 |
| 实测 E1 图上压成纯黑的比例 | 1.51% | 0.10% |

## 时序与资源
- Setup WNS 108 ps / TNS 0 / 违例 S-EP 0
- Hold  WNS 20 ps / TNS 0 / 违例 H-EP 0
- 详见 oute.qor 与 camera_to_dsi_display_phy.area

## 产物
- camera_to_dsi_display.bit          1789539 B  md5 54F018E071A501EC506BFBE9C3C23E08
- camera_to_dsi_display_compress.bit 1398065 B  md5 AFC55DBADFBE06DACFED96F9D6EE7827
- oute.qor / camera_to_dsi_display_phy.area

## 回滚点
proj\releases\2026-10-15_运动灵敏度版\（md5 BDB6C0E86B202FE7D9396587C0C361CC）

## 已知未完成
- 组员 C 的「第 6 层参数行 OSD」尚未合入（hdmi_mixer.v 与 design_top_wrapper.v 需手工合并，v2 分支的版本不含 main 后来的运动描边层）。
- - / . 两个字形本版已就位但暂未被任何图层引用。