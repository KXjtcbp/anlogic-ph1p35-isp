# 给成员 C 的启动 Prompt

> 用途：把本文**全文**复制给成员 C（QQ / 微信 / 邮件均可）。
> 本文是自包含的：C 不需要看任何其他对话或背景。
> **前置条件**：C 必须先注册 Gitee 账号，并由 A 把他的账号加为仓库**开发者**，本文才有用。
> 仓库：`https://gitee.com/wuhu-captain-kx/fpgacnds.git`　主干：`main`
> 修订：2026-10-12

---

**你收到的任务**

你是这个 FPGA 图像处理项目的成员 C。你负责两件事：

1. **把色调曲线改成真正的 S 曲线**
2. **在画面上显示参数数值**

---

## 一、项目是什么

一块安路 PH1P35 FPGA 开发板 + MIPI 摄像头 + HDMI 显示器，做实时图像处理，参加全国大学生嵌入式芯片与系统设计竞赛。数据通路：

```
MIPI 摄像头(SC500, 1280x720@60) -> FPGA -> HDMI 显示器
```

FPGA 内部（都在 `isp_top.v` 里例化）：

```
demosaic -> data128_96 -> awb(白平衡) -> isp_gamma(色调曲线) -> my_algo(风格化) -> data96_128 -> hdmi_mixer(OSD 叠加) -> HDMI
```

**任务一改 `isp_gamma`，任务二改 `hdmi_mixer`。**

---

## 二、代码从哪来

仓库：`https://gitee.com/wuhu-captain-kx/fpgacnds.git`（私有，你的 Gitee 账号会被加为**开发者**，登录后直接能看到）。

### 第 0 步：环境准备（只需一次）

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

> 如果第一次 push 让你输账号密码，输你的 Gitee 账号即可，之后会永久记住。
> 如果报权限错误，去「控制面板 → 凭据管理器 → Windows 凭据」删掉 `git:https://gitee.com` 再试。

### 第 2 步：读三份文档

1. `docs/团队协作指南.md` —— 环境、目录说明、铁律、构建命令
2. `docs/协作流程与时间表.md` —— 时间表和你的截止日
3. `HISTORY.md` —— 这个项目的历史和踩过的坑

### 第 3 步：验证环境（硬性要求）

```powershell
# 3.1 语法体检，必须 39/40
python _analysis\scripts\compile_check.py
# 期望：exit=0: 39 / 40   失败: 1
#       唯一失败的必须是 ph1p35_ddr\ph1p35_324_ddr_wrapper.v（原厂黑盒保护）
```

```powershell
# 3.2 跑一个现成的 Testbench，必须 ALL PASS, errors=0
cd _analysis\sim\blc_gamma
mkdir run_c
cd run_c
vlib work
vlog ..\mipi_to_raw_converter.v ..\tb_blc_template.v
vsim -c -do "run -all; quit -f" tb_blc_template
```

> 如果 vlog/vlib/vsim 找不到，用完整路径，或先设
> `$env:MODELSIM_BIN = "E:\modelsim\modelsim_ase\win32aloem"`。

### 第 4 步：提「环境就绪」PR

分支名 `feat/c-onboarding`，文件写 `docs\队友C_环境就绪.md`（内容同 B：compile_check 结果 + TB 结果 + ModelSim 路径），push 后在 Gitee 网页开 PR 指派给 A。

合并后再建正式分支：

```powershell
git checkout main
git pull origin main
git checkout -b feat/gamma-scurve
```

---

## 三、任务一：把色调曲线改成真正的 S 曲线

### 3.1 现在的问题

色调曲线在 `proj/baseline/lab3/user_source/hdl_source/isp/isp_gamma.v` 里。它是一个 **256 项的查找表**（查表 = 「输入码 → 输出码」的映射，8bit 进 8bit 出）。

**当前的曲线是「反 S」**，公式是：

```
x <= 160:  y = 160 * (x/160)^0.5
x >  160:  y = 160 + 95 * (1 - ((255-x)/95)^0.5)
```

两个指数都是 **0.5（小于 1）**，所以两段都是**凹函数**：

- 暗部被**抬起来**（输入 8 → 输出 18，输入 34 → 输出 62）
- 高光被**压下去**（输入 200 → 输出 183）

结果：**画面的对比度反而下降了，发灰发闷。** 实测数据显示，开曲线后画面的动态范围从 199 码压缩到 148 码（**对比度 −26%**）。

### 3.2 你要的目标

