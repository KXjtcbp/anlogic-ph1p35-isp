# 基于安路 PH1P35 的实时数字图像处理系统

> 全国大学生嵌入式芯片与系统设计竞赛 · FPGA 创新设计赛道 · 选题二
> 芯片 PH1P35MDG324（38184 等效 LUT / 42432 DFF / 40 DSP / 108 ERAM）
> 工具 TangDynasty V6.2.168116 ｜ 截至 **2026-10-23**

## 这是什么

一条从 MIPI 摄像头到 HDMI 显示器的完整实时视频通路。**所有图像处理算法与时序控制都写在 FPGA 内部，不含任何额外处理器**，全链路无帧级缓存，处理延迟是固定流水线级数。

```
SC500CS ── MIPI D-PHY RX ── CSI 解包 ── RAW10 解包（40bit / 4 像素）
                                              │
   ┌──────────────────────────────────────────┘
   │  图像处理通路（ISP 域 60 MHz，AXI4-Stream 逐拍握手）
   ▼
demosaic ─ data128_96 ─ lsc ─ awb ─ isp_gamma ─ my_algo ─ data96_128
   （BGGR）            （暗角） （含 wb_recip）（真 S 曲线）（五模式）   │
                                                                      ▼
                              DDR2 帧缓存 ─ uivtc(720p60) ─ hdmi_mixer(8 层 OSD) ─ HDMI 1.4b
                                                                      │
              旁路观察者（只收不发，不占主流水线节拍）                  ▼
              ae_stat（帧亮度统计）／ obj_detect（颜色目标）      显示器 1280×720@60
              motion_detect（块级帧差）
```

系统框图见 `系统框图_FPGA数据通路.png`；模块级台账见 `WORKSPACE_MAP.md`；目录导航见 `MOVE_INDEX.md`。

## 现在什么状态

| | |
|---|---|
| **交付比特流** | `proj/releases/2026-10-18_a2_hold60/camera_to_dsi_display.bit`<br>**md5 `DB39A5CEB2D0D9A11C797EA6712708CA`**（1 789 539 B） |
| **已固化到板上** | ✅ QSPI Flash（BitWriter Program Flash，断电自启） |
| **报告** | `比赛报告_填空版_20261023.docx` / `比赛报告_20261023.pdf` |
| **演示素材** | `演示视频脚本_20261020.docx`、`演示视频旁白稿_20261023.docx`、`分镜检查表_20261023.docx` |
| **海报** | `作品海报_20261020.pptx` / `.pdf`（A3 单页） |

**已实现并被实测验证的功能**：黑电平扣除、BGGR 去马赛克、灰世界白平衡、镜头色彩暗角校正（LSC）、自动曝光（AE 闭环）、真 S 曲线、五模式风格化（直通 / 灰度 / 伪彩 / 五段彩条 / 卡通化）、块级运动检测（OSD 描框）、颜色目标检测（两帧确认 + 孤立块滤除 + 60 帧保持）、8 层 OSD、两行实时遥测。

## 关键数字（交付版实测，非估算）

| 指标 | 数值 |
|---|---|
| 分辨率 / 帧率 | 1280×720 @ 60 fps，帧计数与墙钟误差 < 0.3% |
| Slice | 17 448 / 21 216 = **82.24%** |
| LUT6 | 16 400 / 21 216 = **77.30%** |
| DFF | 12 092 / 42 432 = 28.50% |
| ERAM | 51 / 108 = **47.22%** |
| DSP | 10 / 40 = 25.00% |
| Setup WNS | **+104 ps**（TNS 0，违例 0） |
| Hold WNS | **+21 ps**（TNS 0，违例 0） |
| 帧级缓存 | 0（除 DDR2 链路的整帧外无额外帧存） |

★**口径提醒**：TangDynasty 报的 `#lut6` 总量是 **21 216 个 6 输入 LUT**，与芯片宣传的 38 189 **等效 4 输入 LUT** 不是同一个单位，两个数字不能混用。本仓库所有百分比都按 TD 口径。**

## 拨码与按键

★实测极性：**拨下 = 逻辑 1，拨上 = 逻辑 0**（与开发板手册的标注相反）★

