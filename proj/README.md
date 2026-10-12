# 全国大学生嵌入式芯片与系统设计竞赛 · 选题二 —— 工程根

**工程根**：`E:\FPGA\proj`
**基线**：官方例程 `lab_ex3_osd_SC500_720P`（lab3）
**初始化**：2026-09-27　|　**最近重整**：2026-10-01
**赛题**：基于安路 PH1P35 的实时图像处理系统（板卡 HX1P35A / 芯片 PH1P35MDG324）

---

## 当前状态（2026-10-01 实测）

| 项 | 状态 |
|---|---|
| 原厂 lab1 / lab2 / lab3 bit | ✅ 全部上板正常（720p / 61 Hz） |
| 自研算法 `my_algo.v`（4 模式）+ 按键切换 + `MODE n` 状态行 | ✅ 代码已就位，TD 分析通过（46 个源文件，无 HDL 错误） |
| **整合工程综合 + 上板** | ❌ **从未做过**（`camera_to_dsi_display_Runs\` 不存在） |
| QSPI 固化 / 上电自启 | ❌ 未做（**赛题硬性失格项**） |
| 扩展要求（至少 1 条） | ❌ 未做 |

> **下一步做什么、谁来做** → 见 `conversation_outputs\reports\下一步工作计划与三人分工_2026-10-01.md`
> **看不懂代码结构** → 见 `conversation_outputs\deliverables\项目文件地图与数据通路导读.md`

---

## 目录结构

```
E:\FPGA\proj\
├── README.md                      ← 本文件
├── INIT_LOG.md                    ← 初始化操作记录
├── baseline\lab3\                 ← 官方 lab3 全树（我们的主战场）
│   ├── td_project\
│   │   ├── camera_to_dsi_display.al     ← TD 工程入口
│   │   └── camera_to_dsi_display.sdc    ← 时序约束
│   └── user_source\
│       ├── constraints_source\pin.adc   ← 引脚约束
│       ├── hdl_source\                  ← RTL 源码
│       │   ├── design_top_wrapper.v     ← 顶层（改过）
│       │   ├── isp\isp_top.v            ← 算法接入点（改过）
│       │   ├── hdmi_mixer.v             ← OSD 合成（改过）
│       │   ├── my_algo\my_algo.v        ← ★ 自研算法
│       │   └── my_algo\key_mode_ctrl.v  ← ★ 按键切模式
│       └── ip_source\                   ← PLL / FIFO / BRAM / DDR2 等 IP
├── rtl\my_algo\                   ← 自研算法的编辑副本（与 baseline 内一致）
├── releases\                      ← ★ 里程碑 bit 归档（含 SHA256）
│   └── lab3_原厂_2026-09-10\
├── docs\                          ← 工程侧文档
│   ├── board_HX1P35B_引脚分配汇总.txt   ← 585 行引脚表
│   ├── 官方_代码更新说明.txt
│   └── 官方赛题PPT截图\            ← 基础/扩展/进阶要求三页
├── logs\                          ← TD 运行日志归档
├── scripts\                        ← TD Tcl 无头校验脚本
│   └── td_check_open.tcl
├── constraints\                   ← 预留
└── conversation_outputs\          ← ★ 所有分析与交付文档的出口
    ├── reports\                   ← 分析、计划、总结
    ├── deliverables\              ← 可直接交付的成果
    ├── probes\                    ← PDF 文本提取等中间产物
    └── imported\                  ← 历史文件归档（含 _deleted_tmp_*.tar.gz）