**「真 S」**：压暗部、提高光、保留中间调。公式形式不变，只改两个指数让它 **大于 1**：

```
x <= P:  y = P * (x/P)^A                               A > 1  -> 暗部变暗
x >  P:  y = P + (255-P) * (1 - ((255-x)/(255-P))^B)   B > 1  -> 高光变亮
```

### 3.3 具体怎么做

1. 找到生成脚本（在 `_analysis/scripts/` 下，包括 `gen_gamma_lut_twosg.py`、`gen_gamma_lut_blackpoint.py` 等，先读一遍搞清楚哪个是当前在用的）。
2. **起始参数建议：拐点 P = 128，指数 A = 1.15、B = 1.10**。不要一次调很猛，先出一版看效果。
3. 重生成表，然后**把表写回 `isp_gamma.v` 的内联 `initial` 块**（在文件里搜 `mem_b00`）。

### 3.4 ★必须知道的坑★

**(a) 不要「优化」成 `$readmemh`。**

`isp_gamma.v` 用的是**把 256 个数值直接写在 Verilog 源码里的内联表**，不是从外部文件读。

原因是 TD 综合时的工作目录是 `..._camera_to_dsi_display_Runs\syn_1\`，相对路径读不到你的 `.hex` 文件，**而 TD 不会报错、不会警告 —— 表会全部变成 0，综合和时序报告全都正常绿，但烧到板子上是全黑画面。** 这个坑在这个项目里踩过。

**(b) 必须同步改 TB 的 `\`include`。**

Testbench `_analysis/sim/blc_gamma/tb_gamma_bp.v` 是通过 `\`include` 引一个 `.vh` 文件来拿真值的。**你改了 `isp_gamma.v` 的表，必须同步改 TB 里 `\`include` 指向的那个 `.vh` 文件**，否则 TB 会报 3000 多个 FAIL —— 那是假故障，不是你的代码错。

**(c) 别碰流水延迟。**

`isp_gamma` 的流水线延迟是**固定的 2 拍**（第 1 级组合查表 + `d1` 打拍；第 2 级 `q2 <= bypass ? d1 : rom_q`）。整条 ISP 链路上下游的同步信号（tlast/tuser/tvalid）都是按这 2 拍对齐的，**必须保持 2 拍不变**。加流水级必须同时改 `isp_top.v` 里 `assign O_tlast = gam_O_tlast;` 的对齐关系，很危险，别做。

### 3.5 ★离线验收标准（不用板子就能验）★

改完表之后，把 256 个输出值打印出来，逐条对照：

| 检查项 | 要求 | 为什么 |
|---|---|---|
| `LUT[0]` | = 0 | 纯黑必须还是纯黑 |
| `LUT[255]` | = 255 | 纯白必须还是纯白 |
| `LUT[128]` | 落在 **124 ~ 132** | 中间调基本不动 |
| `LUT[32]` | **< 32** | 暗部被压暗（真 S 的核心特征） |
| `LUT[200]` | **> 200** | 高光被提起（真 S 的另一个核心特征） |
| 单调性 | 严格不减（`LUT[i] <= LUT[i+1]`） | 非单调会产生假轮廓 |
| 唯一值个数 | ≥ 200（256 个输入里） | 不要出现大片重复码（会断层） |

**这七条全过了再提交 PR。** 一条不过就别提，省得 A 白烧一次板子。

### 3.6 上板后的验收（A 来测）

曲线开/关两张对比：

| 指标 | 曲线关（基准） | 真 S 曲线开（期望） |
|---|---|---|
| `Y≤8` 的像素占比 | 1.5% | **上升到 3% ~ 8%**（暗部确实被压下去了） |
| 中位数 p50 | 40 | **保持 36 ~ 44**（中间调不动） |
| p90 | 123 | **上升到 130 ~ 150**（高光提起） |
| `≥250` 过曝占比 | 0.001% | **不超过 0.5%**（不能爆高光） |

---

## 四、任务二：在画面上显示参数数值

### 4.1 背景

**比赛要求原话**：

> 利用板载开关或按键调节显示参数（如亮度、对比度等），并在画面上呈现参数变化信息。

现在的 OSD（画面上叠加的文字）**只有两条**：

- 黄色 `安路 CNT:005858`（帧计数器，位置约 x=375 y=120，尺寸 200×24）—— 常量 `COLOR_DYN_TEXT = 24'hfff200`
- 绿色 `MODE 0`（当前算法模式，位置约 x=176 y=176，尺寸 84×10）—— 常量 `COLOR_ALG_TEXT = 24'h00ff88`

