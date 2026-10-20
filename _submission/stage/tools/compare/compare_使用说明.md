# `compare.py` 使用说明

> 用途：把「FPGA 当前输出」和「LR 调整后 / 期望效果」两张图做逐项量化对比，输出一份
> 带**反推参数建议**的报告，用来回答一个问题：**"要让 FPGA 的画面变成这张 after，我到底该改哪个常数？"**

---

## 1. 环境准备

本机 Python（已装好依赖）：

```
C:\Users\KX\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe
```

依赖只有 3 个（numpy 已随环境提供）：

```powershell
& "C:\Users\KX\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe" `
  -m pip install opencv-python-headless matplotlib
```

> 用 `opencv-python-headless` 而不是 `opencv-python`：前者不带 GUI 模块，体积小、装得快，
> 本脚本所有出图都走 Matplotlib（`Agg` 后端），不需要 `cv2.imshow`。

---

## 2. 快速开始

```powershell
# 最短用法（输出到 after.png 所在目录）
& $py E:\FPGA\compare.py  E:\FPGA\demo\before.png  E:\FPGA\demo\after.png

# 指定输出目录 + 差异放大 8 倍 + 给报告加标签
& $py E:\FPGA\compare.py  before.png  after.png  -o E:\FPGA\out  --amp 8  --tag 黑电平56
```

`$py` 就是上面那条完整路径，先设一次省事：

```powershell
$py = "C:\Users\KX\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe"
```

★ **中文路径可以直接用**：脚本内部用 `np.fromfile` + `cv2.imdecode` / `cv2.imencode` + `tofile`
读写图片，绕开了 `cv2.imread` 在 Windows 上遇到中文路径返回 `None` 的老问题。
（终端本身若是 GBK 代码页，`print` 的中文可能显示成乱码，但 `report.txt` 一定是正确的 UTF-8；
脚本已对无法编码的字符做 `errors="replace"` 兜底，不会因为打印而崩。）

---

## 3. 三个输出物

| 文件 | 内容 |
|---|---|
| `report.txt` | 与终端完全相同的报告文本（**UTF-8 with BOM**，记事本双击可直接看） |
| `diff.png` | 2×2 四格：before / after / \|diff\|×amp（越白改动越大）/ signed diff（红=变亮、蓝=变暗，seismic 色标 ±32） |
| `histogram.png` | 2×3 六格：灰度 256bin（纵轴对数）/ RGB 32bin 分组 / 灰度 CDF / RGB 通道均值 / HSV 均值 / 差值分布 |

终端报告分 **6 节**，与需求一一对应：

| 节 | 内容 |
|---|---|
| 1 基础统计 | RGB 均值/标准差、灰度均值/标准差、HSV 的 S/V 均值、色相算术均值与**圆均值** |
| 2 直方图特征 | 灰度 32bin、R/G/B 各 32bin（含占比）、1/5/50/95/99 分位数、灰度熵、纯黑/纯白占比 |
| 3 影调特征 | 黑场(P1)、白场(P99)、动态范围（P99-P1 与 max-min）、中间调均值、RMS/Michelson/梯度三种对比度、P1..P99 内实际灰度级数 |
| 4 色彩特征 | 灰世界增益 R/G/B、白点(P99)、Lab 的 Δa*/Δb*、偏色方向（8 扇区中文名）+角度、HSV S、彩度(max-min)、灰像素占比、R/B 比 |
| 5 差异分析 | MAE（灰度与逐通道）、RMS、最大差、PSNR、差异占比(>2/>8/>32)、通道增益比、相对绿通道的 WB 比、亮度/对比度/饱和度/色偏的变化方向 |
| 6 反推参数建议 | 8 小节：黑电平 → gamma/中间调 → 曝光 vs 增益判别 → SC500 增益寄存器换算 → 白平衡 → 饱和度/线性拉伸 → 链路健康度 → 差异总览 |

---

## 4. 命令行参数

| 参数 | 默认 | 说明 |
|---|---|---|
| `before` | 必填 | FPGA 当前输出图（png/jpg/bmp/tif 均可，16bit/灰度/BGRA 会自动归一化） |
| `after` | 必填 | LR 调整后 / 目标图 |
| `-o, --outdir` | after 所在目录 | 输出目录（不存在会自动建） |
| `--amp` | `4` | `diff.png` 里绝对差图的放大倍数（差异小就调大，例如 8/16） |
| `--tag` | 空 | 报告标题追加标签，如 `--tag 增益8x前` |

尺寸不一致时：**after 会被 `INTER_AREA` 缩放到 before 的尺寸**，报告顶部给出警告
（缩放会引入额外模糊，差异分析可信度下降 —— 最好让两张图尺寸一致）。

---

## 5. 报告里几个关键判据怎么读

* **黑场(P1) / 白场(P99)**：比 min/max 抗噪。黑场抬高 = 暗部发灰（黑电平没扣干净或抬了暗部）；
  白场贴 255 + 纯白占比 > 2% = 高光截断（增益/曝光过头）。
* **P1..P99 灰度级数**（阈值 100）：过少 = **量化台阶/断阶**。本工程链路是 10bit→8bit 且要右移 2 位，
  再叠加增益放大，这个数字很有诊断价值。
* **中间调均值** 与目标 `TARGET_MIDTONE=118` 比较：偏离 > 6 就给出亮度乘数建议。
* **RMS 对比度 / 梯度局部对比度**：前者是全局反差，后者近似"细节/锐度"。
  只提亮度不提高前者 = 发灰；后者下降 = 被模糊（例如插值/降采样引入）。
* **灰世界增益 = 灰度均值 / 该通道均值**：= 1 表示该通道已平衡；比值就是 AWB 需要的乘数。
  报告在增益 > 4.0x 时会告警（本工程 `awb.v` 的增益饱和是 `20'hfffff`=16.0x，工程上建议按 4.0x 收敛）。
