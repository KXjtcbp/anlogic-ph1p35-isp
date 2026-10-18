# WORKSPACE_MAP.md — 工作区地图与交付物台账

> 本文件是「工作区在哪有什么」的单一入口。README.md 讲怎么用，HISTORY.md 讲为什么这么改，
> MOVE_INDEX.md 是从旧物理布局到现状的路径变更记录（历史，不再更新），本文件讲**现在**的结构与指标。
>
> 最后更新：2026-10-19（整理登记：transcript 已删、两个 docx 已改名、`proj/docs/官方赛题PPT截图` → `official_slides`）

---

## 一、三层结构（谁在哪一层）

| 层 | 位置 | 内容 | 谁会看 |
|---|---|---|---|
| **L1 工程层** | `proj/baseline/lab3/` | 唯一参与综合的 TD 工程（`.al`、RTL、约束、run 目录） | 我（改代码）、TD（构建） |
| **L2 分析层** | `_analysis/` | 全部脚本、仿真、构建日志、LUT 数据、诊断产物 | 我 |
| **L3 记录层** | `captures/`、`docs/`、`proj/releases/`、`inbox/` | 采集证据、团队文档、比特流归档、投递箱 | 用户、队友、评委 |

**铁律：只有 `proj/baseline/lab3/` 里的 `.v` 会被综合。** 其他任何地方的 `.v` 都是草稿或历史。

---

## 二、目录总览（顶层）

```
E:\FPGA\
├─ README.md                  仓库首页：项目简介 / 快速开始 / 数据通路 / 拨码表 / 状态
├─ HISTORY.md                 踩坑史与决策记录（改 RTL 前必读）
├─ WORKSPACE_MAP.md           ← 本文件
├─ MOVE_INDEX.md              旧路径 → 新路径映射（历史档案，35 KB）
├─ .gitignore
├─ 比赛报告_官方样板.docx      官方空白模板（只读，勿改）
├─ 比赛报告_填空版_20261018.docx 参赛报告（已填，待补实物照片与心得体会）
│
├─ proj/                      ★ L1 工程层
│  ├─ baseline/lab3/          TD 工程本体
│  │  ├─ user_source/hdl_source/     RTL 源码（含全部自研模块）
│  │  ├─ user_source/constraints_source/pin.adc  引脚约束（23 条）
│  │  ├─ td_project/camera_to_dsi_display.al     TD 工程描述（GUI 读这份）
│  │  ├─ td_project/camera_to_dsi_display.sdc    时序约束
│  │  └─ td_project/camera_to_dsi_display_Runs/  syn_1 / phy_1 运行目录（.prj 是权威）
│  ├─ releases/               ★ 比特流归档，一版一目录（27 个）
│  └─ docs/                   工程侧文档 + official_slides（官方赛题 PPT 截图）
│
├─ _analysis/                 ★ L2 分析层
│  ├─ scripts/                全部 Python 脚本（分析 / 生成 / 补丁 / 归档）
│  ├─ sim/                    ModelSim 测试台（awb / ae / lsc / motion / obj / wbrecip）
│  ├─ lut/                    LUT 数据（gamma 表、倒数表等）
│  ├─ misc/                   构建驱动脚本、补丁过的 TD 流程
│  ├─ reports/                编译清单与审计报告
│  ├─ out/                    诊断图与中间产物（不入 git）
│  └─ *.md                    设计说明与诊断报告（人工主读）
│
├─ captures/                  ★ L3 证据层（按批次目录，图片/视频 + README）
├─ docs/                      团队文档（协作指南、时间表、给 B/C 的 prompt）
├─ inbox/                     投递箱（只留 README_采集说明.txt + 采集记录.csv 两张常驻模板）
├─ 官方资料/                   芯片手册、开发板手册、原理图、例程（只读，不入 git）
├─ tools/compare/             （历史）compare.py 调色闭环
└─ _backup/                   逐轮备份（不入 git）
```

---

## 三、表 1 · 模块台账（RTL 模块 → 文件 → 作用 → 谁维护）

数据源：`proj/baseline/lab3/user_source/hdl_source/` 实际文件 + `_analysis/reports/hdl_filelist.txt`

### 3.1 自研模块（本项目新增，9 个）

