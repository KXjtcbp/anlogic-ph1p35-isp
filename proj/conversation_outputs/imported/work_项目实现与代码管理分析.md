# 选题二 · 项目实现与代码管理分析

> 依据：`E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\`（官方例程 lab_ex3，下称 **lab3**）+ lab_ex1 / lab_ex2 源码。
> 所有结论标注文件与行号。无法从资料确定的写「待确认」。
> 本文只覆盖工程与代码本身。

---

## 一、功能模块

### 1.1 系统数据通路（lab3 实测）

```
SC500CS 摄像头
   │ I2C 配置 (S_24m_clk)
   ▼
mipi_dphy_rx_ph1p_mipiio_wrapper   硬核 MIPI D-PHY RX，2 Lane，LOCATION="DPHY0"
   │ O_hs_rx_clk / O_hs_rx_valid / O_hs_rx_data[15:0]
   ▼
csi_unpacket_2lane  →  raw10_unpacket_2lane  →  uial2axis
   │ AXI4-Stream 40bit RAW10
   ▼
isp_top   (axi4s_video_aclk = S_csi_rx_clk)
   │  demosaic → data128_96 → awb → [算法插入点] → data96_128
   │ AXI4-Stream 128bit RGB888
   ▼
video_in   (写侧 S_csi_rx_clk / 读侧 S_ddr_clk)
   │  w128_d512_fifo 跨时钟域
   ▼
mc_to_user_interface  ──►  ph1p35_324_ddr_wrapper  ──►  片内 DDR2
   ▲                              │
   │                              │ O_mc_app_rd_data[127:0]
video_out  (I_dsi_clk = S_hdmi_pixel_clk)
   │  24bit RGB
   ▼
hdmi_mixer  (+ OSD: anlogic_logo_rom / osd_char_lib)
   ▼