* **相对绿通道的通道比 R/G、B/G**：剔除了整体曝光变化后的"纯色偏变化"，
  只有约等于 1 才说明这次调整没动白平衡。
* **曝光 vs 增益的判别逻辑**（第 6 节第 3 小节）：
  * 黑场不动、信号按比例变 → **曝光/积分时间**起作用 → 改 `3e00/3e01/3e02`；
  * 黑场与信号一起按比例变 → **模拟增益**起作用（增益会把黑电平一起放大）→ 改 `3e08/3e09`；
  * 信号幅度不变、黑场整体平移 → **黑电平/偏置**作用 → 改 `mipi_to_raw_converter.v` 的 `S_blk_level`。
* **黑电平换算**：本工程 `raw8 = (raw10 - S_blk_level + 2) >> 2`，
  所以 8bit 域差 `d` 等价于 10bit 域差 `4*d`；报告直接给出「`S_blk_level` 从 56 改成多少」。

---

## 6. 脚本里写死、需要随工程同步的常数

报告第 6 节和末尾「参考常数」会引用这几个值，**工程改了要同步改脚本顶部常量**：

| 常量 | 当前值 | 依据 |
|---|---|---|
| `CURRENT_SC500_GAIN_REG` | `(0x1F, 0x2D)` | 模拟增益 `3e08=0x1F, 3e09=0x2D` ⇒ 11.25x（`uics500_cfg/uics500reg_720p60.v`） |
| `SC500_GAIN_MAX` | `15.75` | 手册表2-4 模拟增益上限（0x1F3F） |
| `CURRENT_BLK_LEVEL` | `56` | `isp/demosaic_4x_2_0/mipi_to_raw_converter.v` 的 `S_blk_level` |
| `TARGET_MIDTONE` | `118.0` | 18% 中性灰在 sRGB 下的码值 |
| 曝光 1990 | 报告中文字 | `{3e00,3e01,3e02}=0x07C6`，且为手册最大值 `2*VTS-10`（VTS=1000）**已顶满** |

---

## 7. 已知限制与判读陷阱

1. **灰度口径不同**：脚本用 Rec.601（`0.299R+0.587G+0.114B`），而本工程 `my_algo.v` 的
   `f_luma` 是自定义权重 —— 同一张图的"灰度均值"与屏上观感会有系统性小差异。
2. **手机照片不能当绝对亮度基准**：拍摄包含显示器电光曲线、手机 AE/AWB/HDR。
   跨设备的绝对亮度/色温比较无意义，只有**同一台设备、同一次拍摄**的 before/after 才有意义。
3. **8bit 量化的天花板**：报告只能看到"输出看到了什么"，看不到 RAW10 域的真实动态。
   要判 10bit 域的问题（黑电平、削顶），还得看 ChipWatcher 采的 `S_axis_tdata[39:0]`。
4. **灰世界假设**：画面被大面积单色物体占据时（例如满屏绿草、红纸），灰世界算出的 AWB 增益会偏。
   此时应结合 Lab 偏色方向与白点(P99)一起判断。
5. **断阶判据是启发式**：`P1..P99 内级数 < 100` 只是提示，不是判决 —— 画面本来就低反差的场景
   （雾、纯色墙面）也会出现级数少。
6. **色相均值**：色相是角度量，报告同时给算术均值与圆均值，**以圆均值为准**，
   并给出合成向量长度（接近 0 表示色相分散、均值没意义）。
7. **`diff.png` 的 signed diff 固定 ±32**：差异超过 ±32 会饱和成纯红/纯蓝，
   这是为了看清小差异；要看大差异请调 `--amp` 看绝对差图。

---

## 8. 推荐工作流（配合本工程）

1. FPGA 出图 → 存 `before.png`（HDMI 采集卡截图，或手机固定机位拍屏，**机位/灯位别动**）。
2. 在 LR 里调到"希望 FPGA 达到的样子" → 导出 `after.png`（同尺寸、同分辨率）。
3. 跑 `compare.py`，看第 6 节的**第 1/2/3/4 小节**，得到三类候选改动：
   `S_blk_level`、gamma LUT/线性拉伸、曝光或增益寄存器。
4. **一次只改一项**（改完重编译、重拍、复跑脚本），否则无法归因。
5. 每轮把 `report.txt` 存一份（例如 `report_20261010_黑电平56.txt`），形成可回查的调参记录。

---

## 9. 示例输出

见同目录 `示例输出_compare_demo.txt`（真实运行结果，用 `E:\FPGA\demo\before.png` /
`E:\FPGA\demo\after.png` 这一对演示图跑出来的完整终端报告）。
演示图由 `E:\FPGA\_analysis\make_demo_pair.py` 从工作区真实照片
`E:\FPGA\mode0室内常光.jpg` 生成：before = 原样，after = 模拟一次 LR 调整
（曝光 +0.15EV、暗部 +6、gamma 0.92、R×1.06 / B×0.96、饱和度 ×1.25）。
