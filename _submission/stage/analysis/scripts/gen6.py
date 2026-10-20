# -*- coding: utf-8 -*-
"""gen6.py —— 生成 batch6 的 spec（vtc/uivtc.v, hdmi_tx.v, hdmi_phy_wrapper.v, pll_hdmi.v）"""
import json
from gen1 import STD_CHG

RENAME = "// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\\FPGA\\_analysis\\reports\\rename_report.txt"

HDR_PHY_CHG = ("// 2026-10-09  文件名拼写修正 hdmi_phy_warpper.v -> hdmi_phy_wrapper.v（模块名本就正确），"
               "同步更新 camera_to_dsi_display.al 中的路径")


def head(path, mod, fields):
    """fields 必须是长度 6 的列表：功能/数据通路/时钟复位/依赖/综合实现/修改记录。
    每项可以是字符串或字符串列表（多行会展开为多行注释，续行对齐）。"""
    assert isinstance(fields, (list, tuple)) and len(fields) == 6, len(fields)
    names = ["// 功能      : ", "// 数据通路  : ", "// 时钟/复位 : ",
             "// 依赖      : ", "// 综合/实现 : ", "// "]
    out = [
        "//=============================================================================",
        "// 文件      : " + path,
        "// 模块      : " + mod,
    ]
    for i, f in enumerate(fields[:5]):
        ls = f if isinstance(f, list) else [f]
        for j, s in enumerate(ls):
            out.append((names[i] if j == 0 else "//             ") + s)
    out += [
        "//-----------------------------------------------------------------------------",
        "// 修改记录  :",
        fields[5],
        "//-----------------------------------------------------------------------------",
        RENAME,
        "//=============================================================================",
    ]
    return out


files = []

# ============================== 1) vtc/uivtc.v（GBK） ==============================
uivtc_hdr = head("vtc/uivtc.v", "uivtc", [
    ["视频时序控制器：用行计数器 hcnt 与场计数器 vcnt 产生一套完整的显示时序（行同步 HS、场同步 VS、数据有效 DE），",
     "并把它转成 AXI4-Stream 风格的 video stream 时序（user=帧起始、last=行结束、valid=像素有效）送给下游 HDMI 发送。"],
    ["由 8 个 parameter 描述一种分辨率：H/V_ActiveSize 是有效像素/行数，H/V_FrameSize 是一行/一帧的总节拍数，",
     "H/V_SyncStart 与 H/V_SyncEnd 给出同步脉冲的起止位置。改参数即可适配不同分辨率。",
     "hcnt/vcnt 由 I_vtc_clk 驱动，输出 vtc_hs/vtc_vs/vtc_de；随后打拍生成 O_vtc_vs/hs/de_valid/user/last。"],
    "I_vtc_rstn 是系统复位（低有效），内部另外用 rst_cnt 做 3 拍上电同步复位（rst_sync）。",
    "无子模块例化；仅使用 reg/wire/assign。",
    ["纯 RTL，可综合；已收录于 td_project/camera_to_dsi_display.al，并在 design_top_wrapper.v:774 以 u_hdmi_vtc 例化。",
     "本文件的 parameter 默认值是 1080p 的示例值（H_ActiveSize=1980、H_FrameSize=1920+88+44+148、V_ActiveSize=1080、",
     "V_FrameSize=1080+4+5+36 等），本工程在上层例化处把 8 个参数全部覆盖为 720p60：",
     "H_ActiveSize=1280、H_FrameSize=1650、H_SyncStart=1390、H_SyncEnd=1430、",
     "V_ActiveSize=720、V_FrameSize=750、V_SyncStart=725、V_SyncEnd=730，因此在板上的行为按 1280x720@60 解释。"],
    STD_CHG,
])

