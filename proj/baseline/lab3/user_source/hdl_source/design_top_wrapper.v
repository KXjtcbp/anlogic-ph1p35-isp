//=============================================================================
// [HDR-2026-10-09] 文件      : design_top_wrapper.v
// 模块      : design_top_wrapper
// 功能      : 整板顶层：把 MIPI 摄像头 → RAW 解包 → ISP → 视频缓存 → HDMI 输出整条链路接起来，并管理时钟/复位、按键、摄像头 I2C 配置。
// 数据通路  : MIPI 差分对 → u_mipi_dphy_rx_* → csi_unpacket_2lane(字节流) → raw10_unpacket_2lane(40bit/4像素 RAW10) → uial2axis(AXI4-Stream) → isp_top(ISP) → video_in/video_out(DDR2 帧缓存) → hdmi_tx → TMDS 差分对
// 时钟/复位 : 主输入 I_sys_clk = 50 MHz；摄像头接收域 S_csi_rx_clk；像素/HDMI 域 HDMI_PIXEL_CLK；按键/配置域 24 MHz。各域间靠单 bit 翻转协议或同步器跨域。复位 I_rst_n 低有效。
// 依赖      : isp_top / csi_unpacket_2lane / raw10_unpacket_2lane / uial2axis / video_in / video_out / hdmi_tx / hdmi_phy_wrapper / uicfgcs500_720p / key_mode_ctrl / u_ph1p35_324_ddr_wrapper 等
// 综合/实现 : ■ 本文件是时序约束 camera_to_dsi_display.sdc 的引用对象：约束里按层次路径点名了 u_PLL/…/u_PH1P_PHY_PLL.clkc[0/1/4/5]、u_mipi_dphy_rx_ph1p_mipiio_wrapper/…/o_fabric_div4_8_clk、u_ph1p35_324_ddr_wrapper/u_ddr2/{ddr_clk,usr_clk} —— 这些实例名禁止改名。
//           ■ 12 个顶层端口被 pin.adc 分派引脚（I_sys_clk/I_rst_n/O_cam_scl/IO_cam_sda/O_cam_24m/O_cam_rst/I_button[1:0]/O_screen_pwm/O_tmds_ch*_p/O_tmds_clk_p），同样禁止改名。
//           ■ (:80-83,:91-94) 8 根观测 wire 带 (*MARK_DEBUG = "TRUE"*)，供 TD 的 ChipWatcher 抓波形；不要删除这些属性。
//-----------------------------------------------------------------------------
// 修改记录  :
//   2026-09-27  [230f479] 导入官方 lab3 基线并把工程路径改为本地路径
//   2026-09-27  [6440c52] 接入自研 RGB 点运算算法集与按键模式切换（新增 S_algo_mode 跨域链路）
//   2026-09-27  [c8e7b96] 新增 SHOW_DEBUG 参数，把 DDR 状态直接画进 HDMI 画面
//   2026-10-03  [043f927] 修复跨时钟域违例（SWNS -4.416ns）与 DSP 用满（40/40）
//   2026-10-03  [364d1bf] 算法模式改为单 bit 翻转跨域协议，消除残留 0.085ns 违例
//   2026-10-08  （未提交）给 8 根观测 wire 加 (*MARK_DEBUG = "TRUE"*)，以便 ChipWatcher 抓 RAW10/ISP 波形
//   2026-10-09  （未提交）标识符改名 10 处（S_ae/S_ag/I_ae/I_ag 等），无逻辑改动
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑，见 E:\FPGA\_analysis\rename_report.txt）
//=============================================================================


