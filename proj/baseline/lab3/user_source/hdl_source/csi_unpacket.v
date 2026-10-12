//=============================================================================
// 文件      : csi_unpacket.v
// 模块      : csi_unpacket
// 功能      : MIPI CSI-2 包头解析 + 2lane 数据拼接：识别帧起始/帧结束短包，按长包长度计数使能，把 2lane 的 16bit 数据拼成 32bit 输出。★全树无例化、不在 .al 编译清单中；本工程实际使用的是 isp/csi_unpacket_2lane.v。
// 数据通路  : 输入 I_hs_valid/I_hs_data[15:0]（MIPI 核输出）；输出 O_csi_frame_start/O_csi_frame_end/O_csi_valid/O_csi_hs/O_csi_data[31:0]。S_head_en = ~S_hs_valid_1d & I_hs_valid 抓包头那一拍的上升沿；随后比较 S_hs_data_1d[15:8]（数据类型 DT）与 localparam FRAME_DATA_DT=8h2B(RAW10)、FRAME_START_DT=8h00、FRAME_END_DT=8h01，判断帧起、帧止与长包；数据长度 S_data_length = {I_hs_data[15:8], S_hs_data_1d[7:0]} >> 1（右移 1 是因为 2lane 每拍送 2 字节，而 LENGTH 字段按字节给出）；S_data_en 由 S_data_en_cnt 计到 S_data_length-1 时关断；csi_valid_r 在 S_data_en 期间二分频产生 O_csi_valid；O_csi_data <= {O_csi_data[15:0], I_hs_data} 把两次 16bit 拼成一个 32bit 字。
// 时钟/复位 : I_clk 上升沿同步，I_rst_n 异步复位、低电平有效。
// 依赖      : 第 138~156 行例化调试核 cwc3 cwc3_inst（probe0~probe14），该模块在本目录中不存在定义，疑似安路 TD 的在线调试 IP。无其它自研依赖。
// 综合/实现 : ★未被 camera_to_dsi_display.al 引用、未参与综合实现（若单独综合会因缺少 cwc3 定义而报未定义模块，属环境/IP 缺失，不是语法问题）。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
/*******************************MILIANKE*******************************
*Company : MiLianKe Electronic Technology Co., Ltd.
*WebSite:https://www.milianke.com
*TechWeb:https://www.uisrc.com
*tmall-shop:https://milianke.tmall.com
*jd-shop:https://milianke.jd.com
*taobao-shop1: https://milianke.taobao.com
*Create Date: 2023/03/23
*Module Name:
*File Name:
*Description: 
*The reference demo provided by Milianke is only used for learning. 
*We cannot ensure that the demo itself is free of bugs, so users 
*should be responsible for the technical problems and consequences
*caused by the use of their own products.
*Copyright: Copyright (c) MiLianKe
*All rights reserved.
*Revision: 1.0
*Signal description
*1) I_ input
*2) O_ output
*3) IO_ input output
*4) S_ system internal signal
*5) _n activ low
*6) _dg debug signal 
*7) _r delay or register
*8) _s state mechine
*********************************************************************/
/*********csi_unpacket_2lane MIPI CSI解码***********
--版本号1.0
--MIPI IP数据解码为32bit数据输出给下一级使用，这里需要了解MIPI协议的数据格式
*********************************************************************/

