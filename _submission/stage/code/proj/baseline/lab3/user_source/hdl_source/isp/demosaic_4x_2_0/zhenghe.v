//=============================================================================
// 文件      : isp/demosaic_4x_2_0/zhenghe.v
// 模块      : zhenghe
// 功能      : 流控「整合」：用一块双口 BRAM 把 4 个像素/拍（DATA_WIDTH 位，本工程 32bit）的输入先存进去，再按自己测出来的行长把它读出来，同时重新生成 tuser/tlast/tvalid，使输出的一行与输入的一行重新对齐；每帧由 I_tuser 重新复位，因此不会串到下一帧去。
// 数据通路  : I_tdata[DATA_WIDTH-1:0] -> data_d0（打 1 拍）-> blk_mem_gen_zhenghe 端口 A 写（addra）-> 端口 B 用 addrb 读 -> data_d -> O_tdata；I_tlast/I_tuser/I_tvalid -> 打拍 + 计数 -> 重新生成 O_tlast/O_tuser/O_tvalid
// 时钟/复位 : 单时钟域 I_clk（BRAM 两端同钟）；I_rst_n 低有效；I_tuser（帧首）复位 addra/addrb/y_cnt/x_cnt，所以每一帧都重新对齐。
// 依赖      : 例化 blk_mem_gen_zhenghe（同目录 isp/demosaic_4x_2_0/blk_mem_gen_zhenghe/ 下的安路 BRAM 包装）。本模块没有 tready 端口，不做反压。
// 综合/实现 : ■ 默认参数是 [12:0] IMG_WIDTH=640、IMG_HEIGHT=480、[8:0] DATA_WIDTH=96、data_complete_delay=50；但本工程在 raw_matrix_3x3_buffer.v:153-158 例化时把 DATA_WIDTH 覆盖成 32、IMG_WIDTH/IMG_HEIGHT 传 1280/720，所以这里的默认值在本工程不生效。
//           ■ 地址寄存器硬编码 [10:0]（2048 深）；IMG_WIDTH_4x = IMG_WIDTH>>2 是一拍容纳的 4 像素组数，1280 时等于 320。
//           ■ 行长不是直接照抄参数，而是用帧首第一行实测到的 cnt_first 来修正（只有实测值 > IMG_WIDTH_4x 时才采用），用来容忍上游实际给的拍数与参数不一致。
//           ■ 每行读出的拍数恰好是一整行：rd_valid 的上下界之差再减 1 正好等于 IMG_WIDTH_4x，见下面 rd_valid_width_d0/d1 的注释。
//           ■ 声明情况：rd_valid 在本文件内没有显式声明，是 assign 左值产生的隐式 1bit wire（综合/仿真时会有 implicit wire 警告）；其余信号都有显式声明。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================

