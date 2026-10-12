# PH1P35 MIPI→ISP→DDR→HDMI 代码事实报告

**读取限制**：`.extract\src\*.txt` 全部 read 成功。原始 `bilinear_interpolation.v` 是 GBK，read 报 `invalid UTF-8` → 按要求跳过全文，改用 grep 读其 ASCII 代码行（行号可信、注释不可读）；`awb.v` 是 UTF-8，与 `awb_v.txt` 逐行一致。另读 `design_top_wrapper_v.txt`、`zhenghe.v`、`signal_delay_v.txt` 与 3 个 ERAM IP 的 .v 以确认连接和存储。

## 1 链路顺序与数据格式（代码确认）

| 级 | 模块(行号) | 输入→输出 | 打包含义 | 握手 |
|---|---|---|---|---|
|1|`csi_unpacket_2lane`(csi:36-48)|`I_hs_data[15:0]`→`O_csi_data[31:0]`|2lane/1B：每个有效沿 `{O_csi_data[15:0],I_hs_data}`(csi:135)|无 tready，只有 valid/hs/frame_start/end|
|2|`raw10_unpacket_2lane`(raw10:33-48)|32bit→**40bit**|4×RAW10；P0..P15 映射见 raw10:91-116（5 拍一组）|无 tready，带 frame_start/end|
|3|`uial2axis`(design_top:610-626)|40bit→AXIS|tdata/tvalid/tlast/tuser|—|
|4|`demosaic`(isp_top:49-70)|40bit in|内含 3x3 缓存 + bilinear|`tready` 直通|
|5|`mipi_to_raw_converter`(mipi_to_raw:50)|40bit→**32bit=4×RAW8**|只取每像素高 8 位、丢低 2 位（截断）|`I_tready` 恒 1(raw_matrix:149)|
|6|`bilinear_interpolation`(bilinear:882-889)|3×96bit→**128bit=4×{8'b0,R,G,B}**|每像素 32bit 带 8bit 零填充|tlast/tuser 打 5 拍|
|7|`data128_96`(data128_96:16)|128→**96bit=4×RGB888**|`{[23:0],[55:32],[87:64],[119:96]}`|组合逻辑|
|8|`awb`(awb:479-482)|96bit→96bit|4 像素 RGB888|`I_tready=O_tready`(awb:485)|
|9|`data_96bit_to_128bit`(data96_128:51-61)|96→128bit|见 §7 可疑点 2|无 tlast/tready|
|10|`video_in`(design_top:672-691)→DDR→`video_out`→HDMI|128bit|跨到 `S_ddr_clk`|—|

**时钟域**：整条 ISP 只有 `axi4s_video_aclk`，`design_top:656` 接 `S_csi_rx_clk`（MIPI RX 域），到 DDR 才由 video_in 跨时钟。**全链路无 tready 反压**（isp_top:36、awb:485），awb 用固定 50 拍延迟（awb:225-239），不能停顿。

## 2 关键 parameter 默认值

- `demosaic`：IMG_HEIGHT=720、IMG_WIDTH=1280、data_complete_delay=50、BAYER_MODE="BGGR"（isp_top:49-54；模块默认 1080/1920/"BGGR"，demosaic:21-24）
- `raw_matrix_3x3_buffer`：N=3、DATA_WIDTH=32、`IMG_WIDTH_4x=IMG_WIDTH>>2`（raw_matrix:66-70）
- `line_buffer_demosaic`：IMG_HEIGHT/IMG_WIDTH 默认 1080/1920（line_buffer:21-22）
- `BLC`：Black_level_offset_r0..r3 默认均 15（BLC:12-15）——**isp_top 未实例化 BLC**
- `awb`：IMG_HEIGHT/IMG_WIDTH；`signal_delay` DATA_WIDTH=96、DELAY_CYCLE=50（awb:225-229）
- `divider`：denom 32bit / numer 48bit / quotient 48bit，UNSIGNED，pipline，level_nu=50（divider.ipc:4-9）

## 3 行缓存 / ERAM

- 3×3 窗口 = **2 个** `line_buffer_demosaic`（generate i=1..2，raw_matrix:176-192），每个 **33bit（32 数据+1 tuser，raw_matrix:117/line_buffer:28）×2048 深**，实现为 `PH1P_LOGIC_ERAM`（blk_mem_gen_demosaic.v:26-31 → ram_c36…v:53）。
- 地址上限是 `(IMG_WIDTH>>2)-1`（line_buffer:43,62）：720p 只用 **320/2048** 字，深度浪费约 6 倍，且 2 个实例。
- 第 3 个 ERAM：zhenghe 内 `blk_mem_gen_zhenghe`，**32bit×2048**（同样只用 320 字，zhenghe.v:167-175）。
- awb 的 signal_delay：`blk_mem_gen_awb_delay_signal` 96bit×2048（blk_mem_gen_awb_delay_signal.v:20-25），只用 ~320 字。
→ 720p 下 ISP 共 **4 个 2048 深 ERAM**。代码里没有分布式 RAM/LUT 实现（原问"用 ERAM 替 LUT"在此工程已成立）。

## 4 AWB 实现

- 把 96bit 拆成 4 个像素（awb:104-118），每帧由 `I_tuser` 清零累加器（awb:122），对 R/G/B 累加到 `sum_r/g/b[0:3]`（awb:141-155）——**4 组独立累加器 = 按 4 像素块相位分别统计**，统计窗口就是整帧（不是局部窗口）。
- **用了除法器**：每个位置 2 个（G/R、G/B），共 **8 个 48÷32 流水除法器**（awb:199-222）；`numerator={sum_g,16'd0}`（awb:207），商是 Q16.16 的 G/R、G/B。
- 增益位宽 **20bit**（awb:245-255）：复位/帧起始置 `20'h10000`(=1.0)（awb:260），高位有 1 时钉 `20'hfffff`(≈16)（awb:264-271）。
- **不是整帧闭环**：`start=I_tvalid_r1` 每个有效周期都重启除法器，`done` 后取"当时的运行均值"配到延迟 50 拍的像素（awb:202-239,263,402-417）→ 流水线式逐像素自适应，帧头若干拍的统计不可靠。

## 5 定点化细节

- bilinear 反马赛克：邻居和（10bit，bilinear:171-261）除以 1/2/4 靠 `>>1/>>2`（bilinear:301-315），**截断不舍入**；结果 `mean[8]?255:mean[7:0]` 饱和（bilinear:855-869）；输出 {8'b0,R,G,B}（bilinear:882-885）。
- RAW10→RAW8 取高 8 位（mipi_to_raw:50），不四舍五入。
- BLC：条件减，负数裁 0（BLC:63-68），10bit 域（但未进链路，见 §7.3）。
- AWB：`in_r(20bit,Q16.16) * R(8bit)` → **28bit**，取 `[23:16]` 即 `(gain*R)>>16`（awb:403,442）；`R_new[27:24]!=0` 时饱和 255（awb:442）。G 通道**不加增益**（awb:404 `G_new=rgb888_g`，awb:443 直通）。

## 6 对参赛者可复用的结论

- 可直接搬：`csi_unpacket_2lane`+`raw10_unpacket_2lane`（40bit=4×RAW10 的 P0..P15 位映射表，raw10:88-116）；`mipi_to_raw_converter`；`line_buffer_demosaic`+`raw_matrix_3x3_buffer` 的首/末像素边界复制（raw_matrix:223-267）；bilinear 的四套 Bayer generate（bilinear:160/328/499/672）；`data128_96`。
- 明显可优化：① 行缓存地址按 `IMG_WIDTH_4x` 取位宽（720p 只需 9bit/512 深），可省掉大量 ERAM；② 8 个 48÷32 除法器对 PH1P35 代价高，可 1 组分时复用或改倒数查表（增益有效位数 ≤16bit）；③ 统计窗口改抽行、去掉 4 相位独立累加；④ 拍平 96↔128 来回转换（bilinear 已出 128bit，AWB 可直接吃 128bit，省两级）。

## 7 可疑点 / 坑

1. **awb 完全没用 `I_tlast`**（仅 awb:28 声明），`O_tlast` 由 valid 下降沿造出：`(valid_d1==0)&&(valid_d2==1)`（awb:474）；而 isp_top 的 `O_tlast` 取 awb、`O_tdata/O_tvalid/O_tuser` 取它后面一级 `data_96bit_to_128bit`（isp_top:37-40）→ **tlast 与 tdata/tvalid 不在同一流水级**，下游按 tlast 分行会错位。
2. `data_96bit_to_128bit`：valid 每 4 拍只出 3 拍（data96_128:42-68，S_cnt=0 时丢一拍并清 0），且第 2、3 拍都用 `S_96b_data_1d`（上一拍整字）而非滑窗（data96_128:56,61）。按 AWB 的口径（96bit=4×RGB888）本应做 24→32bit 补零（被注释掉的 data96_128，data96_128_v.txt:96-98）；按 96bit=3×32bit 口径该拼接又存在重复字节。**该级口径自相矛盾，必须仿真确认。**
3. `I_camera_black_level` 只在被注释代码块里用（raw10:141-233），design_top:593-606 也没接该端口 → 黑电平校正实际不存在；`BLC` 模块全工程未实例化。
4. `csi_unpacket` 取长度用 `{I_hs_data[15:8],S_hs_data_1d[7:0]}>>1`（csi:95，跨拍拼字节），且比较 `S_data_en_cnt==S_data_length-1`（csi:111），±1 边界需仿真确认。
5. 右边界处理不对称：末像素分支只插入 `{...buffer[7:0],{24{1'b0}}}`（raw_matrix:229-231,244-246,259-261），同组另 3 字节为 0；首像素分支却补满 32bit（raw_matrix:225）→ 右边 4 个像素可疑。
6. `data_96bit_to_128bit` 不使用 `I_rst_n`（data96_128:23-36 无复位），`S_cnt` 依赖上电初值。
