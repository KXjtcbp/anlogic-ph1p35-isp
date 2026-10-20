//=============================================================================
// 文件      : I2S_receiver.v
// 模块      : I2S_receiver
// 功能      : I2S（Inter-IC Sound）音频接收器：从 BCLK/LRCK/DOUT 三根线上恢复出左右声道的 24 bit 采样。
//             LRCK 为高时接收的是右声道、为低时是左声道；左声道先锁存、等右声道到齐后成对输出。
// 数据通路  : I_i2s_DOUT 在 BCLK 上升沿按位移入 64 bit 移位寄存器（左/右各一个，另一个清 0）；
//             左声道数据先锁存到 S_left_data_lock，右声道到来时同时取两路的高 24 bit 输出；
//             O_audio_valid 与左右数据同拍输出，供 hdmi_tx 打包成音频采样包。
// 时钟/复位 : 单一时钟 I_clk；I_rst 高有效，但本文件内部所有寄存器都没有复位端，
//             靠 BCLK/LRCK 的边沿事件自然进入确定状态。
// 依赖      : 无子模块例化；纯 RTL，无器件原语、无 IP。
// 综合/实现 : 可综合；已收录于 td_project/camera_to_dsi_display.al（hdmi_tx.v 未收录于 .al），
//             并在 hdmi_tx.v:113 以 u_I2S_receiver 例化。
//-----------------------------------------------------------------------------
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================



//---- 模块说明 ----
// I2S 是“位时钟 + 声道选择 + 串行数据”的三线协议，本模块在本地 I_clk 域把三根异步线恢复成采样值：
// 先把三根线各打三拍去亚稳态，再用边沿检测找到 BCLK 的上升沿与 LRCK 的跳变沿，
// 在 BCLK 上升沿按 LRCK 电平把 DOUT 移入左或右声道移位寄存器。
module I2S_receiver (
    input wire       I_clk,
    input wire       I_rst,
  
    input wire       I_i2s_BCLK,
    input wire       I_i2s_LRCK,
    input wire       I_i2s_DOUT,

    output reg       O_audio_valid,
    output reg[23:0] O_audio_left_data,
    output reg[23:0] O_audio_right_data
);


//---- 内部信号声明 ----
// S_i2s_bclk_1d/2d/3d：BCLK 三级同步链；
// S_i2s_lrck_*：LRCK 三级同步链 + S_i2s_lrck_sync（只在 BCLK 上升沿采样的声道标志）；
// S_i2s_dout_*：DOUT 三级同步链；
// S_left/right_shift_data：64 bit 左右声道移位寄存器；
// S_left_data_lock：左声道先到的锁存副本。
    reg       S_i2s_bclk_1d;
    reg       S_i2s_bclk_2d;
    reg       S_i2s_bclk_3d;
  
    wire      S_i2s_bclk_p_edge;  
  
    reg       S_i2s_lrck_1d;
    reg       S_i2s_lrck_2d;
    reg       S_i2s_lrck_3d;
    reg       S_i2s_lrck_sync;
    wire      S_i2s_lrck_p_edge;
    wire      S_i2s_lrck_n_edge;
  
    reg       S_i2s_dout_1d;
    reg       S_i2s_dout_2d;
    reg       S_i2s_dout_3d;

    reg[63:0] S_left_shift_data;
    reg[63:0] S_right_shift_data;

    reg       S_left_data_valid;
    reg       S_right_data_valid;

    reg[63:0] S_left_data_lock;

//---- 三线输入同步打拍 ----
// 三根 I2S 信号都是相对 I_clk 的异步输入，各打三拍既防亚稳态又给边沿检测提供历史值。
    always @(posedge I_clk) begin
        S_i2s_bclk_1d <= I_i2s_BCLK;
        S_i2s_bclk_2d <= S_i2s_bclk_1d;
        S_i2s_bclk_3d <= S_i2s_bclk_2d;

        S_i2s_lrck_1d <= I_i2s_LRCK;
        S_i2s_lrck_2d <= S_i2s_lrck_1d;
        S_i2s_lrck_3d <= S_i2s_lrck_2d;

        S_i2s_dout_1d <= I_i2s_DOUT;
        S_i2s_dout_2d <= S_i2s_dout_1d;
        S_i2s_dout_3d <= S_i2s_dout_2d;
    end

