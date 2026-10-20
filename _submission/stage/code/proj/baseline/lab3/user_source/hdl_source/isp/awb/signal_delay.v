//=============================================================================
// 文件      : isp/awb/signal_delay.v
// 模块      : signal_delay
// 功能      : 用一块 96bit × 2048 的双口 BRAM 把像素数据缓存后延迟读出，并把 valid/tuser 同步延迟；用途是把像素数据对齐到 awb 中除法器 50 拍的流水延迟(DELAY_CYCLE=50)。
// 数据通路  : I_data/I_valid → 打 1 拍 → 写口 A(addra 行内递增) → 读口 B(addrb 比写口晚 DELAY_CYCLE-3 拍开读、读满一行停) → O_data；O_valid 为 rd_valid 再打 1 拍，O_tuser 在 v_cnt==0 且 rd_cnt==1 时给出。
// 时钟/复位 : 单时钟 I_clk（读写同源）；I_rst_n 低电平异步复位；I_tuser 作为同步清零条件，复位行列计数与读写地址。
// 依赖      : blk_mem_gen_awb_delay_signal（安路 IP 包装壳，内部是 PH1_LOGIC_ERAM 真双口原语，见 isp/awb/ram/blk_mem_gen_awb_delay_signal.v）。
// 综合/实现 : localparam IMG_WIDTH_4x = IMG_WIDTH>>2：每拍送 4 个像素，故行内节拍数 = 行像素数/4。BRAM 深度 2048 × 96bit。默认参数 1080/1920，实际由 awb 例化时传入（awb.v 中 IMG_HEIGHT/IMG_WIDTH 再来自 isp_top.v 的 720/1280，DELAY_CYCLE=50）。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
/*****************************************************************
Company : MiLianKe Electronic Technology Co., Ltd.
WebSite:https://www.milianke.com
TechWeb:https://www.uisrc.com
tmall-shop:https://milianke.tmall.com
jd-shop:https://milianke.jd.com
taobao-shop: https://milianke.taobao.com
Description: 
The reference demo provided by Milianke is only used for learning. 
We cannot ensure that the demo itself is free of bugs, so users 
should be responsible for the technical problems and consequences
caused by the use of their own products.
@Author      :   XiaoQingquan 
@Time        :   2025/01 
version:     :   
@Description :   
*****************************************************************/
module signal_delay #(
    parameter IMG_HEIGHT = 1080,
    parameter IMG_WIDTH  = 1920,
    parameter DATA_WIDTH = 96,
    parameter DELAY_CYCLE = 50
) (
    input                        I_clk,	   // 输入时钟信号
    input                        I_rst_n,  // 输入复位信号，低电平有效
    input                        I_tuser,  // 输入tuser信号，帧起始标志 
    input  wire                  I_valid,  // 输入数据有效信号          
    input  wire [DATA_WIDTH-1:0] I_data,   // 输入数据总线，宽度为33位  
    output wire                  O_valid,  // 输出数据有效信号          
    output wire [DATA_WIDTH-1:0] O_data ,  // 输出数据总线，宽度为33位  
    output wire                  O_tuser   // 输出tuser信号，帧起始标志  
);

//---- 内部信号 ----
    wire        rd_en;   // 读使能（组合）

    reg  [10:0] addra;   // 11bit 地址 → 2048 深度
    reg  [10:0] addrb;   // 读地址


    reg  [13:0] h_cnt;  // 行内节拍计数
    reg  [13:0] v_cnt;  // 行号计数
    reg  [13:0] rd_cnt;  // 读节拍计数
    
    reg  [DATA_WIDTH-1:0] I_data_r;  // 写入 BRAM 的数据打 1 拍
    reg         rd_valid,I_valid_r;

    localparam IMG_WIDTH_4x = (IMG_WIDTH >> 2);  // 每拍 4 个像素，行内节拍数 = 行像素数 / 4
