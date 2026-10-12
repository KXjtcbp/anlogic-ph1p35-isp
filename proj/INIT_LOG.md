# 初始化操作记录

**时间**：2026-09-27
**触发**：用户下达「开始项目」类初始化指令，并确认 4 项决策
**执行者**：对话 Agent（具备文件系统操作能力，直接创建，未走手动命令路径）

---

## 一、用户确认的决策

| # | 决策项 | 用户选择 |
|---|---|---|
| 1 | 工程根位置 | `E:\FPGA\proj`（推荐项） |
| 2 | `conversation_outputs/` 位置 | **两个都建**：工程根下 + 工作区顶层 |
| 3 | 既有零散产物处理 | **只搬我生成的 .md/.csv**，`.tmp-*` 等临时文件留着 |
| 4 | 官方示例复制范围 | **只复制 lab3** |

> 决策 1、3、4 与推荐项一致；决策 2 选了「两个都建」。

---

## 二、执行结果

### 2.1 目录创建（14 个）

```
E:\FPGA\proj\
├── baseline\lab3\
├── rtl\my_algo\
├── constraints\
├── releases\
├── scripts\
├── docs\
├── evidence\
├── sim\
└── conversation_outputs\{reports, deliverables, imported}\
E:\FPGA\conversation_outputs\                    （工作区总索引，平级）
```

### 2.2 官方 lab3 复制

- 源：`E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd`
- 目标：`E:\FPGA\proj\baseline\lab3`
- 命令：`robocopy <src> <dst> /E /XD camera_to_dsi_display_Runs log al_ip`
- 结果：**204 文件 / 60 目录 / 10,934,078 字节**，`FAILED=0`
- 排除项：`camera_to_dsi_display_Runs`（编译产物）、`log`、`al_ip`（IpTool 备份）
- 完整性校验：源（排除后）204 文件 / 10,934,078 字节 == 目标 204 文件 / 10,934,078 字节 ✅
- 关键文件抽查 7 项全部 OK：`.al`(22,859) / `.sdc`(1,156) / `pin.adc`(1,415) / `design_top_wrapper.v`(27,882) / `isp_top.v`(3,588) / `PLL.xml`(10,528) / `w128_d512_fifo.xml`(8,210)

> ⚠️ **被排除的 `best_result\camera_to_dsi_display.bit`（1,789,539 B）尚未备份**——首次编译会生成同名文件并覆盖原厂 bit。已记入 `README.md` 待办。

### 2.3 历史产物迁移（26 个文件）

