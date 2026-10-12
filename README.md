# FPGA 实时数字图像处理系统

全国大学生嵌入式芯片与系统设计竞赛 · FPGA 创新设计赛道 · 选题二
**基于安路 PH1P35 的实时数字图像处理系统**

```
MIPI 摄像头 (SC500, 1280x720@60)  ->  [ 安路 PH1P35 FPGA ]  ->  HDMI 显示器 (1280x720@60)
```

* 芯片：安路 `PH1P35MDG324`（38184 LUT / 42432 DFF / 40 DSP / 108 ERAM / 板载 QSPI Flash 128 MB）
* 工具：TangDynasty（TD）
* 基线工程：官方 `lab_ex3_osd_SC500_720P` 二次开发
* 截止：**2026-11-04**

---

## 快速开始（新队友先做这三步）

```powershell
git clone https://gitee.com/wuhu-captain-kx/fpgacnds.git
cd fpgacnds
git config --global core.autocrlf false        # ★必做★ 源文件是 GBK/CRLF 混合的

python _analysis\scripts\compile_check.py      # 期望 exit=0: 39 / 40
```

**看到的数字必须是 `39 / 40`**，唯一允许失败的是 `ph1p35_ddr\ph1p35_324_ddr_wrapper.v`
（原厂黑盒保护，不是错误）。出现别的失败 = 环境问题，先解决再往下走。

然后读：

| 你是谁 | 先读 |
|---|---|
| 所有人 | [`docs/团队协作指南.md`](docs/团队协作指南.md)（环境、目录、铁律、构建命令） |
| 所有人 | [`docs/协作流程与时间表.md`](docs/协作流程与时间表.md)（里程碑、分支约定、任务清单） |
| 成员 B | [`docs/给成员B的prompt.md`](docs/给成员B的prompt.md) |
| 成员 C | [`docs/给成员C的prompt.md`](docs/给成员C的prompt.md) |
| 所有人 | [`HISTORY.md`](HISTORY.md)（项目历史与踩过的坑）、[`MOVE_INDEX.md`](MOVE_INDEX.md)（文件迁移索引） |

---

## 数据通路

FPGA 内部的 ISP 链路，全部在 [`proj/baseline/lab3/user_source/hdl_source/isp/isp_top.v`](proj/baseline/lab3/user_source/hdl_source/isp/isp_top.v) 里例化：

```
MIPI RX
  └─ demosaic ............ 去马赛克（BGGR），内含黑电平扣除
       └─ data128_96 ..... 128bit -> 96bit 位宽转换（4 像素/拍）
            └─ awb ....... 自动白平衡（灰世界，4 通道并行，TD divider IP）
                 └─ isp_gamma ..... 色调曲线（256 项查找表，2 拍流水）
                      └─ my_algo .. 风格化算法集（直通/灰度/伪彩/彩条/卡通化）
                           └─ data_96bit_to_128bit
                                └─ hdmi_mixer ... OSD 叠加（Logo + CNT + MODE）
                                     └─ HDMI TX
```

ISP 域时钟 = `S_csi_rx_clk` = `MIPI_RX_BYTE_CLK`，60 MHz，每拍 4 个像素。

### 关键模块位置

| 模块 | 路径 |
|---|---|
| 顶层 | `proj/baseline/lab3/user_source/hdl_source/design_top_wrapper.v` |
| ISP 顶层 | `proj/baseline/lab3/user_source/hdl_source/isp/isp_top.v` |
| 黑电平扣除 | `proj/baseline/lab3/user_source/hdl_source/isp/demosaic_4x_2_0/mipi_to_raw_converter.v` |
| 自动白平衡 | `proj/baseline/lab3/user_source/hdl_source/isp/awb/awb.v` |
| 色调曲线 | `proj/baseline/lab3/user_source/hdl_source/isp/isp_gamma.v` |
| 风格化算法 | `proj/baseline/lab3/user_source/hdl_source/my_algo/my_algo.v` |
| 按键模式切换 | `proj/baseline/lab3/user_source/hdl_source/my_algo/key_mode_ctrl.v` |
| OSD 叠加 | `proj/baseline/lab3/user_source/hdl_source/hdmi_mixer.v` |
| 字符点阵库 | `proj/baseline/lab3/user_source/hdl_source/osd_char_lib.v` |
| 传感器 I2C 配置 | `proj/baseline/lab3/user_source/hdl_source/uics500_cfg/` |
| 引脚约束 | `proj/baseline/lab3/user_source/constraints_source/pin.adc` |
| 时序约束 | `proj/baseline/lab3/td_project/camera_to_dsi_display.sdc` |
| TD 工程 | `proj/baseline/lab3/td_project/camera_to_dsi_display.al` |

---

## 板载开关（实测极性：拨上 = 逻辑 0 = 启用）

| 开关 | 引脚 | 功能 |
|---|---|---|
| SW1 | A4 | 黑电平扣除旁路。**上 = 启用扣除**，下 = 直通 |
| SW2 | B4 | 色调曲线旁路。**上 = 曲线启用**，下 = 直通 |
| SW3 | E11 | 数字增益 ×2.000。上 = 开，下 = 关 |
| SW4 | D11 | 模拟增益 15.750× / 4.000×。上 = 15.750×，下 = 4.000× |

增益档位组合：`下下 = 4.000×` / `上下 = 8.000×` / `下上 = 15.750×` / `上上 = 31.500×`（室内常用）

K1–K4 按键切换 `my_algo` 的算法模式（0 直通 / 1 灰度 / 2 伪彩 / 3 彩条 / 4 卡通化）。

---

## 当前状态（2026-10-12）

### 已验证 OK

