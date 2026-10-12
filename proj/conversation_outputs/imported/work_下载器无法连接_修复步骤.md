# 修复：BitWriter 报 `Device not found` / `PRG-8000 ERROR: Connect server failed`

诊断时间：2026-09-26
症状（你的两张截图）：
- UsbDriverTool 弹 `Cannot update driver for the device: Unknown error (0xe000022f)`
- BitWriter 报 `Device not found! ...` + 底部 log `PRG-8000 ERROR: Connect server failed.`

**结论：两个报错是同一个根因。UsbDriverTool 那一步你没做对（点成了 FTDI 驱动，不是 WinUSB），所以 TD 的 JTAG 服务读不到下载器。**

---

## 一、根因（已在本机实测确认，不是猜的）

### 1. TD 的下载链路长这样

```
BitWriter (E:\TD\bin\bw.exe)          ← 你截图里那个窗口
      │  连接 127.0.0.1:5555
      ▼
hwserver.exe (E:\TD\bin\hwserver.exe) ← AL-LINK-FT(Local Host) 服务，默认端口 5555
      │  通过 libusb / libftdi 直接访问 USB 设备
      ▼
AL-LINK-FT 下载器 (FTDI FT2232H, VID_0403 & PID_6042)
```

实测：`netstat` 里 **5555 端口没人监听**，进程表里也没有 `hwserver.exe`。所以 BitWriter 连不上，报 `PRG-8000 ERROR: Connect server failed.`。

### 2. 为什么 hwserver 起不来 / 起来也读不到设备

我直接运行了 `hwserver.exe -L`（列出可用调试适配器），原文输出：

```
List all adapters, count: 1
ftdi_usb_get_strings failed: -4 (libusb_open() failed)
0,OCCUPPIED,,
```

`hwserver` 能"看见"有一个适配器，但 **libusb 打不开它**。原因查到了：

| 项目 | 实测值 |
|---|---|
| 设备 | `USB\VID_0403&PID_6042&MI_00`（USB Serial Converter A） |
| 当前绑定驱动 | **`FTDIBUS`（FTDI 官方 VCP 驱动）** |
| 驱动版本 | 2.12.36.20，2024/10/28 |
| 副作用 | 系统里多出一个 **COM3**（USB Serial Port）——接口被 VCP 占用 |

**WinUSB/libusb 打不开一个已经绑在 FTDI VCP 驱动上的接口，这就是 `libusb_open() failed` 的直接原因。**

### 3. 官方文档写得很明确

`官方资料\1_安路工具和软件\新版TD驱动PH1P35使用方法\（必看）PH1P35烧写程序的使用方法.pdf` 第 1 页原文：

> 首次烧写，插好PH1P35开发板，找到UsbDriverTool.exe工具并运行
> **右键选择ID为0403 6042 的USB_A驱动选择安装WinUSB**
> 将此文件放进新版TD 开发工具的bin 目录下（例如 `D:\Anlogic\TD_6.2.1_Engineer_6.2.168.116\bin`）

第 2–3 页原文：

> 然后点击 AL-LINK-FT(Local Host)，Local port 默认为 5555，然后在弹出的框中点击刷新后点击 Apply and Close，此时便可以看到显示的芯片型号
> 注意，点一次刷新后左上角可能会无法显示目标器件型号，需重新点开 AL-LINK-FT(Local Host) 界面，再点击一次刷新，**刷新后显示为 OCCUPPIED，此时稍等几秒再观察左上角，便会显示出芯片器件型号**

对照你的操作：
- 你的 `USB_A (0403 6042)` **当前是 FTDI 驱动，不是 WinUSB** → 与官方要求相反；
- 你点出来的 `0xe000022f` 是"**要装的驱动和现在装的是同一个**"（FTDI→FTDI）导致的拒绝安装 → 说明你点的是 **FTDI 驱动那一项**，不是 WinUSB。

顺带说明：`0xe000022f` 本身不用管，它只说明 FTDI 驱动已经在了；要装的是 **WinUSB**。

另外要注意一个官方自相矛盾点（别被绕进去）：`al-link-ft刷pid教程_20240814.pdf` 说"要用 FT_Prog 就必须先把驱动设回 FTDI 官方驱动，装了 WinUSB 就认不到"。

→ 这两份文档的服务对象不同：
- **`FT_Prog` 给 EEPROM 刷 VID/PID 字符串**（改下载器固件），需要 FTDI 驱动；
- **烧 FPGA 比特流**需要 **WinUSB**。

