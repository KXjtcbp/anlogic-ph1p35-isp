# FPGA 下一步工作计划（2026-09-26 起）

红线：**2026-11-04 上传作品**。报告与视频你自己处理，本文件不涉及。
三条例程已全部上板：lab1 出实时画面 ✅、lab2 出边缘画面 ✅、**lab3 只有安路 Logo、没有实时画面 ❌**。

---

## 第一步（先做这个，约 1 小时）：把 lab3 的黑屏问题定位到"哪一段"

### 为什么必须先做

lab3 将是我们**正式的工程底板**（它同时含 OSD 与完整显示通路，lab1 没有 OSD、lab2 没有 OSD）。
底板是黑的，后面所有工作都会白做。所以这不是"排查 bug"，这是**打地基**。

### 已经用源码排除掉的可能（不用再怀疑这些）

| 曾经的怀疑 | 实测结论 |
|---|---|
| 分辨率配置不一致 | ❌ 排除。lab1 与 lab3 的 `uivtc` 参数逐字相同（`H_ActiveSize=1280 / H_FrameSize=1650 / V_ActiveSize=720 / V_FrameSize=750`），`hdmi_mixer` 例化也都是 `IMG_WIDTH=1280 / IMG_HEIGHT=720 / H_OFFSET=0 / V_OFFSET=0` |
| 摄像头寄存器表不同 | ❌ 排除。三例程的 `uics500reg_720p60.v` 只有注释与排版差异，**寄存器值逐条相同** |
| 源码比 bit 新（改了没重编） | ❌ 排除。lab3 源码最新 mtime `2026-09-10 16:33:17`，bit 生成于 `2026-09-10 16:44:43`，源码全部早于 bit |
| `video_in.v` 代码写错 | ❌ 排除。lab2 与 lab3 的 `video_in.v` 用 `Compare-Object` 比对**只差 2 行注释，可执行语句完全相同** |
| `case` 少了 `endcase` 语法错 | ❌ 排除。三份 `video_in.v` 均为 `case=3 / endcase=3` |

### 关键推理（这决定了怎么查）

lab3 的 `hdmi_mixer.v` 第 **614–624 行**里，**OSD 整段逻辑被包在 `if(S_video_de_2d)` 里面**；
第 **901–904 行**才是最终选择：

```verilog
if(S_osd_hit) O_hdmi_data <= S_osd_color;   // Logo
else          O_hdmi_data <= S_video_data_2d;  // 从 DDR 读回的像素
```

→ **你能看到 Logo，说明 `S_video_de_2d` 是有效的 → 视频时序（行/场/DE）是活的 → HDMI 输出通路正常发射。**
→ **那么问题只剩一个：从 DDR 读回来的像素是黑的（`S_video_data_2d` 恒为 0）。**

### 实验：用 `DEBUG_MODE` 把"黑"切成四块看清楚

`hdmi_mixer.v` 自带三种调试画面（第 847 / 870 / 885 行），例化开关在 **`design_top_wrapper.v` 第 746 行**：

```verilog
.DEBUG_MODE ( 0    )   // ← 现在是这样，改成 1 或 3 再重编
```

**要改的文件**（只改这一处，一个字符）：
`E:\FPGA\work\baseline\lab3\user_source\hdl_source\design_top_wrapper.v` 第 746 行

**先试 `DEBUG_MODE = 1`（纯彩条，最容易判读）**：
第 847–868 行，屏幕从左到右出现 7 条彩条 + 1 条深灰：红(0–128) / 绿(128–256) / 蓝(256–384) / 黄(384–512) / 青(512–640) / 品红(640–768) / 白(768–896) / 深灰(896–1280)。

| 你看到什么 | 说明什么 | 下一步 |
|---|---|---|
| **彩条正常出现** | HDMI 输出通路 100% 完好 | 换成 `DEBUG_MODE = 3`，进入下表 |
| 彩条也不出来（仍只有 Logo 或全黑） | 问题在更下游（TMDS/HDMI TX）或 OSD 判断有误 | 立刻停下来找我，不要自己改代码 |

**再试 `DEBUG_MODE = 3`（四格状态条）**：
第 885–898 行，屏幕上从左到右四个 256 像素宽的竖条，每个竖条"亮色=1 / 暗色=0"。`I_debug_status` 的定义在 `design_top_wrapper.v` **第 403–408 行**：

