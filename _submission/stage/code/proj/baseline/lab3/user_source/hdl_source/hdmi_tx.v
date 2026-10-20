//=============================================================================
// 文件      : hdmi_tx.v
// 模块      : hdmi_tx
// 功能      : HDMI 发送顶层：把视频（RGB 时序或 stream 时序两种输入方式）、音频（外部 I2S 或已解析的音频流）
//             连同 EDID 读取（DDC/I2C）一起组织起来，交给 HDMI 1.4b 发送核做 TMDS 编码，
//             再经 hdmi_phy_wrapper 串行化输出 4 对 TMDS 差分信号（3 数据通道 + 1 时钟通道）。
// 数据通路  : 视频：I_video_in_data[23:0] 打拍/时序转换成 axis_s_* 送发送核；音频：I2S_receiver 解出左右声道，
//             audio_arc_calculate 算出 ACR 的 CTS/N（48 kHz 对应 N=6144）；按键经 key_remove_shakes 消抖后作为 EDID 读触发；
//             发送核输出 4 组 10 bit TMDS 数据（S_ch0/1/2/clk_tmds_data），由 hdmi_phy_wrapper 转成串行输出。
// 时钟/复位 : 时钟/复位：I_pixel_clk（像素时钟，本工程为 75 MHz）驱动全部逻辑，I_serial_clk（5 倍频 375 MHz）供串行化使用；
//             I_rst 高有效异步复位。另外用 PLL 的 lock（S_pll_lock）给按键消抖做复位。
// 依赖      : 依赖：例化 I2S_receiver、audio_arc_calculate（ACR_N=6144）、key_remove_shakes、
//             hdmi_1_4b_transmitter_core_wrapper（加密 IP）、hdmi_phy_wrapper（DEVICE=PH1P）。
// 综合/实现 : 纯 RTL + 加密 IP + 器件原语，可综合；已收录于 td_project/camera_to_dsi_display.al，
//             并在 design_top_wrapper.v:811 以 u_hdmi_tx 例化。
//             发送核按 720p60 配置：HTOTAL=1650、HSA=40、HFP=110、HBP=220、HACTIVE=1280、
//             VTOTAL=750、VSA=5、VFP=5、VBP=20、VACTIVE=720，VIDEO_VIC=4，像素时钟 74.25 MHz（本工程 PLL 给出 75 MHz）。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
`timescale 1ns / 1ns //仿真时间刻度/精度

//---- 模块说明与端口分组 ----
// 端口按用途分四组：像素/串行时钟与复位、按键与 EDID 读取、视频输入（RGB 时序或 stream 时序）、音频输入（I2S 或已解析数据）。
// I_video_rgb_enable=1 时按 RGB+DE+VS 的显示时序采样输入视频，=0 时按 axis_s_* 流式接口透传。
module hdmi_tx (
    input wire       I_pixel_clk, //像素时钟
    input wire       I_serial_clk,//串行发送时钟
    input wire       I_rst, //异步复位信号，高电平有效

    input wire       I_key_in,
    
    input wire       I_edid_read_trig,//EDID读触发信号
    output wire      O_edid_read_valid,//EDID读有效信号
    output wire[7:0] O_edid_read_data,//EDID读数据
///**********************  video rgb input  *****************************  
    input wire       I_video_rgb_enable,  //是否使能RGB输入接口，设置1使能，否则采用stream video时序接口
    input wire       I_video_in_de, //RGB 输入de有效
    input wire       I_video_in_vs, //RGB 输入VS 帧同步 
///**********************  video stream input  ***************************
    input wire       I_video_in_user,  //视频输入帧起始信号
    input wire       I_video_in_valid, //视频输入有效信号
    input wire       I_video_in_last,  //视频输入行结束信号
    output wire      O_video_in_ready, //视频输入ready信号
    input wire[23:0] I_video_in_data,  //视频输入数据
///*********************  audio stream input  ***************************
    input wire       I_audio_valid,     //音频输入有效信号
    input wire[23:0] I_audio_left_data, //音频左声道数据
    input wire[23:0] I_audio_right_data,//音频左声道数据
    
    input wire       I_i2s_BCLK,
    input wire       I_i2s_LRCK,
    input wire       I_i2s_DOUT,

    output wire      O_ddc_scl,
    inout wire       IO_ddc_sda,

    output           O_hdmi_clk_p, //HDMI输出时钟P端
    output    [2:0]  O_hdmi_tx_p,  //HDMI输出数据P端
    
    output wire      O_tmds_ch0_p, //HDMI数据通道0
    output wire      O_tmds_ch1_p, //HDMI数据通道1
    output wire      O_tmds_ch2_p, //HDMI数据通道2
    output wire      O_tmds_clk_p  //HDMI时钟通道
);

//---- 内部信号声明 ----
// S_ch0/1/2/clk_tmds_data[9:0] 是发送核输出的 4 组 TMDS 码字（带 synthesis keep，避免被优化掉）；
// S_acr_* 是音频时钟恢复（ACR）的 CTS/N 值；S_i2s_* 是 I2S 接收器解出的音频数据；
// S_pll_lock 来自时钟 PLL 的 lock，用作按键消抖模块的复位释放条件。
// 注：S_rst 声明后本文件内未再使用。
    wire       S_pll_lock;
    wire       S_rst;

    wire[9:0]  S_ch0_tmds_data; //synthesis keep; 
    wire[9:0]  S_ch1_tmds_data; //synthesis keep; 
    wire[9:0]  S_ch2_tmds_data; //synthesis keep; 
    wire[9:0]  S_clk_tmds_data; //synthesis keep; 

    wire       S_acr_valid; //synthesis keep; 
    wire[19:0] S_acr_cts;   //synthesis keep; 
    wire[19:0] S_acr_n;     //synthesis keep; 
    wire       S_i2s_audio_valid;
    wire[23:0] S_i2s_audio_left_data;
    wire[23:0] S_i2s_audio_right_data;
    wire       S_key_edid_read_trig;

//**********************  video stream input  ***************************
//如果是输入RGB时序，那么转为stream时序，否则仅对信号打一个节拍
//---- 视频输入打拍寄存器 ----
// 把 RGB/DE/VS/USER/VALID/LAST/DATA 各延迟 1~2 拍，用于做边沿检测和时序对齐。
    reg       I_video_in_de_r1;
    reg       I_video_in_vs_r1;
    reg       I_video_in_user_r1,I_video_in_user_r2;
    reg       I_video_in_valid_r1,I_video_in_valid_r2;
    reg       I_video_in_last_r2;
    reg[23:0] I_video_in_data_r1,I_video_in_data_r2;
    reg       O_video_in_ready_r;
    reg       vs_start;
  
//---- DE/VS 一级打拍 ----
// 先无条件各延迟一拍，后面的模块用它们的延后值做边沿检测（DE 下降沿=一行结束，VS 上升沿=一帧开始）。
    always @(posedge I_pixel_clk)begin
    	I_video_in_de_r1 <= I_video_in_de;
    	I_video_in_vs_r1 <= I_video_in_vs;
    end
      
//---- 视频时序转换（RGB 时序 -> stream 时序） ----
// 复位时把所有输出寄存器清零；I_video_rgb_enable=1 时从 DE/VS 组合出 stream 的 last/valid/user 并寄存数据；
// =0 时输入已是 stream 时序，只做纯打拍透传（VALID/LAST/USER/DATA 各延后一拍）。
    always @(posedge I_pixel_clk or posedge I_rst )begin
    	if(I_rst)begin
        	I_video_in_last_r2  <= 1'b0;
            I_video_in_valid_r1 <= 1'b0;
            I_video_in_data_r1  <= 24'd0;
            I_video_in_user_r1  <= 1'b0;
            I_video_in_valid_r2 <= 1'b0;
            I_video_in_data_r2  <= 24'd0;
            I_video_in_user_r2  <= 1'b0;
        end    
    	else if(I_video_rgb_enable == 1'b1)begin
        	I_video_in_last_r2  <= ~I_video_in_de & I_video_in_de_r1; //产生stream video last 延迟于数据输入2拍
            I_video_in_valid_r1 <= I_video_in_de;//I_video_in_valid延迟1拍
            I_video_in_data_r1  <= I_video_in_data;//I_video_in_data延迟1拍
            I_video_in_user_r1  <= ~I_video_in_user_r1 & vs_start & I_video_in_de;//I_video_in_user延迟1拍
            
            I_video_in_valid_r2 <= I_video_in_valid_r1;//I_video_in_valid对输入信号延迟2拍，以和I_video_in_last_r2信号配套同步
            I_video_in_data_r2  <= I_video_in_data_r1; //I_video_in_data 对输入信号延迟2拍，以和I_video_in_last_r2信号配套同步
            I_video_in_user_r2  <= I_video_in_user_r1; //I_video_in_user 对输入信号延迟2拍，以和I_video_in_last_r2信号配套同步 
        end     
        else begin
        	I_video_in_last_r2  <= I_video_in_last; //I_video_in_last对输入信号直接寄存1次
            I_video_in_valid_r2 <= I_video_in_valid;//I_video_in_valid对输入信号直接寄存1次
            I_video_in_data_r2  <= I_video_in_data;//I_video_in_data对输入信号直接寄存1次
            I_video_in_user_r2  <= I_video_in_user;//I_video_in_user对输入信号直接寄存1次      
        end 
    end
    
//---- 帧起始标志 vs_start ----
// 检测 I_video_in_vs 的上升沿：置 1 后由下游在适当时机清 0，用于标记一帧的开始（发送核据此复位行场状态）。
    always @(posedge I_pixel_clk or posedge I_rst )begin
    	if(I_rst)
        	vs_start <= 1'b0;
    	else if(I_video_in_user_r1)//清除VS帧同步
        	vs_start <= 1'b0;
        else if(I_video_in_vs && I_video_in_vs_r1==1'b0)//当I_video_in_vs发生上升沿跳变代表一帧开始
            vs_start <= 1'b1;
    end    

//---- 音频通路：I2S 接收 ----
// 从外部 I2S 三线（BCLK/LRCK/DOUT）恢复出左右声道 24 bit 音频数据与 valid，工作在本模块的像素时钟域。
    I2S_receiver u_I2S_receiver(
        .I_clk              ( I_pixel_clk        ),
        .I_rst              ( I_rst              ),
  
        .I_i2s_BCLK         ( I_i2s_BCLK         ),
        .I_i2s_LRCK         ( I_i2s_LRCK         ),
        .I_i2s_DOUT         ( I_i2s_DOUT         ),
  
        .O_audio_valid      ( S_i2s_audio_valid      ),
        .O_audio_left_data  ( S_i2s_audio_left_data  ),
        .O_audio_right_data ( S_i2s_audio_right_data )
    );


//---- 音频通路：ACR 计算（Audio Clock Recovery） ----
// 统计两个音频采样之间经过了多少个像素时钟，得到 CTS；N=6144 对应 48 kHz 采样率、
// 发送核用 CTS/N 在接收端重建音频时钟。
    audio_arc_calculate#(
        .ACR_N         ( 6144 )
    )u_audio_arc_calculate(
        .I_clk         ( I_pixel_clk    ),
        .I_rst         ( I_rst          ),

        .I_audio_valid ( I_audio_valid  ),

        .O_acr_valid   ( S_acr_valid    ),
        .O_acr_cts     ( S_acr_cts      ),
        .O_acr_n       ( S_acr_n        )
    );


//---- 按键消抖与 EDID 读触发 ----
// 注意这里的复位接的是 PLL 的 lock（S_pll_lock），只有时钟锁定后才允许按键生效；
// 消抖后产生的单拍脉冲 S_key_edid_read_trig 作为一次 EDID 读取的启动信号。
    key_remove_shakes u_key_remove_shakes(
        .I_clk          ( I_pixel_clk ),
        .I_rst_n        ( S_pll_lock  ),
        .I_key_in       ( I_key_in    ),
        .O_key_trig_out ( S_key_edid_read_trig )
    );



//   video_source_test#(
//        .HTOTAL        ( 2200 ),
//        .HACTIVE       ( 1920 ),
//        .HFP           ( 88   ),
//        .HSA           ( 44   ),
//        .HBP           ( 148  ),
//        .VTOTAL        ( 1125 ),
//        .VACTIVE       ( 1080 ),
//        .VFP           ( 4    ),
//        .VSA           ( 5    ),
//        .VBP           ( 36   )
//    )U_video_source_test(
//        .I_clk         ( I_pixel_clk    ),
//        .I_rst         ( I_rst          ),

//        .I_tpg_trig_en ( 1'b1           ),

//        .O_video_user  ( I_video_in_user  ),
//        .O_video_valid ( I_video_in_valid ),
//        .O_video_last  ( I_video_in_last  ),
//        .O_video_data  ( I_video_in_data  ),
//        .I_video_ready ( O_video_in_ready )
//    );


//---- HDMI 1.4b 发送核（加密 IP） ----
// 参数按 720p60 配置：HTOTAL=1650、HSA=40、HFP=110、HBP=220、HACTIVE=1280、
// VTOTAL=750、VSA=5、VFP=5、VBP=20、VACTIVE=720；VIDEO_TPG=Disable（不使用内部测试图），
// VIDEO_FORMAT=RGB、AUDIO_SAMPLE_RATE=48K、IIC_SCL_DIV=125（DDC 时钟分频）。
// 它把视频/音频/ACR 一起做 TMDS 编码，输出 4 组 10 bit 码字给物理层。
    hdmi_1_4b_transmitter_core_wrapper#(
        .DEVICE                 ( "PH1P"   ),

		.HTOTAL                 ( 1650     ),
        .HSA                    ( 40       ),
        .HFP                    ( 110      ),
        .HBP                    ( 220      ),
        .HACTIVE                ( 1280     ),
        .VTOTAL                 ( 750      ),
        .VSA                    ( 5        ),
        .VFP                    ( 5        ),
        .VBP                    ( 20       ),
        .VACTIVE                ( 720      ),

		.VIDEO_VIC              ( 4        ),

        .VIDEO_TPG              ( "Disable" ),
        .VIDEO_FORMAT           ( "RGB"    ),

        .AUDIO_SAMPLE_RATE      ( "48K"    ),
        
        .IIC_SCL_DIV            ( 125      )
    )u_hdmi_1_4b_transmitter_core_wrapper(
        .I_pixel_clk        ( I_pixel_clk        ),
        .I_rst              ( I_rst              ),

        .I_edid_read_trig   ( I_edid_read_trig   ),
        .O_edid_read_valid  ( O_edid_read_valid  ),
        .O_edid_read_data   ( O_edid_read_data   ),

        .I_axis_s_user      ( I_video_in_user_r2      ),
        .I_axis_s_valid     ( I_video_in_valid_r2     ),
        .I_axis_s_last      ( I_video_in_last_r2      ),
        .I_axis_s_data      ( I_video_in_data_r2      ),
        .O_axis_s_ready     ( O_video_in_ready     ),

        .I_audio_valid      ( I_audio_valid      ),
        .I_audio_left_data  ( I_audio_left_data  ),
        .I_audio_right_data ( I_audio_right_data ),

        .I_acr_valid        ( S_acr_valid        ),
        .I_acr_cts          ( S_acr_cts          ),
        .I_acr_n            ( S_acr_n            ),

        .O_video_locked     ( ),

//---- DDC/I2C（读显示器 EDID）与视频流连接 ----
        .O_ddc_scl          ( O_ddc_scl          ),
        .IO_ddc_sda         ( IO_ddc_sda         ),

        .O_ch0_tmds_data    ( S_ch0_tmds_data    ),
        .O_ch1_tmds_data    ( S_ch1_tmds_data    ),
        .O_ch2_tmds_data    ( S_ch2_tmds_data    ),
        .O_clk_tmds_data    ( S_clk_tmds_data    )
    );


//---- TMDS 物理层 ----
// 把 4 组 10 bit 码字交给 hdmi_phy_wrapper 串行化并做差分输出；DEVICE 选 PH1P 对应安路 PH1P 器件原语。
    hdmi_phy_wrapper  #(
        .DEVICE ( "PH1P" )  //"EF2","EF3","EF4","SF1","EG","PH1A","PH1P","DR1"
    )u_hdmi2phy_wrapper(
        .I_pixel_clk        ( I_pixel_clk     ),
        .I_serial_clk       ( I_serial_clk    ),
        .I_rst              ( I_rst           ),

        .I_tmds_channel_0   ( S_ch0_tmds_data ),
        .I_tmds_channel_1   ( S_ch1_tmds_data ),
        .I_tmds_channel_2   ( S_ch2_tmds_data ),
        .I_tmds_channel_clk ( S_clk_tmds_data ),

        .O_tmds_ch0_p       ( O_tmds_ch0_p    ),
        .O_tmds_ch1_p       ( O_tmds_ch1_p    ),
        .O_tmds_ch2_p       ( O_tmds_ch2_p    ),
        .O_tmds_clk_p       ( O_tmds_clk_p    )
    );


endmodule