| 项 | 证据 |
|---|---|
| 采集链（HDMI 采集卡 → OBS → PNG）是 identity | 用 FPGA 内置的安路 Logo ROM 当色卡（6387 个不透明像素、579 种颜色、每个像素的精确 RGB 和屏幕位置都已知），实测色差 1~3 码 |
| S 曲线确实在通路里 | 曲线开/关两张对比，把旁路图每个分位数过 LUT 预测，与实测差 **±3 码以内**，均值差 +0.38 |
| 运行时增益下发正常 | SW3 数字增益 ×2 实测生效，`LUT[旁路图 p90 ÷ 2]` 与曲线图 p90 完全命中 |
| 黑电平常数 `BLACK_LEVEL = 10'd56` | Testbench `ALL PASS, errors=0`；盖镜头实测 R=B=0、G≤1 码 |
| 除法器 IP 在真实 valid 图案下正常 | 门级仿真 4 种 `start` 占空比（含真实 `1,1,0`），商永远正确、`done` 照常拉高 |
| AWB 的数学是对的 | TB：输入 R/G=0.800 的整帧 → 输出 R/G = **1.0000**（精确） |
| 测试图 bug 已修 | 传感器内置灰度测试图曾被四开关全「上」（推荐工作档）意外点开，已从 RTL 层面拔掉 |

### 未解决

| 问题 | 现状 |
|---|---|
| **AWB 有一个 −3 码的加性偏置** | 5 个场景实测 R−G ≈ −3.2 码、B−G ≈ −3.0 码，**与亮度无关**（Y 从 20 到 69 都成立）。灰世界要求 R/G = B/G = 1.000，实测 0.88~0.96。已排除公式、除法器、每帧增益重置、采集链 4 个方向 |
| **色调曲线仍是「反 S」** | 指数 `A = B = 0.5`（两段都是凹函数），实测把动态范围从 199 码压到 148 码（对比度 **−26%**），画面发灰 |
| **画面上没有任何参数数值** | 扩展要求原文点名「在画面上呈现参数变化信息」，现在 OSD 只有 `CNT` 和 `MODE` 两行 |
| **没有自动曝光** | 曝光硬写死 `0x3e00/01/02 = 1990`（已顶满 `2×VTS−10`），增益只能手拨四选一。光照不可控时是开盲盒 |
| QSPI 固化未做 | 官方硬性要求，但**已决定移到 11-04 之后的线下阶段**（见 `docs/协作流程与时间表.md` §8） |

---

## 资源与时序基线

最近一轮完整构建（2026-10-12 01:49，K=45 黑位版）：

| 项 | 值 |
|---|---|
| Setup WNS / TNS / 违例端点 | **+84 ps / 0 / 0** |
| Hold WNS / TNS / 违例端点 | **+20 ps / 0 / 0** |
| `#slices` | 17687 / 21216 (83.37%) |
| `#RAMs` | 60 |
| `#DSPs` | 8 / 40 (20.00%) |
| `#eram` | 60 / 108 (55.56%) |
| `#lut6` | 14915 / 21216 (70.30%) |
| `#IO` | 68 / 160 (42.50%) |
| 比特流 | `camera_to_dsi_display.bit` 1789539 B |

---

## 铁律

1. **不要改 `mipi_to_raw_converter.v` 的 `BLACK_LEVEL`**（现在 `10'd56`，实测标定值，翻过两次车）。
2. **不要改 `design_top_wrapper.v` 里 `S_blk_bypass` 的极性**（同样翻过车）。
3. **不要在 RTL 里写 `a * b`**。TD 会推断成 DSP 硬核；芯片只有 40 个，历史上一次把整机 DSP 顶到 40/40 用满，
   还连锁造成 5 个时序违例。乘常数要手写移位 + 加法。
4. **`isp_gamma.v` 的内联 LUT 不要改成 `$readmemh`**。TD 综合工作目录是 run 目录，相对路径读不到 `.hex`
   **而不报错**，表会全变 0、报告全绿、上板全黑。
5. **不要推 `main`**，开 `feat/*` 分支走 PR。动 `design_top_wrapper.v` 就在 commit 首行写 `TOUCHES: design_top_wrapper.v`。
6. **本地未推送的改动不超过 24 小时**。

---

## 目录导航

| 目录 | 内容 | 是否入库 |
|---|---|---|
| `proj/baseline/lab3/` | **主战场**：RTL、约束、TD 工程 | ✅ |
| `docs/` | 团队协作指南、时间表、队友 Prompt | ✅ |
| `_analysis/scripts/` | 约 190 个 Python 工具（分析 / 补丁 / 验证 / LUT 生成） | ✅ |
| `_analysis/lut/` | 色调曲线 LUT（`.hex` / `.mif` / `.coe` / `.vh` / `.csv`） | ✅ |
| `_analysis/sim/` | ModelSim Testbench | ✅ |
| `_analysis/*.md` | 设计文档（黑电平方案、色彩诊断、AE 可行性评估等） | ✅ |
| `_analysis/out/` | 分析产物图片 | ❌ 已 gitignore |
| `captures/` | **实拍采集归档**，按日期分组，每组一个 README | ✅ |
| `tools/compare/` | `compare.py`（对比两张图并生成报告） | ✅ |
| `raw_exports/` | ChipWatcher 导出 CSV | ✅ |
| `HISTORY.md` / `MOVE_INDEX.md` | 提交历史转录 / 文件迁移索引 | ✅ |
| `官方资料/` | 芯片手册、开发板手册、赛题文件、TD 安装包 | ❌ 体积过大（7 GB） |
| `anlogic_example/` | 安路官方例程（lab1/2/3） | ❌ |
| `_backup/` | 源码级与比特流备份 | ❌ |
| `_archive/` | 归档 | ❌ |