```verilog
assign S_hdmi_debug_status = {
    (|S_ddr_user_rd_data),   // [3] DDR 读回的数据里有非零值
    S_ddr_user_rd_valid,     // [2] DDR 读有效
    S_vo_ddr_rd_en,          // [1] video_out 正在发读请求
    S_vi_ddr_wr_en           // [0] video_in 正在写 DDR
};
```

| 格位 | 屏幕位置 | 信号 | 亮色（=1） | 暗色（=0） |
|---|---|---|---|---|
| 1 | 最左 0–256 | [3] DDR 读回数据非零 | 橙 `ff8000` | 暗棕 `201000` |
| 2 | 256–512 | [2] DDR 读有效 | 黄 `ffff00` | 暗黄 `202000` |
| 3 | 512–768 | [1] video_out 在读 | 红 `ff0000` | 暗红 `200000` |
| 4 | 最右 768–1280 | [0] video_in 在写 | 青 `00ffff` | 暗青 `002020` |

**判读表（照着念就行）**：

| 四格结果 | 结论 | 要查什么 |
|---|---|---|
| 全亮（橙/黄/红/青） | DDR 读写都在动，数据也非零，**问题在 HDMI 混合之前的最后一段** | 此时把 `DEBUG_MODE` 改回 0，很可能画面就好了（有时是旧 bit 问题） |
| 只有第 4 格亮（青），前 3 格全暗 | **能写进 DDR，但读不出来** | DDR 读通道被写饿死 → 查 `video_in.v` 的 `O_video_in_wr_busy` 与 `I_video_out_rd_busy` 仲裁 |
| 第 1、4 格亮，2、3 格暗 | 写正常、读也回来了但 `rd_valid` 没拉起来 | 查 `video_out.v` 的读请求时序 |
| **四格全暗** | **连写都没发生** → 摄像头数据根本没进 `video_in` | 查摄像头 I2C 配置 / MIPI 是否真的在出流（回到"无数据"一类） |

### 操作步骤（照做，不要跳）

1. **先备份现有 bit**（重编会覆盖同名文件，原厂的 bit 很宝贵）：
   ```
   E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\best_result\camera_to_dsi_display.bit
   → 复制成 camera_to_dsi_display_原厂.bit
   ```
2. 打开 `E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display.al`
3. 找到 `design_top_wrapper.v` 第 **746** 行，`.DEBUG_MODE ( 0 )` → `.DEBUG_MODE ( 1 )`
4. 在 TD 左侧 Design 栏对着 run 右键 → **Reset Run**，再 **Launch Runs**（`-jobs 6`，你的 7500F 是 6 物理核）
5. 等约 3 分半（你上次实测：综合 1 分 0 秒 + 实现 2 分 21 秒）
6. 用 BitWriter 烧 `best_result\camera_to_dsi_display.bit`（SRAM 模式即可）
7. **拍照/录像**，然后来找我，我按判读表给你下一步

⚠️ 做完这个实验后**一定要把第 746 行改回 `0`**，否则正式演示会变成彩条。

---

## 第二步：建立你自己的工程工作树（约 1 小时）

### 为什么不能直接在 `anlogic_example\` 里改

那是**原厂文件的副本**，改坏了无法对比、无法回溯。而且比赛要求"最终一个工程、一个 bit 文件"，需要一个干净的、可版本管理的目录。

### 目录规划（照建）

```
E:\FPGA\work\
   baseline\lab3\          ← 从官方 lab3 整棵复制过来，改名 baseline
   rtl\my_algo.v           ← 已有
   sim\                    ← 以后放 testbench
   docs\                   ← 框图、时钟表、台账
   evidence\               ← 屏摄、录屏（每条判据一份）
   资源与时序台账.csv        ← 已有，所有编译都记一行
```

### 复制工程（关键：整棵复制，不要只复制 .al）

`.al` 里的路径全是**相对路径**，而且它引用了三类资源：

| 段 | 路径 | 说明 |
|---|---|---|
| `<ADC_FILE>` | `../user_source/constraints_source/pin.adc` | 引脚约束，**只有 19 行**（MIPI/DDR 引脚不在这里，由 IP 自动分配） |
| `<SDC_FILE>` | `camera_to_dsi_display.sdc` | 17 行时序约束，**相对 `td_project\`** |
| `<IP_FILE>` | `../user_source/ip_source/PLL/PLL.xml`、`w128_d512_fifo/w128_d512_fifo.xml`、`w155_d512_fifo/...`、`blk_mem_gen_awb_delay_signal/...`、`divider/divider.ipc` | **IP 定义文件，必须一起复制**，否则打开工程会报 IP 找不到 |

所以复制命令是（PowerShell）：

```powershell
# 1) 建目录
New-Item -ItemType Directory -Force -Path 'E:\FPGA\work\baseline' | Out-Null

