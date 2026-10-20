# 给成员 B 的启动 Prompt

> 用途：把本文**全文**复制给成员 B（QQ / 微信 / 邮件均可）。
> 本文是自包含的：B 不需要看任何其他对话或背景。
> 仓库：`https://gitee.com/wuhu-captain-kx/fpgacnds.git`　主干：`main`
> 修订：2026-10-12

---

**你收到的任务**

你是这个 FPGA 图像处理项目的成员 B。任务是把**自动白平衡（AWB）修准**，让画面的三个颜色通道真正对齐。

---

## 一、项目是什么

一块安路 PH1P35 FPGA 开发板 + MIPI 摄像头 + HDMI 显示器，做实时图像处理，要参加全国大学生嵌入式芯片与系统设计竞赛。数据通路是：

```
MIPI 摄像头(SC500, 1280x720@60) -> FPGA -> HDMI 显示器
```

FPGA 内部的数据通路（都在 `isp_top.v` 里例化）：

```
demosaic(去马赛克) -> data128_96(位宽转换) -> awb(白平衡) -> isp_gamma(色调曲线) -> my_algo(风格化) -> data96_128 -> HDMI
```

**你只负责 `awb` 这一个模块。** 代码在 `proj/baseline/lab3/user_source/hdl_source/isp/awb/`。

---

## 二、代码从哪来

仓库：`https://gitee.com/wuhu-captain-kx/fpgacnds.git`（私有，你的 Gitee 账号已被加为**开发者**，不用再申请权限，登录后直接能看到）。

### 第 0 步：环境准备（只需一次）

打开 PowerShell：

```powershell
git config --global user.name  "你的名字或Gitee用户名"
git config --global user.email "你的Gitee邮箱"

# 这条必做：仓库里的源文件是 GBK/CRLF 混合的，开着 autocrlf 会把它们改坏
git config --global core.autocrlf false
git config --global core.quotepath false
```

### 第 1 步：克隆

```powershell
cd <你想放代码的目录>
git clone https://gitee.com/wuhu-captain-kx/fpgacnds.git
cd fpgacnds
git log --oneline -3
```

期望看到三行，最新一行是 `1ba55c1 docs(team): 时间表修订 ...`。

> 如果第一次 push 让你输账号密码，输你的 Gitee 账号即可，之后会永久记住。
> 如果报权限错误，去「控制面板 → 凭据管理器 → Windows 凭据」删掉 `git:https://gitee.com` 再试。

### 第 2 步：读三份文档（都在你刚克隆下来的仓库里）

1. `docs/团队协作指南.md` —— 环境、目录说明、铁律、构建命令
2. `docs/协作流程与时间表.md` —— 时间表和你的截止日
3. `HISTORY.md` —— 这个项目的历史和踩过的坑

### 第 3 步：验证环境（硬性要求，跑不通不要往下走）

```powershell
# 3.1 语法体检，必须 39/40
python _analysis\scripts\compile_check.py

# 期望输出：
#   REPO = <你的克隆目录>
#   exit=0: 39 / 40   失败: 1
#   唯一失败的必须是 ph1p35_ddr\ph1p35_324_ddr_wrapper.v
#   （这是原厂黑盒保护，不是错误）
```

```powershell
# 3.2 跑一个现成的 Testbench，必须 ALL PASS, errors=0
cd _analysis\sim\blc_gamma
mkdir run_b
cd run_b
vlib work
vlog ..\mipi_to_raw_converter.v ..\tb_blc_template.v
vsim -c -do "run -all; quit -f" tb_blc_template
```

> 如果 vlog/vlib/vsim 找不到，说明 ModelSim 不在 PATH 里。用完整路径，例如
> `& "E:\modelsim\modelsim_ase\win32aloem\vlog.exe"`，或者先设环境变量
> `$env:MODELSIM_BIN = "E:\modelsim\modelsim_ase\win32aloem"`。

### 第 4 步：提一个「环境就绪」PR（今晚就做）

目的不是改代码，是**把整条权限链路和命令流程跑通一次**：

```powershell
git checkout -b feat/b-onboarding
# 新建 docs\队友B_环境就绪.md，写三行：
#   # 队友 B 环境就绪
#   - compile_check.py: exit=0: 39 / 40
#   - tb_blc_template: ALL PASS, errors=0
#   - ModelSim 路径: <你的路径>
git add docs/队友B_环境就绪.md
git commit -m "docs(onboarding): 队友B环境就绪"
git push -u origin feat/b-onboarding
```

推完去 Gitee 网页，点「新建 Pull Request」，源分支选 `feat/b-onboarding`，目标 `main`，指派给 A。**A 合并后你才算正式接入。**

---

## 三、你真正要解决的问题

**现象**：白平衡没把三个通道拉平。实测（用 HDMI 采集卡截的图，已扣掉 OSD 文字区域）：

| 场景 | 亮度均值 | R/G | B/G |
|---|---|---|---|
| 均匀灰面（最干净的判据） | 43 | **0.9295** | **0.9327** |
| 室内常光（增益 31.5×） | 58 | 0.9471 | 0.9497 |
| 室内常光（增益 31.5×，开曲线） | 69 | 0.9641 | 0.9565 |
| 室内常光（增益 15.75×） | 41 | 0.9387 | 0.9290 |
| 暗场景 | 20 | 0.8825 | 0.9100 |

