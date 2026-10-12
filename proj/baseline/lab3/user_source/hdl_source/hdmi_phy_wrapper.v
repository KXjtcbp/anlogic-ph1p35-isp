//=============================================================================
// 文件      : hdmi_phy_wrapper.v
// 模块      : hdmi_phy_wrapper
// 功能      : TMDS 物理层包装：把 HDMI 发送核给出的 4 组 10 bit TMDS 码（3 个数据通道 + 1 个时钟通道）
//             先做位序重排，再各用一个 lane_lvds_10_1 串行化器接出，形成 4 对高速串行输出。
// 数据通路  : I_tmds_channel_0/1/2/clk[9:0] 按位倒序重排成 S_tmds_data_ch0/1/2/clk（[0]->[9]、[1]->[8] …… [9]->[0]），
//             再分别送进 4 个 lane_lvds_10_1（DEVICE 由 parameter 透传），输出 O_tmds_ch0/1/2_p 与 O_tmds_clk_p。
// 时钟/复位 : 串行化用的是 I_serial_clk（本工程 375 MHz = 像素时钟 75 MHz 的 5 倍），
//             I_pixel_clk 用于产生并串转换的分相标志，I_rst 是复位（透传给各 lane）。
// 依赖      : 例化 4 次 lane_lvds_10_1（同一模块，实例名仍沿用旧的 ..._lane_lvds_8_1 命名）。
// 综合/实现 : 纯 RTL + 器件原语（原语在 lane_lvds_10_1 内部），可综合；已收录于 td_project/camera_to_dsi_display.al，
//             并在 hdmi_tx.v:231 以 u_hdmi2phy_wrapper 例化（DEVICE=PH1P）。
//-----------------------------------------------------------------------------
// 修改记录  :
// 2026-10-09  文件名拼写修正 hdmi_phy_warpper.v -> hdmi_phy_wrapper.v（模块名本就正确），同步更新 camera_to_dsi_display.al 中的路径
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================


//---- 模块说明 ----
// 本模块不做 TMDS 编码（编码在上游发送核里完成），只负责 位序调整 + 并串转换 + 差分输出。
// 位序之所以要重排，是因为发送核输出的 10 bit 码与物理层期望送入 ODDR 的先后顺序相反，
// 重排之后 lane_lvds_10_1 里 左移取高 2 位 的串行化顺序才与实际要发送的比特顺序一致。
// DEVICE 参数用于选择器件对应的 ODDR 原语（见 lane_lvds_10_1.v 内的 generate 分支）。
module hdmi_phy_wrapper#(
    parameter DEVICE = "EG"
    )(
    input wire      I_pixel_clk,
    input wire      I_serial_clk,
    input wire      I_rst,

    input wire[9:0] I_tmds_channel_0,
    input wire[9:0] I_tmds_channel_1,
    input wire[9:0] I_tmds_channel_2,
    input wire[9:0] I_tmds_channel_clk,
    
    output wire     O_tmds_ch0_p,
    output wire     O_tmds_ch1_p,
    output wire     O_tmds_ch2_p,
    output wire     O_tmds_clk_p
);
    
//---- 重排后的 TMDS 数据 ----
// 每个通道一个 10 bit 中间信号，由下面的 assign 逐位倒序拼出来。
    wire[9:0] S_tmds_data_ch0;
    wire[9:0] S_tmds_data_ch1;
    wire[9:0] S_tmds_data_ch2;
    wire[9:0] S_tmds_data_clk;

//---- 位序重排（4 个通道相同做法） ----
// 把输入的第 0 位放到最高位、第 9 位放到最低位，即整字按位倒序；
// 这样送进串行化器后先移出的是输入的最低位，符合 TMDS 的发送顺序。
    assign S_tmds_data_ch0 = {I_tmds_channel_0[0],
                              I_tmds_channel_0[1],
                              I_tmds_channel_0[2],
                              I_tmds_channel_0[3],
                              I_tmds_channel_0[4],
                              I_tmds_channel_0[5],
                              I_tmds_channel_0[6],
                              I_tmds_channel_0[7],
                              I_tmds_channel_0[8],
                              I_tmds_channel_0[9]};

    assign S_tmds_data_ch1 = {I_tmds_channel_1[0],
                              I_tmds_channel_1[1],
                              I_tmds_channel_1[2],
                              I_tmds_channel_1[3],
                              I_tmds_channel_1[4],
                              I_tmds_channel_1[5],
                              I_tmds_channel_1[6],
                              I_tmds_channel_1[7],
                              I_tmds_channel_1[8],
                              I_tmds_channel_1[9]};

    assign S_tmds_data_ch2 = {I_tmds_channel_2[0],
                              I_tmds_channel_2[1],
                              I_tmds_channel_2[2],
                              I_tmds_channel_2[3],
                              I_tmds_channel_2[4],
                              I_tmds_channel_2[5],
                              I_tmds_channel_2[6],
                              I_tmds_channel_2[7],
                              I_tmds_channel_2[8],
                              I_tmds_channel_2[9]};

    assign S_tmds_data_clk = {I_tmds_channel_clk[0],
                              I_tmds_channel_clk[1],
                              I_tmds_channel_clk[2],
                              I_tmds_channel_clk[3],
                              I_tmds_channel_clk[4],
                              I_tmds_channel_clk[5],
                              I_tmds_channel_clk[6],
                              I_tmds_channel_clk[7],
                              I_tmds_channel_clk[8],
                              I_tmds_channel_clk[9]};


//---- 4 路并串转换与差分输出 ----
// 4 个 lane 结构完全相同：ch0/ch1/ch2 送 3 个数据通道，第 4 个送时钟通道；
// 每个 lane 在 I_serial_clk 域把 10 bit 码按 2 bit 一组串行移出，形成 5 倍频的串行码流。
// 注意实例名仍写作 u0/u1/u2/u3_lane_lvds_8_1，是从早先 8:1 版本沿用下来的命名（模块名已改为 lane_lvds_10_1）。
    lane_lvds_10_1 #(
        .DEVICE ( DEVICE )    
    )u0_lane_lvds_8_1(
        .I_pixel_clk  ( I_pixel_clk     ),
        .I_serial_clk ( I_serial_clk    ),
        .I_rst        ( I_rst           ),

        .I_data_in    ( S_tmds_data_ch0 ),
        .O_serial_out ( O_tmds_ch0_p    )
    );


    lane_lvds_10_1 #(
        .DEVICE ( DEVICE )    
    )u1_lane_lvds_8_1(
        .I_pixel_clk  ( I_pixel_clk     ),
        .I_serial_clk ( I_serial_clk    ),
        .I_rst        ( I_rst           ),
        
        .I_data_in    ( S_tmds_data_ch1 ),
        .O_serial_out ( O_tmds_ch1_p    )
    );


    lane_lvds_10_1 #(
        .DEVICE ( DEVICE )    
    )u2_lane_lvds_8_1(
        .I_pixel_clk  ( I_pixel_clk     ),
        .I_serial_clk ( I_serial_clk    ),
        .I_rst        ( I_rst           ),
        
        .I_data_in    ( S_tmds_data_ch2 ),
        .O_serial_out ( O_tmds_ch2_p    )
    );


    lane_lvds_10_1 #(
        .DEVICE ( DEVICE )    
    )u3_lane_lvds_8_1(
        .I_pixel_clk  ( I_pixel_clk     ),
        .I_serial_clk ( I_serial_clk    ),
        .I_rst        ( I_rst           ),
        
        .I_data_in    ( S_tmds_data_clk ),
        .O_serial_out ( O_tmds_clk_p    )
    );


endmodule