hdmi_tx   →  hdmi_1_4b_transmitter_core_wrapper.enc.v  →  hdmi_phy_warpper  →  TMDS
```

### 1.2 模块清单（按源码目录）

| 层级 | 模块 | 文件 | 职责 | 关键接口 |
|---|---|---|---|---|
| **顶层** | `design_top_wrapper` | `hdl_source/design_top_wrapper.v`（27,882 B） | 例化 15 个子模块，全部连线与时钟分配 | 见 §1.3 |
| **时钟** | `PLL` | `ip_source/PLL/PLL.v` | 1 入 4 出 | `.refclk(I_sys_clk)` `.clk0_out(S_100m_clk)` `.clk1_out(S_24m_clk)` `.clk4_out(S_hdmi_pixel_clk)` `.clk5_out(S_hdmi_serial_clk)` `.lock(S_pll_lock)`（L416–428） |
| **摄像头配置** | `ae_set` | `hdl_source/uiisp_beta/ae_set.v` | 按键 → 曝光/增益请求 | `.I_clk(S_24m_clk)` `.I_btn({I_button,2'b11})` `.O_ae[15:0]` `.O_ag[15:0]`（L434–443） |
| | `uicfgcs500_720p` | `hdl_source/uics500_cfg/uicfgcs500_720p.v` | I2C 写 SC500 寄存器表 | `.CLK_DIV(24000000/100000-1)`、`.I_clk(S_24m_clk)`、`.O_cfg_done`（L445–457） |
| | `SC500GainTbl` / `uics500reg_720p60` / `uics500regAE` / `uii2c` | `hdl_source/uics500_cfg/` | 增益表 / 720p60 寄存器表 / AE 寄存器 / I2C 主机 | — |
| **MIPI 接收** | `mipi_dphy_rx_ph1p_mipiio_wrapper` | `hdl_source/mipi_dphy_rx/…sv` | 硬核 D-PHY RX 封装，参数 `DPHY_RX_LOCATION("DPHY0")` `HS_EQUALIZER("0dB")` `HS_VGA_GAIN("8dB")` `LANE_NUM(2)` `BYTE_NUM(1)` | `.I_lp_clk(S_100m_clk)` → `.O_hs_rx_clk(S_csi_rx_clk)` `.O_hs_rx_data[15:0]` `.O_lane_error[1:0]`（L459–495） |
| **CSI 解包** | `csi_unpacket_2lane` → `raw10_unpacket_2lane` → `uial2axis` | 三个目录各有一份同名文件 | 包头解析 → RAW10 解包 → 转 AXI4-Stream | L507 / L521 / L538 |
| **ISP 顶层** | `isp_top` | `hdl_source/isp/isp_top.v`（**3,588 B, 115 行**） | ISP 流水线容器，**算法插入点在此** | 见 §2.1 |
| | `demosaic` 链 | `isp/demosaic_4x_2_0/`：`demosaic.v` `line_buffer_demosaic.v` `bilinear_interpolation.v` `raw_matrix_3x3_buffer.v` `mipi_to_raw_converter.v` `zhenghe.v` | Bayer(BGGR) → RGB888，含两个 BRAM IP | `#(.IMG_HEIGHT(720),.IMG_WIDTH(1280),.data_complete_delay(50),.BAYER_MODE("BGGR"))` |
| | `data128_96` | `isp/data128_96/data128_96.v`（587 B） | 128bit→96bit | — |
| | `awb` | `hdl_source/awb.v`（13,082 B）+ `isp/awb/awb.v`（17,237 B） | 自动白平衡 | `#(.IMG_HEIGHT(720),.IMG_WIDTH(1280))` |
| | `data96_128` / `data_96bit_to_128bit` | `isp/data96_128/data96_128.v`（2,365 B）/ `hdl_source/data_96bit_to_128bit.v`（2,100 B） | 96bit→128bit，**同一功能两处定义** | — |
| **帧缓存** | `video_in` | `hdl_source/video_in.v`（**6,994 B, 204 行**） | 摄像头侧写入 DDR，四帧乒乓，跨时钟 FIFO | 见 §2.2 |
| | `video_out` | `hdl_source/video_out.v`（**7,000 B**） | 从 DDR 读出并按显示时序输出 | 见 §2.2 |
| | `w128_d512_fifo` | `ip_source/w128_d512_fifo/` | 512 深跨时钟 FIFO（有效深度约 410） | — |
| | `w155_d512_fifo` / `w40_d512_fifo` | `ip_source/` | 寄存器已登记在 `.al`（w155 有），**w40 未登记在 `.al`** | 待确认是否仍在用 |
| **DDR 控制器** | `ph1p35_324_ddr_wrapper` | `hdl_source/ph1p35_ddr/ph1p35_324_ddr_wrapper.v`（4,502 B） | 封装 DDR MC + PHY | 见 §2.3 |
| | `ddr2` 全套 | `ph1p35_ddr/ddr2/`：`ddr2.v` `ph1p_ddrmc_top.v` `ph1p_ddrmc_wrapper_63f4ac254419.v` + `src/rtl/{phy,mc,clk,init,misc,timing}/` | 完整 MC/PHY 源码 | — |
| | `mc_to_user_interface` | `hdl_source/mc_to_user_interface.v`（2,762 B） | DDR 仲裁：写优先于读 | L656 |
| **显示时序** | `uivtc` | `hdl_source/vtc/uivtc.v`（5,798 B） | 视频时序控制器，1 clk = 1 pixel | 见 §1.3 |
| **OSD 混合** | `hdmi_mixer` | `hdl_source/hdmi_mixer.v`（**41,314 B, 909 行**） | 2D 窗口读数据 + OSD 叠加 + 调试图案 | 见 §2.4 |
| | `anlogic_logo_rom` | `hdl_source/anlogic_logo_rom.v`（**298,506 B**） | 160×160 Logo ROM，25bit/像素（最高位=透明度） | — |
| | `osd_char_lib` | `hdl_source/osd_char_lib.v`（38,988 B） | 字符库（"安路 CNT:" 等） | — |
| **HDMI 输出** | `hdmi_tx` → `hdmi_1_4b_transmitter_core_wrapper.enc.v`（**328,975 B，加密/混淆源码**）→ `hdmi_phy_warpper` → `lane_lvds_10_1` | `hdl_source/` | TMDS 编码与串化 | — |
| **音频（未使用）** | `I2S_receiver` / `audio_arc_calculate` | `hdl_source/` | 音频接收与计算 | lab3 例化时 `.I_audio_left_data(24'd0)` `.I_audio_right_data(24'd0)` |
| **按键** | `key_remove_shakes` | `hdl_source/key_remove_shakes.v`（1,762 B） | 按键消抖 | — |
| **其它（lab3 未登记）** | `BLC.v` `image_correction.v` `video_cuttting.v` `auto_white_balance.v` `raw8_to_rgb888.v` `raw10_unpacket.v` `csi_unpacket.v` `ps_wrapper.v` `signal_delay.v` `pll_hdmi.v` | 存在于 `hdl_source/` 但**未在 `.al` 中登记** | 属历史/未启用代码 | 待确认是否可删 |

### 1.3 顶层端口与时钟域

**`design_top_wrapper` 端口**（`design_top_wrapper.v` L3–39）
```verilog
input  I_sys_clk, I_rst_n;
output O_cam_scl;  inout IO_cam_sda;  output O_cam_24m, O_cam_rst;
inout [1:0] I_button;  output O_screen_pwm;
output O_tmds_ch0_p, O_tmds_ch1_p, O_tmds_ch2_p, O_tmds_clk_p;
inout IO_rx_clk_pad_n/p, IO_rx_data_pad_n[3:0]/p[3:0];
output [12:0] ddr_addr; output [1:0] ddr_ba; output ddr_cke/odt/cs_n/ras_n/cas_n/we_n;
output ddr_ck_p/ck_n; inout [1:0] ddr_dm/ddr_dqs_p/ddr_dqs_n; inout [15:0] ddr_dq;
```
> 注意：DDR 引脚宽度是 **DDR2** 形态（`ddr_addr[12:0]`、`ddr_dq[15:0]`、`ddr_dqs_p[1:0]`），但 `ph1p35_324_ddr_wrapper.v` L21 注释写的是 `// DDR3 signals` —— **注释与实际不符，不影响功能，但改 DDR 参数时别被误导**。

**时钟域（4 个 + PLL 输出）**

| 时钟 | 来源 | 频率 | 驱动哪些逻辑 |
|---|---|---|---|
| `S_100m_clk` | `PLL.clk0_out` | 100 MHz | MIPI D-PHY `I_lp_clk` |
| `S_24m_clk` | `PLL.clk1_out` | 24 MHz | `ae_set`、`uicfgcs500_720p`（I2C）、`O_cam_24m` |
| `S_hdmi_pixel_clk` | `PLL.clk4_out` | 像素时钟（720p60） | `video_out.I_dsi_clk`、`hdmi_mixer`、`hdmi_tx` |
| `S_hdmi_serial_clk` | `PLL.clk5_out` | **375 MHz**（2.667 ns） | `hdmi_phy_warpper`/串化；**lab3 最紧时序路径在这** |
| `S_csi_rx_clk` | D-PHY `O_hs_rx_clk` | 由摄像头链路恢复 | `isp_top.axi4s_video_aclk`、`video_in.I_camera_clk` |
| `S_ddr_clk` | `ph1p35_324_ddr_wrapper.O_ddr_clk` | 由 DDR PHY 输出 | `video_in.I_ddr_clk`、`video_out.I_ddr_clk`、`mc_to_user_interface.I_clk` |

**复位**：`assign S_rst_n = S_pll_lock;`（L202）、`assign S_hdmi_rst_n = S_pll_lock;`（L203）、`assign S_video_out_rst_n = S_hdmi_rst_n;`（L632）→ **全系统复位直接由 PLL lock 驱动**，无独立复位状态机。

**未使用/悬空信号**（已知缺陷，见 §4）
- `S_aux_50m_clk`（L44）、`S_10m_clk`（L45）：只声明，**全文件无任何连接**
- `isp_top` 例化中 `.I_tdest()` 与 `.I_tready()` 悬空（L589、L595）
- `video_in` 例化中 `.I_mipi_rx_error(1'b0)`（L606）→ **MIPI 接收错误检测被硬接为常数，功能未启用**（`mipi_rx_error_detect.v` 存在但未接入）

### 1.4 显示时序参数（lab3 实测值）

```verilog
uivtc #(
  .H_ActiveSize(1280), .H_FrameSize(1650), .H_SyncStart(1390), .H_SyncEnd(1430),
  .V_ActiveSize(720),  .V_FrameSize(750),  .V_SyncStart(725),  .V_SyncEnd(730)
)   // design_top_wrapper.v L721–739
hdmi_mixer #(.H_OFFSET(0), .V_OFFSET(0), .IMG_WIDTH(1280), .IMG_HEIGHT(720), .DEBUG_MODE(0))  // L740–762
```
> H_FrameSize 1650 = 1280 + 370 消隐；V_FrameSize 750 = 720 + 30。
> **lab1 与 lab3 这 8 个参数逐字相同** → 分辨率配置不是 lab3 异常的原因。

---

## 二、架构与代码结构

### 2.1 ISP 算法插入点（唯一改造点）

`isp_top.v`（lab3 版 115 行）的流水线：
```
I_tdata[39:0] (RAW10)
  → demosaic #(.IMG_HEIGHT(720),.IMG_WIDTH(1280),.data_complete_delay(50),.BAYER_MODE("BGGR"))  → m_aixs_tdata[127:0]
  → data128_96                                                                                  → m_aixs_tdata_96[95:0]
  → awb #(.IMG_HEIGHT(720),.IMG_WIDTH(1280))                                                    → awb_O_tdata[95:0]
  → data_96bit_to_128bit (.I_96b_data(awb_O_tdata))   ← ★ 插入点就在这两者之间
  → O_tdata[127:0]
```
**lab3 现状：没有算法模块。** `awb` 输出直连 `data_96bit_to_128bit`（L95–106）。
**lab2 的范例（`isp_top.v` L84–132）**才插入 `edge_detect_96 #(.IMG_WIDTH(1280),.IMG_HEIGHT(720),.EDGE_TH(11'd80))`。

**插入点接口契约（96 bit = 3 像素 × 32 bit RGB888）**
```verilog
module <your_algo> (
    input  wire         I_clk,
    input  wire         I_rst_n,
    input  wire         I_tlast,      // 行尾
    input  wire         I_tuser,      // 帧头
    input  wire [95:0]  I_tdata,
    input  wire         I_tvalid,
    output wire         I_tready,     // 注意：output
    output wire         O_tlast,
    output wire         O_tuser,
    output wire [95:0]  O_tdata,
    output wire         O_tvalid,
    input  wire         O_tready      // 注意：input
);
```
参考 lab2 `isp_top.v` 的例化写法（**`I_tready` 是模块 output、`O_tready` 是模块 input，这是原例程约定，不要改**）：
```verilog
edge_detect_96 #(.IMG_WIDTH(1280), .IMG_HEIGHT(720), .EDGE_TH(11'd80)) u_edge_detect_96 (
    .I_clk(axi4s_video_aclk), .I_rst_n(I_rst_n),
    .I_tlast(awb_O_tlast), .I_tuser(awb_O_tuser), .I_tdata(awb_O_tdata),
    .I_tvalid(awb_O_tvalid), .I_tready(awb_O_tready),
    .O_tlast(edge_O_tlast), .O_tuser(edge_O_tuser), .O_tdata(edge_O_tdata),
    .O_tvalid(edge_O_tvalid), .O_tready(edge_O_tready)
);
```
需在 `isp_top` 内新增 5 根 wire：`edge_O_tlast / edge_O_tuser / edge_O_tdata[95:0] / edge_O_tvalid / edge_O_tready`。

**已写好的自研模块**：`E:\FPGA\work\rtl\my_algo.v`（5,935 B）
- 参数：`OFF`（1=直通）、`THRESH[7:0]`、`MODE_INIT[1:0]`
- 端口与 `edge_detect_96` 完全一致
- ⚠️ **未登记进 `.al`、未编译过、未上板**

### 2.2 帧缓存架构（`video_in` / `video_out`）

**四帧乒乓，地址基址**（`video_in.v` L40–43）
```verilog
localparam IMAGE_BASE_ADDR_0 = 25'd0;
localparam IMAGE_BASE_ADDR_1 = 25'd7000000;    // 7,000,000
localparam IMAGE_BASE_ADDR_2 = 25'd14000000;
localparam IMAGE_BASE_ADDR_3 = 25'd21000000;
```
> 25 bit 地址空间 = 33,554,432；4 帧占 28,000,000。地址按 `+ 'd8` 递增（L198）→ **地址单位是 8 字节（128 bit / 16）**，1 行 1280 像素 × 3 字节 = 3,840 字节 = 480 个地址步进。
> 一帧 1280×720×3 = 2,764,800 字节 = 345,600 步进，远小于 7,000,000 的帧间距 → **单帧容量足够**。

**写侧门控**（`video_in.v` L142–152）
```verilog
if(S_ddr_wr_valid && I_ddr_user_ready && S_ddr_wr_cnt == 'd239)  S_ddr_wr_valid <= 1'b0;
else if(S_fifo_rd_num >= 'd240 && (!I_video_out_rd_busy) && (!S_fifo_rst))  S_ddr_wr_valid <= 1'b1;
```
- 一次突发 **240 × 128 bit = 3,840 字节 = 正好一整行 1280 像素**
- `S_fifo_rd_num >= 'd240` 才启动突发 → FIFO 需先积累一行
- `assign S_fifo_rd_en = S_ddr_wr_valid & I_ddr_user_ready;`（L166）
- `assign O_video_in_wr_busy = S_ddr_wr_valid;`（L48）

**FIFO 深度约束**（源码注释原文，乱码还原）：
> 「fifo的深度是512，实际的深度是410，因此需要注意每次读出的长度避免>256，否则连续两次读写会引起fifo读空，丢失数据」

**读写指针**：`S_video_in_wp`（L102–117）/ `O_video_out_rp`（L120–137），`case` 实现四帧环形跳转 `'d0:'d2; 'd1:'d3; 'd2:'d0; 'd3:'d1`

**写读仲裁**（`design_top_wrapper.v` L622–629）
```verilog
assign S_ddr_user_wr_en   = S_vi_ddr_wr_en;
assign S_ddr_user_rd_en   = S_vo_ddr_rd_en;
assign S_ddr_user_addr    = S_vi_ddr_wr_en ? S_vi_ddr_wr_addr : S_vo_ddr_rd_en ? S_vo_ddr_rd_addr : 'd0;
assign S_ddr_user_wr_data = S_vi_ddr_wr_data;
```
> **写使能优先**：写和读同时有效时地址走写。`mc_to_user_interface` 做实际仲裁。

**lab2 vs lab3 的 `video_in.v` 差异**（`Compare-Object -SyncWindow 5`，**只差 4 行，且全是注释**）
- lab3 L48 中文注释：「以完整DDR写突发的占用标志仲裁，避免连续视频写入长期阻塞读通道。」
- lab2 对应处英文注释：「Busy covers the current write transaction only. Including the outgoing request here can keep video_out starved while camera frames are active.」
- **`assign O_video_in_wr_busy = S_ddr_wr_valid;` 两边完全相同**（可执行语句零差异）

**`video_out.v` 接口**（7000 B，**lab1/lab2/lab3 三份 SHA256 完全相同**）
```verilog
module video_out (
    input wire        I_rst_n,
    input wire        I_ddr_clk,
    output wire       O_video_out_rd_busy,
    input wire        I_video_in_wr_busy,
    input wire[1:0]   I_video_out_rp,
    output wire       O_ddr_user_rd_en,
    output reg[24:0]  O_ddr_user_addr,
    input wire        I_ddr_user_ready,
    input wire        I_ddr_user_rd_valid,
    input wire[127:0] I_ddr_user_rd_data,
    input wire        I_dsi_clk,
    input wire        I_video_vsync,
    input wire        I_video_rd_en,
    output reg[23:0]  O_vdieo_data        // ← 注意拼写：vdieo（原厂笔误，已沿用，勿改）
);
```

### 2.3 DDR 控制器接口

`ph1p35_324_ddr_wrapper`（4,502 B）对外两套接口：

**用户侧（MC 应用接口，128 bit 数据）**
```verilog
input  wire        I_sys_clk, I_sys_rst_n;
output wire        O_ddr_clk;               // 这个时钟反过来驱动 video_in/video_out
output wire        O_init_calib_complete;
input  wire[24:0]  I_mc_app_addr;
input  wire[2:0]   I_mc_app_cmd;
input  wire        I_mc_app_en;
input  wire[127:0] I_mc_app_wdf_data;
input  wire        I_mc_app_wdf_end;
input  wire[15:0]  I_mc_app_wdf_mask;
input  wire        I_mc_app_wdf_wren;
output wire[127:0] O_mc_app_rd_data;
output wire        O_mc_app_rd_data_end;
output wire        O_mc_app_rd_data_valid;
output wire        O_mc_app_rdy;
output wire        O_mc_app_wdf_rdy;
```
**DDR 物理侧**：`ddr_addr[12:0] ddr_ba[1:0] ddr_cke ddr_odt ddr_cs_n ddr_ras_n ddr_cas_n ddr_we_n ddr_ck_p/n ddr_dm[1:0] ddr_dq[15:0] ddr_dqs_p/n[1:0]`

内部结构：`alc_mc_top_all.enc.sv`（270 KB，**加密源码**）+ `ph1p_ddrphy_wrapper.v` + `src/rtl/{phy,mc,clk,init,misc,timing}` + IP `ddr2.xml`。

**依赖陷阱**：`ph1p_ddrphy_sync_rst_gen.v`、`ddrphy_cfg_rom.txt`、`ph1p_ddrphy_board_delay.vh`、`ddr2_1066/1333/533/667/800/400.vh` 等 **是器件/板级相关的自动生成文件** → 换板或改 DDR 频率时必须重新生成，不能手改。

### 2.4 OSD 通路（`hdmi_mixer.v`，41,314 B / 909 行）

**像素选择（L901–904）**
```verilog
if(S_osd_hit) O_hdmi_data <= S_osd_color;
else          O_hdmi_data <= S_video_data_2d;   // 来自 DDR
```
**两级打拍（L844–845）**：`S_video_data_1d <= I_video_rd_data; S_video_data_2d <= S_video_data_1d;`

**OSD 命中逻辑被 `if(S_video_de_2d)` 包住（L614–624）**
```verilog
if(S_x_2d >= LOGO_X && S_x_2d < LOGO_X+LOGO_W && S_y_2d >= LOGO_Y && S_y_2d < LOGO_Y+LOGO_H)
    → S_logo_addr = S_logo_y*LOGO_W + S_logo_x;
    → if(S_logo_pixel[24]) begin S_osd_hit=1; S_osd_color=S_logo_pixel[23:0]; end
```
> **推论（重要）**：Logo 能显示 ⟹ `S_video_de_2d` 有效 ⟹ 显示时序在跑 ⟹ 若画面全黑，问题只可能是 `I_video_rd_data`（DDR 读回）恒为 0。

**参数与常量**
| 项 | 值 | 行号 |
|---|---|---|
| `H_OFFSET / V_OFFSET / IMG_WIDTH / IMG_HEIGHT / DEBUG_MODE` | 128 / 60 / 1280 / 720 / 0（默认值；lab3 例化时前 4 项被覆盖为 0/0/1280/720） | L2–6 |
| `LOGO_X/Y/W/H` | 0 / 0 / 160 / 160 | L101–105 |
| `COLOR_LOGO_BLUE / COLOR_LOGO_RED` | `24'h1f315c` / `24'hec1c2d` | L107–108 |
| `COLOR_TEXT / COLOR_DYN_TEXT` | `24'h00e6ff` / `24'hfff200` | L109 / L118 |
| `DYN_OSD_X/Y/W/H` | 375 / 120 / 200 / 24 | L115–118 |
| `CN_Y_OFFSET` | 2 | — |
| 字符码 | `CHAR_AN=8'h80` `CHAR_LU=8'h81` `CHAR_C=8'h43` `CHAR_N=8'h4e` `CHAR_T=8'h54` `CHAR_0=8'h30` | — |
| 调试图案 | `DEBUG_MODE` 1 → L847；2 → L870；3 → L885 | — |
| 例化位置 | `design_top_wrapper.v` **L746** `.DEBUG_MODE ( 0 )` | — |

**调试状态字**（`design_top_wrapper.v` L403–408）
```verilog
assign S_hdmi_debug_status = {
    (|S_ddr_user_rd_data),   // [3] DDR 读回数据非零
    S_ddr_user_rd_valid,     // [2] DDR 读有效
    S_vo_ddr_rd_en,          // [1] video_out 在读
    S_vi_ddr_wr_en           // [0] video_in 在写
};
```
`DEBUG_MODE=3` 时四个竖条分别显示这 4 位。

### 2.5 依赖清单

**外部 IP（`.al` 的 `<IP_FILE>` 登记 8 项，缺一不可打开工程）**
| IP | 路径 | 用途 |
|---|---|---|
| `PLL` | `../user_source/ip_source/PLL/PLL.xml` | 4 路时钟 |
| `w128_d512_fifo` | `ip_source/w128_d512_fifo/w128_d512_fifo.xml` | 像素跨时钟 FIFO |
| `w155_d512_fifo` | `ip_source/w155_d512_fifo/w155_d512_fifo.xml` | 另一宽度 FIFO（当前用途待确认） |
| `blk_mem_gen_awb_delay_signal` | `ip_source/blk_mem_gen_awb_delay_signal/…xml` | AWB 行延迟 |
| `divider` | `ip_source/divider/divider.ipc` | 除法器（`divider_gate.v` **1,360,590 B**） |
| `ddr2` | `hdl_source/ph1p35_ddr/ddr2/ddr2.xml` | DDR 控制器 |
| `blk_mem_gen_zhenghe` | `isp/demosaic_4x_2_0/blk_mem_gen_zhenghe/…xml` | demosaic 行缓冲 |
| `blk_mem_gen_demosaic` | `isp/demosaic_4x_2_0/blk_mem_gen_demosaic/…xml` | demosaic 行缓冲 |

**源码形态分类（影响可搬移性）**
| 形态 | 文件 | 可否修改 |
|---|---|---|
| 明文 Verilog（**可改**） | 绝大多数 `.v` | ✅ |
| **加密/混淆源**（不可改、不可跨版本复用） | `hdmi_1_4b_transmitter_core_wrapper.enc.v`(328,975 B)、`alc_mc_top_all.enc.sv`(270,003 B)、`byte_aligner.enc.v`、`channel_aligner.enc.v`、`hs_detect.enc.v`、`byte_aligner_wrapper.enc.sv`、`channel_aligner_wrapper.enc.sv` | ❌ 只能整体搬运 |
| **IP 生成**（由 XML/IPC 重生成） | `PLL.v`、`soft_fifo_al_*.v`、`ram_*.v`、`divider_gate.v`、`ph1p_ddrmc_wrapper_*.v` | ⚠️ 改 IP 需用 IpTool，别手改 |
| 仿真用文件集 | `ddr2/sim/fileset/fileset_mis.f`、`config_data.mif` | 仅仿真 |

**未登记在 `.al`、但存在于源码目录的文件**（潜在清理对象 / 潜在遗漏）
`BLC.v`、`image_correction.v`、`video_cuttting.v`、`auto_white_balance.v`、`raw8_to_rgb888.v`、`raw10_unpacket.v`、`csi_unpacket.v`、`ps_wrapper.v`、`signal_delay.v`、`pll_hdmi.v`、`isp/awb/signal_delay.v`、`isp/awb/ram/*`、`isp/awb/divider/*`、`ip_source/w40_d512_fifo/*`、`ip_source/MCU/*`
> ⚠️ `ip_source/MCU/` 与 `w40_d512_fifo` 存在但未登记；**删除前必须逐个确认无引用**，否则会破坏工程。**待确认**。

**构建依赖**：TD 6.2.168116（`.al` L4）；器件 `PH1` / `PH1P35MDG324` / Speed `-3`；启动模式 `boot_mode = mspix4`；`mclk_freq = 33MHz`；bitgen `compress = on`。

### 2.6 工程目录结构（lab3）

```
lab_ex3_osd_SC500_720P/lab_ex3_osd/
├── td_project/
│   ├── camera_to_dsi_display.al            (22,859 B / 490 行) ← 工程文件
│   ├── camera_to_dsi_display.sdc           ← SDC（相对 td_project）
│   ├── camera_to_dsi_display_Runs/
│   │   ├── best_result/                    ← 最终 bit 输出
│   │   ├── syn_1/  phy_1/                  ← 两个 run
│   ├── al_ip/.IpToolIpDataBackupDir_ChipWatcher_0/
│   └── log/
└── user_source/
    ├── constraints_source/pin.adc          (1,415 B) ← 引脚约束
    │                     /timing.sdc       (0 B，空文件)
    ├── hdl_source/                         ← RTL（含 encrypted 与 IP 生成源码）
    │   ├── design_top_wrapper.v
    │   ├── isp/  mipi_dphy_rx/  ph1p35_ddr/  uics500_cfg/
    │   ├── isp/demosaic_4x_2_0/  isp/data128_96/  isp/data96_128/  isp/awb/
    │   ├── dsi_tx_packet/  uiisp_beta/  uial2axis/  vtc/  mipi_dphy_tx/
    │   └── ...
    └── ip_source/                          ← IP 定义（PLL/fifo/bram/divider/MCU）
```

**`.al` 关键结构（改工程时必须知道）**
| 行 | 内容 | 备注 |
|---|---|---|
| L2 | `<Project … Path="C:/Users/Cczzzzzq/Desktop/anlogic_example_SC520CS/…">` | ⚠️ **原厂绝对路径，复制工程后必须改** |
| L4 | `<TD_Version>6.2.168116</TD_Version>` | 与本机一致 |
| L7–11 | `<Family>PH1</Family> <Device>PH1P35MDG324</Device> <Speed>-3</Speed>` | — |
| L12– | `<Source_Files><Verilog>` 51 个 File 块 | 每块有 `UsedInSyn`/`UsedInP&R`/`BelongTo`/`CompileOrder` |
| L454–458 | `<TOP_MODULE><LABEL>design_top_wrapper</LABEL><MODULE>design_top_wrapper</MODULE>` | 改顶层时改这里 |
| L459+ | `<ADC_FILE>` 1 项、`<SDC_FILE>` 1 项、`<IP_FILE>` 8 项 | — |
| L472 / L478 | `<Run Name="syn_1" Type="Synthesis">` / `<Run Name="phy_1" Type="PhysicalDesign" SynRun="syn_1">` | 两个 run |
| 末尾 | `<Configurations>` → `mclk_freq=33MHz`、`boot_mode=mspix4` | 固化相关 |

**`.al` 中 `CompileOrder` 实际排序（关键片段）**
```
 1  design_top_wrapper.v
 3  mipi_dphy_rx_ph1p_mipiio_wrapper.sv      4  ph1p_mipiio_rx_wrapper.v
 5  video_in.v                                7  video_out.v
 8  mc_to_user_interface.v                   10–14 mipi_dphy_rx 加密源
15  signal_delay.v                           18  awb.v
20  ph1p35_324_ddr_wrapper.v                 21  csi_unpacket_2lane.v
22  isp_top.v          ← ★ 新算法模块必须排在此之后
23  raw10_unpacket_2lane.v                   24  uial2axis.v
25–30 demosaic 链                              31  data128_96.v
34  data96_128.v                              35–39 uics500_cfg 链
40  ae_set.v                                  41  hdmi_tx.v
42–44 hdmi 链路（含加密源）                     45  uivtc.v
46  hdmi_mixer.v                              47  I2S_receiver.v
48  audio_arc_calculate.v                     49  key_remove_shakes.v
50  anlogic_logo_rom.v                        51  osd_char_lib.v
```
> ⚠️ **新增 `my_algo.v` 时必须给它分配一个 `CompileOrder`（建议 >51，或紧跟 22），并加入 `<Verilog>` 段**。漏了这一步，综合时模块找不到。

**IP_FILE 的 CompileOrder 独立编号**：PLL=2、w128_d512_fifo=6、w155_d512_fifo=9、blk_mem_gen_awb_delay_signal=16、divider.ipc=17、ddr2.xml=19、blk_mem_gen_zhenghe=32、blk_mem_gen_demosaic=33

---

## 三、代码管理

### 3.1 现状：**完全没有版本控制**

实测结果：
```
无 .git: E:\FPGA
无 .git: E:\FPGA\work
无 .git: E:\FPGA\anlogic_example
```
- 唯一的"版本管理"是文件副本：三条例程在 `官方资料\7_lab_ex_2026_nosoft\` 与 `E:\FPGA\anlogic_example\` **各有一份（共 4 处副本）**
- bit 文件靠 `best_result/` 与 `phy_1/` 目录区分
- `git 2.55.0.windows.3` **已安装**，`C:\Program Files\Git\cmd\git.exe`，可直接用

### 3.2 建议的仓库划分与文件策略

**仓库根**：`E:\FPGA\work\`（不要对整个 `E:\FPGA\` 建库——里面有 11,720 个文件、约 680 MB 冗余例程副本）

**`.gitignore` 必含项**
```gitignore
# TD 生成物（体积大、可重建）
**/camera_to_dsi_display_Runs/
**/log/
**/al_ip/.IpToolIpDataBackupDir_*/
*.bit
*.bin
*.aje
*.svf
*.db
*.qor
*.area
*.timing
*.ts

# 但 bit 必须单独归档到 releases/（见下）
```
> ⚠️ **例外**：`best_result/*.bit` 是"能不能上板"的唯一凭据，**不能只靠重编**。做法：把每个里程碑 bit 复制到 `E:\FPGA\work\releases\<日期>_<版本>_<描述>\` 并提交（或至少登记 SHA256 + 大小 + 生成时间），见 §3.4。

**大文件警告**（进 git 前必须知道）
| 文件 | 大小 | 处理 |
|---|---|---|
| `isp/awb/divider/divider_gate.v` | 1,360,590 B | IP 生成，可重建 → 忽略或保留一份 |
| `ip_source/divider/divider_gate.v` | 1,362,623 B | 同上（**两个副本几乎同大小，注意去重**） |
| `hdmi_1_4b_transmitter_core_wrapper.enc.v` | 328,975 B | **加密源，不可重建，必须提交** |
| `anlogic_logo_rom.v` | 298,506 B | 大 ROM，必须提交 |
| `alc_mc_top_all.enc.sv` | 270,003 B | 加密源，必须提交 |
| `osd_char_lib.v` | 38,988 B | 必须提交 |

### 3.3 分支策略（建议）

```
main          ← 可演示的稳定版本，每个里程碑打 tag
  ├─ baseline       ← 原厂 lab3 原封不动，仅改 .al 绝对路径。作为 diff 基线
  ├─ feature/algo    ← my_algo 接入 + 算法迭代
  ├─ feature/osd     ← OSD 文字/状态显示改造
  ├─ feature/key     ← 按键多算法切换
  └─ feature/integrate ← 最终单一镜像整合
```
**基线分支必须先建**：`baseline` 分支是之后所有 diff 的参照物，也用来证明"我们的实现与参考例程不同源"。

### 3.4 提交规范（建议）

**提交信息**：`<类型>: <一句话>` + 正文写"改了什么、为什么、实测结果"
```
feat(isp): 在 awb 与 data96_128 之间插入 my_algo 直通模式
- my_algo.v OFF=1，端口与 edge_detect_96 一致
- .al 新增 CompileOrder 52
- 实测：上板画面与 lab3 原版一致，slice 14852 → 14890
```

**每次成功上板必须登记**（现有台账 `E:\FPGA\work_资源与时序台账.csv` 已含所需列）
```
日期, 版本/commit, 工程, slice(%), lut6, reg, eram, dsp, pll, SetupWNS(ns), SetupTNS(ns), HoldWNS(ns), 来源报告, 备注
```
**归档 bit 的三要素**：SHA256 + 大小 + 生成时间。当前已知样本：
```
lab3 原厂: camera_to_dsi_display.bit  2026-09-10 16:44:43  1,789,539 B
           camera_to_dsi_display_compress.bit  2026-09-10 16:44:42  1,351,409 B
```
> ⚠️ 重编会**覆盖同名文件**。**动手改 DEBUG_MODE / 接入算法之前，必须先备份这份原厂 bit**。

### 3.5 变量隔离原则

`.al` 的 `Path` 字段与 `Best_result` 绝对路径都不应进版本库的"机器相关"部分。做法：
- 建 `baseline` 分支后，**第一次提交只改 `.al` L2 的 `Path` 与清理 Runs**，单独成一个 commit，方便以后 cherry-pick。
- 团队多人协作时，`.al` 是**冲突高发文件**（单文件 XML，行级 diff 噪音大）→ 约定「同一时间只有一人改 `.al`」，或用 `.al` 的生成脚本（TD 支持 `save_project_as`）。

---

## 四、当前差距

### 4.1 代码/功能差距

| # | 差距 | 证据 | 影响 |
|---|---|---|---|
| **G1** | **lab3 上板只有 Logo，无实时画面** | 用户实测；`hdmi_mixer` L614/L901 的 OSD 被 `if(S_video_de_2d)` 包住 ⟹ 时序在跑，只有 DDR 读回像素可能为 0 | **阻塞一切**：lab3 是 OSD 底板 |
| **G2** | **lab3 的 `isp_top.v` 里没有任何图像处理算法** | `isp_top.v` L95–106 直接 `awb_O_tdata → data_96bit_to_128bit` | 基础要求「至少一种图像处理算法」在 lab3 底板上**不满足** |
| **G3** | 自研算法模块从未编译、从未上板 | `my_algo.v` 存在，`.al` 里**无登记** | 未知数：语法、时序、资源全未验证 |
| **G4** | 无单一整合工程 | 三个例程各自独立（lab1 无算法无 OSD / lab2 有算法无 OSD / lab3 有 OSD 无算法） | **最终交付必须是一个镜像**，目前没有 |
| **G5** | 无上电自启动 | 只有 `best_result/*.bit`，未做 QSPI 固化 | 交付形态不满足 |
| **G6** | 时序余量极薄 | lab3 Setup WNS = **+0.103 ns**；最紧路径在 `HDMI_SERIAL_CLK`（2.667 ns / 375 MHz） | 任何新增逻辑都可能转负 |
| **G7** | MIPI 错误检测未启用 | `design_top_wrapper.v` L606 `.I_mipi_rx_error(1'b0)`；`mipi_rx_error_detect.v` 未接入 | 摄像头异常时无诊断信号 |
| **G8** | 死代码/悬空信号 | `S_aux_50m_clk`、`S_10m_clk`（L44–45）无连接；`isp_top` 的 `.I_tdest()`/`.I_tready()` 悬空；十余个 `.v` 未登记 | 维护噪音，误改风险 |
| **G9** | 代码中大量 GBK 乱码注释 | `design_top_wrapper.v` L448–456 等（`绯荤粺鏃堕挓杈撳叆` = 系统时钟输入） | 因为文件是 GBK 但被当 UTF-8 读；**改文件时必须用能正确处理 GBK 的编辑器**，否则注释会继续损坏 |
| **G10** | `video_out.v` 端口拼写错误沿用 | `O_vdieo_data`（应为 video） | 若"修正"会牵动所有例化，**建议保留并在注释中说明** |

### 4.2 代码管理差距

| # | 差距 | 现状 |
|---|---|---|
| M1 | 无 git 仓库 | 0 个 `.git` |
| M2 | 无提交历史、无法回溯"哪一版能跑" | 只有文件副本 |
| M3 | bit 文件无归档、重编即覆盖 | 原厂 lab3 bit 目前**无备份** |
| M4 | 无基线分支，无法证明"与参考例程不同源" | — |
| M5 | 工程含原厂绝对路径 | `.al` L2 = `C:/Users/Cczzzzzq/Desktop/...` |
| M6 | 无编译/仿真自动化 | 只能手工点 TD GUI；TD 提供 Tcl 脚本能力但未使用 |
| M7 | 无单元级验证手段 | 本机无 `iverilog`/`verilator`/`vvp`/`gcc`；有 `winget`（v1.29.380）可装 |

---

## 五、下一步任务

### P0 —— 清障（在写任何新代码之前）

**T1 备份原厂 lab3 bit**
```powershell
Copy-Item 'E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\td_project\camera_to_dsi_display_Runs\best_result\camera_to_dsi_display.bit' `
          'E:\FPGA\work\releases\lab3_原厂_2026-09-10.bit'
```
并记录 SHA256 与大小（1,789,539 B）。

**T2 建 baseline 工程树 + git 仓库**
```powershell
# 1) 整棵复制（含 user_source/ip_source，缺 IP 工程打不开）
robocopy 'E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd' 'E:\FPGA\work\baseline\lab3' /E /XD camera_to_dsi_display_Runs log al_ip
# 2) 建库
cd E:\FPGA\work; git init; git add -A; git commit -m "chore: 导入官方 lab3 作为 baseline"
# 3) 单独一个 commit 只改 .al 的机器相关部分
#    .al L2: Path → E:/FPGA/work/baseline/lab3/td_project
git commit -am "chore(al): 修正工程路径为本地路径"
```
`.gitignore` 见 §3.2。

**T3 用 DEBUG_MODE 定位 G1**
- 改 `work\baseline\lab3\user_source\hdl_source\design_top_wrapper.v` **L746** `.DEBUG_MODE(1)` → 重编 → 烧 SRAM
- 出来彩条 ⟹ HDMI 通路完好，问题锁定在写 DDR 侧
- 再改 `.DEBUG_MODE(3)` → 读四个竖条判 `S_hdmi_debug_status`：
  - 四位全亮 ⟹ 读写都在跑，问题在混合前最后一段
  - 只有 [0] 亮 ⟹ **能写不能读** → 查 `O_video_in_wr_busy` / `I_video_out_rd_busy` / `mc_to_user_interface` 仲裁
  - 四位全暗 ⟹ 连写都没发生 → 查摄像头 I2C 与 MIPI 出流（`S_cam_cfg_done`、`S_hs_rx_valid`）
- 实验完**改回 0** 并提交记录

### P1 —— 算法接入

**T4 登记 + 接入 `my_algo.v`**
1. 复制 `E:\FPGA\work\rtl\my_algo.v` → `work\baseline\lab3\user_source\hdl_source\isp\my_algo\my_algo.v`
2. 编辑 `isp_user_source\hdl_source\isp\isp_top.v`，在 `awb` 之后、`data_96bit_to_128bit` 之前插入：
   - 5 根 wire 声明
   - 例化块（照 lab2 `isp_top.v` L84–132 的写法）
   - 把 `data_96bit_to_128bit` 的 `.I_96b_data(awb_O_tdata)` 改为 `.I_96b_data(my_O_tdata)`，`.I_96b_valid` / `.I_96b_frame_start` 同步改
3. `.al` 的 `<Verilog>` 段新增 `my_algo.v`，`CompileOrder` 给 **52**（>51）
4. **先用 `.OFF(1)` 编译** → 预期画面与 lab3 原版一致（验证接口）
5. 再 `.OFF(0)` → 检查伪彩效果

**T5 每次编译后核对三件事**
- `phy_1\camera_to_dsi_display_phy.area` 的 slice 增长（预期 +100~300）
- `route.qor` 的 Setup WNS（**必须保持为正**；lab3 基线只 +0.103 ns）
- 生成的 bit 是否真被烧进 SRAM

### P2 —— 工程化

**T6 建 Tcl 脚本化流程**（避免手工点 GUI，也便于回归）
TD 提供 `E:\TD\bin\td_commands_prompt.exe`，可喂脚本。核心命令：
```tcl
open_project E:/FPGA/work/baseline/lab3/td_project/camera_to_dsi_display.al -single_run
launch_runs phy_1 -step all -jobs 6
save_best_bits
report_area -file area.rpt -io_info
report_timing_summary -file timing.rpt
```
参考官方流程脚本 `E:\TD\doc\scripts\DefaultFlow.tcl`（249 行，步骤 `read_design → opt_rtl → opt_gate → opt_place → opt_route → bitgen`）。

**T7 装语法/仿真工具**（当前完全没有）
```powershell
winget install --id WilsonSnyder.IcarusVerilog   # 待确认包 ID
```
用途：`iverilog -t null` 做零成本语法检查；对 `my_algo.v` 做小规模仿真（96bit 输入 → 输出像素比对）。

**T8 清理死代码**（**必须逐个确认无引用后再删**）
候选：`isp/awb/divider/` 与 `ip_source/divider/` 的重复 `divider_gate.v`、`ip_source/w40_d512_fifo/`、`ip_source/MCU/`、`hdl_source/BLC.v` 等十余个未登记文件。**待确认**。

### P3 —— 整合与固化

**T9 单一镜像整合**（硬约束）
在 `baseline\lab3` 上依次接入：算法（T4）→ 按键切换（复用 `key_remove_shakes`）→ OSD 状态显示（改 `hdmi_mixer.v` 的动态 OSD 段 L626–628）。
**注意**：必须在**同一个工程、同一个 bit** 里同时可用。

**T10 QSPI 固化与上电自启**
`boot_mode = mspix4`，板载 QSPI Flash 128 MB。用 BitWriter 的 `Create Flash File` 生成固化文件并烧录，**断电重启验证无需 PC**。

**T11 稳定性与回归**
- 连续运行 ≥2 小时，记录有无花屏/缓存溢出
- 强光↔暗场切换时观察 AE 通路（`ae_set` + `uicscfgcs500_720P`）
- 每次改动跑一遍 T6 的 Tcl 脚本，把结果写入台账

---

## 六、待确认

### 6.1 代码事实类

| # | 待确认项 | 怎么确认 |
|---|---|---|
| Q1 | `w155_d512_fifo` 与 `w40_d512_fifo` 当前**是否还在被引用**？ | 在工程里搜 `w155_d512_fifo` / `w40_d512_fifo` 的模块名例化 |
| Q2 | `ip_source/MCU/`（`MCU.v` `MCU_f9f874759a41.v` `Design.xml` 31 KB `MCU.xml` 46 KB）是谁在用？ | 同上；若是芯片内置 MCU 配置，可能关系固化模式 |
| Q3 | 十余个未登记 `.v`（`BLC.v` `image_correction.v` `video_cuttting.v` `auto_white_balance.v` `raw8_to_rgb888.v` …）能否删？ | 逐个搜模块名引用 |
| Q4 | `isp/awb/divider/divider_gate.v` 与 `ip_source/divider/divider_gate.v` 是否为同一 IP 的两份副本？ | 比对 SHA256 |
| Q5 | `hdl_source/isp/` 与 `hdl_source/uiisp_beta/` 下 `csi_unpacket_2lane.v`、`raw10_unpacket_2lane.v` 两份同名文件哪份在用？ | 看 `.al`：登记的是 `isp/` 下的（CompileOrder 21/23）→ **`uiisp_beta/` 那份疑似废弃**，但需确认无交叉引用 |
| Q6 | `S_aux_50m_clk` / `S_10m_clk` 是否曾经接过什么？ | 查 lab1/lab2 的同名文件比对 |
| Q7 | `data96_128.v` 与 `data_96bit_to_128bit.v` 是否重复实现？ | 比对端口与逻辑；`.al` 登记的是 `isp/data96_128/data96_128.v`（CompileOrder 34），**`hdl_source/data_96bit_to_128bit.v` 未登记** |
| Q8 | 源代码文件的**字符编码**到底是什么？ | PowerShell `Get-Content -Encoding` 逐一验证；GBK 乱码（§4.1 G9）必须确认后才能安全编辑 |

### 6.2 工具/环境类

| # | 待确认项 |
|---|---|
| Q9 | TD 是否支持完全无人值守的 `open_project` + `launch_runs` 批处理？（脚本能力已确认存在，但未实测跑通） |
| Q10 | 本机是否有可用的 Verilog 仿真器？（TD 自带目录无 `vlog/vsim/iverilog`；`C:\intelFPGA_lite\20.1\modelsim_ase\` 存在但未验证可用性） |
| Q11 | DDR2 参数的板级校准文件（`ph1p_ddrphy_board_delay.vh`、`ddrphy_cfg_rom.txt`）是否与本板一一对应？（官方 Q&A 明确「网盘没提供 DDR2 手册，需参考例程使用」） |

### 6.3 需要用户提供

| # | 事项 |
|---|---|
| U1 | **DEBUG_MODE 实验的屏摄**（T3 结果）——决定 G1 往哪个方向修 |
| U2 | 队伍是否已建 git 仓库（若已建，告诉我 remote 与分支现状，我按现有约定走） |
| U3 | 是否允许在 `E:\FPGA\work\` 下 `git init`（会写入 `.git` 目录） |
| U4 | 是否有队友并行改代码（决定 `.al` 与 `isp_top.v` 的写权限分配） |
| U5 | `my_algo.v` 的算法方向是否确定（伪彩/边缘/二值化），还是要先看效果再定 |

---

*所有行号与数值均来自 `E:\FPGA\anlogic_example\lab_ex3_osd_SC500_720P\lab_ex3_osd\`（lab3）及 lab1/lab2 源码的实测读取；"待确认"项为资料未覆盖、不做推断。*