files.append({
    "path": "vtc/uivtc.v",
    "header": uivtc_hdr,
    "inserts": [
        {"anchor": "module uivtc#", "lines": [
            "//---- 参数与端口说明（8 个 parameter 描述一种分辨率） ----",
            "// 命名规律：H_ 为一行内的水平方向，V_ 为一帧内的垂直方向；",
            "//   *_ActiveSize ：有效像素数 / 有效行数（= 分辨率）；",
            "//   *_FrameSize  ：一行 / 一帧总共占用的时钟节拍数（有效 + 各种消隐）；",
            "//   *_SyncStart / *_SyncEnd ：同步脉冲的起止计数值。",
            "// 本文件顶部的默认值取自 1080p 官方例程；本工程在 design_top_wrapper.v:774 例化时全部覆盖为 720p60，",
            "// 即一行 1650 拍、一帧 750 行。",
        ]},
        {"anchor": "    else if(hcnt < (H_FrameSize - 1'b1))//计数范围：0 ~ H_FrameSize-1", "lines": [
            "//---- 行计数器 hcnt（水平方向，0 ~ H_FrameSize-1） ----",
            "// 每个像素时钟加 1，计满一行（720p 为 1650 拍）后回零；",
            "// 它同时决定了行同步的位置、一行的有效像素区间和换行的时刻。",
            "// 注意：本工程实际使用的一组参数是 720p60（H_ActiveSize=1280、H_FrameSize=1650、",
            "//   H_SyncStart=1390、H_SyncEnd=1430、V_ActiveSize=720、V_FrameSize=750、V_SyncStart=725、V_SyncEnd=730），",
            "//   由 design_top_wrapper.v:774 例化时覆盖；本文件顶部的默认值是 1080p 官方示例值。",
        ]},
        {"anchor": "reg [2 :0] rst_cnt = 3'd0;  //复位计数器寄存器", "lines": [
            "//---- 上电同步复位 ----",
            "// 只用 I_vtc_rstn 直接复位的话，寄存器会立刻开始计数，而 PLL/时钟刚稳定时可能不可靠，",
            "// 所以这里用一个 3 位计数器 rst_cnt 数 4 拍，rst_sync 取最高位 rst_cnt[2]，作为内部逻辑的同步释放复位。",
        ]},
        {"anchor": "wire hs_valid  =  hcnt < H_ActiveSize;", "lines": [
            "//---- 有效区间与同步脉冲的产生 ----",
            "// hs_valid / vs_valid：当前是否落在有效像素区（不是消隐区）；",
            "// vtc_hs：行同步，hcnt 落在 [H_SyncStart, H_SyncEnd) 区间内有效（720p 即计数 1390~1429，宽 40 拍）；",
            "// vtc_vs：场同步，vcnt 落在 (V_SyncStart, V_SyncEnd] 区间内有效（720p 即第 726~730 行，宽 5 行）；",
            "// vtc_de：只有行、场同时处在有效区才为 1，也就是真正需要送出的像素区间。",
        ]},
        {"anchor": "assign O_vtc_vs       =  vtc_vs_r1;", "lines": [
            "//---- 输出（同步信号与 stream 信号统一打拍对齐） ----",
            "// valid / user / last 都经过两级寄存，使它们与已打一拍的像素数据保持同一节拍，",
            "// 这样下游看到的 de_valid、user、last 与像素是严格对齐的。",
        ]},
    ],
    "insert_seqs": [
        [
            {"anchor": "        vcnt <= 12'd0;", "lines": [
                "//---- 场计数器 vcnt（垂直方向，0 ~ V_FrameSize-1） ----",
                "// vcnt 不是每个时钟都加，而是等一行走完（hcnt 数到 H_ActiveSize-1、即最后一个有效像素）时才加 1；",
                "// 计满一帧（750）后回零，所以它代表 当前正在第几行。",
            ]},
            {"anchor": "        vs_start <= 1'b0;", "lines": [
                "//---- 转 video stream 时序 ----",
                "// 下游（HDMI 发送）使用的是 AXI4-Stream 风格的接口：user 标记一帧的开始、last 标记一行的结束。",
                "// vs_start 用来把 场同步的上升沿 变成一帧的起始标志：检测到 vtc_vs 上升沿时置 1，",
                "// 等 user 已经送出（vtc_user_r1 有效）再清 0，保证每帧只产生一次 user。",
            ]},
        ],
    ],
})

