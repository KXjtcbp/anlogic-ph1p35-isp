//=============================================================================
// 文件      : video_in.v
// 模块      : video_in
// 功能      : 摄像头写入通路：把摄像头域（camera clk）的 128 bit 像素流跨到 DDR 域（ddr clk），
//             以 240 拍一次突发的方式写进 DDR 的 4 帧循环缓冲区，并维护写指针与给显示器用的读指针。
//             帧起始信号被展宽后跨时钟域同步；检测到 MIPI 接收错误时本帧地址回退覆盖上一帧。
// 数据通路  : I_camera_data[127:0] -> w128_d512_fifo（clkw = I_camera_clk，clkr = I_ddr_clk）-> S_fifo_rd_en
//             -> O_ddr_user_wr_data[127:0]，写使能 O_ddr_user_wr_en，地址 O_ddr_user_addr[24:0]。
//             O_video_out_rp[1:0] 送给 video_out.v，告诉它当前该读哪一帧。
// 时钟/复位 : 双时钟域：摄像头域 I_camera_clk（写 FIFO、帧起始展宽）与 DDR 域 I_ddr_clk（读 FIFO、写 DDR、
//             指针维护）；I_rst_n 低有效，两域都用它复位。I_mipi_rx_error 来自上层（本工程被接成常量 0）。
// 依赖      : 例化 w128_d512_fifo（128 bit x 512 深双时钟软 FIFO，来自 ip_source），无其他子模块。
// 综合/实现 : 纯 RTL + FIFO IP，可综合；已收录于 td_project/camera_to_dsi_display.al，
//             并在 design_top_wrapper.v:630 以 u_video_in 例化（其 I_mipi_rx_error 端在 :637 接 1'b0）。
//-----------------------------------------------------------------------------
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================



//---- 模块说明 ----
// 摄像头来的像素流是连续的，DDR 写入却是突发式的，两者速率与节拍都不同，
// 所以这里用“双时钟 FIFO + 攒够一次突发再发”的结构：
// 摄像头侧只管往 FIFO 里塞，DDR 侧等 FIFO 里攒够 240 拍数据再一次性读走写进 DDR。
// 为了不做帧同步抖动，图像在 DDR 里保存 4 帧（环形缓冲区），显示侧固定滞后 2 帧读取。
module video_in (
    input wire         I_rst_n,

    input wire         I_camera_clk,
    input wire         I_camera_frame_start,
    input wire         I_camera_valid,
    input wire[127:0]  I_camera_data,
    input wire         I_mipi_rx_error,

    input wire         I_ddr_clk,

    input wire         I_display_pause,
    input wire         I_video_out_rd_busy,
    output wire        O_video_in_wr_busy,
    output reg[1:0]    O_video_out_rp,     ///读指针

    output reg         O_ddr_user_wr_en,
    output reg[24:0]   O_ddr_user_addr,
    output wire[127:0] O_ddr_user_wr_data,
    input wire         I_ddr_user_ready
);

//---- 内部信号声明 ----
// S_fifo_rst：由展宽后的帧起始同步到 DDR 域后产生，用来在每帧开头把 FIFO 清干净；
// S_camera_frame_start_extend：摄像头域里被展宽的帧起始脉冲；
// S_frame_start：DDR 域里检出的帧起始（单拍）；
// S_video_in_wp / O_video_out_rp：4 帧环形缓冲区的写指针与读指针；
// S_ddr_wr_valid / S_ddr_wr_cnt：一次 DDR 写突发的进行标志与拍的计数。
    wire        S_fifo_rst;
    reg         S_camera_frame_start_extend; ///脉冲展宽，同步到ddr_clk时钟域
    reg[3:0]    S_extend_cnt;
    reg         S_camera_frame_start_extend_1d;
    reg         S_camera_frame_start_extend_2d;
    reg         S_camera_frame_start_extend_3d;
    wire        S_frame_start;
    reg[1:0]    S_video_in_wp;       ///写指针
    wire[8:0]   S_fifo_rd_num;      
    wire        S_fifo_rd_en;   
    wire        S_fifo_rd_valid;
    wire[127:0] S_fifo_rd_data; 
    reg         S_ddr_wr_valid;
    reg[9:0]    S_ddr_wr_cnt;

