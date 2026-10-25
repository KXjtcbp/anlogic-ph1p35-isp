# 工程台账（模块 · 资源 · 约束 · 风险）

> 数据源：`proj/releases/2026-10-18_a2_hold60/camera_to_dsi_display_phy.area`
> 更新 2026-10-23 ｜ 所有百分比按 TangDynasty 口径（`#lut6` 总量 21 216）

## 一、交付版整机资源

| 项 | 用量 | 占比 |
|---|---|---|
| Slice | 17 448 / 21 216 | **82.24%** |
| LUT6 | 16 400 / 21 216 | **77.30%** |
| DFF | 12 092 / 42 432 | 28.50% |
| ERAM | 51 / 108 | **47.22%** |
| DSP | 10 / 40 | 25.00% |
| f7mux | 94 / 10 608 | 0.89% |
| f8mux | 47 / 5 304 | 0.89% |
| GCLK | 9 / 32 | 28.12% |
| SCLK | 21 / 48 | 43.75% |

时序：**Setup WNS +104 ps / TNS 0 / 违例 0；Hold WNS +21 ps / TNS 0 / 违例 0**。

★**余量判断**：Slice 只剩 3 768 个（17.76%），LUT6 剩 4 816 个。加任何新模块前先算这个数。经验值：往 OSD 路径里加 1 bit 逻辑，Setup WNS 曾从 +104 ps 掉到 +2 ps（因为 OSD 在 75 MHz 像素域、逻辑级数已深）。**动 `hdmi_mixer.v` 必须重新综合看时序。**★

## 二、顶层模块台账

`design_top_wrapper.v` 例化 15 个子模块：

| 实例 | 模块 | LUT | Ripple | FF | ERAM | 归属 | 说明 |
|---|---|---|---|---|---|---|---|
| `u_ph1p35_324_ddr_wrapper` | DDR2 控制器 | 2 553 | — | — | 多 | 官方 | 帧缓存 |
| `u_isp_top` | ISP 链 | 5 668（聚合） | — | — | 34 | **自研为主** | 见下节 |
| `u_hdmi_mixer` | OSD 叠加 | **3 747** | 75 | 428 | 0 | **自研改动** | 8 层 OSD，改动最大 |
| `u_hdmi_tx` | HDMI 1.4b | 637 | 28 | 1 224 | 5 | 官方 | 加密 IP |
| `u_PLL` | 时钟 | — | — | — | — | 官方 | 3 个输出 |
| `uivtc` | 视频时序 | — | — | — | — | 官方 | 720p60 |
| `video_in` / `video_out` | AXI-Stream FIFO | — | — | — | — | 官方 | |
| `u_csi_unpacket` | CSI 解包 | — | — | — | — | 官方 | |
| `u_raw10_unpacket` | RAW10 解包 | — | — | — | — | 官方 | → 40 bit / 4 像素 |
| `u_mc_to_user_interface` | DDR 用户接口 | 37 | 18 | 29 | 4 | 官方 | |
| `u_uicfgcs500` | 传感器 I2C 配置 | — | — | — | — | **自研改动** | 接 AE 表 |
| `u_key_mode_ctrl` | 按键切模式 | 108 | 93 | 149 | 0 | **自研** | K1~K4 + 长按 |
| `u_ae_ctrl` | AE 闭环 | 127 | 85 | 188 | 0 | **自研** | 24 MHz 域 |
| `uial2axis` | | — | — | — | — | 官方 | |

## 三、ISP 链内部（`isp_top.v`，串行顺序）

```
demosaic → data128_96 → lsc → (ae_stat 旁路观察) → awb → isp_gamma → my_algo → data96_128
```