**灰世界（grey world）AWB 的定义就是：把整帧的三通道均值拉成相等。** 所以上面每一行的 R/G 和 B/G 都**应该精确等于 1.000**。实测差 3~12%。

**更关键的发现** —— 把上表换算成「绝对码差」：

| 场景 | R−G | B−G |
|---|---|---|
| 均匀面 Y=43 | **−3.157** | **−3.015** |
| 31.5× 曲线关 Y=58 | **−3.165** | **−3.007** |
| 31.5× 曲线开 Y=69 | −2.547 | −3.086 |
| 15.75× 曲线开 Y=41 | −2.608 | −3.019 |
| 暗场景 Y=20 | −2.575 | — |

**R−G 和 B−G 是恒定的 −2.6 ~ −3.2 码，跟画面亮度基本无关。**

→ 这说明它**不是「增益倍数不够」**（那样残差会随亮度成比例变化），而是**一个固定的加性偏置**。R 和 B 通道各比 G 低约 3 码。

这个偏置也解释了「越暗越绿」：同样 3 码，在亮度 20 的画面里占 15%，在亮度 60 的画面里只占 5%。

**已经排除的可能（不要重复查，会浪费时间）**：

1. ~~AWB 的数学公式错了~~ —— 已用 ModelSim 证明：喂一整帧 R=80/G=100/B=90（输入 R/G=0.800），输出 R/G = **1.0000**（精确）。灰世界公式、Q16 定点、`(R*g)>>16` 的饱和判据，全部正确。
2. ~~TD 除法器 IP 有问题~~ —— 已用门级仿真（`_analysis/sim/awb/tb_div_pattern.v`）测过 4 种 `start` 占空比（含真实的 `1,1,0` 图案），商永远正确、`done` 照常拉高。
3. ~~增益在每帧开头被重置成 1.0×、永远追不上~~ —— 已逐行读过 `awb.v` 的增益块，逻辑是「跨帧保持 + 每帧向目标走 1/4」，数学上必然收敛。
4. ~~HDMI 采集链把颜色改了~~ —— 已用 FPGA 内置的安路 logo ROM（每个像素的精确 RGB 已知）验证过，采集链是 identity，色差只有 1~3 码。

**这就是你的任务：找出这个 −3 码的加性偏置来自哪里，并修掉它。**

---

## 四、第一步该做什么（必做，不要跳）

**用真实的激励图案重建 AWB 的 Testbench。**

历史上这个项目写过的 AWB TB（`_analysis/sim/awb/tb_awb_means.v` 等）用的激励都是**连续 64 拍 valid**。但真实数据通路的 valid 图案不是这样 —— `data128_96` 输出的是 **`1,1,0` 循环（2/3 占空比）**，而且每拍是**4 个像素打包在 96bit 里**（每个像素 `{R[23:16], G[15:8], B[7:0]}`，4 个像素分别对应 `awb.v` 里的 4 组通道）。

所以要做的是：

1. 复制一份 `tb_awb_means.v`，改成用 **`1,1,0` 的 valid 图案**驱动 DUT；
2. 输入一整个 1280×720 帧（或至少几千个 beat），像素值取**恒定** R=80/G=100/B=90；
3. 统计**输出**这一帧的 R、G、B 均值**和绝对差 R−G、B−G**；
4. 看能不能复现出 −3 码左右。

- **如果复现出来了** —— 你手上就有一个离线的、可反复运行的最小复现，接下来慢慢二分定位（改哪一行能让偏差变小）。
- **如果复现不出来** —— 那说明问题不在 `awb.v` 本体，而在它和上下游的交互（比如 `signal_delay` 的时序、或者 `isp_top.v` 里的例化）。这本身也是极有价值的信息。

**运行参考**（门级仿真需要 AL 原语库，顺序不能乱）：

```powershell
vlib work
vlog "E:\TD\sim_release\common\al_phy_glbl.v" `
     "E:\TD\sim_release\common\al_map_basic.v" `
     "E:\TD\sim_release\common\al_map_lut.v" `
     "E:\TD\sim_release\common\al_map_adder.v" `
     "E:\TD\sim_release\common\al_map_alu2b.v" `
     "E:\TD\sim_release\common\al_map_mux4.v" `
     "E:\TD\sim_release\common\al_map_seq.v" `
     <divider_gate.v 的路径> <sim_blk_mem_gen_awb_delay_signal.v 的路径> `
     <signal_delay.v 的路径> <awb.v 的路径> <你的 tb.v>
vsim -c -do "run -all; quit -f" glbl <你的tb名>
```

**注意两个坑**：

1. `glbl` 必须显式作为顶层传进去，否则报 `vsim-3043 Unresolved reference to 'glbl'`；
2. `glbl` 的定义在 `al_phy_glbl.v` 里，**不在** `glbl.v`（那个文件不存在）。现成的 `_analysis/sim/awb/glbl.v` 可以用。

