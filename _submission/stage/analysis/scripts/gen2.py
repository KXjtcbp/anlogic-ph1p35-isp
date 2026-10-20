# -*- coding: utf-8 -*-
"""生成 annotate.py 用的 spec（batch2：lane_lvds_10_1.v + mipi_rx_error_detect.v）"""
import json

HDR = [
    "//=============================================================================",
    "// 文件      : {path}",
    "// 模块      : {mod}",
    "// 功能      : {func}",
    "// 数据通路  : {data}",
    "// 时钟/复位 : {clk}",
    "// 依赖      : {dep}",
    "// 综合/实现 : {syn}",
    "//-----------------------------------------------------------------------------",
    "// 修改记录  :",
    "{chg}",
    "//-----------------------------------------------------------------------------",
    "// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\\FPGA\\_analysis\\reports\\rename_report.txt",
    "//=============================================================================",
]
STD_CHG = "//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改"


def hdr(path, mod, func, data, clk, dep, syn, chg=STD_CHG):
    return [h.format(path=path, mod=mod, func=func, data=data, clk=clk, dep=dep, syn=syn, chg=chg)
            for h in HDR]


files = []

# ------------------------------------------------------------------ 3. lane_lvds_10_1.v
files.append({
    "path": "lane_lvds_10_1.v",
    "header": hdr(
        path="lane_lvds_10_1.v",
        mod="lane_lvds_10_1",
        func="TMDS 串行发送的最小单元（1 条 lane）：把 10 bit 并行 TMDS 字符按像素时钟节拍装入移位寄存器，在串行时钟域每拍左移 2 bit，最后借助器件 ODDR 原语以双沿方式输出，得到串行 TMDS 码流。",
        data="I_data_in[9:0]（来自 hdmi_phy_wrapper 位序重排后的 TMDS 字符）→ S_shift_data 移位 → S_oddr_data[1:0] → ODDR 的 d1/d0 → O_serial_out。串行时钟是像素时钟的 5 倍（10 bit = 5 个串行周期 × 双沿 2 bit）。",
        clk="I_pixel_clk（装载节拍，来自 HDMI_PIXEL_CLK）；I_serial_clk（移位时钟，来自 HDMI_SERIAL_CLK，本工程 375 MHz）；I_rst 高电平异步复位，分别复位像素域与串行域逻辑。",
        dep="依赖 TD 原语 EF2_LOGIC_ODDR / EF3_ / EF4_ / SF1_ / EG_ / PH1_ / PH1P_ / DR1_LOGIC_ODDR，由 parameter DEVICE 选择（本工程 hdmi_phy_wrapper 传 DEVICE=\"PH1P\"）。被 hdmi_phy_wrapper.v:71/83/95/107 例化 4 次（ch0/ch1/ch2/clk）。",
        syn="含器件专属 ODDR 原语，只能由 TD 综合；generate 里没有 else 分支，DEVICE 取值不在列表中时不会产生任何输出。已收录于 td_project/camera_to_dsi_display.al。",
    ),
    "inserts": [
        {"anchor": "module lane_lvds_10_1 #(", "lines": [
            "",
            "//---- 模块说明 ----",
            "// 10 bit TMDS 字符无法由普通寄存器直接串出，这里采用像素域装载 + 5 倍串行域移位 + ODDR 双沿输出的结构：",
            "// 每个像素周期装载一次，随后 5 个串行时钟周期正好把 10 bit 全部移出。",
        ]},
        {"anchor": "    reg      S_odd_even;", "lines": [
            "//---- 内部信号声明 ----",
        ]},
        {"anchor": "    always @(posedge I_pixel_clk or posedge I_rst) begin", "lines": [
            "//---- 像素域节拍标志 S_odd_even ----",
            "// 在像素时钟域每个周期翻转一次，用于把每像素装载一次这个事件搬移到串行时钟域。",
        ]},
        {"anchor": "        S_load_en    <= S_odd_even_1d ^ S_odd_even_2d;", "lines": [
            "//---- 装载使能产生 ----",
            "// 两级同步后的异或即边沿检测：S_odd_even 每像素周期翻转一次，",
            "// 所以 S_load_en 在串行域里每个像素周期出现一次高电平，作为装载脉冲。",
        ]},
        {"anchor": "    always @(posedge I_serial_clk or posedge I_rst) begin", "lines": [
            "//---- 并串移位寄存器 S_shift_data ----",
            "// S_load_en_2d 有效时把 10 bit 并行数据整体装入；",
            "// 其余串行周期每次左移 2 bit，为 ODDR 的双沿输出每次提供 2 bit。",
            "// 装载 1 次 + 移位 5 次正好把 10 bit 全部送出。",
        ]},
        {"anchor": "        S_oddr_data <= S_shift_data[9:8];", "lines": [
            "//---- ODDR 数据准备 ----",
            "// 取最高 2 bit 交给 ODDR：d1 在时钟上升沿输出、d0 在下降沿输出（见下方端口连接）。",
        ]},
        {"anchor": "    generate", "lines": [
            "//---- 器件相关 ODDR 原语选择 ----",
            "// 同一份逻辑要在多种安路器件上综合，用 generate + parameter 字符串比较挑选对应原语；",
            "// 各分支里实例名都叫 U_EG4_ODDR（历史沿用），只有被选中的分支才会被实例化。",
            "// 本工程 hdmi_phy_wrapper 传 DEVICE=\"PH1P\"，实际生效的是 PH1P_LOGIC_ODDR 那一支。",
        ]},
        {"anchor": "    endgenerate", "lines": [
            "//---- 器件原语选择结束 ----",
            "// 注意：generate 里没有 else 分支，若 DEVICE 不属于上面 8 种取值，O_serial_out 将无驱动。",
        ]},
    ],
    # `always @(posedge I_serial_clk) begin`（无复位版）出现 3 次：同步、装载使能、ODDR 数据准备
    "insert_seqs": [
        [
            {"anchor": "    always @(posedge I_serial_clk) begin", "lines": [
                "//---- 跨时钟域同步（像素域 -> 串行域） ----",
            ]},
            {"anchor": "    always @(posedge I_serial_clk) begin", "lines": []},
            {"anchor": "    always @(posedge I_serial_clk) begin", "lines": []},
        ],
    ],
})

