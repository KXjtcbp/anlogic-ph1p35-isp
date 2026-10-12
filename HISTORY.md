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

3. **`wire` 忘了写位宽会被推断成 1 bit（2026-10-12，被 Testbench 抓到）**
   `ae_ctrl.v` 里 `wire S_gi_dec = (S_gi > S_step_n) ? (S_gi - S_step_n) : 7'd0;` 漏了 `[6:0]`
   ⇒ 被推断成 1 bit ⇒ `120−1=119` 被截成 119 的最低位 = `1` ⇒ 增益一帧从 120 掉到 1。
   现象是「增益抖动到 0 之后再也起不来」。**任何做算术的 `wire` 都必须显式写位宽。**

4. **组合逻辑"回退"导致状态机永远不动（2026-10-12）**
   `S_gi_next = !S_can_act ? S_gi : ...`，而 `S_can_act` 里含 `!S_req_pend`。
   下单那一拍 `S_req_pend` 刚刚拉高 ⇒ `S_can_act` 变假 ⇒ `S_gi_next` 组合地退回 `S_gi`
   ⇒ `S_gi <= S_gi`，增益永远不动（现象：请求发了 90 次，增益值恒为初值）。
   **修法：决策与执行必须用两个寄存器（先锁存目标 `S_gi_tgt`，下一拍再执行）。**

5. **★TD 命令行流程读的是 run 目录的 `.prj`，不是 `td_project/*.al`★（2026-10-12，第二次"假成功"）**
   往 `camera_to_dsi_display.al` 里加了 `ae_stat.v` / `ae_ctrl.v` 两条 `<File>`，
   但 `_Runs\syn_1\camera_to_dsi_display.prj`（TD 实际打开的工程文件）没同步 ⇒ 两个新模块
   **没被 analyze，被当黑盒**，日志里只有两行：
   ```
   HDL-8007 ERROR: ae_ctrl(...) is a black box in .../design_top_wrapper.v(603)
   HDL-8007 ERROR: ae_stat is a black box in .../isp_top.v(192)
   ```
   而 TD **照常跑完 place / route / bitgen 并写出了一个新时间戳的 `.bit`**；
   `route.qor` 的数字（WNS +84ps / #slices 17687 / #RAMs 60 / 线长 4703376）
   与上一轮**逐位相同** —— 因为网表压根没变。
   **判据：`*.bit` 时间戳变新 ≠ 构建成功。必须同时看 (a) 日志里有没有 `HDL-8007 ... black box`，
   (b) `route.qor` 的资源/线长数字有没有变化。**
   **对策：`_analysis/scripts/sync_al_to_prj.py` 把 `.al` 的 `<Verilog>` 清单同步进每个 run 的 `.prj`；
   `_analysis/misc/td_run_direct.ps1` 在启动前自动调用它。**

6. **★两个模块各自的 Testbench 都过，不等于它们之间的接口是对的★（2026-10-12）**
   `ae_stat.v` 的契约是 `O_luma_sum = Σ(Y × 256)`（因为它把 `77R+150G+29B` 的 `>>8` 省掉了），
   而 `ae_ctrl.v` 里 `wire [39:0] S_lsum = S_luma_sum;` 直接把它当成 ΣY 用。
   结果 `S_lsum` 恒为 `TARGET_SUM` 的 **256 倍** ⇒ 恒判"画面过亮" ⇒ 每帧降档 ⇒
   **上板现象是"拨上 AE 使能后画面越来越黑"**（Y 均值 6.24 → 2.17 → 1.12 → 0.98）。
   两个模块各自的 TB 都是 `ALL PASS`，因为它们**各自**遵守了自己那侧的约定；
   旧 TB 是直接灌 ΣY 当激励的，**恰好把这个 256 倍错误完全遮住了**。
   **对策：TB 里必须显式写出接口契约的来源（哪一行注释、哪一行加法树），
   并加一条"结果级"的回归用例（`CASE 9`：断言送到 `ae_ctrl` 手里的值真的等于 `TARGET_SUM`）。**