//---- 4 帧缓冲区的基地址 ----
// 每帧占 7,000,000 个地址单元，4 帧依次排开，正好覆盖一帧 1280x720 的存储需求并留有余量；
// 写指针/读指针就是在 0..3 之间轮转，选中哪一个就取哪一段基地址。
    localparam IMAGE_BASE_ADDR_0 = 25'd0;
    localparam IMAGE_BASE_ADDR_1 = 25'd7000000;
    localparam IMAGE_BASE_ADDR_2 = 25'd14000000;
    localparam IMAGE_BASE_ADDR_3 = 25'd21000000;


    assign S_fifo_rst = S_camera_frame_start_extend_3d;

    // 以完整DDR写突发的占用标志仲裁，避免连续视频写入长期阻塞读通道。
    assign O_video_in_wr_busy = S_ddr_wr_valid;

//---- 跨时钟域像素 FIFO ----
// 128 bit 宽（一拍一个完整像素组的宽度）、512 深；
// 写侧在摄像头时钟域 I_camera_clk（we 用 I_camera_valid），读侧在 DDR 时钟域 I_ddr_clk；
// rst 接 S_fifo_rst（每帧开头清一次），rdusedw 引出为 S_fifo_rd_num 用来判断攒够没；
// afull / full_flag / wrusedw / valid / empty_flag / aempty 都不使用，留空。
    w128_d512_fifo U_w128_d512_fifo(
        .rst        ( S_fifo_rst         ),   

        .clkw       ( I_camera_clk       ),     
        .we         ( I_camera_valid     ),
        .di         ( I_camera_data      ),
        .afull      (),
        .full_flag  (),
        .wrusedw    (),
 
        .clkr       ( I_ddr_clk          ),
        .re         ( S_fifo_rd_en       ), 
        .dout       ( O_ddr_user_wr_data ),  
        .rdusedw    ( S_fifo_rd_num      ),
        .valid      (), 
        .empty_flag (),
        .aempty     ()
    );