---

## 五、第二步：定位候选方向

复现出来之后，按这个顺序试（每个都单独做一次 TB，看 R−G 怎么变）：

1. **把 `(R * gain) >> 16` 改成 `(R * gain + 32768) >> 16`**（加四舍五入）。
   这是最常见的定点截断偏差来源。截断会让 R/B 平均低 0.5 码，G 因为乘以 1.0 不受影响 —— 方向和现象一致，但**幅度只有 0.5 码，解释不了 −3**。先做这一步是因为它便宜，能快速告诉你「偏差的量级对不对」。

2. **给累加器加亮度门限**：`if (I_tvalid_r0 && (rgb_sum >= TH))` 才累加，排除近黑像素。
   `awb.v` 现在的累加器**没有任何亮度门限**（文档里说的 `rgb_sum < 720` 条件在这个版本里不存在，我核对过）。近黑像素本身值很小，任何定点误差在它们身上的**相对占比都最大**，把它们排除掉有可能显著改善。

3. **检查 4 组通道的对齐**：`awb.v` 里有 4 组独立的累加器和 4 个独立的除法器（对应 4 个 Bayer 相位）。分别在 `awb.v` 里搜 `sum_r`、`done[`、`in_r_tgt`、`in_r_r1`。确认第 N 组的增益**确实只作用在第 N 组像素**上，不要错位一格。

4. **检查 `signal_delay` 的延迟量**：它用的是 `DELAY_CYCLE(50)`，但实际读使能在 `h_cnt == DELAY_CYCLE - 3` 拉高 —— 也就是**真实延迟是 47 拍，不是 50**。确认这个 3 拍的差不会让「用于计算的像素」和「应用增益的像素」错位。

---

## 六、禁区（碰了会被打回）

1. **不要改 `mipi_to_raw_converter.v` 里的 `BLACK_LEVEL`。** 它现在设成 `10'd56`，是实测标定值，有 Testbench 覆盖（`ALL PASS, errors=0`）。这个参数在这个项目里翻过两次车了。
2. **不要改 `design_top_wrapper.v` 里 `S_blk_bypass` 的极性。** 同样翻过车。
3. **不要在 RTL 里写 `a * b` 这种乘法表达式。** TD 会把它推断成 DSP 硬核。这块芯片只有 40 个 DSP，历史上一次不小心把整机 DSP 顶到 40/40 用满，还连锁造成 5 个时序违例。要乘常数就手写移位 + 加法。
4. **不要引入新的 IP 核**（比如再例化一个除法器）。资源够用，但新 IP 会改变时序收敛。
5. **不要改 `isp_gamma.v`**（那是成员 C 的地盘）。
6. **不要动 `awb/divider/` 下面的 `divider_gate.v`** —— 那是 TD 自动生成的门级网表，改了没用，下次综合会被覆盖。

---

## 七、你必须交付的四样东西

每次提交 PR，PR 描述里必须齐全：

1. **你的分支**：`feat/awb-robust`（不要直接推 `main`）。
   如果动了 `design_top_wrapper.v`，**commit message 首行必须写** `TOUCHES: design_top_wrapper.v`。
2. **ModelSim 完整日志**：`run -all` 的输出，必须出现 `ALL PASS` 和 `errors=0`。日志文件放进 `_analysis/sim/awb/` 下。
3. **`compile_check.py` 的输出**：必须是 `exit=0: 39 / 40`，唯一允许失败的是 `ph1p35_ddr\ph1p35_324_ddr_wrapper.v`。
4. **一份改动说明**，回答五个问题：
   - 改了哪些文件的哪些行？
   - 每处为什么改？
   - **烧到板子上应该看到什么？** 用两种话各说一遍 —— 摄影语言（「画面不再发绿」）+ 可测数字（「均匀灰面的 R/G 从 0.93 变成 0.99 以上」）。
   - **哪些地方不应该变？**（回归基线）
   - 哪些地方你**没能验证**？

第 3、4 条特别重要：A 手上只有一块板子，每次烧录只能验一次。你说不清「应该看到什么」，A 就得反复烧，一周的进度就没了。

---

## 八、验收标准

| 项 | 标准 |
|---|---|
| ModelSim | `ALL PASS, errors=0` |
| 语法体检 | `exit=0: 39 / 40` |
| 上板（A 来测） | 均匀灰面实拍的 R/G、B/G 落在 **0.98 ~ 1.02** |
| 上板（A 来测） | 真实场景的 \|R−G\|、\|B−G\| **≤ 1.5 码** |
| 上板（A 来测） | 画面上/中/下三段的 R/G 极差 **< 0.01**（说明全画面均匀校正） |

**截止时间：10 月 22 日**（第二个 PR）。今天（10-12）晚上先交「环境就绪」PR。

---

## 九、卡住了怎么办

不要一个人憋。直接在 QQ 群里发：

- 你想做什么
- 你敲了哪条命令
- **完整的报错原文**（不要截断、不要转述）
- 你已经试过什么、结果如何

**不要**在没跑通 TB 的情况下说「应该没问题」—— 这个项目里每一个「应该没问题」最后都出了问题。