# ============================== 2) hdmi_tx.v ==============================
hdmi_tx_hdr = head("hdmi_tx.v", "hdmi_tx", [
    ["HDMI 发送顶层：把视频（RGB 时序或 stream 时序两种输入方式）、音频（外部 I2S 或已解析的音频流）",
     "连同 EDID 读取（DDC/I2C）一起组织起来，交给 HDMI 1.4b 发送核做 TMDS 编码，",
     "再经 hdmi_phy_wrapper 串行化输出 4 对 TMDS 差分信号（3 数据通道 + 1 时钟通道）。"],
    ["视频：I_video_in_data[23:0] 打拍/时序转换成 axis_s_* 送发送核；音频：I2S_receiver 解出左右声道，",
     "audio_arc_calculate 算出 ACR 的 CTS/N（48 kHz 对应 N=6144）；按键经 key_remove_shakes 消抖后作为 EDID 读触发；",
     "发送核输出 4 组 10 bit TMDS 数据（S_ch0/1/2/clk_tmds_data），由 hdmi_phy_wrapper 转成串行输出。"],
    ["时钟/复位：I_pixel_clk（像素时钟，本工程为 75 MHz）驱动全部逻辑，I_serial_clk（5 倍频 375 MHz）供串行化使用；",
     "I_rst 高有效异步复位。另外用 PLL 的 lock（S_pll_lock）给按键消抖做复位。"],
    ["依赖：例化 I2S_receiver、audio_arc_calculate（ACR_N=6144）、key_remove_shakes、",
     "hdmi_1_4b_transmitter_core_wrapper（加密 IP）、hdmi_phy_wrapper（DEVICE=PH1P）。"],
    ["纯 RTL + 加密 IP + 器件原语，可综合；已收录于 td_project/camera_to_dsi_display.al，",
     "并在 design_top_wrapper.v:811 以 u_hdmi_tx 例化。",
     "发送核按 720p60 配置：HTOTAL=1650、HSA=40、HFP=110、HBP=220、HACTIVE=1280、",
     "VTOTAL=750、VSA=5、VFP=5、VBP=20、VACTIVE=720，VIDEO_VIC=4，像素时钟 74.25 MHz（本工程 PLL 给出 75 MHz）。"],
    STD_CHG,
])