# 2) 整棵复制 lab3（约 900 个文件，比"只复制源码"可靠得多）
Copy-Item -Path 'E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd' `
          -Destination 'E:\FPGA\work\baseline\lab3' -Recurse -Force

# 3) 清理旧编译产物（省空间，也避免"我到底烧的是哪个 bit"的混乱）
Remove-Item 'E:\FPGA\work\baseline\lab3\td_project\camera_to_dsi_display_Runs' -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item 'E:\FPGA\work\baseline\lab3\td_project\log' -Recurse -Force -ErrorAction SilentlyContinue

# 4) 把自研算法放进去
Copy-Item 'E:\FPGA\work\rtl\my_algo.v' 'E:\FPGA\work\baseline\lab3\user_source\hdl_source\isp\my_algo.v' -Force
```

### 复制完必须手改的 2 处

**① `.al` 第 2 行的原厂绝对路径**（不改的话 TD 可能在某些操作下写回错误位置）：
`E:\FPGA\work\baseline\lab3\td_project\camera_to_dsi_display.al` 第 2 行
```xml
<Project Version="3" Minor="2" Path="C:/Users/Cczzzzzq/Desktop/anlogic_example_SC520CS/lab_ex3_osd_SC500_720P/lab_ex3_osd/td_project">
```
改成你实际所在的目录（用正斜杠）：
```xml
<Project Version="3" Minor="2" Path="E:/FPGA/work/baseline/lab3/td_project">
```

**② 给文件加一行注释，防止搞混**：在 `baseline\lab3\user_source\hdl_source\design_top_wrapper.v` 第 1 行加：
```verilog
// [OUR BASELINE] based on official lab3 (OSD route). Do not edit the copy under anlogic_example\.
```

### 验证工程能打开

TD → File → Open Project → 选 `E:\FPGA\work\baseline\lab3\td_project\camera_to_dsi_display.al`。
左侧 Design 栏应该能看到完整的 Verilog 文件列表 + `pin.adc` + `camera_to_dsi_display.sdc` + 5 个 IP。
**先不要编译**，确认能打开、文件树完整即可。

---

## 第三步：把自研算法接进通路（工程的第一次真实改动）

### 插入点：`isp_top.v` 里 `awb` 之后、`data_96bit_to_128bit` 之前

结构（lab2 的 `isp_top.v` 第 84–132 行者就是现成范例）：

```
I_tdata[39:0] (RAW10)
   → demosaic #(.IMG_HEIGHT(720), .IMG_WIDTH(1280), .data_complete_delay(50), .BAYER_MODE("BGGR"))
   → m_aixs_tdata[127:0] → data128_96 → m_aixs_tdata_96[95:0]
   → awb #(.IMG_HEIGHT(720), .IMG_WIDTH(1280))
   → awb_O_tdata[95:0]
   → 【★ 你的算法插在这里 ★】
   → data_96bit_to_128bit → O_tdata[127:0]
```

**全工程只有这一个插入点，不需要碰 MIPI、DDR、HDMI、PLL 的任何一行。**

### 要动的文件：`baseline\lab3\user_source\hdl_source\isp\isp_top.v`

lab3 现在是**直通**（第 95–106 行），写法是：

```verilog
data_96bit_to_128bit u_data_96bit_to_128bit(
    .I_96b_frame_start  ( awb_O_tuser  ),
    .I_96b_valid        ( awb_O_tvalid ),
    .I_96b_data         ( awb_O_tdata  ),
    ...
```

**改成**（照抄 lab2 的写法，只是把模块名换成 `my_algo`）：

```verilog
my_algo u_my_algo (
    .I_clk   (axi4s_video_aclk),
    .I_rst_n (I_rst_n),
    .I_tlast (awb_O_tlast),
    .I_tuser (awb_O_tuser),
    .I_tdata (awb_O_tdata),
    .I_tvalid(awb_O_tvalid),
    .I_tready(awb_O_tready),
    .O_tlast (edge_O_tlast),
    .O_tuser (edge_O_tuser),
    .O_tdata (edge_O_tdata),
    .O_tvalid(edge_O_tvalid),
    .O_tready(edge_O_tready)
);

data_96bit_to_128bit u_data_96bit_to_128bit(
    .I_96b_frame_start  ( edge_O_tuser   ),
    .I_96b_valid        ( edge_O_tvalid  ),
    .I_96b_data         ( edge_O_tdata   ),
    .O_128b_frame_start ( awb_O_tuser_128 ),
    .O_128b_valid       ( awb_O_tvalid_128),
    .O_128b_data        ( awb_O_tdata_128 )
);
```

