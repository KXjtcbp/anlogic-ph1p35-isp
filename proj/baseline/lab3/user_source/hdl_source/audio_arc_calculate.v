//=============================================================================
// 文件      : audio_arc_calculate.v
// 模块      : audio_arc_calculate
// 功能      : HDMI 音频 ACR（Audio Clock Regeneration，音频时钟再生）参数发生器：对 I2S 送来的音频采样打点计数，每隔 AUDIO_DIV 个采样输出一次 ACR 包，给出本次 ACR 周期内 HDMI 像素时钟的计数 CTS 与音频采样率标称值 N，供 HDMI 发送核重建音频时钟。
// 数据通路  : I_audio_valid 是音频采样有效指示（来自 I2S_receiver）；本模块在像素时钟域内分频出 S_audio_valid_div 作为 ACR 触发，并统计相邻两次触发之间经过的像素时钟数得到 O_acr_cts[19:0]，与 O_acr_n[19:0] 一起送往 hdmi_1_4b_transmitter_core_wrapper。
// 时钟/复位 : I_clk（HDMI 像素时钟域）；I_rst 按代码是 posedge 触发且高电平有效（同步复位）。
// 依赖      : 无其它子模块依赖；被 hdmi_tx.v:127 以 audio_arc_calculate #(.ACR_N(6144)) u_audio_arc_calculate 例化（6144 对应 48 kHz）。
// 综合/实现 : 纯寄存器逻辑（1 个 8 bit 分频计数器、1 个 20 bit CTS 计数器），无 IP 与原语依赖；已收录于 td_project/camera_to_dsi_display.al。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================




//---- 模块说明 ----
// ACR 的用途：HDMI 用 N/CTS 描述音频采样时钟与像素时钟的关系，
// 接收端按 fs = f_pixel * N / CTS 反推音频采样率，因此 CTS 必须在像素时钟域测量。
module audio_arc_calculate #(
    parameter ACR_N = 6144
    )(
    input wire       I_clk,
    input wire       I_rst,

    input wire       I_audio_valid,

    output reg       O_acr_valid,
    output reg[19:0] O_acr_cts,
    output reg[19:0] O_acr_n
);


//---- ACR 触发分频 ----
// ACR_N = 6144 是 48 kHz 对应的音频采样率标称值（N 值）；
// AUDIO_DIV = ACR_N >> 7 = 6144/128 = 48，即每累计 48 个音频采样产生一次 ACR 更新（约 1 ms）。
    localparam AUDIO_DIV = ACR_N >> 7;

    reg[7:0]  S_audio_div_cnt;
    wire      S_audio_valid_div;
    reg[19:0] S_acr_cts_cnt;


    always @(posedge I_clk or posedge I_rst) begin
        if(I_rst)
            S_audio_div_cnt <= 'd0;
        else
//---- 采样分频计数器 S_audio_div_cnt ----
// 只在 I_audio_valid 有效时累加，计到 AUDIO_DIV-1 回 0，形成每 48 个采样的周期标志。
            if(I_audio_valid)
                begin
                    if(S_audio_div_cnt >= AUDIO_DIV-1)
                        S_audio_div_cnt <= 'd0;
                    else
                        S_audio_div_cnt <= S_audio_div_cnt + 'd1;
                end
            else
                S_audio_div_cnt <= S_audio_div_cnt;
    end


//---- ACR 周期标志 ----
// S_audio_valid_div 有效表示本次采样正好是第 48 个，此刻发出并锁存一份新的 ACR 参数。
    assign S_audio_valid_div = I_audio_valid && (S_audio_div_cnt == AUDIO_DIV-1) ? 1'b1 : 1'b0;

    always @(posedge I_clk or posedge I_rst) begin
        if(I_rst)
            S_acr_cts_cnt <= 'd0;
        else
//---- CTS 计数：统计一个 ACR 周期内的像素时钟数 ----
// S_acr_cts_cnt 平时逐拍加一，只有 ACR 周期标志有效时清零，
// 因此它记录的是上一次发 ACR 到本次发 ACR 之间经过了多少个 I_clk 周期。
            if(S_audio_valid_div)
                S_acr_cts_cnt <= 'd0;
            else
                S_acr_cts_cnt <= S_acr_cts_cnt + 'd1;
    end


    always @(posedge I_clk) begin
//---- ACR 输出寄存 ----
// 只在 ACR 周期点输出一次（O_acr_valid 单拍有效）：
//   O_acr_cts = 统计值 + 1，把当前这一拍也计入，避免每次少算 1 拍；
//   O_acr_n   = ACR_N（6144），即 48 kHz 对应的 N 值。
// 其余时间三根输出线全部归零，等待下一个 ACR 周期。
        if(S_audio_valid_div)
            begin
                O_acr_valid <= 1'b1;
                O_acr_cts   <= S_acr_cts_cnt + 'd1;
                O_acr_n     <= ACR_N;
            end
        else    
            begin
                O_acr_valid <= 1'b0;
                O_acr_cts   <= 'd0;
                O_acr_n     <= 'd0;
            end
    end

    
endmodule