files.append({
    "path": "hdmi_tx.v",
    "header": hdmi_tx_hdr,
    "inserts": [
        {"anchor": "module hdmi_tx (", "lines": [
            "//---- 模块说明与端口分组 ----",
            "// 端口按用途分四组：像素/串行时钟与复位、按键与 EDID 读取、视频输入（RGB 时序或 stream 时序）、音频输入（I2S 或已解析数据）。",
            "// I_video_rgb_enable=1 时按 RGB+DE+VS 的显示时序采样输入视频，=0 时按 axis_s_* 流式接口透传。",
        ]},
        {"anchor": "    wire       S_pll_lock;", "lines": [
            "//---- 内部信号声明 ----",
            "// S_ch0/1/2/clk_tmds_data[9:0] 是发送核输出的 4 组 TMDS 码字（带 synthesis keep，避免被优化掉）；",
            "// S_acr_* 是音频时钟恢复（ACR）的 CTS/N 值；S_i2s_* 是 I2S 接收器解出的音频数据；",
            "// S_pll_lock 来自时钟 PLL 的 lock，用作按键消抖模块的复位释放条件。",
            "// 注：S_rst 声明后本文件内未再使用。",
        ]},
        {"anchor": "    reg       I_video_in_de_r1;", "lines": [
            "//---- 视频输入打拍寄存器 ----",
            "// 把 RGB/DE/VS/USER/VALID/LAST/DATA 各延迟 1~2 拍，用于做边沿检测和时序对齐。",
        ]},
        {"anchor": "    always @(posedge I_pixel_clk)begin", "lines": [
            "//---- DE/VS 一级打拍 ----",
            "// 先无条件各延迟一拍，后面的模块用它们的延后值做边沿检测（DE 下降沿=一行结束，VS 上升沿=一帧开始）。",
        ]},
        {"anchor": "    I2S_receiver u_I2S_receiver(", "lines": [
            "//---- 音频通路：I2S 接收 ----",
            "// 从外部 I2S 三线（BCLK/LRCK/DOUT）恢复出左右声道 24 bit 音频数据与 valid，工作在本模块的像素时钟域。",
        ]},
        {"anchor": "    audio_arc_calculate#(", "lines": [
            "//---- 音频通路：ACR 计算（Audio Clock Recovery） ----",
            "// 统计两个音频采样之间经过了多少个像素时钟，得到 CTS；N=6144 对应 48 kHz 采样率、",
            "// 发送核用 CTS/N 在接收端重建音频时钟。",
        ]},
        {"anchor": "    key_remove_shakes u_key_remove_shakes(", "lines": [
            "//---- 按键消抖与 EDID 读触发 ----",
            "// 注意这里的复位接的是 PLL 的 lock（S_pll_lock），只有时钟锁定后才允许按键生效；",
            "// 消抖后产生的单拍脉冲 S_key_edid_read_trig 作为一次 EDID 读取的启动信号。",
        ]},
        {"anchor": "    hdmi_1_4b_transmitter_core_wrapper#(", "lines": [
            "//---- HDMI 1.4b 发送核（加密 IP） ----",
            "// 参数按 720p60 配置：HTOTAL=1650、HSA=40、HFP=110、HBP=220、HACTIVE=1280、",
            "// VTOTAL=750、VSA=5、VFP=5、VBP=20、VACTIVE=720；VIDEO_TPG=Disable（不使用内部测试图），",
            "// VIDEO_FORMAT=RGB、AUDIO_SAMPLE_RATE=48K、IIC_SCL_DIV=125（DDC 时钟分频）。",
            "// 它把视频/音频/ACR 一起做 TMDS 编码，输出 4 组 10 bit 码字给物理层。",
        ]},
        {"anchor": "        .O_ddc_scl          ( O_ddc_scl          ),", "lines": [
            "//---- DDC/I2C（读显示器 EDID）与视频流连接 ----",
        ]},
        {"anchor": "    hdmi_phy_wrapper  #(", "lines": [
            "//---- TMDS 物理层 ----",
            "// 把 4 组 10 bit 码字交给 hdmi_phy_wrapper 串行化并做差分输出；DEVICE 选 PH1P 对应安路 PH1P 器件原语。",
        ]},
    ],
    "insert_seqs": [
        [
            {"anchor": "    always @(posedge I_pixel_clk or posedge I_rst )begin", "lines": [
                "//---- 视频时序转换（RGB 时序 -> stream 时序） ----",
                "// 复位时把所有输出寄存器清零；I_video_rgb_enable=1 时从 DE/VS 组合出 stream 的 last/valid/user 并寄存数据；",
                "// =0 时输入已是 stream 时序，只做纯打拍透传（VALID/LAST/USER/DATA 各延后一拍）。",
            ]},
            {"anchor": "    always @(posedge I_pixel_clk or posedge I_rst )begin", "lines": [
                "//---- 帧起始标志 vs_start ----",
                "// 检测 I_video_in_vs 的上升沿：置 1 后由下游在适当时机清 0，用于标记一帧的开始（发送核据此复位行场状态）。",
            ]},
        ],
    ],
})

# ============================== 3) hdmi_phy_wrapper.v ==============================
phy_hdr = head("hdmi_phy_wrapper.v", "hdmi_phy_wrapper", [
    ["TMDS 物理层包装：把 HDMI 发送核给出的 4 组 10 bit TMDS 码（3 个数据通道 + 1 个时钟通道）",
     "先做位序重排，再各用一个 lane_lvds_10_1 串行化器接出，形成 4 对高速串行输出。"],
    ["I_tmds_channel_0/1/2/clk[9:0] 按位倒序重排成 S_tmds_data_ch0/1/2/clk（[0]->[9]、[1]->[8] …… [9]->[0]），",
     "再分别送进 4 个 lane_lvds_10_1（DEVICE 由 parameter 透传），输出 O_tmds_ch0/1/2_p 与 O_tmds_clk_p。"],
    ["串行化用的是 I_serial_clk（本工程 375 MHz = 像素时钟 75 MHz 的 5 倍），",
     "I_pixel_clk 用于产生并串转换的分相标志，I_rst 是复位（透传给各 lane）。"],
    "依赖：例化 4 次 lane_lvds_10_1（同一模块，实例名仍沿用旧的 ..._lane_lvds_8_1 命名）。",
    ["纯 RTL + 器件原语（原语在 lane_lvds_10_1 内部），可综合；已收录于 td_project/camera_to_dsi_display.al，",
     "并在 hdmi_tx.v:231 以 u_hdmi2phy_wrapper 例化（DEVICE=PH1P）。"],
    HDR_PHY_CHG,
])