**画面上一个参数数值都没有。** 你要加一行，把当前生效的参数显示出来。

### 4.2 具体怎么做

1. 读 `proj/baseline/lab3/user_source/hdl_source/hdmi_mixer.v`，找到画 `MODE n` 那一段（搜 `COLOR_ALG_TEXT`）。照它抄一个新区块：定一个新颜色常量、一个新的 X/Y 坐标（建议放在 CNT 那一行的下面，比如 y≈150），和一段新的地址生成逻辑。
2. 字符点阵库在 `osd_char_lib.v`（16×16 点阵），搜一下已有字符的编码方式，把 0-9 和字母的码补上。
3. **要显示的内容**（先用现有信号，不要新增参数寄存器）：
   - 黑电平值（当前是 56，来自 `mipi_to_raw_converter.v` 的 `BLACK_LEVEL` 常量）
   - 曲线开/关状态（来自 `design_top_wrapper.v` 里的 `S_gamma_bypass`，1=关 0=开）
   - 当前增益档（来自 `S_gain_high` / `S_gain_digital`，四个组合对应 4.000× / 8.000× / 15.750× / 31.500×）

### 4.3 ★绝对不要新增乘法器★

`hdmi_mixer` 的逻辑锥**已经深到 13 级**，历史上因为这里新增了乘法（被 TD 推断成 DSP），直接产生了 **28 个时序违例**。

- 不要写 `S_addr = y * 200 + x` 这类表达式 —— 用移位和加法拼（这正是 `anlogic_logo_rom` 那边的做法）。
- 不要用 `*`、不要用除法、不要用取模。
- 显示数字用**逐位查表**：从寄存器里把每一位拆出来，分别查字符库，不要走「整数转字符串」。

**提交前自查**（这条命令会误报注释和位宽声明，人工过一遍）：

```powershell
grep -nE "[a-zA-Z0-9_\]\)]\s*\*\s*[a-zA-Z0-9_\(]" proj\baseline\lab3\user_source\hdl_source\hdmi_mixer.v
```

### 4.4 验收标准

拨动 SW1（黑电平旁路）、SW2（曲线旁路）、SW3/SW4（增益），画面上的数字/文字**必须在 1~2 帧内跟着变**。开关在像素时钟域每周期采样，拨动后会立刻生效。

---

## 五、禁区（碰了会被打回）

1. **不要改 `mipi_to_raw_converter.v` 的 `BLACK_LEVEL`**（现在 `10'd56`，实测标定值，翻过两次车）。
2. **不要改 `design_top_wrapper.v` 里 `S_blk_bypass` 的极性**（同样翻过车）。
3. **不要改 `awb.v`**（那是成员 B 的地盘）。
4. **不要在像素域新增乘法器**（见 4.3）。
5. **不要把内联 LUT 改成 `$readmemh`**（见 3.4a）。
6. **不要改 `isp_gamma` 的 2 拍流水延迟**（见 3.4c）。
7. **不要改 `isp_gamma.v` 的 `I_tready`/`O_tready` 反压写法**（现在是 `assign I_tready = O_tready;`，全链无反压，改了会破坏流水）。

---

## 六、你必须交付的四样东西

1. **你的分支**：`feat/gamma-scurve`（不要直接推 `main`；动了 `design_top_wrapper.v` 就在 commit 首行写 `TOUCHES: design_top_wrapper.v`）。
2. **ModelSim 完整日志**：`ALL PASS` + `errors=0`。
3. **`compile_check.py` 输出**：`exit=0: 39 / 40`。
4. **改动说明**，回答五个问题：
   - 改了哪些文件的哪些行？
   - 每处为什么改？
   - **烧到板子上应该看到什么？** 摄影语言（「暗部更黑、高光更亮、中间调不动」）+ 可测数字（「`Y≤8` 占比从 1.5% 升到 5% 左右」）。
   - 哪些地方不应该变？
   - 哪里没验证？

**另外单独交一张表**：改后的 256 个 LUT 值，以及 3.5 那七条离线验收标准逐条的判定结果（过 / 不过 + 实际数值）。

**截止时间**：任务一 **10 月 22 日**，任务二 **10 月 28 日**。

---

## 七、卡住了怎么办

在 QQ 群里发：你想做什么 / 敲了哪条命令 / **完整报错原文** / 试过什么。

**不要**在没跑通 TB 的情况下说「应该没问题」—— 这个项目里每一个「应该没问题」最后都出了问题。
