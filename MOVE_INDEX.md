# 工作区目录索引

> 更新 2026-10-23 ｜ 顶层目录与实际体积（本机实测）

## 一、哪些进 git，哪些不进

| 目录 | 体积 | 进 git | 说明 |
|---|---|---|---|
| `proj/` | 335.6 MB | ✅ | 工程本体。`baseline/lab3/` 是主战场 |
| `_analysis/` | 344.6 MB | ✅（`out/` 除外） | 脚本、LUT、仿真、报告数据。`out/` 是渲染中间产物，已 gitignore |
| `captures/` | **1 821.3 MB** | ✅ | 采集证据（图片与视频）。占仓库体积大头 |
| `docs/` | 0.1 MB | ✅ | 团队文档 |
| `tools/` | 3.1 MB | ✅ | `compare.py` 等独立工具 |
| `raw_exports/` | 0.9 MB | ✅ | ChipWatcher 导出的 CSV |
| `inbox/` | 2 个文件 | 模板进 git，图片不进 | **照片/视频投放口**，只留 `README_采集说明.txt` + `采集记录.csv` |
| `官方资料/` | **7 092.1 MB** | ❌ | 官方手册、PPT、安装包、教学视频。需单独给 |
| `anlogic_example/` | 277.8 MB | ❌ | 官方三个例程原样备份 |
| `.extract/` | 27.5 MB | ❌ | 官方文档文本提取中间产物 |
| `_archive/` | 56.6 MB | ✅ | 历史快照与过程稿 |
| `_backup/` | 24.8 MB | ❌ | 改动前的文件备份（`.before` / `.bak`） |
| `_submission/` | 48.6 MB | ❌ | 提交包打包用的中间目录（与源码重复） |
| `.git/` | **500.2 MB** | — | pack 约 265 MiB |

## 二、`proj/` 内部

```
proj/
├─ baseline/lab3/                        ← 主战场（官方 lab_ex3_osd_SC500_720P 二次开发）
│  ├─ user_source/hdl_source/            ← 全部 RTL
│  │  ├─ design_top_wrapper.v            ← 顶层（15 个子模块）
│  │  ├─ hdmi_mixer.v                    ← 8 层 OSD 叠加（本项目改动最大）
│  │  ├─ awb.v                           ← 白平衡（本项目改动）
│  │  ├─ isp/                            ← ISP 链路
│  │  │  ├─ isp_top.v                    ← ISP 链顶层
│  │  │  ├─ lsc.v                        ← ★自研：镜头色彩暗角校正
│  │  │  ├─ isp_gamma.v                  ← ★自研：真 S 曲线 LUT
│  │  │  ├─ ae_stat.v / ae_ctrl.v        ← ★自研：自动曝光
│  │  │  ├─ obj_detect.v                 ← ★自研：颜色目标检测
│  │  │  ├─ motion_detect.v              ← ★自研：块级帧差运动检测
│  │  │  ├─ wb_recip.v                   ← ★自研：倒数查表（替代 TD 除法器）
│  │  │  ├─ my_algo/                     ← ★自研：五模式风格化 + 按键切换
│  │  │  ├─ demosaic_4x_2_0/            ← 官方去马赛克（改了 black_level）
│  │  │  └─ awb/                         ← 官方 AWB 副本（★未参与综合，见下方警告）
│  │  └─ anlogic_logo_rom.v              ← 官方 Logo ROM
│  ├─ user_source/constraints_source/pin.adc   ← 引脚约束（ASCII，注释用 #）
│  └─ td_project/
│     ├─ camera_to_dsi_display.al        ← 工程文件（GUI 读这个）
│     ├─ camera_to_dsi_display.sdc       ← 时钟与 CDC 约束
│     └─ camera_to_dsi_display_Runs/     ← ★TD 只认这里的 .prj，不认 .al★
└─ releases/                             ← 33 个历史比特流（每个都带 .bit + route.qor + phy.area + readMe.txt）
```

★**警告：`isp/awb/awb.v` 与 `hdl_source/awb.v` 是两份。参与综合的是后者。**★ 曾经把改动打在没进综合的那份上，查了半天。

## 三、`_analysis/` 内部

| 子目录 | 放什么 |
|---|---|
| `scripts/` | 约 190 个 Python（图像统计、LUT 生成、打补丁、验证、文档生成） |
| `lut/` | 所有 LUT 表（`*.hex` / `*.csv` / `*.vh`）与生成脚本 |
| `sim/` | ModelSim 测试平台（`tb_*.v`）与 `run_*` 工作目录（工作目录已 gitignore） |
| `misc/` | `td_run_direct.ps1`（构建入口）、`DefaultFlow_noCWC.tcl`（去 ChipWatcher 版流程） |
| `out/` | 渲染与分析中间产物（**不进 git**） |
| `reports/` | 编译检查、时序违例解析等报告 |
| `docs/` | 早期设计文档 |
| 根目录 `*.md` | 各阶段设计与诊断文档（黑电平、色彩修复、自动曝光、LSC 等） |

## 四、`captures/` 内部

按批次建子目录，命名规则 `YYYY-MM-DD_<阶段名>/`。每批带 `README.md` 写明：拍摄时刻、场景、光照、SW1~SW4 状态、OSD 帧计数、统计数字、以及**这批图能不能用**。

★关键教训：`captures/` 里 2026-10-11 之前的基线**带采集链失真**（HDMI 采集卡把 limited 当 full 展开，每通道减 12 码再乘 1.1644），颜色数据不可用；10-11 之后 OBS 设为 Rec.709 + 扩展(Full) 才可信。★

## 五、根目录文档

| 文件 | 用途 |
|---|---|
| `README.md` | 项目门面（本文件的上层） |
| `WORKSPACE_MAP.md` | 模块台账 + 资源 + 约束 + 风险 |
| `MOVE_INDEX.md` | 本文件，目录索引 |
| `HISTORY.md` | 里程碑与踩过的坑 |
| `比赛报告_填空版_20261023.docx` / `.pdf` | 参赛报告 |
| `作品海报_20261020.pptx` / `.pdf` | A3 单页海报 |
| `系统框图_FPGA数据通路.png` | 四条通路框图 |
| `分镜检查表_20261023.docx` | 现场录制用逐段检查表 |
| `演示视频脚本_20261020.docx` | 逐段动作与台词 |
| `演示视频旁白稿_20261023.docx` | 可直接照读的旁白 |
| `给成员B_项目上手指南_20261020.docx` / `给成员C_…` | 队友上手文档 |
| `心得体会模板_20261019.docx` / `心得体会写作指引_20261021.docx` | 心得写作参考 |
| `比赛报告_官方样板.docx` | 官方原始样板（勿改） |