| 实例 | 模块 | LUT | Ripple | FF | ERAM | DSP | 归属 |
|---|---|---|---|---|---|---|---|
| `u_demosaic` | 去马赛克 | 742 | — | — | 12 | — | 官方（改了 `black_level=56`） |
| `u_data128_96` | 128→96 bit | — | — | — | — | — | 官方 |
| `u_lsc` | **镜头暗角校正** | 828 | 662 | 266 | 0 | 0 | **自研** |
| `u_ae_stat` | **帧亮度统计** | 257 | 175 | 263 | 0 | 0 | **自研** |
| `u_awb` | 白平衡 | 854 | — | 601 | 10 | 10 | 官方（大改） |
| `u_wb_recip_r` / `_b` | **倒数查表** | 153 + 157 | — | — | — | — | **自研**（替代 TD 除法器，省约 1 700 LUT） |
| `u_isp_gamma` | **真 S 曲线 LUT** | 122 | 0 | 206 | 12 | 0 | **自研** |
| `u_my_algo` | **五模式风格化** | 643 | 36 | 121 | 0 | 0 | **自研** |
| `u_motion_detect` | **块级帧差** | 1 179 | 320 | 1 784 | 0 | 42/21（dram/shifter） | **自研** |
| `u_obj_detect` | **颜色目标检测** | 897 | 220 | 851 | 0 | 0 | **自研** |
| `u_data_96bit_to_128bit` | 96→128 bit | — | — | — | — | — | 官方 |

★三个「旁路观察者」只收不发、不占主流水线节拍：`ae_stat`、`obj_detect`、`motion_detect`。**它们改变了主流水线的空拍吗？没有——观察者只读 `tdata/tvalid/tuser`，不参与 `tready` 握手。**★

## 四、时钟域与 CDC

| 时钟 | 频率 | 谁在跑 |
|---|---|---|
| `mipi_rx_ck_pad` | 240 MHz | MIPI D-PHY |
| `MIPI_RX_BYTE_CLK` = `S_csi_rx_clk` = `axi4s_video_aclk` | **60 MHz** | **整条 ISP 链**（每拍 4 像素） |
| `pll_clk_24m` | 24 MHz | 按键、拨码同步、AE 闭环、传感器 I2C |
| `HDMI_PIXEL_CLK` | 75 MHz | `hdmi_mixer`、`hdmi_tx` |
| `HDMI_SERIAL_CLK` | 375 MHz | HDMI 串行 |
| DDR 两个 | — | `ph1p35_324_ddr_wrapper` |

`sdc` 里三组 `set_clock_groups -asynchronous`（MIPI / sys+pll+HDMI / DDR），另加两条 `set_max_delay -datapath_only`：
- `pll_clk_24m → HDMI_PIXEL_CLK` **8.000 ns**（遥测总线单 bit 翻转跨域）
- `MIPI_RX_BYTE_CLK → pll_clk_24m` **20.000 ns**（AE 统计结果跨域）

★另有一条 `set_false_path -from [get_clocks {config_inst.cwc_tck_o}]`——TD 的 JTAG 调试中枢会在 `config_inst.cwc_tck_o`（100 ns）与 `MIPI_RX_BYTE_CLK` 之间生成一条假路径，不加这条会报 −231 ps 的假违例。★

## 五、OSD 八层（`hdmi_mixer.v`）

按优先级从低到高，后画的盖前面的：

| # | 图层 | 位置（内部 1280×720 坐标） | 内容 |
|---|---|---|---|
| 1 | Logo | (0, 0) 160×160 | 安路 Logo（ROM，298 506 B，579 种颜色） |
| 2 | CNT | (375, 120) 200×24 | `安路 CNT:xxxxxx` 帧计数 |
| 3 | MODE | (176, 176) 84×10 | `MODE n` |
| 4 | 遥测行 1 | (376, 152) | `AE<gi>S<st>M<ml>W<gr>B<gb>` |
| 5 | 遥测行 2 | (376, 164) | `F<flags>T<settle>N<next>D<dec>U<inc>` |
| 6 | 参数行 | (376, 176) | `S-CURVE ON  LSC ON  MOT:1 SENS H` |
| 7 | 运动框 | 全屏 | 144 块（16×9）红色描边 |
| 8 | 目标框 | 全屏 | 绿色绿色矩形描边 |

★**位置是 1280×720 内部坐标，屏幕上要乘 1.5 才是 1920×1080 的实际位置**★（曾按 1280 坐标去 1920 图里找 OSD，找了半天）。