还要在 `isp_top.v` 的信号声明区加上这 5 根 wire（如果 lab3 里还没有）：
```verilog
wire        edge_O_tlast;
wire        edge_O_tuser;
wire [95:0] edge_O_tdata;
wire        edge_O_tvalid;
wire        edge_O_tready;
```
（`edge_O_tready` 由 `data_96bit_to_128bit` 驱动，方向是 **input**；`my_algo` 的 `I_tready` 是 **output**，两者对接——这是原例程的命名习惯，别改。）

### ⚠️ 注意 `my_algo.v` 的两个已知点

1. **文件必须是 `//` 注释，不是 `##`** —— 我先前留下的脚手架写错了，**已修正**，请重新从 `E:\FPGA\work\rtl\my_algo.v` 复制一份（别用旧的那份）。
2. **端口名与 `edge_detect_96.v` 完全一致**，所以将来想切回官方边缘检测，只需把例化名换掉。

### 第一次编译：先验证"接口接通"

`my_algo.v` 有参数 `OFF`（第 26 行）：

```verilog
parameter integer OFF = 0,   // 1 = 完全直通
```

**第一次编译请设 `OFF = 1`**（在 `isp_top.v` 例化时传参：`my_algo #(.OFF(1)) u_my_algo (...)`）。
- 预期现象：画面与 lab3 原版**一模一样**（Logo + 摄像头画面，无算法效果）。
- 意义：证明"接进去了、接口没错、时序标记同拍"。这一步能省掉后面几小时的无头调试。
- 然后改成 `OFF = 0` 重编，应该看到伪彩热力图（`MODE_INIT = 2'd2`）。

### 每次改完的固定动作

1. 记录**改动**：改了哪个文件、哪几行、为什么（写进 `work\docs\调试日志.md`）
2. 在 TD 里 Reset Run + Launch Runs（`-jobs 6`）
3. 打开 `Runs\phy_1\camera_to_dsi_display_phy.area`，抄 `#slice` / `#lut6` / `#eram` / `#dsp`
4. 打开 `Runs\phy_1\route.qor`，抄 `Setup WNS` / `Hold WNS`
5. **往 `work\资源与时序台账.csv` 加一行**
6. 烧录、屏摄、存 `work\evidence\`

---

## 第四步：你的可用资源（精确数字，直接可用）

### 4.1 三个例程的最终数字（全部来自 `phy_1\..._phy.area` 与 `route.qor`，无星号=最终值）

| 工程 | `#slice` | 占比 | `#lut6` | 占比 | `#slice reg` | `#eram` | `#dsp` | Setup WNS |
|---|---|---|---|---|---|---|---|---|
| lab1 MIPI→HDMI | 12,358 | 58.25% | 9,865 | 46.50% | 13,313 | 40 | 8 | **+1.408 ns** |
| lab2 加边缘检测 | 12,926 | 60.93% | — | — | — | 40 | 8 | **+1.163 ns** |
| **lab3 加 OSD（我们的底板）** | **14,852** | **70.00%** | **12,669** | **59.71%** | **13,380** | **40** | **9** | **+0.103 ns** ⚠️ |

### 4.2 器件总规模（答辩时用这组数字）

| 资源 | 总量 | lab3 已用 | **你还能用** | 剩余比例 |
|---|---|---|---|---|
| slice | 21,216 | 14,852 | **6,364** | 30.00% |
| LUT6 | 21,216 | 12,669 | **8,547** | 40.29% |
| 触发器 DFF | 42,432 | 13,380 | **29,052** | 68.47% |
| ERAM20K（块 RAM） | 108 | 40 | **68** | 62.96% |
| DSP | 40 | 9 | **31** | 77.50% |
| PLL | 6 | 3 | **3** | 50.00% |
| **MIPI RX 硬核** | 2 | 1 | **1** | 50.00% |
| DDR byte 通道 | 12 | 6 | **6** | 50.00% |
| 全局时钟 gclk | 32 | 9 | **23** | 71.88% |
| IO | 160 | 58 | **102** | 63.75% |

> 换算关系：`slice 21,216 × 1.8 ≈ LUT4 38,189`（官方口径 42,432 DFF / 38,189 LUT 指的就是这套硬件）。
> **占用率只能 slice 对 slice**，不要拿 `#lut6` 去除以 38,189。

### 4.3 资源结论（三条，直接影响设计决策）

