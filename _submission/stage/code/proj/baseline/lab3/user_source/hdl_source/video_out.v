//=============================================================================
// 文件      : video_out.v
// 模块      : video_out
// 功能      : 显示读出通路：按 video_in 给出的读指针从 DDR 的 4 帧缓冲区取数，
//             经 DSI 域 FIFO 后把 128 bit 字流按 24 bit 像素逐拍拆出来送给显示侧。
//             每帧开始时重新对齐地址并复位读 FIFO。
// 数据通路  : I_ddr_user_rd_data[127:0] -> w128_d512_fifo（clkw = I_ddr_clk，clkr = I_dsi_clk）
//             -> S_fifo_rd_data -> 位段拆分/跨字拼接 -> O_vdieo_data[23:0]（原文拼写如此，保留不改）。
//             读命令由 O_ddr_user_rd_en / O_ddr_user_addr[24:0] 发给 DDR 控制器。
// 时钟/复位 : 双时钟域：DDR 域 I_ddr_clk（发读命令、维护地址、同步 vsync）与 DSI/像素域 I_dsi_clk
//             （读 FIFO、拆像素）；I_rst_n 低有效。
// 依赖      : 例化 w128_d512_fifo（128 bit x 512 深双时钟软 FIFO，来自 ip_source），无其他子模块。
// 综合/实现 : 纯 RTL + FIFO IP，可综合；已收录于 td_project/camera_to_dsi_display.al，
//             并在 design_top_wrapper.v:665 以 u_video_out 例化。
//-----------------------------------------------------------------------------
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================




//---- 模块说明 ----
// 与 video_in 相对称：video_in 负责把摄像头数据写进 DDR 的 4 帧环，本模块负责按显示侧的节拍取出来。
// 取数同样是突发式的：攒够空间就发一次 240 拍读突发，再用 FIFO 缓冲到像素域慢慢消费。
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
    output reg[23:0]  O_vdieo_data
);

//---- 内部信号声明 ----
// S_fifo_rst / S_fifo_rst_cnt：帧起始触发的读 FIFO 复位与复位脉冲计数；
// S_video_vsync_1d/2d/3d：显示 vsync 同步到 DDR 域的三级链；
// S_video_frame_start：DDR 域检出的帧起始（单拍）；
// S_ddr_rd_trig / S_ddr_rd_valid / S_ddr_rd_cnt：读突发触发条件、突发进行标志与突发内计数；
// S_fifo_rd_cnt / S_fifo_rd_cnt_1d：像素域读节拍计数（打一拍供拆包用）；
// S_fifo_rd_data_1d：上一拍 FIFO 数据，用于跨 128 bit 边界拼接像素；
// S_fifo_emtpy：FIFO 空标志（原文拼写如此，保留不改）。
    reg         S_fifo_rst;     
    reg[7:0]    S_fifo_rst_cnt;
    wire[8:0]   S_fifo_wr_num;       
    wire        S_fifo_rd_en;        
    wire[127:0] S_fifo_rd_data;      
    reg         S_video_vsync_1d;
    reg         S_video_vsync_2d;
    reg         S_video_vsync_3d;
    wire        S_video_frame_start;   
    wire        S_ddr_rd_trig;       
    reg         S_ddr_rd_valid;      
    reg[9:0]    S_ddr_rd_cnt;        
    reg[3:0]    S_fifo_rd_cnt;       
    reg         S_video_rd_en_1d;
    reg[3:0]    S_fifo_rd_cnt_1d;     
    reg[127:0]  S_fifo_rd_data_1d;    
	wire        S_fifo_emtpy;     



//---- 4 帧缓冲区基地址 ----
// 与 video_in.v 中的取值完全一致，读侧必须用同一张地址表才能对上写侧存的帧。
    localparam IMAGE_BASE_ADDR_0 = 25'd0;
    localparam IMAGE_BASE_ADDR_1 = 25'd7000000;
    localparam IMAGE_BASE_ADDR_2 = 25'd14000000;
    localparam IMAGE_BASE_ADDR_3 = 25'd21000000;


//---- vsync 同步与帧起始检测（DDR 域） ----
// I_video_vsync 来自显示/DSI 侧，先三级同步到 I_ddr_clk，再用相邻两级比较得到上升沿；
// vsync 上升沿代表新的一帧开始，DDR 域需要据此重新对齐读地址。
    always @(posedge I_ddr_clk) begin
        S_video_vsync_1d <= I_video_vsync;
        S_video_vsync_2d <=S_video_vsync_1d;
        S_video_vsync_3d <= S_video_vsync_2d;
    end