`timescale 1ns / 1ns

//---- kuai 1: duan-kou sheng-ming (MIPI 2lane 16bit shu-ru -> 32bit shu-chu) ----
module csi_unpacket 
(
input wire          I_clk,  //来自MIPI 核的时钟
input wire          I_rst_n,//异步复位

input wire          I_hs_valid,//synthesis keep //来自MIPI核的数据有效信号,其中也包含的数据类型
input wire[15: 0]   I_hs_data, //synthesis keep //来自MIPI核的数据,其中也包含的数据类型数据，这里定义2LANE，1BYTE模式

output reg           O_csi_frame_start, //帧起始，1个周期有效
output reg           O_csi_frame_end,   //帧结束，1个周期有效
output reg           O_csi_valid, //synthesis keep      //有效数据输出
output reg           O_csi_hs,
output reg  [31: 0]  O_csi_data   //synthesis keep      //有效数据，这里定义2LANE，1BYTE模式
);


//---- kuai 2: MIPI CSI-2 DT (data type) shuo-ming yu ben mo-kuai shi-yong de DT chang-liang ----
//MIPI数据类型
//DT 00 帧起始包
//DT 01 帧结束包
//DT 02 行起始包
//DT 03 行结束包
//DT 2a 8BIT模式下的数据长包
//DT 2b 10BIT模式下的数据长包

//---- FRAME_DATA_DT = 8h2B (RAW10 chang-bao); di 61 hang zhu-shi wei 8h2A (RAW8) ----
localparam FRAME_DATA_DT  = 8'h2B;   //RAW10
//localparam FRAME_DATA_DT  = 8'h2A;     //RAW8
//---- FRAME_START_DT = 8h00 / FRAME_END_DT = 8h01 (duan-bao) ----
localparam FRAME_START_DT = 8'h00;
localparam FRAME_END_DT   = 8'h01;

//---- kuai 3: nei-bu ji-cun qi / xian-wang ----
reg        S_hs_valid_1d;      //synthesis keep   
reg [15:0] S_hs_data_1d;       //synthesis keep   
wire       S_head_en;          //synthesis keep   
reg        S_head_en_1d;       //synthesis keep      
reg [15:0] S_data_length;      //synthesis keep      
reg        S_data_en;          //synthesis keep        
reg [15:0] S_data_en_cnt;      //synthesis keep      

//---- kuai 4: bao-tou shang-sheng-yan jian-ce (S_head_en = ~1d & I_hs_valid) ----
assign  S_head_en  = ~S_hs_valid_1d & I_hs_valid;//帧头使能

//I_hs_valid 和 I_hs_data 各打1拍
//---- kuai 5: zhen-qi / zhen-zhi / chang-bao shi-neng pan-duan (bi DT + chang-du ji-shu) ----
always @(posedge I_clk) begin 
    S_hs_valid_1d        <= I_hs_valid;
    S_hs_data_1d         <= I_hs_data;
    S_head_en_1d         <= S_head_en;//帧头使能
end

//帧起始判断
always @(posedge I_clk) 
    O_csi_frame_start <= (S_head_en_1d && S_hs_data_1d[15:8] == FRAME_START_DT);


//帧结束判断
always @(posedge I_clk) 
    O_csi_frame_end  <= (S_head_en_1d && S_hs_data_1d[15:8] == FRAME_END_DT);

//获取数据长度
always @(posedge I_clk) begin 
    if(I_hs_valid)begin
        if(S_head_en_1d && S_hs_data_1d[15:8] == FRAME_DATA_DT)
            S_data_length <= {I_hs_data[15:8],S_hs_data_1d[7:0]} >> 1;
        else    
            S_data_length <= S_data_length;
    end
    else    
        S_data_length <= 'd0;
end


//数据有效使能
//---- kuai 6: shu-ju chang-du ji-shu yu S_data_en guan-duan ----
always @(posedge I_clk or negedge I_rst_n) begin
    if(!I_rst_n)
        S_data_en <= 1'b0;
    else    
        if(S_head_en_1d && S_hs_data_1d[15:8] == FRAME_DATA_DT)
            S_data_en <= 1'b1;
        else if(S_data_en_cnt == S_data_length-1)
            S_data_en <= 1'b0;
        else    
            S_data_en <= S_data_en;
end

//数据长度计数器
//---- kuai 7: 2lane 16bit pin-jie cheng 32bit ----
always @(posedge I_clk) begin
    if(S_data_en)
        S_data_en_cnt <= S_data_en_cnt + 'd1;
    else
        S_data_en_cnt <= 'd0;
end

//有效数据同步输出,把2LANE的16bit数据转为32bit数据
//---- kuai 8: O_csi_valid er-fen-pin sheng-cheng (S_data_en qi-jian fan-zhuan) ----
reg  csi_valid_r;//synthesis keep

always @(posedge I_clk) begin
    csi_valid_r   <= S_data_en ? ~csi_valid_r : 0; 
    O_csi_valid   <= csi_valid_r;
    O_csi_hs      <= I_hs_valid; 
end

always @(posedge I_clk) begin
    O_csi_data    <= S_data_en ? {O_csi_data[15:0],I_hs_data} : 0;
end

//---- kuai 9: tiao-shi-he cwc3 (ben mu-lu wu gai mo-kuai ding-yi, yi shi Anlogic TD zai-xian tiao-shi IP) ----
   cwc3 cwc3_inst
 (
     .probe0(I_hs_valid),
     .probe1(I_hs_data),
     .probe2(S_hs_valid_1d),
     .probe3(S_hs_data_1d),
     .probe4(S_head_en),
     .probe5(S_head_en_1d),
     .probe6(S_data_length),
     .probe7(S_data_en),
     .probe8(S_data_en_cnt),
     .probe9(csi_valid_r),
     .probe10(O_csi_frame_start),
     .probe11(O_csi_frame_end),
     .probe12(O_csi_valid),
     .probe13(O_csi_hs),
     .probe14(O_csi_data),
     .clk(I_clk)
 );

    
endmodule