**① 逻辑资源很宽裕，硬核资源很紧张。**
还剩 6,364 slice / 8,547 LUT6 / 68 块 ERAM / 31 个 DSP —— 做一个点运算级算法绰绰有余。
但 **MIPI RX 只剩 1 个、PLL 只剩 3 个、DDR byte 只剩 6 个**。加功能必须优先用 LUT/DSP，**不要想再挂一路摄像头或再加一个 DDR 控制器**。

**② 算法本身很便宜，通路很贵。**
lab1→lab2（加完整 Sobel 边缘检测 + 3×3 行缓存）只多了 **+568 slice（+2.7 pp）**。
→ **你的 `my_algo.v` 是点运算、无行缓存，预计只吃 +100~300 slice**，怎么都放得下。

**③ 真正的约束是时序，不是资源。**
lab3 的 Setup WNS 只剩 **+0.103 ns**（最紧路径挂在 `HDMI_SERIAL_CLK`，周期 2.667 ns / 375 MHz，余量不到 4%）。而 lab3 用了 9 个 DSP，lab2 只有 8 个 —— OSD 那 1,926 个 slice 里包含了一套 DYN_OSD 比较逻辑。
→ **你的模块必须"浅"**：单级寄存器、组合逻辑不超过 2~3 级 LUT。
→ **每加一次逻辑都要重看 `route.qor` 的 Setup WNS。一旦变成负数，按下面顺序熔断。**

### 4.4 熔断顺序（时间或时序不够时按此砍）

1. 砍掉所有进阶项（帧计数、多算法切换）
2. 算法降级到只有灰度/二值化（去掉伪彩）
3. 扩展要求从"视觉增强"退回"性能优化对比表"（用 lab1→lab2→lab3 的现成数字）
4. OSD 动态文字退回静态 Logo

**绝不放弃**：4 条基础要求可演示、单一工程+固化上电自启、算法与参考实例不同源。

---

## 第五步：验收清单（每步做完必须有"文件证据"）

| # | 动作 | 判据（拿得出手的东西） |
|---|---|---|
| 1 | lab3 黑屏定位 | 一张 DEBUG 画面屏摄 + 你能说出"问题在哪一段" |
| 2 | 建立 baseline 工程 | `work\baseline\lab3` 能打开、文件树完整 |
| 3 | 算法以 `OFF=1` 接入 | 画面与 lab3 原版一致 + 台账第一行你自己的数字 |
| 4 | 算法设为伪彩模式 | 屏幕出现热力图伪彩 + 一段 >= 10 秒屏摄 |
| 5 | 时序复检 | `route.qor` 的 Setup WNS 仍为正数，台账新增一行 |

**卡住超过半天就停下来找我**，不要自己硬啃——尤其是"编译通过但画面不对"这类问题，源码我已经读过大半，能直接指到行号。

---

## 附：本文件所有结论的出处

| 结论 | 文件 |
|---|---|
| lab3 `hdmi_mixer` 的 OSD 被 `if(S_video_de_2d)` 包住 | `E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\user_source\hdl_source\hdmi_mixer.v` 第 614–624 行 |
| 最终像素选择 `S_osd_hit ? OSD : 视频` | 同上，第 901–904 行 |
| `DEBUG_MODE` 三种调试画面 | 同上，第 847 / 870 / 885 行 |
| `DEBUG_MODE` 例化位置（第 746 行） | `...\lab_ex3_osd\user_source\hdl_source\design_top_wrapper.v` 第 746 行 |
| 四个调试状态位的定义 | 同上，第 403–408 行 |
| 算法插入点与端口写法 | `E:\FPGA\anlogic_example\lab_ex2_edge_SC500_720P\lab_ex2_edge\user_source\hdl_source\isp\isp_top.v` 第 84–132 行 |
| lab3 的 `isp_top.v` 是直通（无算法） | `...\lab_ex3_osd\user_source\hdl_source\isp\isp_top.v` 第 95–106 行 |
| `.al` 的 ADC/SDC/IP 相对路径 | `E:\FPGA\work\baseline\lab3\td_project\camera_to_dsi_display.al` 第 2 / 361–373 / 381–420 行 |
| lab3 资源与时序最终值 | `...\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display_phy.area`、`route.qor` |
| 器件规模与 DFF 数 | `官方资料\选题二.docx` 2.2 节（42,432 DFF / 38,189 LUT） |
| 三例程摄像头寄存器表逐条相同 | `...\uics500_cfg\uics500reg_720p60.v`（三份 Compare-Object） |