7. **做算术的 `wire`：既要写对位宽，也要保证溢出判断发生在截断之前**（2026-10-12）
   `ae_ctrl.v` 里
   ```verilog
   wire [6:0] S_gi_inc_raw = S_gi + S_step_n;                        // ✗ 7 位求和
   wire [6:0] S_gi_inc = (S_gi_inc_raw > 7'd127) ? 7'd127 : S_gi_inc_raw;
   ```
   `124 + 8 = 132` 先在 7 位里截成 `4`，之后 `4 > 127` 恒假 ⇒ **上限钳位形同虚设** ⇒
   增益爬到接近满档时**跳回最低档**并振荡（实测一帧从 116 掉到 4）。
   修法：`wire [7:0] S_gi_inc_raw = {1'b0,S_gi} + {1'b0,S_step_n};` 再比较。
   **这是第 3 条那个"漏写位宽"的同类问题，但更隐蔽 —— 位宽写全了也可能在中间就溢出。**

8. **参数默认值必须按"本工程的实际场景"选，不能照搬通用相机策略**（2026-10-12）
   `ae_ctrl.v` 的"暗场景护栏"原来是"近黑像素 > 25% 就停止加亮"（通用相机防止把夜景拍成灰的习惯）。
   但本工程的使用场景（宿舍、只开显示器）整帧 `<=8` 占 **65%~95%** ⇒ 该护栏恒真 ⇒
   **AE 在"本来就暗"的场景里完全不加亮，而那正是最需要加亮的时候。**
   修法：默认关闭该护栏（`LO_GUARD_SHIFT = 0`），把防削顶交给高光护栏（1.56%）。
   **可调参数要么按实测场景定标定值，要么给一个"两难时偏向哪边"的明确理由。**


---

## 新仓库（`E:\FPGA` 根）里程碑

| 日期 | 提交 | 说明 |
|---|---|---|
| 2026-10-12 | `090e148` | chore: 初始化团队共享仓库（首次导入 761 文件 / 108 MiB） |
| 2026-10-12 | `eda9f2e` | docs(team): 团队协作指南 |
| 2026-10-12 | `6ab64f8` | fix(tools): `compile_check.py` 路径可移植化（队友克隆后无需改代码） |
| 2026-10-12 | `ed4f9ee` | docs(team): 给成员 B / C 的自包含启动 Prompt |
| 2026-10-12 | `0b869ed` | docs: 仓库首页 README + 时间表修订 |
| 2026-10-12 | `8c80c2e` | feat(ae): `ae_stat.v` 帧亮度统计器 + TB（**AE 第 1 步**） |
| 2026-10-12 | `99bd620` | feat(ae): `ae_ctrl.v` 自动曝光闭环控制器 + TB（**AE 第 2 步**） |
| 2026-10-12 | `689735f` | feat(ae): AE 第 3 步 —— 接进 `isp_top` / `design_top_wrapper`，SW4 改为 AE 使能 |
| 2026-10-12 | `e204a80` | fix(tools): TD 命令行流程只认 run 目录的 `.prj` —— 新增同步脚本并接进构建入口 |
| 2026-10-12 | — | fix(ae): 修掉 AE 方向反向的三个 bug（256 倍量纲 / 增益回绕 / 暗场景护栏），TB 扩到 10 个 CASE |

**当前已验证的能力**：黑电平扣除（`BLACK_LEVEL=56`，盖镜头逐像素精确为 0）、
S 曲线（K=45 黑位版）、`my_algo` 五模式（K1–K4）、数字增益 ×2、
AWB（算法正确，但有 −3 码加性偏置待查）、**AE 闭环（代码层已修正好，待上板复验）**。

**比特流版本台账**：

| 版本 | 位置 | md5 | 说明 |
|---|---|---|---|
| K=45 基线 | `_backup/20261012_bit_K45_0149/` | `f4f9ce5ec969a7524bb0d5e609ca60d1` | 无 AE |
| AE 首版 | `proj/releases/2026-10-12_AE首版/` | `57ce384dd79433dec0e5728511c7be8c` | AE 方向反的，已作废 |
| **AE 修正版** | `proj/releases/2026-10-12_AE修正版/` | `4c75078a4c31b091a3e015dde4854b59` | **当前推荐**，WNS +95ps |
| 原厂 lab3 | `proj/releases/lab3_原厂_2026-09-10/` | — | 未改动的官方基线 |