## 六、坑清单（按踩过次数排序）

| 坑 | 现象 | 规避 |
|---|---|---|
| **TD 只认 run 目录的 `.prj`** | 改了 `.al`、综合照旧；或新 `.v` 报 black box | 新增文件三处都写：`.al` + `syn_1/*.prj` + `phy_1/*.prj`；综合后复查 `.al` 是否被 TD 回写 |
| **模块被当冗余扫掉** | `#RAMs` 从 51 掉到 12、功能全丢 | 综合后核对 `#RAMs`=51、`#DSPs`=10；新模块必须在 `*.area` 里搜得到 |
| **`.bit` 时间戳变新 ≠ 成功** | 以为构建好了，烧上去是旧的 | 查日志 `HDL-8007` + `route.qor` 数字有没有变 |
| **常数乘法被推断成 DSP** | `r*77` 顶满 40/40，迫使别处乘法走 LUT，产生违例 | 一律手写移位加法 |
| **`wire` 漏写位宽** | 被推断成 1 bit，算术结果截断成最低位 | 任何做算术的 `wire` 显式写 `[n:0]`；溢出判断要在截断之前 |
| **同一 always 块对同一 reg 多次非阻塞赋值** | 只有最后一条生效 | 想清楚再写，或拆块 |
| **UTF-8 BOM** | ModelSim 报 `syntax error, unexpected non-printable character` | GBK 文件改写后检查首 3 字节 |
| **中文路径 + OpenCV** | `cv2.imread` 静默返回 `None` | 用 `np.fromfile` + `cv2.imdecode` |
| **`$readmemh` 相对路径** | TD 在 run 目录综合，读不到 → 表全 0 → 黑屏但报告全绿 | 表一律内联进 `initial` |
| **测量口径** | 把 `#lut6` 与宣传的「等效 LUT」混用 | 全仓库统一 TD 口径 |
| **两份 `awb.v`** | 改动打在没进综合的那份上 | 认准 `hdl_source/awb.v` |

## 七、当前仍未解决的 5 项

| 编号 | 问题 | 当前状态 | 影响 |
|---|---|---|---|
| 1 | R/B 相对 G 约 2~3 码加性偏置 | 亮场景达标（R/G 0.985、B/G 0.983），**暗场景仍偏绿**（Y≈30 时 R/G 0.947） | 演示时选亮场景即可回避 |
| 2 | 目标检测只支持红色 | 颜色判定阈值固定（`R≥56 且 R−G≥24 且 R−B≥24`） | 换颜色需改参数重综合 |
| 3 | 运动检测对整幅变暗不敏感 | 块级帧差对**全局**亮度变化天然不敏感（会整帧一起变，差值被阈值吃掉） | 手挡镜头不出框是正常行为，不是故障 |
| 4 | OSD 顶部 0~3 行品红瞬态 | 帧起始几行有 R 偏高的瞬时伪影 | 3 行 / 1080 行，肉眼基本不可见 |
| 5 | QSPI 固化 | ✅ **已完成**（BitWriter Program Flash，md5 `DB39A5CE…`，断电自启，15 分钟长跑正常） | — |

## 八、构建与验证入口

| 用途 | 命令 |
|---|---|
| 语法回归 | `python _analysis/scripts/compile_check.py`（期望 **42/43**，唯一失败是官方 DDR 黑盒保护） |
| 综合 + 布线 | `pwsh -ExecutionPolicy Bypass -File _analysis/misc/td_run_direct.ps1 syn_1 phy_1` |
| 去 ChipWatcher 调试中枢 | 用 `_analysis/misc/DefaultFlow_noCWC.tcl`（省 9 ERAM / 4 852 FF / 781 slice） |
| 图像统计 | `python _analysis/scripts/stat_imgs.py <图...>` |
| LUT 生成 | `python _analysis/gen_gamma_lut_toe.py` 等，改完必须同步改 TB 的 `.vh` |

★**不要用 `Start-Process` 起 TD**——会卡死在 `phy_1` 之前且不报错。用 `pwsh` 直接调 `td_commands_prompt.exe`，或在后台任务里跑。★