files.append({
    "path": "hdmi_phy_wrapper.v",
    "header": phy_hdr,
    "inserts": [
        {"anchor": "module hdmi_phy_wrapper#(", "lines": [
            "//---- 模块说明 ----",
            "// 本模块不做 TMDS 编码（编码在上游发送核里完成），只负责 位序调整 + 并串转换 + 差分输出。",
            "// 位序之所以要重排，是因为发送核输出的 10 bit 码与物理层期望送入 ODDR 的先后顺序相反，",
            "// 重排之后 lane_lvds_10_1 里 左移取高 2 位 的串行化顺序才与实际要发送的比特顺序一致。",
            "// DEVICE 参数用于选择器件对应的 ODDR 原语（见 lane_lvds_10_1.v 内的 generate 分支）。",
        ]},
        {"anchor": "    wire[9:0] S_tmds_data_ch0;", "lines": [
            "//---- 重排后的 TMDS 数据 ----",
            "// 每个通道一个 10 bit 中间信号，由下面的 assign 逐位倒序拼出来。",
        ]},
    ],
    "insert_seqs": [
        [
            {"anchor": "    assign S_tmds_data_ch0 = {I_tmds_channel_0[0],", "lines": [
                "//---- 位序重排（4 个通道相同做法） ----",
                "// 把输入的第 0 位放到最高位、第 9 位放到最低位，即整字按位倒序；",
                "// 这样送进串行化器后先移出的是输入的最低位，符合 TMDS 的发送顺序。",
            ]},
            {"anchor": "    assign S_tmds_data_ch1 = {I_tmds_channel_1[0],", "lines": []},
            {"anchor": "    assign S_tmds_data_ch2 = {I_tmds_channel_2[0],", "lines": []},
            {"anchor": "    assign S_tmds_data_clk = {I_tmds_channel_clk[0],", "lines": []},
        ],
        [
            {"anchor": "    lane_lvds_10_1 #(", "lines": [
                "//---- 4 路并串转换与差分输出 ----",
                "// 4 个 lane 结构完全相同：ch0/ch1/ch2 送 3 个数据通道，第 4 个送时钟通道；",
                "// 每个 lane 在 I_serial_clk 域把 10 bit 码按 2 bit 一组串行移出，形成 5 倍频的串行码流。",
                "// 注意实例名仍写作 u0/u1/u2/u3_lane_lvds_8_1，是从早先 8:1 版本沿用下来的命名（模块名已改为 lane_lvds_10_1）。",
            ]},
            {"anchor": "    lane_lvds_10_1 #(", "lines": []},
            {"anchor": "    lane_lvds_10_1 #(", "lines": []},
            {"anchor": "    lane_lvds_10_1 #(", "lines": []},
        ],
    ],
})