//---- 帧起始（单拍脉冲） ----
    assign S_video_frame_start = ~S_video_vsync_3d & S_video_vsync_2d;


    always @(posedge I_ddr_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            S_fifo_rst <= 1'b0;
        else
            if(S_video_frame_start)
//---- 帧起始复位读 FIFO ----
// 每帧开头把读 FIFO 清空一次，保证本帧的像素从第一个字开始，不会残留上一帧的尾巴；
// 紧跟着的计数器把这次复位脉冲维持 11 拍（计到 'd10），足够 FIFO 内部完成清空。
                S_fifo_rst <= 1'b1;
            else if(S_fifo_rst_cnt == 'd10)
                S_fifo_rst <= 1'b0;
            else
                S_fifo_rst <= S_fifo_rst;
    end


//---- 复位脉冲计数 ----
// 复位脉冲维持 11 拍（计到 'd10），足够 FIFO 内部完成清空。
    always @(posedge I_ddr_clk) begin
        if(S_fifo_rst)
            S_fifo_rst_cnt <= S_fifo_rst_cnt + 'd1;
        else
            S_fifo_rst_cnt <= 'd0;
    end

    /*
        这里需要注意fifo的剩余空间一定要大于将要写入的长度，因为ddr读出的时候会有至少40个时钟周期的延时，
        例如每次从ddr读出240个长度的数据，那么fifo的剩余空间最少要设为280，否则会引起fifo写满丢失数据。
    */
//---- 读突发触发条件 ----
// 各个条件的含义：
//   (511 - 已写入字数) >= 300：FIFO 剩余空间要留够一次 240 拍突发外加 DDR 读回延迟；
//   !I_video_in_wr_busy：写通路此时没有占用 DDR 突发，避免两边抢总线；
//   !S_ddr_rd_valid：当前没有正在进行的读突发；
//   !S_fifo_rst 与 I_rst_n：复位期间不发命令。
// 紧随其后的寄存器是读突发进行标志与突发内计数：触发后置起，读满 240 拍（到 'd239）落下。
    assign S_ddr_rd_trig = (('d511 - S_fifo_wr_num) >= 'd300) && (!I_video_in_wr_busy) && (!S_ddr_rd_valid) && (!S_fifo_rst) && I_rst_n ? 1'b1 : 1'b0;

    /*
        fifo的深度是512，实际的深度是510，因此需要注意每次读出的长度避免为256，否则连续两次写入会引起fifo写满，丢失数据
    */
    always @(posedge I_ddr_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            S_ddr_rd_valid <= 1'b0;
        else
			if(O_ddr_user_rd_en && S_ddr_rd_cnt == 'd239)
                S_ddr_rd_valid <= 1'b0;
            else if(S_ddr_rd_trig)
                S_ddr_rd_valid <= 1'b1;
            else
                S_ddr_rd_valid <= S_ddr_rd_valid;
    end

//---- 读使能输出 ----
// 突发进行中且 DDR 接受时，每拍发出一个读请求（地址由下面的地址寄存器给出）。
    assign O_ddr_user_rd_en = S_ddr_rd_valid & I_ddr_user_ready;

//---- 突发内计数 S_ddr_rd_cnt ----
// 一次突发 240 拍（0..239），用于判断何时结束这次突发。
    always @(posedge I_ddr_clk) begin
        if(S_ddr_rd_valid)
            begin
                if(O_ddr_user_rd_en)
                    S_ddr_rd_cnt <= S_ddr_rd_cnt + 'd1;
                else
                    S_ddr_rd_cnt <= S_ddr_rd_cnt;
            end
        else    
            S_ddr_rd_cnt <= 'd0;
    end


    always @(posedge I_ddr_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            O_ddr_user_addr <= 'd0;
        else
            if(S_video_frame_start)
                begin
//---- 读地址产生 ----
// 每帧开始按读指针对齐到该帧基地址，随后每读一个 128 bit 字地址加 8；
// 与写侧 video_in.v 的地址步进一致，保证读写访问的是同一个地址序列。
                    case(I_video_out_rp)
                        'd0: O_ddr_user_addr <= IMAGE_BASE_ADDR_0;
                        'd1: O_ddr_user_addr <= IMAGE_BASE_ADDR_1;
                        'd2: O_ddr_user_addr <= IMAGE_BASE_ADDR_2;
                        'd3: O_ddr_user_addr <= IMAGE_BASE_ADDR_3;
                    endcase
                end
            else if(O_ddr_user_rd_en)
                O_ddr_user_addr <= O_ddr_user_addr + 'd8;
            else    
                O_ddr_user_addr <= O_ddr_user_addr;
    end

    
//---- 读通路忙标志 ----
// 触发或正在突发都算忙，汇报给 video_in.v 用于写侧仲裁（避免读写抢 DDR）。
    assign O_video_out_rd_busy = S_ddr_rd_trig | S_ddr_rd_valid;


//---- 跨时钟域像素 FIFO ----
// 写侧是 DDR 时钟域（we 用 I_ddr_user_rd_valid），读侧是 DSI 像素时钟域 I_dsi_clk；
// wrusedw 引出为 S_fifo_wr_num 供触发条件判断剩余空间，empty_flag 引出为 S_fifo_emtpy；
// rst 接每帧一次的 S_fifo_rst，其余标志位不使用。
    w128_d512_fifo U_w128_d512_fifo(
        .rst        ( S_fifo_rst          ),   

        .clkw       ( I_ddr_clk           ),     
        .we         ( I_ddr_user_rd_valid ),
        .di         ( I_ddr_user_rd_data  ),
        .wrusedw    ( S_fifo_wr_num       ),
        .afull      (),
        .full_flag  (),
 
        .clkr       ( I_dsi_clk           ),
        .re         ( S_fifo_rd_en        ), 
        .dout       ( S_fifo_rd_data      ),  
        .rdusedw    (), 
        .valid      (),  
        .empty_flag ( S_fifo_emtpy        ),
        .aempty     ()
    );


//---- 行内读节拍计数（DSI 域） ----
// I_video_rd_en 有效期间从 0 累加到 15 循环，代表一行里 16 个像素节拍；
// 无效时清零，等下一次行有效重新开始。
   always @(posedge I_dsi_clk) begin
       if(I_video_rd_en)
           S_fifo_rd_cnt <= S_fifo_rd_cnt + 'd1;
       else
           S_fifo_rd_cnt <= 'd0;
   end

//---- FIFO 读请求（每 5 拍一次） ----
// 一个 128 bit 字正好装 5 个 24 bit 像素（120 bit，余 8 bit），
// 所以每 5 个像素节拍才需要从 FIFO 取一个新字；
// 取数点选在节拍 0 / 5 / 10，与下面 case 的拆包位置一一对应。
   assign S_fifo_rd_en = I_video_rd_en && (S_fifo_rd_cnt == 'd0)  ? 1'b1 :
                         I_video_rd_en && (S_fifo_rd_cnt == 'd5)  ? 1'b1 :
                         I_video_rd_en && (S_fifo_rd_cnt == 'd10) ? 1'b1 : 1'b0;

//---- 拆包流水打拍 ----
// 把读节拍计数、行有效与 FIFO 数据各打一拍，使下一级能在同一个节拍里用旧数据做跨字拼接。
   always @(posedge I_dsi_clk) begin
       S_video_rd_en_1d  <= I_video_rd_en;
       S_fifo_rd_cnt_1d  <= S_fifo_rd_cnt;
       S_fifo_rd_data_1d <= S_fifo_rd_data;
   end

//---- 128 bit 拆成 24 bit 像素 ----
// case 用打了一拍的节拍计数 0..15 逐拍选出一个 24 bit 像素：
//   'd0..'d4  ：从当前 128 bit 字里依次取 [127:104]、[103:80]、[79:56]、[55:32]、[31:8]；
//   'd5       ：当前字剩下的 [7:0] 与上一字的 [127:112] 拼成一个像素（跨字边界）；
//   'd6..'d9  ：继续从当前字取 [111:88]、[87:64]、[63:40]、[39:16]；
//   'd10      ：当前字剩下的 [15:0] 与上一字的 [127:120] 拼接；
//   'd11..'d15：取 [119:96]、[95:72]、[71:48]、[47:24]、[23:0]。
// 16 拍正好输出 16 个像素，整体上恰好消费 3.2 个 128 bit 字；
// 行无效时输出清零，避免显示侧把消隐期的残留数据当成有效像素。
   always @(posedge I_dsi_clk) begin
       if(S_video_rd_en_1d)
           begin
               case(S_fifo_rd_cnt_1d)
                   'd0: O_vdieo_data  <= S_fifo_rd_data[127:104];
                   'd1: O_vdieo_data  <= S_fifo_rd_data[103:80];
                   'd2: O_vdieo_data  <= S_fifo_rd_data[79:56];
                   'd3: O_vdieo_data  <= S_fifo_rd_data[55:32];
                   'd4: O_vdieo_data  <= S_fifo_rd_data[31:8];
                   'd5: O_vdieo_data  <= {S_fifo_rd_data_1d[7:0],S_fifo_rd_data[127:112]};
                   'd6: O_vdieo_data  <= S_fifo_rd_data[111:88];
                   'd7: O_vdieo_data  <= S_fifo_rd_data[87:64];
                   'd8: O_vdieo_data  <= S_fifo_rd_data[63:40];
                   'd9: O_vdieo_data  <= S_fifo_rd_data[39:16];
                   'd10: O_vdieo_data <= {S_fifo_rd_data_1d[15:0],S_fifo_rd_data[127:120]};
                   'd11: O_vdieo_data <= S_fifo_rd_data[119:96];
                   'd12: O_vdieo_data <= S_fifo_rd_data[95:72];
                   'd13: O_vdieo_data <= S_fifo_rd_data[71:48];
                   'd14: O_vdieo_data <= S_fifo_rd_data[47:24];
                   'd15: O_vdieo_data <= S_fifo_rd_data[23:0];
               endcase
           end
       else
           O_vdieo_data <= 'd0;
   end

    
endmodule