| 模块 | 文件 | 所在级 | 作用 | 资源（logic LUT / ripple / FF / ERAM / DSP） | 状态 |
|---|---|---|---|---|---|
| `lsc` | `isp/lsc.v` | ISP | 镜头色彩暗角校正（20×12 双线性，只校 R/B） | 795 / 658 / 274 / 0 / 0 | ✅ 已验收 |
| `ae_stat` | `isp/ae_stat.v` | ISP | 帧亮度统计（ΣY、像素数、高/低光计数） | 264 / 175 / 268 / 0 / 0 | ✅ |
| `ae_ctrl` | `isp/ae_ctrl.v` | 控制 | AE 闭环（7bit 增益索引 → 传感器寄存器字节） | 142 / 85 / 173 / 0 / 0 | ✅ |
| `wb_recip` | `wb_recip.v` | ISP | 白平衡倒数查表除法器（替代 TD 流水除法器） | 170+174 / — / — / 0 / 2 | ✅ |
| `motion_detect` | `isp/motion_detect.v` | ISP | 帧差运动检测（16×9=144 块，只存块均值） | 1150 / 320 / 1809 / 0 / 0 | ✅ |
| `obj_detect` | `isp/obj_detect.v` | ISP | 红色目标检测（16×9 块 + 两帧确认 + 孤立块滤除 + 60 帧保持） | 855 / 220 / 878 / 0 / 0 | ✅ |
| `my_algo` | `my_algo/my_algo.v` | 算法 | 五模式风格化（灰度/伪彩/彩条/卡通化/直通） | 630 / 36 / 116 / 0 / 0 | ✅ |
| `key_mode_ctrl` | `my_algo/key_mode_ctrl.v` | 控制 | K1~K4 模式切换（去抖 + 长按） | 93 / 93 / 149 / 0 / 0 | ⚠️ 已实现未验收 |
| `isp_gamma` | `isp/isp_gamma.v` | ISP | 色调曲线（真 S：P=128,A=1.15,B=1.10,K=1） | 115 / 0 / 196 / 12 / 0 | ✅ |

### 3.2 改造的原厂模块（6 个，改动均已用 `[HDR-*]` 标注）

| 模块 | 文件 | 改动内容 | 状态 |
|---|---|---|---|
| `mipi_to_raw_converter` | `isp/demosaic_4x_2_0/mipi_to_raw_converter.v` | `BLACK_LEVEL=10'd56`、`ROUND_ADD=10'd2`、四路下溢钳位 | ✅ |
| `raw_matrix_3x3_buffer` / `demosaic` | 同目录 | 适配 40bit/4 像素输入 | ✅ |
| `isp_top` | `isp/isp_top.v` | 插入 lsc / ae_stat / motion_detect / obj_detect；修 `assign O_tdata` 悬空 | ✅ |
| `hdmi_mixer` | `hdmi_mixer.v` | 6→7 层 OSD（加运动框、目标框、参数行） | ✅ |
| `uicfgcs500_720p` | `uics500_cfg/uicfgcs500_720p.v` | `rt_exposure`/`rt_analog_gain` 改接 AE 输出 | ✅ |
| `design_top_wrapper` | `design_top_wrapper.v` | 全部顶层接线、拨码语义、`S_gain_digital=1'b1` | ✅ |

### 3.3 原厂未改动模块（依赖，不改）

`csi_unpacket_2lane`、`raw10_unpacket_2lane`、`ph1p35_324_ddr_wrapper`、`uivtc`、`video_in`、`video_out`、`uial2axis`、`mc_to_user_interface`、`hdmi_tx`、`PLL`、`awb`（已改 4 处）

---

## 四、表 2 · 资源与指标（口径 + 实测值）

**口径**：TD 报告的 `#lut6` / `#slice` 是 **6 输入 LUT 单元**（总 21216）；厂商宣传的 38189 是**等效 4 输入 LUT**。两者不可混用，本表统一用 TD 口径。
**数据源**：`proj/baseline/lab3/td_project/camera_to_dsi_display_Runs/phy_1/{route.qor, camera_to_dsi_display_phy.area}`