//---- 帧起始脉冲展宽（摄像头时钟域） ----
// 原始 I_camera_frame_start 可能只有一个摄像头时钟周期宽，直接跨到 DDR 域很容易被漏采；
// 这里把它展宽成 8 拍（计到 'd7 结束），保证 DDR 域一定采得到。
    always @(posedge I_camera_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            S_camera_frame_start_extend <= 1'b0;
        else
            if(I_camera_frame_start)
                S_camera_frame_start_extend <= 1'b1;
            else if(S_extend_cnt == 'd7)
                S_camera_frame_start_extend <= 1'b0;
            else
                S_camera_frame_start_extend <= S_camera_frame_start_extend;
    end

	
//---- 展宽计数器 ----
// 只在展宽期内累加，数到 8（'d7 时的下一拍）就停止展宽。
    always @ (posedge I_camera_clk) begin
    	if(S_camera_frame_start_extend)
        	S_extend_cnt <= S_extend_cnt + 'd1;
      	else
          	S_extend_cnt <= 'd0;
    end


//---- 展宽脉冲同步到 DDR 域 ----
// 三级打拍做跨时钟域同步，同时给出历史值用于边沿检测。
    always @(posedge I_ddr_clk) begin
        S_camera_frame_start_extend_1d <= S_camera_frame_start_extend;
        S_camera_frame_start_extend_2d <= S_camera_frame_start_extend_1d;
        S_camera_frame_start_extend_3d <= S_camera_frame_start_extend_2d;
    end

//---- 帧起始边沿检测（DDR 域） ----
// 相邻两级比较得到展宽脉冲的下降沿，作为 DDR 域里唯一的“一帧开始”标志；
// 因为展宽脉冲宽度固定，下降沿出现的位置每帧都一样，天然对齐。
    assign S_frame_start = ~S_camera_frame_start_extend_3d & S_camera_frame_start_extend_2d;

	/*
		如果前一帧图像有误少行了，那么地址回退为之前的，覆盖有问题的那帧图像
	*/
    always @(posedge I_ddr_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            S_video_in_wp <= 'd0;
        else
            if(I_display_pause)
                S_video_in_wp <= S_video_in_wp;
            else if(S_frame_start)
                begin
//---- 写指针 S_video_in_wp（4 帧轮转）与 MIPI 错误处理 ----
// 每来一次帧起始就把写指针在 0..3 之间加一，指向下一块帧缓冲区；
// I_display_pause 期间指针冻结，暂停结束后从原来的位置接着写。
// 紧随其后的同一结构寄存器是给显示侧的读指针 O_video_out_rp：
// 写第 N 帧时读第 N-2 帧（写 0->读 2、写 1->读 3、写 2->读 0、写 3->读 1），
// 滞后 2 帧是为了让一帧图像完整落进 DDR 之后再被读出，避免读到写了一半的帧。
// 而在帧起始时若 I_mipi_rx_error 有效（本帧被判为坏帧，如少行），就故意不递增写指针，
// 让下一帧仍写回同一块缓冲区，等于用新帧覆盖坏帧，避免显示器读到残缺画面；
// 本工程该信号由 design_top_wrapper.v:637 接常量 0，故此分支当前不会触发。
                    if(I_mipi_rx_error)
                        S_video_in_wp <= S_video_in_wp;
                    else
                        S_video_in_wp <= S_video_in_wp + 'd1;
                end
            else
                S_video_in_wp <= S_video_in_wp;
    end


    always @(posedge I_ddr_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            O_video_out_rp <= 'd0;
        else
            if(I_display_pause)
                O_video_out_rp <= O_video_out_rp;
            else if(S_frame_start)
                begin
                    case(S_video_in_wp)
                        'd0: O_video_out_rp <= 'd2;
                        'd1: O_video_out_rp <= 'd3;
                        'd2: O_video_out_rp <= 'd0;
                        'd3: O_video_out_rp <= 'd1;
                    endcase
                end
            else
                O_video_out_rp <= O_video_out_rp;
    end

    /*
        fifo的深度是512，实际的深度是510，因此需要注意每次读出的长度避免为256，否则连续两次读写会引起fifo读空，丢失数据
    */
    always @(posedge I_ddr_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            S_ddr_wr_valid <= 1'b0;
        else
            if(S_ddr_wr_valid && I_ddr_user_ready && S_ddr_wr_cnt == 'd239)
                S_ddr_wr_valid <= 1'b0;
//---- DDR 写突发控制 ----
// 攒够 240 拍数据、且读通路此时不忙时置起 S_ddr_wr_valid，开始一次写突发；
// 突发中数满 240 拍后落下。突发长度取 240 而不是 256 的原因见上面原有注释。
            else if(S_fifo_rd_num >= 'd240 && (!I_video_out_rd_busy) && (!S_fifo_rst))
                S_ddr_wr_valid <= 1'b1;
            else
                S_ddr_wr_valid <= S_ddr_wr_valid;
    end

    always @(posedge I_ddr_clk) begin
        if(S_ddr_wr_valid)
            begin
                if(I_ddr_user_ready)
                    S_ddr_wr_cnt <= S_ddr_wr_cnt + 'd1;
                else
                    S_ddr_wr_cnt <= S_ddr_wr_cnt;
            end
        else
            S_ddr_wr_cnt <= 'd0;
    end

//---- 突发内计数与 FIFO 读出 ----
// S_ddr_wr_cnt 一次突发共 240 拍（0..239），DDR 没 ready 时保持，突发结束或未开始时清零；
// 只有突发进行中且 DDR 接受数据时才从 FIFO 取一个 128 bit 字；
// 输出写使能再打一拍，与 FIFO 的 dout 保持同一节拍输出。
    assign S_fifo_rd_en = S_ddr_wr_valid & I_ddr_user_ready;

    always @(posedge I_ddr_clk) begin
        O_ddr_user_wr_en <= S_fifo_rd_en;
    end

	/*
		如果前一帧图像有误少行了，那么地址回退为之前的，覆盖有问题的那帧图像
	*/
    always @(posedge I_ddr_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            O_ddr_user_addr <= 1'b0;
        else
            if(S_frame_start && (!I_mipi_rx_error))
                begin
                    case(S_video_in_wp)
//---- 写地址产生 ----
// 帧起始且非错误帧时按写指针对齐到该帧基地址；
// 帧起始且是错误帧时对齐到上一帧基地址（写指针未递增，故取 wp-1 对应的表项），
// 与前面“地址回退覆盖坏帧”的注释对应；
// 突发进行中每写一个 128 bit 字地址加 8（DDR 控制器地址以 8 个 128 bit 为单位递增）。
                        'd0: O_ddr_user_addr <= IMAGE_BASE_ADDR_0;
                        'd1: O_ddr_user_addr <= IMAGE_BASE_ADDR_1;
                        'd2: O_ddr_user_addr <= IMAGE_BASE_ADDR_2;
                        'd3: O_ddr_user_addr <= IMAGE_BASE_ADDR_3;
                    endcase
                end
			else if(S_frame_start && I_mipi_rx_error)
				begin
                	case(S_video_in_wp)
                        'd0: O_ddr_user_addr <= IMAGE_BASE_ADDR_3;
                        'd1: O_ddr_user_addr <= IMAGE_BASE_ADDR_0;
                        'd2: O_ddr_user_addr <= IMAGE_BASE_ADDR_1;
                        'd3: O_ddr_user_addr <= IMAGE_BASE_ADDR_2;
                    endcase
                end
            else if(O_ddr_user_wr_en)
                O_ddr_user_addr <= O_ddr_user_addr + 'd8;
            else    
                O_ddr_user_addr <= O_ddr_user_addr;
    end

    
endmodule
