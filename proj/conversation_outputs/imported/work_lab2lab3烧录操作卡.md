# lab2 / lab3 烧录操作卡（手上照着做）

日期：2026-09-25　适用：HX1P35A 板 + TD 6.2.1 + 已出图的 lab1 环境
前提：你的 lab1 已经在同一块板、同一根线、同一台显示器上出过实时图像 → **硬件链路不用动，只换比特流。**

---

## 0. 先明确一件事：这次烧的是 SRAM，不是 Flash

| | SRAM 在线下载（本次用） | Flash 固化（11/4 交付必须用） |
|---|---|---|
| 用的文件 | `camera_to_dsi_display.bit` | `camera_to_dsi_display_compress.bit` 经 Boot Image Tool 转出的固化文件 |
| 掉电/拔线后 | **程序消失，屏幕变黑** | 保留，上电自动跑 |
| 用途 | 看现象、留屏摄证据 | 最终交付 |

⚠️ **所以本次烧完必须"趁热"拍屏摄，别先拔线。**
⚠️ **本次烧的 bit 不改变板子里的任何东西**，lab1 随时可以再烧回来。

---

## 1. 开工前 5 分钟检查

1. **HDMI 线**：你只有 1 根 → 先确认显示器输入源切到接板子那个口（很多显示器要手动选 HDMI1/HDMI2）。
2. **Type-C 下载线**：接板子的下载口，电脑能识别（lab1 能烧说明这条是好的）。
3. **摄像头排线**：**不要拔插**，lab1 出图说明它现在是好的。
4. **上电顺序**：先接好线 → 再给板子上电 → 最后开 TD。
5. **一次只开一个 TD**：不要在 TD 里同时打开 lab2 和 lab3 两个工程。

---

## 2. 烧 lab2（边缘检测）—— 预计 10 分钟

### 2.1 打开工程
TD 菜单 `File → Open Project`，打开：
`E:\FPGA\anlogic_example\lab_ex2_edge_SC500_720P\lab_ex2_edge\td_project\camera_to_dsi_display.al`
**等它加载完**（加载时会扫器件）。

### 2.2 打开下载界面
菜单 `Tools → Download`（官方《安路软件使用完整流程》第 20 页原文：**"选择 Tools->Download 进行下板"**）。
> Tools 菜单里那个 **Program Device / 烧录** 的入口，在 TD 里就叫 **Download**。
> 如果 `Tools` 下找不到，看工具栏上的下载图标，或 `Window` 菜单里是不是已经开过这个窗口。

### 2.3 加文件
在 **File Selection** 区域点 `Add`，选：
```
E:\FPGA\anlogic_example\lab_ex2_edge_SC500_720P\lab_ex2_edge\td_project\camera_to_dsi_display_Runs\best_result\camera_to_dsi_display.bit
```
> 文件对话框默认可能只显示 `*.compress`/`*.bin` 之类。**把筛选改成 All Files (\*.\*)**，否则你会"看不到"这个 .bit 文件——这是这一步最常见的卡点。

### 2.4 确认器件（不用改）
器件应显示 **PH1P35MDG324 / PH1 / Speed -3**。这是工程 `.al` 里写死的，正常。**若显示其他器件，停下来告诉我**（器件选错会让引脚全乱）。

### 2.5 选模式
找 **SRAM / JTAG / 在线下载** 那一档（**不要选 Flash / Program Flash / 固化**）。
你自己点一下这个界面的截图给我，我帮你确认每一项该选什么。

### 2.6 下载
点 **Run**。官方原文（同 PDF 第 22 页）：**"点击 run 后下面的进度条显示 100% 证明烧录完成。"**

### 2.7 立刻观察 + 留证（**在拔线之前**）
预期画面（`edge_detect_96.v` 的 `EDGE_TH = 11'd80`、`isp_top.v:105` 例化同值）：
- 显示器出 **1280×720 实时画面，但是黑白的**；
- 物体轮廓/边缘是**白色线条**，平坦区域是**黑色**；
- 手在镜头前晃动时，白边**实时**跟着动。

**留证三件套**：
1. 屏摄照片 1 张（能看清边缘画面）；
2. **屏摄视频 ≥10 秒**（手在镜头前移动，让边缘变化的动态被录下来）；
3. 亮环境 + 暗环境各拍一组（顺手为"光线剧烈变化"评分项留证）。

**同时记 3 个数**：下载完成的时间、显示器 OSD 显示的**分辨率**与**刷新率**。

---

## 3. 烧 lab3（OSD 叠加）—— 预计 10 分钟

完全一样的流程，只换工程和文件：

- 工程：`E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display.al`
- 文件：`E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\best_result\camera_to_dsi_display.bit`