| 开关 | 引脚 | 拨上 | 拨下 |
|---|---|---|---|
| SW1 | A4 | LSC 校正**启用** | LSC **旁路** |
| SW2 | B4 | S 曲线**启用** | S 曲线**旁路** |
| SW3 | E11 | 运动检测**启用** | 运动检测**关闭**（位图清空） |
| SW4 | D11 | 运动灵敏度**严格**（DIFF 12 / FLOOR 10 / 3 帧） | **宽松**（8 / 6 / 4） |

| 按键 | 引脚 | 功能 |
|---|---|---|
| K1 | D5 | MODE 0 原图直通 |
| K2 | A9 | MODE 1 灰度（BT.601 加权） |
| K3 | B9 | MODE 2 伪彩热力图 |
| K4 | C7 | MODE 4 卡通化 |
| 任意键长按 ≥1 s | — | MODE 3 五段彩条 |

## 怎么跑起来

**上板**：只接电源 + HDMI，上电约 10 秒画面自动出来，不需要 PC。

**重新构建**（需要 TangDynasty 与硬件 license）：

```bash
# 1. 语法回归（期望 42/43，唯一失败是官方 DDR 黑盒保护，属正常）
python _analysis/scripts/compile_check.py

# 2. 综合 + 布线（约 5 分钟）
pwsh -ExecutionPolicy Bypass -File _analysis/misc/td_run_direct.ps1 syn_1 phy_1
```

★**四条成功判据，缺一不可**★：① 日志里无 `HDL-8007` / 无 black box；② 目标模块在 `*.area` 里搜得到；③ `route.qor` 里 Setup WNS > 0 且 TNS = 0 且违例 = 0；④ `#RAMs` = 51、`#DSPs` = 10（数值突变说明模块被当冗余扫掉了）。

★**新增 `.v` 文件必须同时写三处**：`td_project/camera_to_dsi_display.al`、`td_project/camera_to_dsi_display_Runs/syn_1/*.prj`、`.../phy_1/*.prj`。TD 命令行只认 run 目录的 `.prj`，不认 `.al`；而 TD GUI 保存时会用 `.al` 回写 `.prj`。这是本项目踩过三次的坑。**

## 30 秒版本回滚

所有历史比特流都在 `proj/releases/`（**33 个目录，每个都带 `.bit` + `route.qor` + `phy.area` + `readMe.txt`**）。

★**所有 `.bit` 都是 1 789 539 B，大小对不能证明版本对，必须比 md5**★

| 用途 | 目录 | bit md5 |
|---|---|---|
| **当前交付版** | `2026-10-18_a2_hold60` | `DB39A5CEB2D0D9A11C797EA6712708CA` |
| 已知良好，可回滚 | `2026-10-18_a2_hold` | `8F17896E045B770AECE1E0AA75CA692C` |
| 已知良好（P0 闭环最干净基线） | `2026-10-17_baseline_p0_closed` | `6CB52C8463FB6E96A7EC7DE69AE6E754` |
| 原厂基线（未改过） | `lab3_vendor_2026-09-10` | `B12FF9AE…` |

烧完必须**拔电 5 秒**重新上电（不是按复位键），因为摄像头 init 表与传感器状态只在冷启动时重来。

## 还需要做的事

| 项 | 状态 |
|---|---|
| 报告 §3.1 系统实物照片 / §3.2.2 开发板照片 | ⬜ 待拍（清单见对话记录） |
| 三个创新关键词 | ⬜ 待定稿 |
| 提交表单（GitHub 链接 `https://github.com/KXjtcbp/anlogic-ph1p35-isp`） | ⬜ 待填 |
| 演示实拍视频 | ⬜ 计划 10-31 实验室录制 |

## 目录速查

| 想找 | 去 |
|---|---|
| RTL 源码 | `proj/baseline/lab3/user_source/hdl_source/` |
| 约束（引脚 / 时序） | `proj/baseline/lab3/user_source/constraints_source/pin.adc`、`td_project/*.sdc` |
| 交付与历史比特流 | `proj/releases/`（33 个） |
| 分析脚本（约 190 个） | `_analysis/scripts/` |
| LUT 表 | `_analysis/lut/` |
| 仿真 TB | `_analysis/sim/` |
| 采集证据 | `captures/` |
| 交付文档 | 仓库根目录 |

完整导航见 `MOVE_INDEX.md`。