从 `E:\FPGA\` 顶层迁入 `E:\FPGA\proj\conversation_outputs\imported\`：

- **校验前置**：先逐文件比对「目标存在 + 大小完全一致」，全部通过后才删除源文件
- **迁移方式**：复制 → 校验 → 删除源（等价于移动，但有回滚点）
- 结果：**26 文件 / 741,007 字节**，顶层剩余 `.md`/`.csv` = **0**

清单（按类型）：

| 类别 | 文件 |
|---|---|
| 分轮报告（11 份） | 第5轮(94,862) / 第6轮(34,515) / 第7轮(23,221) / 第8轮(40,439) / 第9轮(38,696) / 第10轮(44,170) / 第11轮(43,044) / 第12轮(35,749) / 第13轮(23,009) / 第14轮(26,232) / 第15轮(14,139) |
| work_* 交付物（6 份） | work_下一步工作计划(18,141) / work_比赛要求整理与执行规划(23,161) / work_项目实现与代码管理分析(37,574) / work_下载器无法连接_修复步骤(11,018) / work_lab2lab3烧录操作卡(8,475) / work_资源口径速查(4,299) |
| 台账（1 份） | work_资源与时序台账.csv(1,347) |
| 专题分析（3 份） | 工作区文件全量提炼报告(57,687) / 工作区增量核查与下一步行动_第4轮(21,585) / SC500CS_配置与控制_分析报告(7,353) / isp_analysis(7,419) |
| 选题二系列（3 份） | 选题二_备赛工作流程(79,898) / 选题二_大二知识点地图(25,482) / 选题二_执行清单与排错手册(18,635) |
| 临时件（1 份） | .tmp-round10-user.md(857) |

### 2.4 既有同名目录处理（规则 6）

`E:\FPGA\work\` 已存在（内含 `rtl\my_algo.v`，5,935 B）：
- **未覆盖、未合并、未重命名**——按规则先询问，用户选择工程根为 `proj` 而非 `work`，故无冲突
- 已将 `my_algo.v` **复制**（非移动）到 `E:\FPGA\proj\rtl\my_algo\my_algo.v`
- `E:\FPGA\work` 原目录**保留未动**，其中文件仍可访问

---

## 三、未搬动的文件（按决策 3 保留原位）

顶层仍留 19 个 `.txt` / 5 个 `.py` / 3 个 `.mjs` / 2 个 `.v` / 3 个 `.png` / 2 个 `.log` / 2 个 `.logw` / 1 个 `.json`，全部为中间提取件与调试产物，例如：
`.tmp-*`、`_tmp_pdf_*.py`、`_tmp_*.txt`、`td_*.log`、`代码更新说明.txt`、`_pin_doc_HX1P35B.txt`、`_tmp_image_correction_utf8.v`、`_tmp_uivtc_utf8.v`、三个无语义命名 `.png`

> 注：`.png` 三张（约 2.7 MB）来源不明，未识别内容，保留在原位未动。

---

## 四、初始化后的状态

| 项 | 状态 |
|---|---|
| 工程根 | ✅ `E:\FPGA\proj` 已建 |
| 标准子目录 | ✅ 9 个已建 |
| 基线工程 | ✅ lab3 全树 204 文件已就位（**但 `.al` 路径未改**） |
| 自研算法 | ✅ `rtl\my_algo\my_algo.v` 已就位（**未编译未上板**） |
| `conversation_outputs/` | ✅ 两处均已建，历史 26 文件已归入 `imported\` |
| git 仓库 | ❌ 未初始化（README 已给命令与分支建议） |
| releases/ 目录 | ⚠️ 空——原厂 bit 尚未归档 |

**待办（留给「第一步工作」）**
1. 归档原厂 lab3 bit 到 `releases\`（在任何人重编之前）
2. 改 `.al` L2 的绝对路径
3. `git init` + 两次提交（基线 / 路径修正）

---

## 五、停止点

按用户规则第 7 条：**初始化完成，停止操作，等待「第一步工作」指令，不自行推进。**

初始化期间**未执行**任何编译、烧录、git 操作；**未修改**官方源文件内容（只做复制）。

---

## 六、2026-10-01 工作区重整记录

**触发**：用户确认「三个 lab 原厂 bit 全部上板正常」（P0 黑屏问题关闭），并下达「删除无用文件 + 指导团队下一步工作」。

### 6.1 删除项（已先打包备份）

备份包：`conversation_outputs\imported\_deleted_tmp_2026-10-01.tar.gz`（111,061 B，57 个条目）

| 类别 | 内容 | 理由 |
|---|---|---|
| TD/PowerShell 临时输出 | `_tmp_td_out2.txt`、`_tmp_tdcmd*`、`_tmp_hwserver_help*`、`_tmp_anlu_flow_*`、`_tmp_swug101_*` | 一次性探查输出，内容可由官方 PDF 重新提取 |
| PDF 提取脚本与产物 | `_tmp_pdf_scan*.py`、`_tmp_readpdf*.py`、`_tmp_pdf_jtag.txt`、`_tmp_extract\`、`_tmp_pindoc\` | `.extract\` 中已有正式解包文本 |
| 官方文档文本副本 | `_tmp_qa.txt`、`_tmp_xuanti2.txt`、`_tmp_ziliao_zhiyin.txt` | 同上 |
| 源码 UTF-8 转码副本 | `_tmp_uivtc_utf8.v`、`_tmp_image_correction_utf8.v` | 原件在工程内或官方资料内 |
| 会话中间文件 | `.tmp-extract*.mjs`、`.tmp-last-user.json`、`.tmp-now-user*.txt`、`.tmp-one.mjs`、`.tmp-seqs.txt`、`.dsh-vision-toolkit\`（空） | 会话临时产物 |
| 早期工程副本 | `work\`（仅 `work\rtl\my_algo.v`，5,935 B **旧版**） | 新版 10,169 B 已在 `proj\rtl\my_algo\` 与 `baseline\...\my_algo\`（md5 一致） |

### 6.2 迁移项

| 原位置 | 新位置 | 说明 |
|---|---|---|
| 根目录 24 个 `td_2026*.log/.logw` | `proj\logs\` | TD 无头运行日志，保留取证 |
| `归档\选题二_备赛工作流程_v1_估算版.md` | `proj\conversation_outputs\imported\` | 与 `imported\选题二_备赛工作流程.md` **内容不同**，是两个版本，故并存 |
| 根目录 `_pin_doc_HX1P35B.txt` | `proj\docs\board_HX1P35B_引脚分配汇总.txt` | 585 行引脚表，XDC 基础资料。原件同源：`官方资料\9_康芯开发板\HX1P35B开发板引脚分配汇总.docx` |
| 根目录 `代码更新说明.txt` | `proj\docs\官方_代码更新说明.txt` | 官方版本说明（"三例程统一更新为 1280×720@60fps"） |
| 根目录 3 个 `*.png` | `proj\docs\官方赛题PPT截图\` | 已确认是**赛题解析 PPT 的三页截图**（基础/扩展/进阶要求），非上板屏摄 |
| 顶层 `conversation_outputs\README.md` | `proj\conversation_outputs\README.md` | 顶层该目录随之删除 |

### 6.3 保留不动

`官方资料\`（7.1 GB，含 **TD 6.2.1 安装包 1.86 GB**、ModelSim Setup 1.15 GB、芯片手册、原理图、赛题文档）／
`anlogic_example\`（280 MB 原厂三例程树）／`.extract\`（29 MB 官方文档解包纯文本，报告引用基准）／
`doc\hw\config.json`（插件硬件面板配置，必须留在工作区根）

> ⚠️ `官方资料\1_安路工具和软件\安路开发软件TD_6.2.1版本.zip` **不要删** —— 赛题要求评审环境统一 TD 6.2.1，
> 而本机装的是 6.2.168116，两者是否兼容**【待确认】**（见 6.4）。

### 6.4 本次新增的待确认项

| # | 事项 | 为何重要 |
|---|---|---|
| V5 | **TD 6.2.168116 与官方要求的 6.2.1 是否同一版本** | 若不同，"高版本工程无法向下兼容 6.2.1"会导致评委打不开工程 |
| V2 | **作品提交截止日 + 提交格式** | 工作区无任何文件记载；此前文档用的 2026-11-04 未给出出处 |
| V1 | 是否已报名成功 | 未报名则一切白做 |

### 6.5 本次产出

- `conversation_outputs\deliverables\项目文件地图与数据通路导读.md`
- `conversation_outputs\reports\下一步工作计划与三人分工_2026-10-01.md`
- 重写 `README.md`（原文中"lab3 黑屏未解决""git 未初始化""`.al` 路径未改"等已全部过期）
- `scripts\td_check_open.tcl`（TD 无头校验脚本）