```

**工作区（`E:\FPGA`）顶层**：`官方资料\`（只读原始资料）、`anlogic_example\`（原厂三例程）、`.extract\`（官方文档解包纯文本，可引用行号）、`doc\hw\config.json`（插件硬件面板配置）。

---

## 基线工程要点（改工程前必读）

| 项 | 值 | 出处（行号为 2026-10-01 实测） |
|---|---|---|
| 器件 | PH1 / PH1P35MDG324 / Speed -3 | `.al` L8–10 |
| TD 版本 | 6.2.168116 | `.al` L5 |
| 顶层模块 | `design_top_wrapper` | `.al` L470–474 |
| 启动模式 | `boot_mode = mspix4`（板上 Flash = N25Q128） | `.al` `<Configurations>` |
| 时钟 | `S_100m_clk` / `S_24m_clk` / `S_hdmi_pixel_clk` / `S_hdmi_serial_clk`(375MHz) / `S_csi_rx_clk` / `S_ddr_clk` | `design_top_wrapper.v` |
| 复位 | `assign S_rst_n = S_pll_lock;` | `design_top_wrapper.v:206-207` |
| 算法插入点 | `isp_top.v` 中 `awb` 之后、`data_96bit_to_128bit` 之前（96 bit = 4 像素 × 24 bit） | `isp_top.v:54-56`、`:119-136`、`:138-149` |
| 调试状态条开关 | `.SHOW_DEBUG(0)` —— **诊断完必须改回 0** | `design_top_wrapper.v:779` |
| 按键切模式 | `key_mode_ctrl`，按键 `I_button[1]`（J14，24 MHz 域，按下为低） | `design_top_wrapper.v:445` |
| 上电默认算法模式 | MODE 2 伪彩热力图 | `isp_top.v:120`（`MODE_INIT=2`） |

**时序余量极薄**：底板 Setup WNS 仅 **+0.103 ns**，最紧路径在 `HDMI_SERIAL_CLK`（375 MHz）。
新增逻辑后若 WNS 变负，按此顺序砍：`SHOW_DEBUG` 分支 → `MODE n` 状态行 → 算法本身。

---

## 工作流（改代码 → 验证）

1. **改代码**：优先只改 `hdl_source\my_algo\my_algo.v`（纯算法，96bit 进 / 96bit 出，不碰接口）。
2. **无头分析**（1 分钟，不用上板）：
   ```
   E:\TD\bin\td_commands_prompt.exe E:/FPGA/proj/scripts/td_check_open.tcl
   ```
   期望：`PRJ-1401 : Successfully analyzed 46 source files.`
   （tcl 里的路径**必须用正斜杠**；`open_project` 会打印 7 条 `PRJ-9210` 假告警，**无害**）
3. **行为仿真**（只对纯逻辑模块）：本机有 ModelSim Altera Starter 10.3c 与 iverilog。
   ⚠️ 只能仿真 `my_algo` / `key_mode_ctrl` 这类纯 RTL，**不能仿真安路器件原语**（PLL/DDR/MIPI/TMDS 是加密 IP）。
4. **综合 + 上板**（需人类操作）：TD 界面 `Reset Run` → `Launch Runs` → BitWriter 烧录 → 屏摄。

**⚠️ 重编会覆盖 `camera_to_dsi_display_Runs\best_result\`，重要版本先另存到 `releases\` 并记 SHA256。**

---

## 版本控制

git 仓库**已初始化**（分支 `master`，`user.name=FPGA-agent`，`core.autocrlf=false`）。
建议为并行开发切分支：`feature/algo` / `feature/osd` / `feature/fix`（当前尚未切分）。

`.gitignore` 已忽略可重建产物（`**/camera_to_dsi_display_Runs/`、`*.bit`、`*.qor`、`*.area`、`*.timing` 等），
并用 `!releases/**` 保证**里程碑 bit 必须归档**。

---

## 三条"接口铁律"（踩过的坑）

1. **96 bit = 4 像素 × 24 bit**（`[95:72]`/`[71:48]`/`[47:24]`/`[23:0]`，每像素 `{R,G,B}`）。
   旧文档里"3 像素 × 32 bit"的说法**是错的**。
2. `my_algo` / `edge_detect_96` 的 **`tready` 端口方向是反的**（`input I_tready` / `output O_tready`），照抄不要改。
3. `my_algo` 有 **1 拍输出延迟**，`isp_top` 里 `O_tlast/O_tuser/O_tvalid` 必须取 `algo_O_*`，不能取 `awb_O_*`。

---

## 文件写入规则

1. 所有由对话生成的文件写入 `conversation_outputs\`：分析/计划 → `reports\`；交付物 → `deliverables\`。
2. 官方示例文件只放 `baseline\`，**不在其中就地修改**——改动走 git 提交留痕。
3. 遇到同名文件夹先询问，不擅自覆盖/合并/重命名。