`timescale 1ns / 1ps
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
@Time        :   2024/10 
version:     :   1.0
@Description :   使用BRAM进行FIFO整合，并且不影响下一帧的数据传输
*****************************************************************/


//---- 参数：行长、行数与数据位宽 ----
// 这里的默认值只是形参初值；本工程实际由 raw_matrix_3x3_buffer.v:153-158 覆盖为 IMG_WIDTH=1280 / IMG_HEIGHT=720 / DATA_WIDTH=32。
// data_complete_delay 的含义见文件头注释：一行数据在 BRAM 里传完之后，与这一行最后一个数据之间的距离。
module zhenghe#(
    parameter [12:0] IMG_WIDTH  = 640,
    parameter [12:0] IMG_HEIGHT = 480,
    parameter [8:0]  DATA_WIDTH = 96 ,
    parameter [8:0]  data_complete_delay = 50 //每行BRAM完成数据传输后与这行最后一个数据的距离
) 
//---- 端口：纯流式，没有 tready（本模块不做反压） ----
(
    input                   I_clk  ,
    input                   I_rst_n,

    input                   I_tlast  ,
    input                   I_tuser  ,
    input [DATA_WIDTH-1:0]  I_tdata  ,
    input                   I_tvalid , 

    output reg              O_tlast  ,
    output reg              O_tuser  ,
    output [DATA_WIDTH-1:0] O_tdata  ,
    output reg              O_tvalid 
);
//---- 内部寄存器与线网 ----
    reg  [10:0]             addra,addrb;
    reg                     valid_r0,valid_r1;
    reg                     I_tlast_d0,I_tlast_d1;
    reg                     I_tuser_d0,I_tuser_d1;
    reg  [13:0]             y_cnt;  // 行计数器：每来一个行尾（I_tlast_d0）加 1，帧首 I_tuser 清零；只在本模块内部用来标记「第几行」
    reg  [20:0]             x_cnt;  // 行内拍计数器：flag_valid 为高的期间每拍加 1，离开有效区就清零；它是下面读窗口判据的唯一时间基准
    reg  [DATA_WIDTH-1:0]   data_d0;
    wire [DATA_WIDTH-1:0]   data_d;
//---- 每行拍数 ----
// IMG_WIDTH_4x = IMG_WIDTH >> 2：一拍 4 个像素，所以一行的拍数就是宽度除以 4；本工程 1280 => 320。
    localparam   IMG_WIDTH_4x = (IMG_WIDTH>>2);

//---- 派生信号：有效区标志、读窗口边界与行列计数器 ----
    wire         flag_valid       ;
    wire [15:0]  rd_valid_width_d0;
    wire [15:0]  rd_valid_width_d1;
    reg          flag_valid_d0    ;
    reg          flag_valid_d1    ;
    reg          flag_valid_first;
    reg  [15:0]  cnt_first;
    reg  [15:0]  valid_width;
    ////为了方便对后续的信号进行合理的处理，在此对部分信号进行打拍操作
//---- 输入信号打 1 拍：数据、有效、行尾、帧首各打一拍，让它们同相 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            valid_r0   <= 0;
            valid_r1   <= 0;
            I_tlast_d0 <= 0;
            I_tlast_d1 <= 0;
            data_d0    <= 0;
            I_tuser_d0 <= 0;
            I_tuser_d1 <= 0;
        end else begin
            valid_r0   <= I_tvalid;
            valid_r1   <= valid_r0;
            I_tlast_d0 <= I_tlast;
            I_tlast_d1 <= I_tlast_d0;
            data_d0    <= I_tdata;
            I_tuser_d0 <= I_tuser;
            I_tuser_d1 <= I_tuser_d0;
        end
    end  
    
    ////以每帧的第一行的数据长度作为VALID_WIDTH，为了防止可能的错误，每一帧都更新一次。
//---- 用「帧首第一行实测的拍数」修正有效行长 ----
// flag_valid_first 在帧首置 1、在第一个行尾清 0，只罩住第一行；cnt_first 就是这一行实际来了多少拍。
// valid_width 默认取 IMG_WIDTH_4x，只有当实测值比它大时才改用实测值（防御上游拍数与参数不一致）。
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) 
            flag_valid_first <= 0;
        else if(I_tuser )
            flag_valid_first <= 1;
        else if(I_tlast_d0)
            flag_valid_first <= 0;
    end
    
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n || I_tuser_d1) 
            cnt_first <= 0;
        else if(flag_valid_first )
            cnt_first <= cnt_first + 1;
    end

    
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n ) 
            valid_width <= IMG_WIDTH_4x;  // 每帧开头先回到参数值 IMG_WIDTH_4x，再按实测值修正一次，所以行长是「每帧重新确认」的
        else if(I_tuser && (cnt_first > IMG_WIDTH_4x))
            valid_width <= cnt_first;
    end

    ////计数行数
//---- 行计数器 y_cnt：每个行尾 +1 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n || I_tuser) 
            y_cnt <= 0;
        else if(I_tlast_d0)
            y_cnt <= y_cnt + 1;
    end
    
    //从每行的第一个数据到这行的最后一个数据，flag_valid_d0处于高电平
//---- 行内有效区标志 ----
// flag_valid_d0 罩住「本行从第 1 个数据到最后一个数据」，flag_valid_d1 罩住「本行最后一个数据到下一行第 1 个数据」，
// 两者相或得到 flag_valid：它在一行里几乎一直为高，只在行首那一两拍短暂变低，x_cnt 就是靠这一次变低回到 0，从而完成行同步。
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) 
            flag_valid_d0 <= 0;
        else if(I_tuser || I_tlast_d1)
            flag_valid_d0 <= 0;
        else if(valid_r1)
            flag_valid_d0 <= 1;
    end
    
    //从每行的最后一个数据到下一行的第一个数据，flag_valid_d1处于高电平
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n || I_tuser ) 
            flag_valid_d1 <= 0;
        else if(I_tlast)
            flag_valid_d1 <= 1;
        else if(I_tvalid)
            flag_valid_d1 <= 0;    
    end

//---- 读窗口的上下界（都以 x_cnt 计） ----
// rd_valid_width_d0 = valid_width - IMG_WIDTH_4x + data_complete_delay：读出起点相对行首的偏移；
// rd_valid_width_d1 = valid_width + data_complete_delay + 1：读出终点。
// 两者之差再减 1 恰好等于 IMG_WIDTH_4x，也就是说每行只读出一整行的字数（1280 时是 320 拍）。
    assign flag_valid        = flag_valid_d0 || flag_valid_d1 ;
    assign rd_valid_width_d0 = valid_width - IMG_WIDTH_4x + data_complete_delay;  // 读出起点：行长与参数一致时 (= IMG_WIDTH_4x) 就等于 data_complete_delay
    assign rd_valid_width_d1 = valid_width + data_complete_delay + 1;  // 读出终点：比起点多 IMG_WIDTH_4x+1，所以 rd_valid 的有效拍数正好是一整行
    
//---- 列计数器 x_cnt：行内位置 ----
// flag_valid 为高时每拍加 1，flag_valid 为低（行首那一两拍）时清零；上面所有读窗口判据都比对的是它。
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n || I_tuser) 
            x_cnt <= 0;
        else if(flag_valid)
            x_cnt <= x_cnt + 1;
        else 
            x_cnt <= 0;
    end
    
    assign rd_valid = (x_cnt < rd_valid_width_d1) && (x_cnt > rd_valid_width_d0);  // rd_valid 没有显式声明，靠这条 assign 产生隐式 1bit wire；它同时决定 addrb 是否推进和 O_tvalid
    
    //////A端口
//---- A 端口：写入 ----
// 写地址在帧首清零，之后每个有效输入拍 +1，到 IMG_WIDTH_4x-1 回绕，因此写地址就是「行内位置」。
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n || I_tuser) begin
            addra <= 0;
        end 
        else if(valid_r0)begin
            addra <= (addra == IMG_WIDTH_4x -1) ? 'b0 : addra + 1'b1;
        end
    end

    //////B端口
//---- B 端口：读出 ----
// 读地址只在 rd_valid 有效时 +1，回绕条件与写地址相同，因此读指针始终跟着写指针走，读出的就是先前写进去的那一行。
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n || I_tuser) begin
            addrb <= 0;
        end 
        else if(rd_valid)begin
            addrb <= (addrb == IMG_WIDTH_4x -1) ? 'b0 : addrb + 1'b1;
        end
    end
//---- 例化 BRAM（双口，读写同钟） ----
// 端口 A 写（clka=I_clk、wea=valid_r0、addra、dia=data_d0），端口 B 只读（clkb=I_clk、addrb），dob 就是读出的数据。
    blk_mem_gen_zhenghe blk_mem_gen_zhenghe_d1 (
      .clka (I_clk   ),  // input wire clka
      .wea  (valid_r0),  // input wire [0 : 0] wea
      .addra(addra   ),  // input wire [10 : 0] addra
      .dia (data_d0 ),  // input wire [95 : 0] dina
      .clkb (I_clk   ),  // input wire clkb
      .addrb(addrb   ),  // input wire [10 : 0] addrb
      .dob(data_d  )   // output wire [95 : 0] doutb
    );
//---- 输出流控与数据的重新生成 ----
// 帧首 O_tuser_d 用「x_cnt 恰好落在读出起点、且还在第 0 行」来判断，所以它标志的是「读出数据流的帧首」而不是输入帧首；
// O_tvalid_d 直接就是 rd_valid；O_tlast_d 落在读出终点前一拍。
    wire   O_tuser_d,O_tvalid_d,O_tlast_d;
    assign O_tuser_d  = (x_cnt == rd_valid_width_d0 + 1) && (y_cnt == 0);  // 读出第 0 行的第一个数据那一拍：即输出帧首
    assign O_tvalid_d = rd_valid;
    assign O_tdata    = data_d;
    assign O_tlast_d  = (x_cnt == rd_valid_width_d1 - 1) ;  // 读出终点前一拍：即输出行尾


//---- 输出再打 1 拍，与 BRAM 读出的数据对齐 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            O_tuser  <= 0;
            O_tvalid <= 0;
            O_tlast  <= 0;
        end else begin
            O_tuser  <= O_tuser_d;
            O_tvalid <= O_tvalid_d;
            O_tlast  <= O_tlast_d;
        end
    end  
    
endmodule