| 项 | 实测 | 总量 | 占用 | 备注 |
|---|---|---|---|---|
| `#slice` | **17448** | 21216 | **82.24%** | ★瓶颈★ 建议留 5% 余量 → 可用约 650 |
| `#lut6` | **16400** | 21216 | **77.30%** | |
| `#reg` | 12092 | 42432 | 28.50% | |
| `#eram` | 51 | 108 | 47.22% | |
| `#dsp` | 10 | 40 | 25.00% | wb_recip 各占 1 |
| `#IO` | 68 | 160 | 42.50% | |
| `#gclk` / `#sclk` | 9 / 21 | 32 / 48 | | |
| Setup WNS | **+104 ps** | — | — | TNS 0，违例端点 0 |
| Hold WNS | +20 ps | — | — | TNS 0，违例 0 |
| 线长 | 4 429 232 | — | — | |

**分模块（logic LUT / ripple / FF / ERAM / DSP）**

| 模块 | LUT | ripple | FF | ERAM | DSP |
|---|---|---|---|---|---|
| `u_hdmi_mixer` | 2 874 | 75 | 429 | 0 | 0 |
| `u_isp_top` | 4 708 | 1 568 | 4 674 | 34 | 10 |
| ├ `u_motion_detect` | 1 150 | 320 | 1 809 | 0 | 0 |
| ├ `u_obj_detect` | 855 | 220 | 878 | 0 | 0 |
| ├ `u_awb` | 844 | 28 | 601 | 10 | 10 |
| ├ `u_lsc` | 795 | 658 | 274 | 0 | 0 |
| ├ `u_demosaic` | 770 | 351 | 1 183 | 12 | 0 |
| ├ `u_my_algo` | 630 | 36 | 116 | 0 | 0 |
| ├ `u_ae_stat` | 264 | 175 | 268 | 0 | 0 |
| ├ `u_ae_ctrl` | 142 | 85 | 173 | 0 | 0 |
| ├ `u_isp_gamma` | 115 | 0 | 196 | 12 | 0 |
| `u_hdmi_tx` | 659 | 28 | 1 224 | 5 | 0 |

**关键指标（演示/报告用）**

| 指标 | 值 |
|---|---|
| 输入 | SC500CS，RAW10，2-lane MIPI，720p60 |
| 输出 | HDMI 1.4b，1280×720@60Hz |
| 处理延迟 | 固定流水线级数（数十拍量级），不随帧率波动 |
| AWB 整帧残差 | R/G、B/G ∈ 0.98~1.02（Y=168 场景实测 0.9854 / 0.9834） |
| LSC 效果 | 逐列 R/G 极差降 44%（0.1640 → 0.0916，四次独立验证 −43%~−46%） |
| 运动检测 | 16×9 块，DIFF_TH 12/10/3（严格）或 8/6/4（宽松） |
| 目标检测 | 红色目标，两帧确认 + 孤立块滤除 + 60 帧（1 s）跟踪保持 |
| 长期稳定性 | 15 分钟长跑 Y 漂移 0.86%，`gi` 全程 0x2E 未变 |

---

## 五、表 3 · 风险清单（按「会不会影响成绩」排序）

| # | 风险 | 触发条件 | 影响 | 状态 / 缓解 |
|---|---|---|---|---|
| R1 | **QSPI 固化未做** | 现场 | ★赛题硬性失格★（赛题解析 slide26：必须固化、上电即运行） | ⛔ **未做**；R3 待执行，见第六节 |
| R2 | AE 目标 70 在暗场景不可达 | 暗光现场 | 画面偏暗，评委观感差 | ⚠️ 已知；`gi` 已顶满 0x7F（15.75×）+ 数字增益 ×2 = 31.5× |
| R3 | 演示现场误触拨码 | 现场 | 画面突变 | ⚠️ 建议胶带封 SW3/SW4 |
| R4 | 评委问答答不出 | 答辩 | 影响印象分 | ⚠️ 需一页纸备忘 |
| R5 | `#slice` 82.24% | 再加功能 | 布线失败风险 | ⚠️ 剩余约 650 slice，A2 坐标标注大概率进不去 |
| R6 | 卡通化/按键模式未板级验收 | — | 演示时可能出意外 | ⚠️ 需一次 5 模式回归 |
| R7 | 报告缺实物照片与心得体会 | 11-04 | 报告不完整 | ⚠️ 需用户提供 |
| R8 | TD 会回写 `.al` | 用 GUI 打开保存一次 | `lsc.v`/`wb_recip.v` 等静默消失、LSC 失效且无报错 | ⚠️ 已在 `HISTORY.md` 记录；构建后必须复核 `.al` |