//---- 边沿检测 ----
// 用同步链最近两级做上升沿检测，得到与 I_clk 对齐的单拍脉冲。
    assign S_i2s_bclk_p_edge = ~S_i2s_bclk_3d & S_i2s_bclk_2d;


//---- 声道标志采样 ----
// 只在 BCLK 上升沿才对 LRCK 采样：一个 BCLK 周期里 LRCK 是稳定的，
// 这样得到的 S_i2s_lrck_sync 与实际移入的位严格对应，避免在 LRCK 跳变附近采错。
    always @(posedge I_clk) begin
        if(S_i2s_bclk_p_edge)
            S_i2s_lrck_sync <= S_i2s_lrck_3d;
        else
            S_i2s_lrck_sync <= S_i2s_lrck_sync;
    end

// 这两条是 LRCK 的上升沿（进入右声道）与下降沿（进入左声道）；
// 与 S_i2s_lrck_sync 比较而不是与原始 LRCK 比较，保证声道判定与数据采样用的是同一时刻的电平。
    assign S_i2s_lrck_p_edge = ~S_i2s_lrck_sync & S_i2s_lrck_3d;

    assign S_i2s_lrck_n_edge = ~S_i2s_lrck_3d & S_i2s_lrck_sync;

//---- 串行移位接收 ----
// BCLK 上升沿才移位；LRCK 为高移入右声道寄存器并把左声道清零，为低则相反；
// 非 BCLK 上升沿时保持，这样一位数据只被采一次。
// 使用 64 bit 宽（远大于 24 bit 采样）是为了兼容不同 I2S 数据延迟，最终只取高 24 bit。
    always @(posedge I_clk) begin
        if(S_i2s_bclk_p_edge)
            if(S_i2s_lrck_sync)
                begin
                    S_right_shift_data <= {S_right_shift_data[62:0],S_i2s_dout_3d};
                    S_left_shift_data  <= 'd0;
                end
            else
                begin
                    S_right_shift_data <= 'd0;
                    S_left_shift_data  <= {S_left_shift_data[62:0],S_i2s_dout_3d};
                end
        else
            begin
                S_right_shift_data <= S_right_shift_data;
                S_left_shift_data  <= S_left_shift_data;
            end
    end


//---- 左右声道有效标志 ----
    always @(posedge I_clk) begin
        if(S_i2s_bclk_p_edge && S_i2s_lrck_p_edge)
            S_left_data_valid <= 1'b1;
        else
            S_left_data_valid <= 1'b0;
    end

    always @(posedge I_clk) begin
        if(S_i2s_bclk_p_edge && S_i2s_lrck_n_edge)
            S_right_data_valid <= 1'b1;
        else
            S_right_data_valid <= 1'b0;
    end

//---- 左声道锁存 ----
// 左声道数据先到，先存副本；等右声道到齐后再一起输出，保证左右样本属于同一帧。
    always @(posedge I_clk) begin
        if(S_left_data_valid)
            S_left_data_lock <= S_left_shift_data;
        else
            S_left_data_lock <= S_left_data_lock;
    end

//---- 成对输出 ----
// 右声道有效（即一次左右采样都收齐）时，输出 valid 与两路各 24 bit 采样；
// 取移位寄存器的高 24 bit（[63:40]）作为有效数据位，其余低位在成帧时已被清 0。
// 其余时刻输出清零，避免下游把旧数据当成新样本。
    always @(posedge I_clk) begin
        if(S_right_data_valid)
            begin
                O_audio_valid      <= 1'b1;
                O_audio_left_data  <= S_left_data_lock[63:40];
                O_audio_right_data <= S_right_shift_data[63:40];
            end
        else
            begin
                O_audio_valid      <= 1'b0;
                O_audio_left_data  <= 'd0;
                O_audio_right_data <= 'd0;
            end
    end

    // always @(posedge I_clk) begin
    //     if(S_i2s_bclk_p_edge)
    //         begin
    //             if(S_i2s_lrck_3d)
    //                 begin
    //                     S_right_channel_cnt <= S_right_channel_cnt + 1'b1;
    //                     S_left_channel_cnt  <= 'd0;
    //                 end
    //             else    
    //                 begin
    //                     S_right_channel_cnt <= 'd0;
    //                     S_left_channel_cnt  <= S_left_channel_cnt + 1'b1;
    //                 end
    //         end
    //     else
    //         begin
    //             S_right_channel_cnt <= S_right_channel_cnt;
    //             S_left_channel_cnt  <= S_left_channel_cnt;
    //         end
    // end


    

endmodule