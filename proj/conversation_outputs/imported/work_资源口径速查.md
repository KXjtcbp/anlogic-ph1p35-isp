# 资源口径速查（写答辩材料前必读）

## 1. 一句话规则

**只有 `camera_to_dsi_display_phy.area` 和 `route.qor` 里的数字能写进报告。**
判断依据：**这些数字后面没有星号 `*`**。

`gate.area`（综合后）里的 `#slice*`、`#with luts*`、`#reg only*` 全部带星号，而且文件自己写着：

> `* Note! The LUT and Slice count after Optimize-Gate is not the final value, Run Optimize-place for a more realistic count.`

所以综合后的 slice 数**一律不得引用**。

## 2. 器件规模：两种口径，绝不混用

| 官方口径 | 数值 |
|---|---|
| LUT4 | 38,189 |
| slice | 21,216 |
| DFF / slice reg | 42,432 |
| ERAM20K | 108 |
| DSP | 40 |
| PLL | 6 |

`21,216 × 1.8 ≈ 38,189` —— **同一批硬件的两种数法**，不是两个矛盾的数字。

- ✅ 正确：`12358 / 21216 = 58.25%`（slice 对 slice）
- ❌ 错误：`12705 / 38189 = 33.27%`（分子是 LUT1~6 混合数，分母是纯 LUT4，口径不同）

## 3. ex1 基线的四口径演变（记忆链）

```
4530 (RTL 估算)
  → 10524 (综合后未打包上界，带星号)
  → 3391  (综合后打包下界，靠 MACRO 合并，带星号)
  → 12358 (布局布线后最终值，无星号)  ← 只有这个能引用
```

**答辩时只写 58.25%。**

## 4. 时序四件套在哪看

| 数字 | 位置 |
|---|---|
| SWNS / STNS / HWNS / HTNS | `Runs\best_result\camera_to_dsi_display_phy.ts`（62 B） |
| Setup WNS / TNS | `Runs\phy_1\route.qor` |
| 布局阶段（故意不修 hold） | `Runs\phy_1\place.qor` |
| 时钟汇总 / 最差路径 | `Runs\syn_1\camera_to_dsi_display_gate.timing` |

**重要教训**：`place.qor` 里出现成百条 hold 违例（Hold WNS -270 ps、violated H-EP 541）是**正常的** —— 工具把 fix_hold 留在 route 阶段做。只有 **route 之后**仍有违例才是真问题。

## 5. ex1/ex2/ex3 最终对比（可直接用于"性能优化对比表"）

| 工程 | 后布线 slice | 占比 | DSP / ERAM | Setup WNS |
|---|---|---|---|---|
| ex1 MIPI→HDMI | 12,358 | 58.25% | 8 / 40 | +1.408 ns |
| ex2 加边缘检测 | 12,926 | 60.93% | 8 / 40 | +1.163 ns |
| ex3 加 OSD | 14,852 | 70.00% | 9 / 40 | **+0.103 ns** ⚠️ |

**三条推论（写报告时很有用）**
1. 综合后 → 后布线，slice 会涨 14%~17%（+7.6~10.1 个百分点）。
2. **算法很便宜、通路很贵**：ex1→ex2 只 +568 slice（+2.7pp），ex2→ex3 +1,926 slice（+9.1pp）。
   → 自研算法必须做在算法层，**绝不碰 DDR2 / HDMI / MIPI RX**。
3. ex1 基线就吃掉 58.25%，"资源很充裕"的说法不成立；ex3 已 70% 且余量不到 4%。

## 6. 最紧的路径在哪

`place.qor` 里 `SWNS path clock period 2666` ps → 最紧路径挂在 **`HDMI_SERIAL_CLK`（2.667 ns / 375 MHz）**上。

## 7. 引脚：哪些要自己写，哪些不用

- **要自己写**（`user_source\constraints_source\pin.adc`，共 19 行）：`I_sys_clk`=C4、`I_rst_n`=R10、`O_cam_scl`=K3、`IO_cam_sda`=J3、`O_cam_24m`=L3、`O_cam_rst`=L2、`I_button[0]`=N2、`I_button[1]`=J14、`O_screen_pwm`=R11、TMDS 四对 `G16/F17/H14/C17`（IOSTANDARD=TMDS33）。
- **不用自己写**：**MIPI 差分引脚与 DDR 引脚由硬核/控制器 IP 自动分配**（后布线报告里 ddr_addr 显示为 `S82_5`、`S82_47` 这类硬核专用位置，MIPI 用掉 1/2 个 RX 硬核）。
  → 全工作区对 `rx_clk_pad|rx_data_pad|MIPI` 搜 `*.adc/*.pin/*.fdc` 是 **0 命中**，属正常，不是缺约束。

## 8. 不要动的文件

| 文件 | 原因 |
|---|---|
| `user_source\constraints_source\timing.sdc`（0 字节） | 预留给参赛者的槽位，空的正常 |
| `ph1p35_ddr\ddr2\src\sdc\ddr2.sdc`（792 B） | DDR 控制器自带约束 |
| `td_project\camera_to_dsi_display.sdc`（17 行） | 官方已写好，"看懂即可，不要破坏" |

## 9. 两份约束不可互换（易错）

| | 2026 lab1 | `2_Example\32_cs500_mipi_hdmi`（旧） |
|---|---|---|
| 时钟名 | `I_sys_clk` / `sys_clk_50m`（20 ns = 50 MHz） | `I_sys_clk_25m`（40 ns = 25 MHz） |
| HDMI 时钟 | PLL 命名时钟 `HDMI_PIXEL_CLK` / `HDMI_SERIAL_CLK` | `S_pixel_clk` / `S_serial_clk` |
| 时钟组 | 3 组 `set_clock_groups -asynchronous` | `-exclusive` 两组 |

**不要把旧例程的 SDC 拷到 2026 例程里。**