# ------------------------------------------------------------------ 4. mipi_rx_error_detect.v
files.append({
    "path": "mipi_rx_error_detect.v",
    "header": hdr(
        path="mipi_rx_error_detect.v",
        mod="mipi_rx_error_detect",
        func="MIPI CSI-2 接收侧的帧结构错误检测：统计一帧内的行数（以及辅助用的列数），若帧结束时行数与预期值 832 不符，则置起 O_mipi_rx_error 供上层丢弃或回退该帧数据；帧内一旦重新收到有效数据即清除错误标志。",
        data="输入 I_frame_start / I_frame_end / I_data_valid 为摄像头接收通路的帧头、帧尾、数据有效指示；内部用 S_col_cnt（行内数据个数）与 S_line_cnt（帧内行数）计数，比较结果写入 O_mipi_rx_error。",
        clk="I_clk（摄像头接收时钟域，S_csi_rx_clk 一类）；I_rst_n 低电平异步复位。",
        dep="例化了 ChipWatcher 调试核 cwc1（probe0..probe9 观测帧信号与计数器），属历史草稿：本工程源码树中未找到 cwc1 的模块定义，也未发现有任何模块例化本模块；video_in.v 的 I_mipi_rx_error 在 design_top_wrapper.v:637 被常量 1'b0 取代，因此本模块疑似未接入。",
        syn="引用了不存在的 cwc1 模块定义，无法直接综合；工程文件 td_project/camera_to_dsi_display.al 未收录本文件。",
    ),
    "inserts": [
        {"anchor": "    reg[11:0] S_line_cnt;", "lines": [
            "//---- 内部信号声明 ----",
            "// S_line_cnt：帧内已统计的行数；S_col_cnt：当前行内有效数据个数（仅作观测）。",
        ]},
        {"anchor": "        S_data_valid_1d <= I_data_valid;", "lines": [
            "//---- I_data_valid 打拍，用于产生行结束标志 ----",
        ]},
        {"anchor": "    assign S_line_end = ~I_data_valid & S_data_valid_1d;", "lines": [
            "//---- 行结束标志 ----",
            "// 上一拍有效、这一拍无效，即一行的数据刚刚结束（下降沿）。",
        ]},
        {"anchor": "    always @(posedge I_clk or negedge I_rst_n) begin", "lines": [
            "//---- 错误判定 ----",
            "// 判据：帧尾到来时行数必须等于 832。",
            "// 832 是本工程 1280x720 RAW10 数据流下期望的帧内行数（按实际接收通路统计值写死），",
            "// 帧结构或分辨率改变时需要同步修改该常数，否则会误报。",
            "// 一旦检出错误，标志保持到帧内重新出现有效数据（I_data_valid）才清除。",
        ]},
        {"anchor": "   cwc1 cwc_inst", "lines": [
            "//---- ChipWatcher 观测实例（历史草稿） ----",
            "// cwc1 是 TD 在线调试工具 ChipWatcher 生成的观测核，把上列信号引出到探针；",
            "// 本工程未提供 cwc1 的模块定义，本模块也未在工程中被例化，故此段按原样保留、不参与功能。",
            "// 注意：此处探针列表中并没有任何 lane 错误相关信号。",
        ]},
    ],
    "insert_seqs": [
        [
            {"anchor": "if(I_data_valid)", "lines": [
                "//---- 行内计数器 S_col_cnt ----",
                "// 数据有效期间逐拍累加，行间无效时清零，因此它的值就是本行的数据个数。",
            ]},
            {"anchor": "if(I_frame_start)", "lines": [
                "//---- 帧内行计数器 S_line_cnt ----",
                "// 帧头清零，之后每检测到一次行结束加一，帧尾时的值即本帧总行数。",
            ]},
            {"anchor": "always@(posedge I_clk)begin", "lines": [
                "//---- 辅助调试计数 h_cnt ----",
                "// h_cnt 统计帧尾之前累计的数据有效拍数，与 c_cnt（帧尾次数）都未参与错误判定，仅用于观测。",
            ]},
        ],
    ],
})

with open(r"E:\FPGA\_analysis\docs\spec2.json", "w", encoding="utf-8") as f:
    json.dump({"files": files}, f, ensure_ascii=False, indent=1)
print("ok")