//---- 输入打 1 拍（写侧数据与使能对齐） ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n ) begin
            I_valid_r <= 0;
            I_data_r  <= 0;
        end
        else begin
            I_valid_r <= I_valid;
            I_data_r  <= I_data;
        end
    end
	
//---- 行列计数器：h_cnt = 行内节拍，v_cnt = 行号 ----
	//行列计数器
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            h_cnt <= 0;
            v_cnt <= 0;
        end
        else begin
            h_cnt <= I_valid_r ? ((h_cnt == IMG_WIDTH_4x-1) ? 0 : h_cnt + 1) : h_cnt;  // 行内节拍递增，到 IMG_WIDTH_4x-1 回卷
            v_cnt <= I_valid_r &&(h_cnt == IMG_WIDTH_4x-1) ? ((v_cnt == IMG_HEIGHT - 1) ? 0 : v_cnt + 1) : v_cnt;  // 行号递增，帧末回卷
        end
    end
    
//---- 读使能：行首第 DELAY_CYCLE-3 拍开读，读满一行关闭 ----
	//读有效信号
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            rd_valid <= 0;
        end
        else if(h_cnt == DELAY_CYCLE - 3)begin  // 延迟 DELAY_CYCLE-3 拍后开始读（配合 BRAM 读延迟与输出打拍，整体约 50 拍）
            rd_valid <= 1;
        end
        else if(rd_cnt == IMG_WIDTH_4x - 1) //一次都有效开始之后，读IMG_WIDTH_4x个数据即可  // 一行数据读完即停
            rd_valid <= 0;
    end
	
//---- 读数据计数（判断一行读完） ----
	 //读数据计数
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            rd_cnt <= 0;
        end
        else if(rd_cnt == IMG_WIDTH_4x )
            rd_cnt <= 0;  // 读满一行重新计数
        else if(rd_valid)begin
            rd_cnt <= rd_cnt + 1;
        end
    end
	
//---- 写地址（行内递增） ----
	//写地址
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            addra <= 0;
        end else if (I_valid_r) begin
            addra <= (addra == IMG_WIDTH_4x - 1) ? 'b0 : addra + 1'b1;  // 写地址行内 +1
        end
    end

//---- 读地址（行内递增） ----
	//读地址
    always @(posedge I_clk or negedge I_rst_n) begin
      if (!I_rst_n || I_tuser) begin
        addrb <= 0;
      end else begin
        addrb <= rd_valid ? (addrb == IMG_WIDTH_4x - 1) ? 'b0 : addrb + 1'b1 : addrb;  // 读地址行内 +1
      end
    end
    
//---- 输出有效信号打拍（与 BRAM 读延迟对齐） ----
	//为了和输出的数据O_data同步，进行打拍处理
    reg rd_valid_d;
    always @(posedge I_clk or negedge I_rst_n) begin
      if (!I_rst_n) begin
        rd_valid_d <= 0;
      end else begin
        rd_valid_d <= rd_valid;  // 再打 1 拍，与 BRAM 输出 dob 同步
      end
    end
    assign O_valid = rd_valid_d;
    assign O_tuser = (v_cnt == 0) && (rd_cnt == 1);  // 第一行且读到第 2 拍时给出帧首标记

//---- BRAM 例化：96bit × 2048 真双口，A 口写 / B 口读 ----
    blk_mem_gen_awb_delay_signal blk_mem_gen_awb_delay_signal_d (
      .clka (I_clk   ),  // input wire clka
      .wea  (I_valid_r),  // input wire [0 : 0] wea
      .addra(addra   ),  // input wire [10 : 0] addra
      .dia  (I_data_r ),  // input wire [95 : 0] dina
      .clkb (I_clk   ),  // input wire clkb
      .addrb(addrb   ),  // input wire [10 : 0] addrb
      .dob  (O_data  )   // output wire [95 : 0] doutb
    );


endmodule