---

## 六、R3 · QSPI 固化路径（手册已确认）

**硬件**：板载 `N25Q128` QSPI Flash（128 Mb），**手册原文：「此 FLASH 用于 FPGA 配置」**。
引脚：`QSPI_CS=D14`、`QSPI_SDO=D1=D16`、`QSPI_WP=D2=C16`、`QSPI_HOLD=D3=A13`、`QSPI_SCLK=N6`、`QSPI_SDI=D0=E13`。

**⇒ 结论：不需要写任何 RTL 加载器**，这是 TD 官方的「烧写 Flash」流程，生成的 `.bit` 直接烧进 Flash 即可上电自启动。

**固化前检查项**
1. `.bit` md5 与 `proj/releases/` 中记录一致
2. 拔电 5 秒冷启动后功能正常（证明是 SRAM 配置下的干净状态）
3. TD 工程打开时 `camera_to_dsi_display.al` 里 `lsc.v` / `wb_recip.v` / `motion_detect.v` / `obj_detect.v` / `ae_stat.v` / `ae_ctrl.v` 六个文件各命中 1 次

**固化步骤（需在 TD GUI 里做，命令行未验证）**
1. TD → `Tools` → `Programmer`（或 `Download`）
2. 选择 `.bit` 文件 → 选 `SPI Flash` / `Program Flash` 模式
3. 确认 Flash 型号识别为 `N25Q128`
4. 执行烧写 → 等待完成
5. **断电 5 秒 → 重新上电**（不接 PC、不按复位）
6. 观察：HDMI 出图、OSD 计数递增、拨码有效

**异常处理**：若上电无输出 → 用 JTAG 重新烧 SRAM 版确认硬件没坏 → 再重试 Flash 烧写；若 Flash 识别不到 → 检查 USB-JTAG 与板子供电。

---

## 七、拨码与按键现状（最终版）

| 开关 | 引脚 | 上（逻辑 0） | 下（逻辑 1） | 代码位置 |
|---|---|---|---|---|
| SW1 | A4 | **LSC 启用** | LSC 旁路 | `design_top_wrapper.v` `S_lsc_bypass = S_sw1_sync1` |
| SW2 | B4 | **S 曲线启用** | 曲线旁路 | `S_gamma_bypass = S_sw2_sync1` |
| SW3 | E11 | **运动检测开** | 运动检测关（清空位图） | `S_mot_en = ~S_sw3_sync1` |
| SW4 | D11 | **严格档** 12/10/3 | 宽松档 8/6/4 | `S_mot_strict = ~S_sw4_sync1` |

| 按键 | 引脚 | 功能 |
|---|---|---|
| K1/K2/K3 | D5/A9/B9 | MODE 0 / 1 / 2 |
| K4 | C7 | MODE 4（卡通化，一键直达） |
| 长按任意键 ≥1 s | — | MODE 3 |

**注意：实测极性「拨下 = 逻辑 1，拨上 = 逻辑 0」与多数手册相反**，现场按表操作。

---

## 八、自检结果（本次整理）

| 项 | 结果 |
|---|---|
| 工程可打开（`.al` 存在、44 条 Verilog） | ✅ |
| 六个自研/新增 `.v` 均在 `.al` 中 | ✅ |
| `compile_check.py` | ✅ `exit=0: 42 / 43`（唯一失败是 `ph1p35_ddr\ph1p35_324_ddr_wrapper.v` 的黑盒保护，已知且无害） |
| `fill_report.py` 路径引用 | ✅ 已同步到新文件名 |
| 仓库根目录无遗留临时文件 | ✅ 只剩 4 个 md + 1 个 .gitignore + 2 个 docx |
| 综合/实现/固化路径 | ✅ 综合与实现在 `proj/baseline/lab3/td_project/` 下未被本次整理触碰；固化见第六节 |
| QSPI 固化实物验证 | ❌ **无法在无板级条件下验证**（需用户在 TD GUI 里烧 Flash） |

---

## 九、剩余工作清单见对话；本文件只负责「现状在哪里」