# ============================== 4) pll_hdmi.v ==============================
pll_hdr = head("pll_hdmi.v", "pll_hdmi", [
    ["HDMI 通路专用 PLL（由安路 TD 6.1.155545 的 IP 生成器生成）：把 50 MHz 参考时钟倍频/分频出 4 路时钟，",
     "其中 C0=75.000000 MHz 作为 HDMI 像素时钟、C1=375.000000 MHz 作为 TMDS 串行时钟，",
     "C2=70.312500 MHz、C3=23.936170 MHz 为生成的其余两路输出（本文件中未做进一步处理，直接引出）。"],
    ["refclk -> PLL 的 clk0/1/2/3_out -> 分别经 PH1P_LOGIC_BUFG（C0/C2）和 PH1P_PHY_MLCLK（C3）后输出；",
     "C1 不经过 BUFG 直接输出；C0 同时经 bufg_feedback 回灌到 PLL 的 fbclk 完成外部反馈。"],
    "输入 50 MHz（20 ns，与约束里的 sys_clk_50m 一致）；输出 4 路时钟 + lock 指示；无复位端口。",
    "依赖：器件原语 PH1P_LOGIC_BUFG、PH1P_PHY_MLCLK 与 PLL 原语 ph1p_phy_pll_wrapper_27c53fedd344（由安路 TD 提供）。",
    ["TD 生成的参数化原语，需结合安路器件库/仿真模型编译；本文件在工程 .al 中未以 .v 形式收录",
     "（工程里以 ip_source/PLL/PLL.xml 的 IP 形式存在），因此未能确认它是否已被实际接入本次设计，本文件按原样保留。"],
    STD_CHG,
])

files.append({
    "path": "pll_hdmi.v",
    "header": pll_hdr,
    "inserts": [
        {"anchor": "module pll_hdmi", "lines": [
            "//---- 模块说明 ----",
            "// 下面文件头的时钟表由 TD 的 PLL IP 生成器自动生成，含义是：",
            "//   输入 50 MHz，整体倍频系数 3、分频系数 2，得到 4 路输出（相位均为 0 度）；",
            "//   C0 = 75.000000 MHz —— 给 HDMI 像素逻辑用；",
            "//   C1 = 375.000000 MHz —— 给 TMDS 串行化用（= 像素时钟的 5 倍）；",
            "//   C2 = 70.312500 MHz、C3 = 23.936170 MHz —— 另外两路输出，本文件直接引出。",
            "// PLL 的参考输入是 refclk，lock 指示锁定状态（锁定后才允许下游逻辑复位释放）。",
        ]},
        {"anchor": "  wire							  clk0_buf;", "lines": [
            "//---- 输出时钟缓冲与反馈 ----",
            "// C0 先经过 PH1P_LOGIC_BUFG 到 clk0_out，同时把该输出回灌给 PLL 的 fbclk，",
            "// 形成 外部反馈（FBKCLK=CLKC0_EXT），使 PLL 把输出现场的走线延迟也计入相位控制。",
        ]},
        {"anchor": "  ph1p_phy_pll_wrapper_27c53fedd344", "lines": [
            "//---- PLL 原语例化（TD 生成，参数与 IP 配置一一对应） ----",
            "// 关键参数含义：FIN=50 MHz 参考频率；REFCLK_DIV=2、FBCLK_DIV=3（分数分频比 3/2）；",
            "// CLKC0_DIV=15/CPHASE=14 → C0=75 MHz；CLKC1_DIV=3/CPHASE=2 → C1=375 MHz；",
            "// CLKC2_DIV=16/CPHASE=15 → C2=70.3125 MHz；CLKC3_DIV=47/CPHASE=46 → C3≈23.936 MHz；",
            "// DUTY50=ENABLE 表示各路都输出 50% 占空比；FEEDBK_MODE=NORMAL、PLL_FASTLOOP=ENABLE。",
        ]},
        {"anchor": "      .clk4_en(1'b0),", "lines": [
            "//---- 未使用的资源与非必要端口的固定接法 ----",
            "// clk4/clk5/clk6 三路不使用（en 接 0、输出悬空）；DRP 动态重配置端口全部接常量、输出悬空；",
            "// 相位移动（ps*）与扩频（ssc_reset）也全部关闭；pllpd/reset 接 0 表示常开不复位。",
            "// 真正使用的只有 clk0/1/2/3 四路输出与 lock，其中 clk0/2/3 分别写到对应的 *_buf 再经缓冲输出。",
        ]},
    ],
})

with open(r"E:\FPGA\_analysis\docs\spec6.json", "w", encoding="utf-8") as fp:
    json.dump({"files": files}, fp, ensure_ascii=False, indent=1)

print("ok")