**你现在的任务是烧 FPGA，所以要走 WinUSB 这条线。EEPROM 那边不用动**（你的设备已经能报出 `VID_0403 & PID_6042`，说明 PID 已经是 6042 了，不需要再刷）。

---

## 二、修复步骤（照做，每步都有验证方法）

### 步骤 0：先接好硬件
- 下载器 USB 插在**主板后面板的 USB 口**（不要前置面板、不要 USB Hub、不要 USB3 蓝色口，优先用黑色 USB2 口）。
- 开发板**独立供电并上电**，JTAG 排线接牢。
- 关掉 TD 里所有正在跑的下载窗口（BitWriter 窗口留着也行，先不管它）。

### 步骤 1：用 UsbDriverTool 装 WinUSB（关键一步）

运行：
```
E:\FPGA\官方资料\1_安路工具和软件\新版TD驱动PH1P35使用方法\安路JTAG驱动安装_固件\UsbDriverTool\UsbDriverTool.exe
```
（建议"以管理员身份运行"）

操作：
1. 列表里找到 **VID/PID = 0403 6042、名字含 `USB Serial Converter A`** 的那一项；
2. **右键它**，在菜单里选 **`Install WinUSB`**（完整名字可能是 "Install WinUSB (libusb)" / "Libusb - WinUSB"）；
   - ⚠️ **不要选** "Install FTDI" / "Install FTDI CDM" / "Update driver" 这类项——那是导致 `0xe000022f` 的那一项；
3. 等它跑完，不报错即可（会新增一个 `libusb (WinUSB) devices` 分类）。

**验证方法 A**：设备管理器里 `USB Serial Converter A` 应该从「通用串行总线控制器」挪到 **`libusb (WinUSB) devices`** 分类下。原来那个 `USB Serial Port (COM3)` 会消失。

**验证方法 B**（更硬）：在 PowerShell 里跑
```powershell
& 'E:\TD\bin\hwserver.exe' -L
```
- 修复前输出：`0,OCCUPPIED,,` + `ftdi_usb_get_strings failed: -4 (libusb_open() failed)`
- **修复后应该输出真实的 VID/PID/序列号**，例如 `0,AVAILABLE,0403,6042,<序列号>`（不再是 OCCUPPIED、不再报 libusb_open 失败）

### 步骤 2：确认 hwserver 能被 TD 起来

装完 WinUSB 后：
1. **保持 BitWriter 窗口开着**，回到 BitWriter；
2. 左上角 `USB cable is [下拉框]` 点 **Refresh**（或先点一下下拉框）：
   - 修复前：显示 `USB cable is `（空的）
   - **修复后**：应该出现一条具体的线缆名（AL-LINK-FT / USB-JTAG Cable 之类）；
3. 若还是空的：把 BitWriter **完全关掉**，在 TD 里重新走 `Tools → Download...` 打开它（TD 会自动拉起 hwserver）；
4. 再不行：`127.0.0.1:5555` 那个对话框按官方说明**点两次刷新**（第一次可能显示 OCCUPPIED，第二次或等几秒才出器件型号）。

**验证方法 C**：另开一个 PowerShell 窗口
```powershell
netstat -ano | Select-String ':5555'
```
修复后应该看到有一行 `LISTENING`，对应 PID 是 `hwserver.exe`。

### 步骤 3：扫描器件、烧 lab2

在 BitWriter 里：
1. `File Selection` 那张表里你**已经加好的那一行**就是 lab2 的 bit：
   `E:/FPGA/anlogic_example/lab_ex2_edge_SC500_720P/lab_ex2_edge/td_project/camera_to_dsi_display_Runs/best_result/camera_to_dsi_display.bit`
   —— 路径和器件都对（Device=`ph1_35p`，Package=`PH1P35MDG324`），**这一行不用改**；
2. 确认左上角出现器件型号 `PH1P35MDG324`（这就是"JTAG 通了"的标志）；
3. 选 **SRAM** 模式（在线下载，掉电即失效，先用它验证功能）；
4. 点 **Run**，进度条到 100%。

### 步骤 4：lab2 应该看到什么

- 显示器上出现 **只有黑白两色** 的画面：是边缘的地方白、不是边缘的地方黑；
- 摄像头对准有细节的东西（文字、书脊、手、桌边）边缘才明显；对着白墙会几乎全黑；
- 这个例程的按键**只用来调摄像头采样延时**（`ae_set.v` 里 `I_button[0]:IncDatDly, [1]DecDatDly, [2]IncI_clkDly, [3]DecI_clkDly`），**没有算法切换功能**，按下去画面不会切换模式。

