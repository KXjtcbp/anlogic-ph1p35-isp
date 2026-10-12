# 工程历史沿革（HISTORY）

> 本文件保留 `E:\FPGA\proj` 在成为本仓库子目录之前、作为独立 git 仓库时的提交记录。
> 原始仓库对象完整保存在 `_backup/20261012_proj_git_history/proj.git`（已 gitignore），
> 需要查看可执行：
> ```powershell
> git --git-dir=E:\FPGA\_backup\20261012_proj_git_history\proj.git log --stat
> ```

## 项目背景

- 竞赛：全国大学生嵌入式芯片与系统设计竞赛 FPGA 创新设计赛道，选题二
  —— **基于安路 PH1P35 的实时数字图像处理系统**
- 芯片：安路 **PH1P35MDG324**（约 38184 LUT / 42432 DFF / 40 DSP / 108 ERAM / 2160 Kbit ERAM）
- 工具：TangDynasty（TD）
- 基线：安路官方例程 `lab_ex3_osd_SC500_720P`，二次开发
- 通路：MIPI 摄像头 SC500CS → FPGA → HDMI 720p60（1280×720）

## 提交记录（新 → 旧）

| 提交 | 日期 | 说明 |
|---|---|---|
| `0d1c56f` | 2026-10-04 | fix(lab3): 用 `set_max_delay -datapath_only` 约束 24m→像素域 单 bit CDC，消除最后 −20ps 违例 |
| `364d1bf` | 2026-10-03 | fix(cdc): 算法模式改为单 bit 翻转跨域协议，消除残留 0.085ns 时序违例 |
| `e562752` | 2026-10-03 | fix(algo): 修复 `f_heat` 未初始化读取导致的综合致命错误 `HDL-8007` |
| `043f927` | 2026-10-03 | fix(timing): 修复跨时钟域违例（SWNS −4.416ns）与 DSP 用满（40/40） |
| `30d16f8` | 2026-10-01 | chore(td): 补充 TD 命令行检查/构建脚本 |
| `80e5f85` | 2026-10-01 | chore(workspace): 重整工作区、清理临时文件、补全团队文档 |
| `b0a1f30` | 2026-09-28 | docs(handoff): 生成给 iCoder Agent 的交接提示词 |
| `276332a` | 2026-09-28 | docs(chip): 补齐 PH1P35MDG324 芯片完整资料（Datasheet 取证） |
| `c8e7b96` | 2026-09-27 | feat(debug): `SHOW_DEBUG` 参数把 DDR 状态直接画进 HDMI 画面 |
| `c6b85b2` | 2026-09-27 | fix(al): 删除 `.al` 中的 XML 注释，TD 解析器不支持 |
| `6440c52` | 2026-09-27 | feat(algo): 接入自研 RGB 点运算算法集与按键模式切换 |
| `230f479` | 2026-09-27 | chore: 导入官方 lab3 基线并修正工程路径为本地路径 |

## 这两条坑值得单独记住

1. **`PHY-1001 Remove keep and sweep redundant instances`（10-05）**
   `isp_top.v` 里 `assign O_tdata` 整行被误删 ⇒ 顶层输出悬空 ⇒ TD 认为整条 ISP 链路无消费者，
   在物理实现阶段把 `u_my_algo`、两个 `divider`、`awb` 的延时 BRAM、`demosaic` 的两条行缓存 BRAM
   全部当冗余扫掉（`#slices 15748 → 9041`、`#RAMs 40 → 12`、`#DSPs 9 → 1`），上板黑屏。
   **判据：综合后 `#RAMs` 必须是 40、`#DSPs` 必须是 9。变成 34/12/1 就是这段接线又出问题了。**

2. **常数乘法会被 TD 推断成 DSP**
   自研 `my_algo.v` 里写成 `r * 77` 会推断 DSP；4 像素 × 3 乘法 + 伪彩 `d * 5` 把整机 DSP
   从 9 顶到 **40/40 用满**，进而迫使 `hdmi_mixer` 的乘法改走 LUT，产生 5 个 HDMI 像素域违例
   （0.018~0.081 ns）。**改成手写移位 + 加法后不再推断 DSP。**