### 预期画面（已从 lab3 源码逐行核实）
| 位置 | 内容 | 源码依据 |
|---|---|---|
| 左上角 160×160 | **安路 Logo**（蓝色块 `24'h1f315c` + 红色带 `24'hec1c2d`） | `hdmi_mixer.v:101-107, 615-623` |
| (375, 120) 起 200×24 | **"安路 CNT:" + 递增的帧计数** | `hdmi_mixer.v:109-112, 626-630` |
| 其余区域 | **实时摄像头画面**（lab3 是 OSD 例程，画面本体不是边缘图） | `hdmi_mixer.v:901-902` |

⚠️ 注意：**lab2 和 lab3 都是"边缘检测 + OSD 分别独立"的两个工程**。lab3 只叠加 OSD，不保证同时显示边缘效果。**不要以为 lab3 画面不对是烧错了。**

---

## 4. 遇到问题怎么办（按"先分类"原则）

**先分两类，别乱猜：**

| 现象 | 含义 | 往哪查 |
|---|---|---|
| 纯白、无任何文字/图标 | 显示器**收到了**有效信号，但像素恒为白 | FPGA 内部数据通路 |
| 白/蓝/黑底 + "No Signal/无信号/不支持分辨率"，或电源灯橙色 | 显示器**没收到**有效信号 | 信号/时钟/烧录/接线 |

**最可能的三种情况：**

1. **下载成功（进度条 100%）但黑屏**
   → 先按一次板上复位、再重连一次 Type-C；还不行就重烧一次。
   → 因为同样的流程 lab1 成功过，**这多半不是板子问题**，而是 bit 没真正进 SRAM 或显示器输入源没切对。

2. **提示找不到器件 / 下载失败**
   → 确认 line 没被别的 TD 实例占用；拔插 Type-C；确认板子在上电状态。

3. **画面雪花/偏色**
   → 那是 TMDS 或 Bayer 相位问题，**但 lab1 正常过，所以先怀疑烧进去的不是这三个 bit**（检查你选的文件路径）。

---

## 5. 顺手把这两件事同时办了（不额外花时间）

### 5.1 确认按键是否可用（决定你能不能做"算法切换"这个加分项）
我查了代码：lab2/lab3 的顶层都是这样写的——
`design_top_wrapper.v:437`：`.I_btn({I_button,2'b11})`，而 `I_button` 在 `pin.adc` 里是 **N2 / J14** 两个脚；`ae_set.v:84` 是 `r_button_0 <= ~I_btn;`（低电平有效）。

→ 也就是说：**官方例程里按键只用来调摄像头采样延时，没有任何算法切换逻辑。** 按下去画面**不会**变。
→ 你要做"按键切换算法"，得自己加**消抖模块 + 状态切换逻辑**；而且要先确认 N2/J14 在板子上到底是不是那两个按键（这与 HX1P35B 引脚汇总文档里写的 D5/A9/B9/C7 不一致，**用万用表量一下通断最稳**）。

### 5.2 观察"有没有可能烧错"
烧 lab2 前先记下 lab1 的画面样子（彩色实时图），烧 lab2 后变黑白 → 说明你换的就是算法那一版。这个对照本身就是很好的证据。

---

## 6. 做完后请给我这 6 条信息（我据此排下一步）

```
lab2: 下载是否成功[是/否]  屏幕现象[描述]  屏摄[有/无]  视频[有/无]
lab3: 下载是否成功[是/否]  屏幕现象[描述]  左上角有没有 Logo[有/无]  中间有没有"安路 CNT:"+数字[有/无]
显示器 OSD 显示的分辨率/刷新率 = ______
按键 NJ2/J14 按下去有没有任何反应 = ______
下载时间（几点几分）= ______
```

拿到这些我就能告诉你：**下一步是先做 Flash 固化，还是先写你的自研算法**。

---

## 附：文件路径速查（可直接复制到资源管理器）

```
lab2 工程
E:\FPGA\anlogic_example\lab_ex2_edge_SC500_720P\lab_ex2_edge\td_project\camera_to_dsi_display.al
lab2 比特流
E:\FPGA\anlogic_example\lab_ex2_edge_SC500_720P\lab_ex2_edge\td_project\camera_to_dsi_display_Runs\best_result\camera_to_dsi_display.bit

lab3 工程
E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display.al
lab3 比特流
E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\best_result\camera_to_dsi_display.bit
```

（两个 `.bit` 均为 1,789,539 字节，生成时间 lab2 = 2026-09-10 16:23:49、lab3 = 2026-09-10 16:44:43，都已实测存在。）

**官方依据**：《安路软件使用完整流程.pdf》第 20–22 页（`Tools → Download` → `Add` 加文件 → `Run` → 进度条 100%）；`SWUG101_TangDynasty_Getting-Started_User_Guide_TD6.0.2_V1.0.pdf` 表 4-1（支持的下载器：Anlogic AL-Link / AL-Link Pro，所有版本）。
