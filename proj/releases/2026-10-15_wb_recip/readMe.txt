# 2026-10-15 优化1：AWB 除法器 -> 倒数查表法（wb_recip.v）

## 这一版做了什么
把 `awb.v` 里两个 TD 流水除法器 `div_gen_G_R_r1` / `divide_G_B_r1` 换成
`wb_recip.v`（归一化 + 256x16 倒数 ROM + 一次 20x16 乘法，纯组合、零流水）。
接口 `in_r_x1`/`in_b_x1` 与溢出饱和语义完全不变，帧锁存逻辑一行未改。

## 资源对照（同一次 TD 流程，PH1P35MDG324 speed 3）
| 指标 | 2026-10-14_无调试中枢版_v2 | 本版 | 变化 |
|---|---|---|---|
| #slices | 17774 (83.78%) | **14023 (66.10%)** | **-3751 (-17.68 pp)** |
| #lut6   | 16143 (76.09%) | **13080 (61.65%)** | **-3063 (-14.44 pp)** |
| #reg    | 14961 (35.26%) | **9447 (22.27%)**  | **-5514 (-12.99 pp)** |
| #eram   | 51 (47.22%)    | 51 (47.22%)        | 0 |
| #dsp    | 8 (20.00%)     | 10 (25.00%)        | +2 |
| Wire    | 4270352        | 3325216            | -22.1% |

分模块实测：`u_awb` 2309->1059 logic LUT、2196->42 ripple、6112->623 FF；
新增 `u_wb_recip_r` 175 LUT + 1 DSP、`u_wb_recip_b` 170 LUT + 1 DSP，**0 ERAM**
（256x16 倒数表被 TD 推成 LUT ROM，没占 ERAM）。

## 时序
Setup WNS **+102 ps** / TNS 0 / 违例 S-EP **0**
Hold  WNS **+20 ps**  / TNS 0 / 违例 H-EP **0**
日志无 HDL-8007 / black box。

## 产物
- `camera_to_dsi_display.bit` 1789539 B md5 **3C619ABF75F2645323B299D4942334F6**
- `camera_to_dsi_display_compress.bit` 1394929 B md5 370A4CFF538C97C3D60ABA1969E70E72

## 数值精度（tb_wb_recip.v，ALL PASS / n_chk=1880）
典型 0.16~0.21%，最差 0.39%（相对精确整数除法）。AWB 验收带宽 ±2%，不可见。
误差根源：`m = floor(n/2^(e-8))` 的 1/256 截断。

## 回滚点
`proj\releases\2026-10-14_无调试中枢版_v2\`
（bit md5 BCC685D935EC04DB72AF123FC2D65D55）

## 注意（踩坑记录）
1. **`.al` 会被 TD 回写覆盖**。本版发现早前补进去的 `lsc.v` 从 `.al` 里消失了
   （尺寸回到 24762 B）。已把 `lsc.v`(57) 与 `wb_recip.v`(58) 一起补回。
   任何新加 `.v` 都必须同时写 `.prj` 与 `.al`，构建后要复核 `.al`。
2. `Start-Process` 起的 TD 构建会卡死在 phy_1 之前（进程活着、无输出）。
   要用普通后台任务跑 `_analysis\misc\td_run_direct.ps1`。