### 步骤 5：再烧 lab3

lab3 的 bit（工作树里已确认存在）：
```
E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\best_result\camera_to_dsi_display.bit
```
在 BitWriter 里 **Add** 加进来（或把 lab2 那行删掉再加 lab3），SRAM 下载。

lab3 应该看到：
- 主画面仍是 1280×720 实时彩色图像；
- **左上角 160×160 区域是安路 Logo**（`LOGO_X=0, LOGO_Y=0, LOGO_W=160, LOGO_H=160`）；
- **画面中部偏左（约 375,120）显示「安路 CNT:」+ 递增的帧计数**；
- Logo 颜色是深蓝 `24'h1f315c` / 红 `24'hec1c2d` 两种。

---

## 三、如果步骤 1 之后还是 `libusb_open() failed`

按顺序试，每试一步就重跑一次 `hwserver.exe -L`：

1. **拔插下载器 USB**（装完驱动必须重插一次才生效）。
2. **换一个 USB 口**（优先主板后面板 USB2 口）。
3. **重启电脑**（驱动重新绑定最干净的一招）。
4. **确认 B 通道没被误改**：UsbDriverTool 里只处理 `MI_00`（USB_A）那一项。如果你把 `MI_01`（USB_B）也改成了 WinUSB，把它改回 FTDI 即可（B 通道对应 COM3 串口，不是 JTAG）。
5. **手动指定 Vid/Pid 启动服务**（绕过自动识别）：
   ```powershell
   Start-Process 'E:\TD\bin\hwserver.exe' -ArgumentList '-d -V 0403 -p 6042 -f 12' -WorkingDirectory 'E:\TD\bin'
   ```
   `-d` 打开调试输出，可以直接看到它到底卡在哪一步。启动后用 `netstat -ano | Select-String ':5555'` 确认监听。
   （`-f 12` = JTAG 时钟 12 MHz；官方 BitWriter 的日志里也是 `-f 12`，一致。）
6. **用 Zadig 强制装 WinUSB**：下载 Zadig → `Options → List All Devices` → 选 `USB Serial Converter A (Interface 0)` → 目标驱动选 **WinUSB** → `Replace Driver`。
   （Zadig 是 WinUSB 安装的通用工具，和 UsbDriverTool 做的是同一件事，但更"强硬"，能覆盖旧驱动。）
7. **最后手段**：把 `E:\TD\bin\hwserver.exe` 复制一份到工作区，管理员权限运行，看它自己的报错。

---

## 四、我这边已经排除掉的可能

| 曾怀疑的原因 | 实测结论 |
|---|---|
| UsbDriverTool 报 `0xe000022f` 是坏了 | ❌ 不是。FTDI 驱动 2.12.36.20 已装好，Windows 拒绝重复安装同版本 → 这步本来就该跳过，要装的是 WinUSB |
| USB 线/口没插好 | ✅ 设备已被系统枚举（`USB\VID_0403&PID_6042&MI_00`），线是通的 |
| 缺 hwserver.exe | ❌ 不缺，`E:\TD\bin\hwserver.exe`（464,896 B，2024-12-09 编译）在 |
| Intel/Altera 的 JTAG 服务抢了设备 | ❌ 它监听的是 TCP 1309（Quartus jtagserver），与 5555 无关；且它不是本设备的驱动 |
| 下载器 PID 不对（需要 FT_Prog 刷） | ❌ 系统已报 `PID_6042`，正是安路要求的 PID，**不需要刷 EEPROM** |
| 端口 5555 被别的程序占用 | ❌ 没人监听，是"服务没起来"而不是"端口被占" |

---

## 五、给你的一句话总结

**症状不是"BitWriter 坏了"，而是"下载器现在绑在 FTDI 的 VCP 驱动上（多了个 COM3），而 TD 的 hwserver 要用 libusb/WinUSB 直接读它，读不到。"**

**修复就一条命令级别的事：UsbDriverTool → 右键 `0403 6042 的 USB_A` → 装 `WinUSB`（不是 FTDI）→ 拔插一次 → 重开 TD 的 Download → 等 5555 起来 → 烧。**

验证成功的唯一硬指标：
```powershell
& 'E:\TD\bin\hwserver.exe' -L
```
输出里**不再有** `libusb_open() failed`，且状态不是 `OCCUPPIED`。