module design_top_wrapper (
    input wire        I_sys_clk,
    input wire        I_rst_n,
      
    output wire       O_cam_scl,
    inout  wire       IO_cam_sda,
    output wire       O_cam_24m,
    output wire       O_cam_rst,
      
    inout wire [3:0]  I_button,

    // [HDR-2026-10-10] 板上乒乓开关 SW1-SW4
    //   手册《新HX1P35A开发板手册-HDL版2604》P396-404：
    //     手册原文：「SW1-SW4 是作为与 FPGA 的 IO 输入信号，拨上为"1"，拨下为"0"」
    //   ★2026-10-10 实测极性相反：【拨下 = 逻辑 1】【拨上 = 逻辑 0】（用 2×2 开关对照图确认）
    //     引脚 SW1=A4 / SW2=B4 / SW3=E11 / SW4=D11
    //   SW1(A4) = 黑电平扣除旁路：1 = 直通（老行为），0 = 启用扣除
    //   SW2(B4) = S 曲线旁路    ：1 = 直通（老行为），0 = 启用 S 曲线
    //   SW3(E11) = 传感器灰度递增测试图：★2026-10-10b 起**已退役**（实测该引脚恒为逻辑 0，
    //             接上后画面会永久变成灰度斜坡）⇒ 顶层硬接 1'b0，传感器恒为正常图像。
    //             该引脚不再控制任何功能，只作为 LED3 的电平指示使用。
    //   SW4(D11) = 模拟增益档：拨上 = 11.25×（0x1f/0x2d）；拨下/复位 = 4.000×（0x0f/0x20）
    //   ★SW4 只在开机初始化表里下发一次 ⇒ 拨动后需复位或断电重启才生效；SW1/SW2 是实时的。
    input wire [3:0]  I_switch,

    // ---- [HDR-2026-10-10b] 板载 LED1..LED4（D10/E10/C6/D6，高电平点亮）----
    //   直连四个拨动开关的同步后电平：O_led[0]←SW1 … O_led[3]←SW4。
    //   用途：把"FPGA 到底把这个引脚读成几"变成肉眼可见（拨开关时 LED 实时变化，无需重编译）。
    //   实测极性（与手册相反）：开关拨下 = 逻辑 1 = 灯亮；拨上 = 逻辑 0 = 灯灭。
    output wire [3:0] O_led,

    output wire       O_screen_pwm,
    output wire       O_tmds_ch0_p,
    output wire       O_tmds_ch1_p,
    output wire       O_tmds_ch2_p,
    output wire       O_tmds_clk_p,

    inout wire        IO_rx_clk_pad_n, 
    inout wire        IO_rx_clk_pad_p, 
    inout wire[3:0]   IO_rx_data_pad_n,
    inout wire[3:0]   IO_rx_data_pad_p,

    output wire[12:0] ddr_addr,
    output wire[ 1:0] ddr_ba,
    output wire[ 0:0] ddr_cke,
    output wire[ 0:0] ddr_odt,
    output wire[ 0:0] ddr_cs_n,
    output wire       ddr_ras_n,
    output wire       ddr_cas_n,
    output wire       ddr_we_n,
    output wire[ 0:0] ddr_ck_p,
    output wire[ 0:0] ddr_ck_n,
    inout wire[1:0]   ddr_dm,
    inout wire[15:0]  ddr_dq,
    inout wire[1:0]   ddr_dqs_p,
    inout wire[1:0]   ddr_dqs_n   
);


    wire        	S_100m_clk;
    wire        	S_24m_clk;
    wire        	S_aux_50m_clk;
	wire        	S_10m_clk;
		
	wire        	S_pll_lock;
    wire        	S_rst_n;
	
	// [OUR ALGO] 自研算法模式选择（2 bit = 4 种模式），由按键 key_mode_ctrl 产生
	//   跨时钟域协议：S_algo_mode 只在 24 MHz 域内有效，**不要**把它直接送到
	//   其他时钟域（实测会把 Setup WNS 从 +0.103ns 打到 -4.416ns）。
	//   跨域只走 S_algo_mode_tgl 这 1 bit 翻转信号，目标域各自同步并本地计数。
	wire [2:0]  	S_algo_mode;
	wire        	S_algo_mode_chg;
	wire        	S_algo_mode_tgl;
	wire        	S_algo_mode_wrap;      // ★跨域用★：单 bit 翻转
	
	wire [15:0] 	S_exposure_time;
    wire [15:0] 	S_analog_gain;
    wire 			S_cam_cfg_done;
    wire 			S_ae_cfg_done;
    wire 			S_ae_req; 
	
	wire        	S_csi_rx_clk;  
    wire        	S_hs_rx_valid;  
    wire[15:0]  	S_hs_rx_data;   
	wire[1:0]   	S_lane_error;
	
	wire        	S_csi_frame_start;       
	wire        	S_csi_frame_end;         
	wire        	S_csi_valid;             
	wire[31:0]  	S_csi_data;  
		
	wire        	S_raw10_frame_start; 
	wire        	S_raw10_frame_end;   
	wire        	S_raw10_valid;       
	wire [39:0] 	S_raw10_data;
		
	(*MARK_DEBUG = "TRUE"*) wire 			S_axis_tlast;  
	(*MARK_DEBUG = "TRUE"*) wire 			S_axis_tuser;  
	(*MARK_DEBUG = "TRUE"*) wire [39:0]		S_axis_tdata;  
	(*MARK_DEBUG = "TRUE"*) wire 			S_axis_tvalid; 
	
	wire [39:0]		S_raw_tdata ;
	wire			S_raw_tlast ;
	wire 			S_raw_tvalid;
	wire 			S_raw_tuser ;
	
	wire			S_ISP_O_tready;
	(*MARK_DEBUG = "TRUE"*) wire [127:0]	S_ISP_O_tdata ;
	(*MARK_DEBUG = "TRUE"*) wire 			S_ISP_O_tlast ;
	(*MARK_DEBUG = "TRUE"*) wire 			S_ISP_O_tuser ;
	(*MARK_DEBUG = "TRUE"*) wire 			S_ISP_O_tvalid; 
	

    wire        S_ddr_clk;
    wire        S_hdmi_pixel_clk;
    wire        S_hdmi_serial_clk;
    wire        S_hdmi_rst_n;
    wire        S_video_out_rst_n;


    wire        S_vi_128b_frame_start;
    wire        S_vi_128b_valid;      
    wire[127:0] S_vi_128b_data;    
    
    wire        S_video_out_rd_busy;
    wire        S_video_in_wr_busy; 
    wire[1:0]   S_video_out_rp;     

    wire        S_ddr_user_wr_en;       
    wire        S_ddr_user_rd_en;       
    wire[24:0]  S_ddr_user_addr;        
    wire[127:0] S_ddr_user_wr_data;     
    wire        S_ddr_user_ready;       
    wire        S_ddr_user_rd_valid;    
    wire[127:0] S_ddr_user_rd_data;     

    wire        S_vi_ddr_wr_en;   
    wire[24:0]  S_vi_ddr_wr_addr; 
    wire[127:0] S_vi_ddr_wr_data;
    wire        S_vi_ddr_wr_ready;

    wire        S_vo_ddr_rd_en;   
    wire[24:0]  S_vo_ddr_rd_addr; 
    wire        S_vo_ddr_rd_ready;
    wire        S_vo_dbg_fifo_rst;
    wire        S_vo_dbg_ddr_rd_valid;
    wire        S_vo_dbg_fifo_rd_en;
    wire        S_vo_dbg_fifo_empty;

    wire        S_init_calib_complete; 
    wire[24:0]  S_mc_app_addr;          
    wire[2:0]   S_mc_app_cmd;           
    wire        S_mc_app_en;            
    wire[127:0] S_mc_app_wdf_data;      
    wire        S_mc_app_wdf_end;       
    wire[15:0]  S_mc_app_wdf_mask;      
    wire        S_mc_app_wdf_wren;      
    wire[127:0] S_mc_app_rd_data;       
    wire        S_mc_app_rd_data_end;   
    wire        S_mc_app_rd_data_valid; 
    wire        S_mc_app_rdy;           
    wire        S_mc_app_wdf_rdy;       
    wire        S_mc_dbg_fifo_afull;
    wire        S_mc_dbg_app_rdy;
    wire        S_mc_dbg_wdf_rdy;
    wire        S_mc_dbg_cmd_pop;

    wire        S_hdmi_vsync;
    wire        S_hdmi_hsync;
    wire        S_hdmi_de;
    wire        S_hdmi_user;
    wire        S_hdmi_last;
    wire        S_video_out_vsync;
    wire        S_hdmi_window_rd_en;
    wire        S_hdmi_out_vsync;
    wire        S_hdmi_out_hsync;
    wire        S_hdmi_out_de;
    wire[23:0]  S_hdmi_out_data;

    wire[23:0]  S_video_rd_data;
    reg         S_dbg_raw_seen;
    reg         S_dbg_isp_seen;
    reg         S_dbg_ddr_wr_seen;
    reg         S_dbg_ddr_rd_seen;
    reg         S_dbg_cam_cfg_seen;
    reg         S_dbg_hs_seen;
    reg         S_dbg_csi_seen;
    reg         S_dbg_raw10_seen;
    reg         S_dbg_isp_fs_seen;
    reg         S_dbg_isp_valid_seen;
    reg         S_dbg_ddr_req_seen;
    reg         S_dbg_ddr_ready_seen;
    reg [1:0]   S_dbg_raw_seen_sync;
    reg [1:0]   S_dbg_isp_seen_sync;
    reg [1:0]   S_dbg_ddr_wr_seen_sync;
    reg [1:0]   S_dbg_ddr_rd_seen_sync;
    reg [1:0]   S_dbg_cam_cfg_seen_sync;
    reg [1:0]   S_dbg_hs_seen_sync;
    reg [1:0]   S_dbg_csi_seen_sync;
    reg [1:0]   S_dbg_raw10_seen_sync;
    reg [1:0]   S_dbg_isp_fs_seen_sync;
    reg [1:0]   S_dbg_isp_valid_seen_sync;
    reg [1:0]   S_dbg_ddr_req_seen_sync;
    reg [1:0]   S_dbg_ddr_ready_seen_sync;
    reg         S_dbg_video_nonzero_seen;
    reg         S_dbg_rd_req_seen;
    reg         S_dbg_rd_valid_seen;
    reg         S_dbg_rd_nonzero_seen;
    reg [1:0]   S_dbg_rd_req_seen_sync;
    reg [1:0]   S_dbg_rd_valid_seen_sync;
    reg [1:0]   S_dbg_rd_nonzero_seen_sync;
    reg         S_dbg_mc_init_seen;
    reg         S_dbg_mc_app_rdy_seen;
    reg         S_dbg_mc_wdf_rdy_seen;
    reg         S_dbg_mc_cmd_pop_seen;
    reg [1:0]   S_dbg_mc_init_seen_sync;
    reg [1:0]   S_dbg_mc_app_rdy_seen_sync;
    reg [1:0]   S_dbg_mc_wdf_rdy_seen_sync;
    reg [1:0]   S_dbg_mc_cmd_pop_seen_sync;
    wire[3:0]   S_hdmi_debug_status;
    wire        S_lane_error_any;


    assign O_screen_pwm = 1'b1;
    assign S_video_out_vsync = ~S_hdmi_vsync;
	
	
    assign S_rst_n 		= S_pll_lock;
    assign S_hdmi_rst_n = S_pll_lock;

    always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_raw_seen <= 1'b0;
        else if(S_raw10_frame_start | S_axis_tvalid)
            S_dbg_raw_seen <= 1'b1;
    end

    always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_isp_seen <= 1'b0;
        else if(S_ISP_O_tuser | S_ISP_O_tvalid)
            S_dbg_isp_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_ddr_wr_seen <= 1'b0;
        else if(S_vi_ddr_wr_en)
            S_dbg_ddr_wr_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_ddr_rd_seen <= 1'b0;
        else if(S_ddr_user_rd_valid)
            S_dbg_ddr_rd_seen <= 1'b1;
    end

    always @(posedge S_24m_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_cam_cfg_seen <= 1'b0;
        else if(S_cam_cfg_done)
            S_dbg_cam_cfg_seen <= 1'b1;
    end

    always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_hs_seen <= 1'b0;
        else if(S_hs_rx_valid)
            S_dbg_hs_seen <= 1'b1;
    end

    always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_csi_seen <= 1'b0;
        else if(S_csi_frame_start | S_csi_valid)
            S_dbg_csi_seen <= 1'b1;
    end

    always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_raw10_seen <= 1'b0;
        else if(S_raw10_frame_start | S_raw10_valid)
            S_dbg_raw10_seen <= 1'b1;
    end

    always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_isp_fs_seen <= 1'b0;
        else if(S_ISP_O_tuser)
            S_dbg_isp_fs_seen <= 1'b1;
    end

    always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_isp_valid_seen <= 1'b0;
        else if(S_ISP_O_tvalid)
            S_dbg_isp_valid_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_ddr_req_seen <= 1'b0;
        else if(S_vi_ddr_wr_en)
            S_dbg_ddr_req_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_ddr_ready_seen <= 1'b0;
        else if(S_ddr_user_ready)
            S_dbg_ddr_ready_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_video_out_rst_n) begin
        if(!S_video_out_rst_n)
            S_dbg_rd_req_seen <= 1'b0;
        else if(S_video_out_vsync)
            S_dbg_rd_req_seen <= 1'b0;
        else if(S_vo_ddr_rd_en)
            S_dbg_rd_req_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_video_out_rst_n) begin
        if(!S_video_out_rst_n)
            S_dbg_rd_valid_seen <= 1'b0;
        else if(S_video_out_vsync)
            S_dbg_rd_valid_seen <= 1'b0;
        else if(S_ddr_user_rd_valid)
            S_dbg_rd_valid_seen <= 1'b1;
    end

    always @(posedge S_hdmi_pixel_clk or negedge S_video_out_rst_n) begin
        if(!S_video_out_rst_n)
            S_dbg_rd_nonzero_seen <= 1'b0;
        else if(S_video_out_vsync)
            S_dbg_rd_nonzero_seen <= 1'b0;
        else if(S_hdmi_window_rd_en && (S_video_rd_data != 24'd0))
            S_dbg_rd_nonzero_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_mc_init_seen <= 1'b0;
        else if(S_init_calib_complete)
            S_dbg_mc_init_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_mc_app_rdy_seen <= 1'b0;
        else if(S_mc_dbg_app_rdy)
            S_dbg_mc_app_rdy_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_mc_wdf_rdy_seen <= 1'b0;
        else if(S_mc_dbg_wdf_rdy)
            S_dbg_mc_wdf_rdy_seen <= 1'b1;
    end

    always @(posedge S_ddr_clk or negedge S_rst_n) begin
        if(!S_rst_n)
            S_dbg_mc_cmd_pop_seen <= 1'b0;
        else if(S_mc_dbg_cmd_pop)
            S_dbg_mc_cmd_pop_seen <= 1'b1;
    end

    always @(posedge S_hdmi_pixel_clk or negedge S_hdmi_rst_n) begin
        if(!S_hdmi_rst_n) begin
            S_dbg_cam_cfg_seen_sync <= 2'b00;
            S_dbg_hs_seen_sync      <= 2'b00;
            S_dbg_csi_seen_sync     <= 2'b00;
            S_dbg_raw10_seen_sync   <= 2'b00;
            S_dbg_raw_seen_sync    <= 2'b00;
            S_dbg_isp_seen_sync    <= 2'b00;
            S_dbg_ddr_wr_seen_sync <= 2'b00;
            S_dbg_ddr_rd_seen_sync <= 2'b00;
            S_dbg_isp_fs_seen_sync  <= 2'b00;
            S_dbg_isp_valid_seen_sync <= 2'b00;
            S_dbg_ddr_req_seen_sync <= 2'b00;
            S_dbg_ddr_ready_seen_sync <= 2'b00;
            S_dbg_video_nonzero_seen <= 1'b0;
            S_dbg_rd_req_seen_sync <= 2'b00;
            S_dbg_rd_valid_seen_sync <= 2'b00;
            S_dbg_rd_nonzero_seen_sync <= 2'b00;
            S_dbg_mc_init_seen_sync <= 2'b00;
            S_dbg_mc_app_rdy_seen_sync <= 2'b00;
            S_dbg_mc_wdf_rdy_seen_sync <= 2'b00;
            S_dbg_mc_cmd_pop_seen_sync <= 2'b00;
        end
        else begin
            S_dbg_cam_cfg_seen_sync <= {S_dbg_cam_cfg_seen_sync[0], S_dbg_cam_cfg_seen};
            S_dbg_hs_seen_sync      <= {S_dbg_hs_seen_sync[0],      S_dbg_hs_seen};
            S_dbg_csi_seen_sync     <= {S_dbg_csi_seen_sync[0],     S_dbg_csi_seen};
            S_dbg_raw10_seen_sync   <= {S_dbg_raw10_seen_sync[0],   S_dbg_raw10_seen};
            S_dbg_raw_seen_sync    <= {S_dbg_raw_seen_sync[0],    S_dbg_raw_seen};
            S_dbg_isp_seen_sync    <= {S_dbg_isp_seen_sync[0],    S_dbg_isp_seen};
            S_dbg_ddr_wr_seen_sync <= {S_dbg_ddr_wr_seen_sync[0], S_dbg_ddr_wr_seen};
            S_dbg_ddr_rd_seen_sync <= {S_dbg_ddr_rd_seen_sync[0], S_dbg_ddr_rd_seen};
            S_dbg_isp_fs_seen_sync  <= {S_dbg_isp_fs_seen_sync[0],  S_dbg_isp_fs_seen};
            S_dbg_isp_valid_seen_sync <= {S_dbg_isp_valid_seen_sync[0], S_dbg_isp_valid_seen};
            S_dbg_ddr_req_seen_sync <= {S_dbg_ddr_req_seen_sync[0], S_dbg_ddr_req_seen};
            S_dbg_ddr_ready_seen_sync <= {S_dbg_ddr_ready_seen_sync[0], S_dbg_ddr_ready_seen};
            S_dbg_rd_req_seen_sync <= {S_dbg_rd_req_seen_sync[0], S_dbg_rd_req_seen};
            S_dbg_rd_valid_seen_sync <= {S_dbg_rd_valid_seen_sync[0], S_dbg_rd_valid_seen};
            S_dbg_rd_nonzero_seen_sync <= {S_dbg_rd_nonzero_seen_sync[0], S_dbg_rd_nonzero_seen};
            S_dbg_mc_init_seen_sync <= {S_dbg_mc_init_seen_sync[0], S_dbg_mc_init_seen};
            S_dbg_mc_app_rdy_seen_sync <= {S_dbg_mc_app_rdy_seen_sync[0], S_dbg_mc_app_rdy_seen};
            S_dbg_mc_wdf_rdy_seen_sync <= {S_dbg_mc_wdf_rdy_seen_sync[0], S_dbg_mc_wdf_rdy_seen};
            S_dbg_mc_cmd_pop_seen_sync <= {S_dbg_mc_cmd_pop_seen_sync[0], S_dbg_mc_cmd_pop_seen};
            if(S_hdmi_window_rd_en && (S_video_rd_data != 24'd0))
                S_dbg_video_nonzero_seen <= 1'b1;
        end
    end

    assign S_lane_error_any = |S_lane_error;

    assign S_vo_dbg_fifo_rst = 1'b0;
    assign S_vo_dbg_ddr_rd_valid = 1'b0;
    assign S_vo_dbg_fifo_rd_en = 1'b0;
    assign S_vo_dbg_fifo_empty = 1'b0;
    assign S_mc_dbg_fifo_afull = 1'b0;
    assign S_mc_dbg_app_rdy = 1'b0;
    assign S_mc_dbg_wdf_rdy = 1'b0;
    assign S_mc_dbg_cmd_pop = 1'b0;

    assign S_hdmi_debug_status = {
        (|S_ddr_user_rd_data),
        S_ddr_user_rd_valid,
        S_vo_ddr_rd_en,
        S_vi_ddr_wr_en
    };
	
	assign O_cam_rst 	= 1'b1;
    assign O_cam_24m 	= S_24m_clk;
	
	
	
	
    PLL u_PLL(
        .refclk      ( I_sys_clk         ),
        .reset    	 ( ~I_rst_n          ),
        
        .clk0_out    ( S_100m_clk        ),
        .clk1_out    ( S_24m_clk         ),

        .clk4_out    ( S_hdmi_pixel_clk  ),
        .clk5_out    ( S_hdmi_serial_clk ),

        .lock        ( S_pll_lock        )

    );


	
	//==========================================================================
	// [OUR ALGO] 按键算法模式切换
	//   K1..K4 = I_button[0..3] = D5 / A9 / B9 / C7（带内部上拉，按下为低电平）
	//   必须挂在 24 MHz 慢时钟域：key_remove_shakes 内部固定计数 100000，
	//   24 MHz 下约 4.2 ms（正常消抖）
	//   K1/K2/K3/K4 分别直选 MODE0 原图 / MODE1 灰度 / MODE2 伪彩热力图 / MODE4 卡通化（不再循环）；
	//   长按任意键 >=1s -> MODE3（5 段彩条诊断模式）。
	//   ★MODE4 卡通化是评分细则点名的功能（基础扩展项(1) 视频图像风格化处理），必须一键直达。★
	//   注意：I_button 输入引脚是 inout（inout wire [3:0] I_button），
	//        这里只读不驱动，不会和 ae_set 的 I_btn 冲突。
	//==========================================================================
	key_mode_ctrl u_key_mode_ctrl (
		.I_clk      ( S_24m_clk        ),
		.I_rst_n    ( S_rst_n          ),
		.I_key_n    ( I_button        ),   // K1-K4 四键直选 + 长按（bit0=K1/D5, bit1=K2/A9, bit2=K3/B9, bit3=K4/C7）
		.O_mode     ( S_algo_mode      ),
		.O_mode_chg ( S_algo_mode_chg  ),
		.O_mode_tgl ( S_algo_mode_tgl  ),
		.O_mode_wrap( S_algo_mode_wrap )   // ★跨域只走这 1 bit★
	);

  

  //--------------------------------------------------------------------------
  // [HDR-2026-10-12] 原厂的 ae_set.v（手动按键步进器）在此**不再例化**。
  //   原因：它本来就是个"按一下 +1 档"的手动工具（`I_btn` 一直硬接 4'b1111 全松，
  //   等于死代码），而且文件头自己标注了 3 处隐患（复位曝光 3000 超手册上限 1990、
  //   复位后 r_exposure == r_exposure_set ⇒ r_ae_req 永不置位、按键会把非法曝光写进传感器）。
  //   替代实现 ae_ctrl.v 见下面「SW3/SW4」一节之后；ae_set.v 文件仍留在工程里
  //   （camera_to_dsi_display.al 不动它），需要时随时可以改回来。
  //--------------------------------------------------------------------------
  
    // ---- [HDR-2026-10-10] SW3 / SW4（24MHz 域 2 级同步）----------------------------
    //   实测极性（与手册相反）：拨下 = 逻辑 1，拨上 = 逻辑 0。
    //   SW3：★已退役（2026-10-10b）。原设计是"拨上 = 打开传感器灰度递增测试图"，
    //        但实测拨 SW3 到任意一边、断电重启后画面仍是灰度斜坡 ⇒ E11 恒为逻辑 0
    //        ⇒ `~` 之后恒为 1 ⇒ 测试图常开。故顶层已硬接 I_test_pattern = 1'b0，
    //        此信号只用于 O_led[2] 的电平指示，不再进寄存器表。
    //   SW4：拨上 = 模拟增益高档 **15.750×**（0x1f/0x3f，手册表2-4 上限）；拨下/复位 = 低档 4.000×（厂商原值，安全默认）。
    //        只在开机初始化时下发 ⇒ 换档后需复位/断电重启。
    //   SW3：★2026-10-10c 起改作"数字增益"选择：拨上 = ×2.000（0x3e06=0x01）；拨下/复位 = ×1.000（0x00，复位默认）。
    //        同样只在开机初始化时下发。SW4上+SW3上 = 15.750×2.000 = 31.5×（比厂商原值 4.000× 亮 7.87×）。
    //        ★为什么要用它：曝光已顶满（1990 = 2×VTS−10），模拟增益的上限只有 15.750×，
    //          而 0x3e06/0x3e07 这两个数字增益寄存器全工程从未写过（停在默认 1.000×），
    //          它是手册允许的最后一根杠杆（上限 31.500×，见手册表2-5）。
    reg S_sw3_sync0, S_sw3_sync1;
    reg S_sw4_sync0, S_sw4_sync1;
    always @(posedge S_24m_clk or negedge S_rst_n) begin
        if(!S_rst_n) begin
            S_sw3_sync0 <= 1'b1;
            S_sw3_sync1 <= 1'b1;
            S_sw4_sync0 <= 1'b1;
            S_sw4_sync1 <= 1'b1;
        end
        else begin
            S_sw3_sync0 <= I_switch[2];
            S_sw3_sync1 <= S_sw3_sync0;
            S_sw4_sync0 <= I_switch[3];
            S_sw4_sync1 <= S_sw4_sync0;
        end
    end
    // ★2026-10-12 起 SW4 不再是"模拟增益选择"，它的作用改为 AE 使能★
    //   （原行 `wire S_gain_high = ~S_sw4_sync1;` 已删除，见下面 AE 一节的 S_ae_en）
    wire S_gain_digital = ~S_sw3_sync1;   // 复位默认 0 = ×1.000（复位默认，安全默认）

    //==========================================================================
    // [HDR-2026-10-12] ★自动曝光 AE★ —— SW4 从"模拟增益选择"改为"AE 使能"
    //==========================================================================
    //   为什么改 SW4：SW4 原来唯一的作用是选 4.000×/15.750×，而 AE 一旦上线，模拟增益
    //   就必须由闭环连续控制；何况 SW3（数字 ×2）× SW4（模拟 ×1/×4）的四档组合本来
    //   就只有 4 档、且必须断电重启才生效 —— 与评分标准里"光线剧烈变化时工作正常"
    //   这条直接冲突。改后 SW4 只当总开关：
    //     SW4 拨上（读到逻辑 0）⇒ S_ae_en = 1 ⇒ AE 闭环运行
    //     SW4 拨下 / 悬空       ⇒ S_ae_en = 0 ⇒ AE 冻结在当前档
    //   （复位默认 S_sw4_sync1 = 1 ⇒ S_ae_en = 0，安全默认，绝不会一上电就乱动。）
    //
    //   ★首次烧录后画面会比现在暗约 1/4，这是预期行为、不是坏了★：
    //     上电默认 = 模拟 {0x0F,0x20} = 4.000× × 数字（SW3 上）2.000× = 8.000×，
    //     而改之前 SW4上+SW3上 = 15.750 × 2.000 = 31.500×。
    //     AE 会在约 0.5s（30 帧）内把模拟增益爬回 15.750×，画面随之变亮。
    //     把 SW4 拨下等 1 秒再拨上，可以看到 AE 重新爬升的全过程。
    //
    //   ★统计点为什么在 isp_top 里★：见 isp_top.v 的 ae_stat 例化处 —— 它挂在 awb
    //     的输入侧（去马赛克之后、白平衡与 S 曲线之前），保证 AE 与 AWB 解耦、
    //     且拨 SW2 开关 S 曲线不会让 AE 的目标亮度漂移。
    //==========================================================================
    wire        S_ae_en = ~S_sw4_sync1;   // 复位默认 S_sw4_sync1 = 1 ⇒ S_ae_en = 0（冻结）

    // ae_stat 的全部输出（60MHz ISP 域，准静态）
    wire [39:0] S_ae_stat_lsum;
    wire [31:0] S_ae_stat_pix;
    wire [31:0] S_ae_stat_hi;
    wire [31:0] S_ae_stat_lo;
    wire        S_ae_stat_tgl;

    // 准静态多 bit CDC：数据每帧只变一次并保持约 16.7ms，本域打 1 拍即可。
    // 采样时刻由 ae_ctrl 内部对 S_ae_stat_tgl 做 2 级同步 + 边沿检测决定，
    // 比数据变化时刻晚 3 个 24MHz 周期（125ns），数据早已稳定。
    // （同步链本身在 ae_ctrl 里；这里只做"把 60MHz 域的组合输出落到本域寄存器"。）
    reg [39:0] S_ae_lsum_r;
    reg [31:0] S_ae_pix_r, S_ae_hi_r, S_ae_lo_r;
    always @(posedge S_24m_clk or negedge S_rst_n) begin
        if (!S_rst_n) begin
            S_ae_lsum_r <= 40'd0;
            S_ae_pix_r  <= 32'd0;
            S_ae_hi_r   <= 32'd0;
            S_ae_lo_r   <= 32'd0;
        end
        else begin
            S_ae_lsum_r <= S_ae_stat_lsum;
            S_ae_pix_r  <= S_ae_stat_pix;
            S_ae_hi_r   <= S_ae_stat_hi;
            S_ae_lo_r   <= S_ae_stat_lo;
        end
    end

    wire [7:0]  S_ae_meas;    // 回读：本帧实测帧均值（供 ChipWatcher / 将来的 OSD）
    wire [6:0]  S_ae_gi;      // 回读：当前增益索引 0..127
wire [33:0] S_osd_dbg2;   // [HDR-2026-10-12m] 第二行遥测：AE 决策链内部量
    wire [1:0]  S_ae_state;   // 0=等init表/表下载中 1=稳定计时中 2=闭环运行 3=冻结

    //--------------------------------------------------------------------------
    // ★★★ AE 目标亮度——现场唯一需要调的一个旋钮 ★★★
    //
    //   改下面这一行 -> 重综合（td_run_direct.ps1 syn_1 phy_1）-> 重烧
    //   即可改变 AE 稳定后的画面亮度。除这一行之外不需要动任何东西。
    //
    //   取值参考（数值是线性域的行均值，不是荧幕 E 4 行里的 M）：
    //     45~50  偏暗保高光，暗场景不会死黑
    //     60~62  折中（推荐宿舍现场）
    //     70     原值，偏亮
    //   实测参考：宿舍一窗一灯满增益也只能到 M≈24~35
    //             （此时 gi 顶格 7F）；开台灯照白墙可到 M≈60~85。
    //             目标比场景能达到的最高值还高时，AE 会一直顶格在最大增益——
    //             那是正确行为（照不够就加到最大），不是故障。
    //--------------------------------------------------------------------------
    localparam [7:0] AE_TARGET_MEAN = 8'd70;

    // [HDR-2026-10-14] LSC 镜头色彩暗角校正使能（0 = 开启校正，1 = 直通）
    //   用 localparam 而不是拨码开关：四个开关已全部占满，且这一步属于「标定」
    //   而不是「操作」，现场不需要手动切换；要对比就重综合一版。
    //   与 AE_TARGET_MEAN 同一种模式。
    localparam       LSC_BYPASS   = 1'b0;
    wire             S_lsc_bypass = LSC_BYPASS;

    ae_ctrl #(
        .TARGET_MEAN    (AE_TARGET_MEAN),   // ★目标帧均值 ≈70（8bit 线性亮度域）★
        .NOM_PIX        (32'd921600),   // 230400 拍 × 4 像素/拍
        .EXPOSURE_FIXED (16'd1990  ),   // 2×VTS−10；720p60 下再长会掉帧，曝光没有余量
        .GAIN_IDX_INIT  (7'd64     )    // = {0x0F,0x20} = 4.000×（厂商原值，安全默认）
    ) u_ae_ctrl (
        .I_clk          (S_24m_clk     ),
        .I_rst_n        (S_rst_n       ),
        .I_ae_en        (S_ae_en       ),
        .I_stat_tgl     (S_ae_stat_tgl ),   // 原始翻转信号，内部自带 2 级同步 + 边沿检测
        .I_luma_sum     (S_ae_lsum_r   ),
        .I_pix_cnt      (S_ae_pix_r    ),
        .I_hi_cnt       (S_ae_hi_r     ),
        .I_lo_cnt       (S_ae_lo_r     ),
        .I_cam_cfg_done (S_cam_cfg_done),
        .I_ae_cfg_done  (S_ae_cfg_done ),
        .O_ae_req       (S_ae_req      ),
        .O_exposure_time(S_exposure_time),
        .O_analog_gain  (S_analog_gain ),
        .O_meas_luma    (S_ae_meas     ),
        .O_gain_idx     (S_ae_gi       ),
              .O_dbg2         (S_osd_dbg2    ),
        .O_state        (S_ae_state    )
    );

    // ---- [HDR-2026-10-12k] 遥测总线：把 5 个诊断量打包送给 u_hdmi_mixer 显示 ----
    //   屏幕第 4 行（橙色）会显示：  AE <增益索引2位16进制> S<状态1位> M<实测均值2位> W<R增益4位> <B增益4位>
    //     例：AE7F S2 M46 W1000 1053   ⇒ 增益档 0x7F(=15.75x)、状态 2=闭环、
    //          本帧实测均值 0x46(=70)、AWB 的 R 增益 0x1000(=1.000x)、B 增益 0x1053(=1.020x)
    //   为什么要显示：AE 的 O_gain_idx / O_state / O_meas_luma 在此之前一根线都没引出来，
    //     导致"AE 到底动没动增益"只能靠亮度差反推（而画面里但凡有会动的东西就会误判）。
    //     AWB 那两个增益同理 —— 屏幕上偏色到底是"没算出来"还是"没施加"，
    //     只有把 in_r_r1/in_b_r1 拿出来看才能一刀切开。
    //   CDC：这 5 个量最慢 16.7ms 才变一次，远慢于 HDMI 像素时钟；两条时钟已由
    //     camera_to_dsi_display.sdc 的 set_clock_groups -asynchronous 隔离，
    //     hdmi_mixer 内部只用 2 级 FF 打拍，不做握手（与 I_debug_status 同待遇）。
    wire [19:0] S_wb_gain_r;   // awb 实际在用的 R 通道增益（20bit Q16，0x10000 = 1.000x）
    wire [19:0] S_wb_gain_b;   // awb 实际在用的 B 通道增益（20bit Q16）
    wire [48:0] S_osd_dbg = {S_ae_gi, S_ae_state, S_ae_meas,
                             S_wb_gain_r[19:4], S_wb_gain_b[19:4]};

    // ---- [HDR-2026-10-11i] SW1/SW2 同步器声明提前到此 ----------------
    //   因为下面 S_gain_applied 要比较 {S_sw1_sync1,...,S_sw4_sync1}；它们的 always 块仍在后部 SW1/SW2 那一节。
    reg S_sw1_sync0, S_sw1_sync1;
    reg S_sw2_sync0, S_sw2_sync1;

    // ---- [HDR-2026-10-10d] 运行时增益下发：拨开关不再需要断电重启 --------------
    //   根因（SW3/SW4 拨了没反应）：init 表只在复位/上电后由 uicfgcs500_720p 的 FSM
    //   走一遍（见 uicfgcs500_720p.v:60-91），之后 reg_index 停住不动 ⇒ 开机后再拨
    //   SW3/SW4 根本不会产生任何 I2C 写 ⇒ 画面当然不变。
    //   解决：复用早已存在、并且已经用 ModelSim 端到端验证过的 **AE 表运行时下发通路**
    //   （AE 表现在 8 条：曝光 3e00/01/02、模拟增益 3e08/09、数字增益 3e06/07、测试图 4501），
    //   由本模块产生 I_ae_req 脉冲：
    //     (1) config 完成（S_cam_cfg_done）后 1s 自动补发一次 —— 兼作"运行时写通路是否通"的自检；
    //     (2) 任一开关电平变化并稳定 10ms（去抖）后补发一次。
    //   传感器手册 §2.2.2：曝光/增益第 N 帧写入、第 N+2 帧生效，允许运行时写 ⇒ 不必重启码流。
    //   ★注意：S_ae_req 来自 ae_set.v（AE 算法，当前永不置位），两者相或送 I_ae_req。
    wire        S_ae_req_all;
    wire        S_tp_canary;              // ★自检用★ 四个开关全拨"上"时 = 1（见文件后部 assign）
    reg  [3:0]  S_gain_applied;
    reg  [19:0] S_gain_dbcnt;
    reg         S_gain_sw_req;
    reg         S_boot_req_done;
    reg  [24:0] S_boot_cnt;
    always @(posedge S_24m_clk or negedge S_rst_n) begin
        if(!S_rst_n) begin
            S_gain_applied  <= 4'b1111;
            S_gain_dbcnt    <= 20'd0;
            S_gain_sw_req   <= 1'b0;
            S_boot_req_done <= 1'b0;
            S_boot_cnt      <= 25'd0;
        end
        else begin
            S_gain_sw_req <= 1'b0;
            if (!S_boot_req_done) begin
                if (S_cam_cfg_done) begin
                    if (S_boot_cnt == 25'd24_000_000) begin   // 1s @24MHz
                        S_boot_cnt      <= 25'd0;
                        S_boot_req_done <= 1'b1;
                        S_gain_applied  <= {S_sw1_sync1, S_sw2_sync1, S_sw3_sync1, S_sw4_sync1};
                        S_gain_sw_req   <= 1'b1;
                    end
                    else S_boot_cnt <= S_boot_cnt + 1'b1;
                end
            end
            else if (S_gain_applied != {S_sw1_sync1, S_sw2_sync1, S_sw3_sync1, S_sw4_sync1}) begin
                if (S_gain_dbcnt == 20'd240_000) begin        // 10ms @24MHz 去抖
                    S_gain_dbcnt   <= 20'd0;
                    S_gain_applied <= {S_sw1_sync1, S_sw2_sync1, S_sw3_sync1, S_sw4_sync1};
                    S_gain_sw_req  <= 1'b1;
                end
                else S_gain_dbcnt <= S_gain_dbcnt + 1'b1;
            end
            else S_gain_dbcnt <= 20'd0;
        end
    end
    assign S_ae_req_all = S_ae_req | S_gain_sw_req;

    // ---- [HDR-2026-10-10b] 四个开关的同步后电平送 LED1..LED4 ----
    //   灯亮 = FPGA 读到该引脚为逻辑 1（实测 = 该开关拨下）。
    //   自检判据：四个开关全部拨下时，四个 LED 应全亮；若某个 LED 不亮，说明该引脚
    //   没有被开关有效驱动（未装/未接/被外部拉低），对应功能就不可用。
    //   ★assign O_led 必须写在 S_sw1_sync1/S_sw2_sync1 的声明之后（Verilog 要求先声明后使用），
    //     故实际 assign 语句放在本文件后面 "SW1/SW2" 那一节（见 S_gamma_bypass 之后）。

    uicfgcs500_720p #(
      .CLK_DIV(24000000 / 100000 - 1)
  ) u_uicfgcs500 (
      .I_clk(S_24m_clk),  //系统时钟输入
      .I_rst_n(S_rst_n),  //系统复位输入
      .I_ae_req(S_ae_req_all),          // [HDR-2026-10-10d] AE算法请求 或 开关变化触发的运行时重下发
      .I_exposure_time(S_exposure_time),
      .I_analog_gain(S_analog_gain),
      .O_cam_scl(O_cam_scl),  //I2C总线，SCL时钟
      .IO_cam_sda(IO_cam_sda),  //I2C总线，SDA数据
      .I_test_pattern(1'b0),             // [HDR-2026-10-11i] ★永久关闭测试图★ 原来接 S_tp_canary（四开关全上 = 1），而四开关全上正是出厂推荐工作档 (SW1上=黑电平开、SW2上=曲线开、SW3上=×2.000、SW4上=15.750×) ⇒ 自检钩子被正常使用点开，且只有 SW3/SW4 变化才重下发，一旦点开就卡死。运行时 I2C 写通路已由增益梯与曲线 A/B 证明是通的，不再需要这个钩子。
      .I_gain_high(1'b0),                // [HDR-2026-10-12] AE 接管模拟增益 ⇒ 本端口不再使用（改前接 S_gain_high）
      .I_gain_digital(S_gain_digital),   // [HDR-2026-10-10c] SW3：数字增益 ×1.000/×2.000（0x3e06）
      .O_cfg_done(S_cam_cfg_done),  //摄像头寄存器初始化完成
      .O_ae_cfg_done(S_ae_cfg_done)  //AE配置完成
  );
	
    mipi_dphy_rx_ph1p_mipiio_wrapper#(
        .DPHY_RX_LOCATION      ( "DPHY0" ),
        .HS_EQUALIZER          ( "0dB"   ),//"0dB","1.5dB","3dB","4.5dB","6dB","7.5dB","9dB","10.5dB"
        .HS_VGA_GAIN           ( "8dB" ),//"-3dB","-1.5dB","0dB","1.5dB","3dB","4.5dB","6dB","7.5dB"
        .LANE_NUM              ( 2       ),
        .BYTE_NUM              ( 1       )
    )u_mipi_dphy_rx_ph1p_mipiio_wrapper(
        .I_lp_clk              ( S_100m_clk       ),
        .I_rst                 ( ~S_rst_n         ),

        .I_clk_lane_in_delay   ( 6'd0             ),
        .I_data_lane0_in_delay ( 6'd0             ),
        .I_data_lane1_in_delay ( 6'd0             ),
        .I_data_lane2_in_delay ( 6'd0             ),
        .I_data_lane3_in_delay ( 6'd0             ),

        .I_lane_invert         ( 4'b0000          ),
     
        .O_hs_rx_clk           ( S_csi_rx_clk     ),
        .O_hs_rx_valid         ( S_hs_rx_valid    ),
        .O_hs_rx_data          ( S_hs_rx_data     ),
      
        .O_lp_rx_lane0_p       (  ),
        .O_lp_rx_lane0_n       (  ),
      
        .I_lp_tx_en            ( 1'b0             ),
        .I_lp_tx_lane0_p       ( 1'b1             ),
        .I_lp_tx_lane0_n       ( 1'b1             ),
      
        .O_lane_match_error    (                  ),
        .O_lane_error          ( S_lane_error     ),
      
        .IO_rx_clk_pad_n       ( IO_rx_clk_pad_n  ),
        .IO_rx_clk_pad_p       ( IO_rx_clk_pad_p  ),
        .IO_rx_data_pad_n      ( IO_rx_data_pad_n ),
        .IO_rx_data_pad_p      ( IO_rx_data_pad_p )
    );
	
	
 //  cwc cwc_inst
 //(
 //    .probe0(S_hs_rx_valid),
 //    .probe1(S_hs_rx_data),
 //    .probe2(S_lane_error),
 //    .clk(S_csi_rx_clk)
 //);

 //csi 解码为RAW数据
csi_unpacket_2lane u_csi_unpacket(
.I_clk                 ( S_csi_rx_clk       ),
.I_rst_n               ( S_rst_n        	),
.I_hs_valid            ( S_hs_rx_valid     ),
.I_hs_data             ( S_hs_rx_data      ),

.O_csi_frame_start     ( S_csi_frame_start ),
.O_csi_frame_end       ( S_csi_frame_end   ),
.O_csi_valid           ( S_csi_valid       ),
.O_csi_data            ( S_csi_data        )
);


//解码为RAW8
raw10_unpacket_2lane u_raw10_unpacket (
.I_clk  (S_csi_rx_clk),
.I_rst_n(S_rst_n),

.I_csi_frame_start(S_csi_frame_start),
.I_csi_frame_end  (S_csi_frame_end),
.I_csi_valid      (S_csi_valid),
.I_csi_data       (S_csi_data),

.O_raw10_frame_start(S_raw10_frame_start),
.O_raw10_frame_end  (S_raw10_frame_end),
.O_raw10_valid      (S_raw10_valid),
.O_raw10_data       (S_raw10_data)
  );


//将数据转为stream流
uial2axis #(
.IMG_WIDTH(1280),
.IMG_HEIGHT(720),
.INPUT_DATA_WIDTH(40)
) 
u_uial2axis (
.I_native_clk(S_csi_rx_clk),
.I_rst_n     (S_rst_n),
.I_data      (S_raw10_data       ),
.I_data_valid(S_raw10_valid      ),
.I_data_start(S_raw10_frame_start),
.I_data_end  (S_raw10_frame_end  ),
.axis_tvalid (S_axis_tvalid),
.axis_tdata  (S_axis_tdata ),
.axis_tuser  (S_axis_tuser ),
.axis_tlast  (S_axis_tlast )
);
	

// 原厂HD模式直接输出1280x720 RAW10，不再进行FPGA固定窗口裁剪。
assign S_raw_tdata  = S_axis_tdata;
assign S_raw_tlast  = S_axis_tlast;
assign S_raw_tvalid = S_axis_tvalid;
assign S_raw_tuser  = S_axis_tuser;


//cwc1 cwc1_Inst
//  (
//      .probe0(S_axis_tuser),
//      .probe1(S_axis_tvalid),
//      .probe2(S_axis_tlast),
//      .probe3(S_axis_tdata),
//      .probe4(S_ISP_O_tuser),
//      .probe5(S_ISP_O_tvalid),
//      .probe6(S_ISP_O_tlast),
//      .probe7(S_ISP_O_tdata),
//      .probe8 (S_raw_tdata ),
//      .probe9 (S_raw_tlast ),
//      .probe10(S_raw_tvalid),
//      .probe11(S_raw_tuser ),
//      .clk(S_csi_rx_clk)
//  );


//=============================================================================
// [HDR-2026-10-10] 乒乓开关 SW1/SW2 → ISP 旁路控制（跨时钟域同步）
//   ★实测极性（与手册相反）：拨下 = 1 = 【旁路】= 加黑电平扣除 / S 曲线之前的老行为（最亮）；拨上 = 0 = 启用新功能。
//   pin.adc 里对这 4 根都声明了 PULLUP ⇒ 开关未焊/悬空时读到 1 ⇒ 自动老行为。
//   机械开关抖动极慢（毫秒级），这里只做 2 级同步消除亚稳态，不做去抖。
//   复位期间输出 1（旁路）⇒ 上电瞬间画面就是老行为，不会闪。
//=============================================================================
// ★声明已上移到本文件前部「运行时增益下发」之前★（2026-10-11i）：
//   S_gain_applied 现在要比较 {S_sw1_sync1,S_sw2_sync1,S_sw3_sync1,S_sw4_sync1}，
//   而 Verilog 要求先声明后使用。always 块保留在此处。
always @(posedge S_csi_rx_clk or negedge S_rst_n) begin
    if(!S_rst_n) begin
        S_sw1_sync0 <= 1'b1;
        S_sw1_sync1 <= 1'b1;
        S_sw2_sync0 <= 1'b1;
        S_sw2_sync1 <= 1'b1;
    end
    else begin
        S_sw1_sync0 <= I_switch[0];
        S_sw1_sync1 <= S_sw1_sync0;
        S_sw2_sync0 <= I_switch[1];
        S_sw2_sync1 <= S_sw2_sync0;
    end
end

wire S_blk_bypass   = S_sw1_sync1;   // 1 = 黑电平扣除【直通】；0 = 启用扣除
//   ★2026-10-11e 回退 10-11d 的反相★ 恢复与本文件 :750、pin.adc:22、
//   captures/README.md 全部历史采集标注一致的定义：**拨下 = 逻辑 1 = 旁路 = 老行为**。
//   反相版会把「拨下」变成「启用扣除」，与 :750 的注释自相矛盾，也让 V1-V5 验收矩阵失效；
//   而且 PULLUP 悬空读到 1，原版语义下悬空 = 旁路 = 老行为，是唯一安全的默认。
wire S_gamma_bypass = S_sw2_sync1;   // 1 = S 曲线直通

// [HDR-2026-10-10b] 四个开关的同步后电平 → 板载 LED1..LED4（灯亮 = 读到的电平为 1）
//   O_led[0]←SW1(A4)  O_led[1]←SW2(B4)  O_led[2]←SW3(E11)  O_led[3]←SW4(D11)
//   放在这里是因为 Verilog 要求信号先声明后使用（S_sw1_sync1/S_sw2_sync1 在上面刚声明）。
assign O_led = {S_sw4_sync1, S_sw3_sync1, S_sw2_sync1, S_sw1_sync1};

// ---- [HDR-2026-10-10d] 运行时写通路自检信号（放在这里是因为要先声明 S_sw1_sync1/S_sw2_sync1）----
  //   ★已停用（2026-10-11i）★ 原设计：四个开关全部拨“上”⇒ S_tp_canary = 1
  //   ⇒ 下一次运行时表下发把 0x4501 写成 0xbc = 传感器灰度递增测试图。
  //   ★原注释“正常使用绝不会出现的状态”是错的★：推荐工作档正好就是
  //   SW1上（黑电平扣除）+ SW2上（S 曲线）+ SW3上（×2.000）+ SW4上（15.750×）=
  //   四开关全上。而且重下发原本只由 SW3/SW4 变化触发（S_gain_applied 只有 2 bit）
  //   ⇒ 拨 SW1/SW2 不会重下发 ⇒ 一旦在“四开关全上”时下发过，测试图就卡死，再也关不掉。
  //   （2026-10-11 23:37 那两张验证图就是这个状态：灰度斜坡、零纹理、一半画面为 0，
  //    户对着房间拍但房间从未到达 FPGA）。
  //   现已硬接 1'b0 彻底关闭；同时 S_gain_applied 扩到 4 bit（含 SW1/SW2），
  //   任何开关变化都会重下发，杜绝“寄存器表状态陈旧”这一类 bug。
assign S_tp_canary = 1'b0;  // [HDR-2026-10-11i] 停用：原为 ~(四开关)，但“四开关全上”正是推荐工作档，会把传感器灰度测试图点开。保留信号名供 LED/调试备用。

//ISP算法顶层模块
isp_top u_isp_top (
.axi4s_video_aclk(S_csi_rx_clk),
.I_rst_n         (S_rst_n),
.I_tlast         (S_raw_tlast	),
.I_tuser         (S_raw_tuser	),
.I_tdata         (S_raw_tdata	),
.I_tvalid        (S_raw_tvalid	),
.I_tdest         (),
.O_tready        (S_ISP_O_tready),
.O_tdata         (S_ISP_O_tdata ),
.O_tlast         (S_ISP_O_tlast ),
.O_tuser         (S_ISP_O_tuser ),
.O_tvalid        (S_ISP_O_tvalid),
.I_tready        (),
// [OUR ALGO] 算法模式来自 24 MHz 按键域，my_algo 内部有 2 级同步器
.I_algo_mode     (S_algo_mode),
// [HDR-2026-10-10] SW1/SW2 旁路控制（已在 S_csi_rx_clk 域做过 2 级同步）
.I_blk_bypass    (S_blk_bypass  ),
.I_gamma_bypass  (S_gamma_bypass),
        .I_lsc_bypass (S_lsc_bypass ),
// [HDR-2026-10-12] AE 帧统计输出（60MHz ISP 域，准静态），送下面 u_ae_ctrl
.O_ae_luma_sum   (S_ae_stat_lsum),
.O_ae_pix_cnt    (S_ae_stat_pix ),
.O_ae_hi_cnt     (S_ae_stat_hi  ),
.O_ae_lo_cnt     (S_ae_stat_lo  ),
.O_ae_frame_tgl  (S_ae_stat_tgl ),
// [HDR-2026-10-12k] 白平衡遥测（awb 实际在用的 R/B 增益，ISP 域准静态）
.O_wb_gain_r     (S_wb_gain_r   ),
.O_wb_gain_b     (S_wb_gain_b   )
  );


    video_in u_video_in(
        .I_rst_n              (  S_rst_n             ),

        .I_camera_clk         ( S_csi_rx_clk          ),
        .I_camera_frame_start ( S_ISP_O_tuser  ),
        .I_camera_valid       ( S_ISP_O_tvalid ),
        .I_camera_data        ( S_ISP_O_tdata  ),
        .I_mipi_rx_error      ( 1'b0			      ),

        .I_ddr_clk            ( S_ddr_clk             ),
		.I_display_pause      ( 1'b0                  ),
        .I_video_out_rd_busy  ( S_video_out_rd_busy   ),
        .O_video_in_wr_busy   ( S_video_in_wr_busy    ),
        .O_video_out_rp       ( S_video_out_rp        ),

        .O_ddr_user_wr_en     ( S_vi_ddr_wr_en        ),
        .O_ddr_user_addr      ( S_vi_ddr_wr_addr      ),
        .O_ddr_user_wr_data   ( S_vi_ddr_wr_data      ),
        .I_ddr_user_ready     ( S_ddr_user_ready      )
    );



    assign S_ddr_user_wr_en    = S_vi_ddr_wr_en;

    assign S_ddr_user_rd_en    = S_vo_ddr_rd_en;

    assign S_ddr_user_addr     = S_vi_ddr_wr_en ? S_vi_ddr_wr_addr :
                                 S_vo_ddr_rd_en ? S_vo_ddr_rd_addr : 'd0;

    assign S_ddr_user_wr_data  = S_vi_ddr_wr_data;


    assign S_video_out_rst_n = S_hdmi_rst_n;

    video_out u_video_out(
        .I_rst_n             ( S_video_out_rst_n    ),
        .I_ddr_clk           ( S_ddr_clk            ),
 
        .O_video_out_rd_busy ( S_video_out_rd_busy  ),
        .I_video_in_wr_busy  ( S_video_in_wr_busy   ),
        .I_video_out_rp      ( S_video_out_rp       ),
 
        .O_ddr_user_rd_en    ( S_vo_ddr_rd_en       ),
        .O_ddr_user_addr     ( S_vo_ddr_rd_addr     ),
        .I_ddr_user_ready    ( S_ddr_user_ready     ),
        .I_ddr_user_rd_valid ( S_ddr_user_rd_valid  ),
        .I_ddr_user_rd_data  ( S_ddr_user_rd_data   ),

        .I_dsi_clk           ( S_hdmi_pixel_clk     ),
        .I_video_vsync       ( S_video_out_vsync    ),
        .I_video_rd_en       ( S_hdmi_window_rd_en  ),
        .O_vdieo_data        ( S_video_rd_data      )
    );



    mc_to_user_interface u_mc_to_user_interface(
        .I_clk                   ( S_ddr_clk               ),
        .I_rst_n                 ( S_rst_n                 ),

        .I_ddr_user_wr_en        ( S_ddr_user_wr_en        ),
        .I_ddr_user_rd_en        ( S_ddr_user_rd_en        ),
        .I_ddr_user_addr         ( S_ddr_user_addr         ),
        .I_ddr_user_wr_data      ( S_ddr_user_wr_data      ),
        .O_ddr_user_ready        ( S_ddr_user_ready        ),
        .O_ddr_user_rd_valid     ( S_ddr_user_rd_valid     ),
        .O_ddr_user_rd_data      ( S_ddr_user_rd_data      ),
            
        .O_mc_app_en             ( S_mc_app_en             ),
        .O_mc_app_addr           ( S_mc_app_addr           ),
        .O_mc_app_cmd            ( S_mc_app_cmd            ),
        .I_mc_app_rdy            ( S_mc_app_rdy            ),
        .O_mc_app_wdf_wren       ( S_mc_app_wdf_wren       ),
        .O_mc_app_wdf_data       ( S_mc_app_wdf_data       ),
        .O_mc_app_wdf_end        ( S_mc_app_wdf_end        ),
        .O_mc_app_wdf_mask       ( S_mc_app_wdf_mask       ),
        .I_mc_app_wdf_rdy        ( S_mc_app_wdf_rdy        ),
        .I_mc_app_rd_data        ( S_mc_app_rd_data        ),
        .I_mc_app_rd_data_end    ( S_mc_app_rd_data_end    ),
        .I_mc_app_rd_data_valid  ( S_mc_app_rd_data_valid  )
    );



    ph1p35_324_ddr_wrapper u_ph1p35_324_ddr_wrapper(
        .I_sys_clk              ( I_sys_clk              ),
        .I_sys_rst_n            ( S_rst_n                ),

        .O_ddr_clk              ( S_ddr_clk              ),
        .O_init_calib_complete  ( S_init_calib_complete  ),
        .I_mc_app_addr          ( S_mc_app_addr          ),
        .I_mc_app_cmd           ( S_mc_app_cmd           ),
        .I_mc_app_en            ( S_mc_app_en            ),
        .I_mc_app_wdf_data      ( S_mc_app_wdf_data      ),
        .I_mc_app_wdf_end       ( S_mc_app_wdf_end       ),
        .I_mc_app_wdf_mask      ( S_mc_app_wdf_mask      ),
        .I_mc_app_wdf_wren      ( S_mc_app_wdf_wren      ),
        .O_mc_app_rd_data       ( S_mc_app_rd_data       ),
        .O_mc_app_rd_data_end   ( S_mc_app_rd_data_end   ),
        .O_mc_app_rd_data_valid ( S_mc_app_rd_data_valid ),
        .O_mc_app_rdy           ( S_mc_app_rdy           ),
        .O_mc_app_wdf_rdy       ( S_mc_app_wdf_rdy       ),

        .ddr_addr               ( ddr_addr               ),
        .ddr_ba                 ( ddr_ba                 ),
        .ddr_cke                ( ddr_cke                ),
        .ddr_odt                ( ddr_odt                ),
        .ddr_cs_n               ( ddr_cs_n               ),
        .ddr_ras_n              ( ddr_ras_n              ),
        .ddr_cas_n              ( ddr_cas_n              ),
        .ddr_we_n               ( ddr_we_n               ),
        .ddr_ck_p               ( ddr_ck_p               ),
        .ddr_ck_n               ( ddr_ck_n               ),
        .ddr_dm                 ( ddr_dm                 ),
        .ddr_dq                 ( ddr_dq                 ),
        .ddr_dqs_p              ( ddr_dqs_p              ),
        .ddr_dqs_n              ( ddr_dqs_n              )
    );



    uivtc #(
        .H_ActiveSize ( 1280 ),
        .H_FrameSize  ( 1650 ),
        .H_SyncStart  ( 1390 ),
        .H_SyncEnd    ( 1430 ),
        .V_ActiveSize ( 720  ),
        .V_FrameSize  ( 750  ),
        .V_SyncStart  ( 725  ),
        .V_SyncEnd    ( 730  )
    )u_hdmi_vtc(
        .I_vtc_rstn    ( S_hdmi_rst_n    ),
        .I_vtc_clk     ( S_hdmi_pixel_clk ),
        .O_vtc_vs      ( S_hdmi_vsync     ),
        .O_vtc_hs      ( S_hdmi_hsync     ),
        .O_vtc_de_valid( S_hdmi_de        ),
        .O_vtc_user    ( S_hdmi_user      ),
        .O_vtc_last    ( S_hdmi_last      )
    );

    hdmi_mixer #(
        .H_OFFSET   ( 0    ),
        .V_OFFSET   ( 0    ),
        .IMG_WIDTH  ( 1280 ),
        .IMG_HEIGHT ( 720  ),
        .DEBUG_MODE ( 0    ),
        // [DBG] 排查 lab3「只有 Logo 无实时画面」时把这里改成 1：
        //   会重新综合，然后在 HDMI 画面最左侧出现 4 根竖条（每根 120 行高）
        //     第 1 根 (y 0..119)   bit0 = video_in 正在写 DDR
        //     第 2 根 (y 120..239) bit1 = video_out 正在读 DDR
        //     第 3 根 (y 240..359) bit2 = DDR 读返回 valid
        //     第 4 根 (y 360..479) bit3 = DDR 读回数据非零
        //   亮绿 = 1，暗红 = 0。诊断完请改回 0。
        //   背景：原工程 S_hdmi_debug_status 声明了但没引到任何引脚/LED，
        //         所以"改 DEBUG_MODE 看四格颜色"的老办法在上板时没有输出。
        .SHOW_DEBUG ( 0    )
    )u_hdmi_mixer(
        .I_clk           ( S_hdmi_pixel_clk   ),
        .I_rst_n         ( S_hdmi_rst_n       ),
        .I_video_vsync   ( S_hdmi_vsync       ),
        .I_video_hsync   ( S_hdmi_hsync       ),
        .I_video_de      ( S_hdmi_de          ),
        .I_video_user    ( S_hdmi_user        ),
        .I_video_last    ( S_hdmi_last        ),
        .I_debug_status  ( S_hdmi_debug_status),
        // [OUR ALGO] 在 HDMI 画面上叠加 "MODE n" 算法状态行
        //   只把 24 MHz 域的"翻转"信号送进来；hdmi_mixer 内部自己同步、
        //   并在像素域计数出模式值（见 hdmi_mixer.v 末尾 [MODE-PIPE] 段）。
        //   直接送 2 bit 模式值会让这条路被当成跨域组合路径，
        //   实测 Setup WNS 由 +0.103ns 掉到 -4.416ns。别改回去。
        .I_algo_mode_tgl ( S_algo_mode_tgl    ),
        .I_algo_mode_wrap( S_algo_mode_wrap   ),
        // [HDR-2026-10-12k] 遥测总线（49bit，24MHz/ISP 域 → 像素域，hdmi_mixer 内部 2 级 FF 同步）
        .I_dbg_vals      ( S_osd_dbg          ),
              .I_dbg2_vals     ( S_osd_dbg2         ),
        .O_video_rd_en   ( S_hdmi_window_rd_en),
        .I_video_rd_data ( S_video_rd_data    ),
        .O_hdmi_vsync    ( S_hdmi_out_vsync   ),
        .O_hdmi_hsync    ( S_hdmi_out_hsync   ),
        .O_hdmi_de       ( S_hdmi_out_de      ),
        .O_hdmi_data     ( S_hdmi_out_data    )
    );

    hdmi_tx u_hdmi_tx(
        .I_pixel_clk        ( S_hdmi_pixel_clk  ),
        .I_serial_clk       ( S_hdmi_serial_clk ),
        .I_rst              ( ~S_hdmi_rst_n     ),
        .I_key_in           ( 1'b0              ),
        .I_edid_read_trig   ( 1'b0              ),
        .O_edid_read_valid  (                   ),
        .O_edid_read_data   (                   ),
        .I_video_rgb_enable ( 1'b1              ),
        .I_video_in_vs      ( S_hdmi_out_vsync  ),
        .I_video_in_de      ( S_hdmi_out_de     ),
        .I_video_in_user    ( 1'b0              ),
        .I_video_in_valid   ( 1'b0              ),
        .I_video_in_last    ( 1'b0              ),
        .O_video_in_ready   (                   ),
        .I_video_in_data    ( S_hdmi_out_data   ),
        .I_audio_valid      ( 1'b0              ),
        .I_audio_left_data  ( 24'd0             ),
        .I_audio_right_data ( 24'd0             ),
        .I_i2s_BCLK         ( 1'b0              ),
        .I_i2s_LRCK         ( 1'b0              ),
        .I_i2s_DOUT         ( 1'b0              ),
        .O_ddc_scl          (                   ),
        .O_hdmi_clk_p       (                   ),
        .O_hdmi_tx_p        (                   ),
        .O_tmds_ch0_p       ( O_tmds_ch0_p      ),
        .O_tmds_ch1_p       ( O_tmds_ch1_p      ),
        .O_tmds_ch2_p       ( O_tmds_ch2_p      ),
        .O_tmds_clk_p       ( O_tmds_clk_p      )
    );


    
endmodule
