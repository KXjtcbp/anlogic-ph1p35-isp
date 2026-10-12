//=============================================================================
// 文件      : isp/demosaic_4x_2_0/line_buffer_demosaic.v
// 模块      : line_buffer_demosaic
// 功能      : 单行缓存（1 行延迟）：把 33bit/拍的输入（32bit 数据 + 1bit tuser）写进一块双口 BRAM，再用一个和写地址同规律推进、但要等第 1 行写满之后才启动的读地址把它读出来，于是在输出端拿到的是「上一行同一列」的数据，供 3×3 窗口取行用。
// 数据通路  : I_data[32:0] -> data_d0（打 1 拍）-> blk_mem_gen_demosaic 端口 A 写（addra，0..IMG_WIDTH_4x-1）-> 端口 B 用 addrb 读 -> O_data[32:0]；I_valid -> valid_d0 -> 既是写使能也决定 O_valid
// 时钟/复位 : 单时钟域 I_clk，BRAM 的 clka/clkb 都接 I_clk；I_rst_n 低有效，帧首信号 I_tuser 用来把 addra / addrb / tlast_lock_d0 清零。
// 依赖      : 例化 blk_mem_gen_demosaic（同目录 isp/demosaic_4x_2_0/blk_mem_gen_demosaic/，安路 TD 6.1.155545 生成的 BRAM 包装：33bit × 2048 深、地址位宽 11、端口 B 只读）。
// 综合/实现 : ■ 本文件唯一的存储就是那 1 块 BRAM；没有别的 RAM，也没有乘法/除法，只有比较与自增。
//           ■ 地址寄存器是硬编码的 [10:0]（2048 深），不随 IMG_WIDTH 变化；本工程 IMG_WIDTH=1280 时 IMG_WIDTH_4x=320，只占 320 个地址，其余深度空置。
//           ■ 「读比写晚整整一行」不是靠地址减法实现的，而是靠 tlast_lock_d0：写侧从帧首就开始写，读侧必须等写地址第一次回绕（也就是第 1 行写完）才放行，之后读写以相同速率推进。
//           ■ 一处未能在代码内确认的点：包装内 IP 参数写的是 REGMODE_A/REGMODE_B("NOREG")，而 raw_matrix_3x3_buffer.v:194 的既有注释是按「BRAM 输出延迟 1 拍」来解释三行对齐的；本注释只按代码既有说明描述对齐关系，没有断言硬件实际读延迟。
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
version:     :   
@Description :   
*****************************************************************/

//---- 参数：图像宽高（只用于推算每行拍数） ----
// IMG_WIDTH 只用来算 IMG_WIDTH_4x（一拍 4 个像素之后每行有多少个 32bit 字）；IMG_HEIGHT 在本文件内其实没有被使用到。
module line_buffer_demosaic #(
    parameter IMG_HEIGHT = 1080,   // 图像高度参数，默认值为1080
    parameter IMG_WIDTH  = 1920    // 图像宽度参数，默认值为1920
) (
//---- 端口 ----
    input              I_clk,      // 输入时钟信号
    input              I_rst_n,    // 输入复位信号，低电平有效
    input              I_tuser,    // 输入tuser信号，帧起始标志 
    input  wire        I_valid,    // 输入数据有效信号          
    input  wire [32:0] I_data,     // 输入数据总线，宽度为33位  
    output wire        O_valid,    // 输出数据有效信号          
    output wire [32:0] O_data      // 输出数据总线，宽度为33位  
);

//---- 内部信号 ----
    // 定义读使能信号
    wire        rd_en;  // synthesis keep 

//---- 地址计数器与数据寄存器 ----
// 注意 data_d0 是 33bit，比数据多出的最高位 [32] 放的是 tuser，这样 tuser 能和这一行的数据一起被存进 BRAM、一起读出来。
    // 定义地址计数器寄存器和数据寄存器
    reg  [10:0] addra;     // 写地址计数器               
    reg  [10:0] addrb;     // 读地址计数器               
    reg  [32:0] data_d0;   // 延时一个时钟的数据         
    reg         valid_d0;  // 延时一个时钟的数据有效信号  

//---- 每行拍数 ----
// IMG_WIDTH_4x = IMG_WIDTH >> 2：一拍搬 4 个像素，所以一行的拍数就是宽度除以 4；本工程 1280 => 320。
// 地址寄存器是硬编码的 [10:0]（2048 深），不随这个 localparam 变化。
    // 定义局部参数，计算图像宽度的四分之一，用于地址计数
    localparam IMG_WIDTH_4x = (IMG_WIDTH >> 2);

//---- 输入数据打 1 拍：写进 BRAM 的时序对齐 ----
    // 数据和有效信号的寄存，延时一个时钟
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            data_d0  <= 0;            // 复位时将data_d0清零
            valid_d0 <= 0;            // 复位时将valid_d0清零
        end else begin
            data_d0  <= I_data;       // 正常工作时，data_d0跟随I_data
            valid_d0 <= I_valid;      // 正常工作时，valid_d0跟随I_valid
        end
    end

//---- 写地址计数器 addra：每个有效输入拍 +1 ----
    // 写地址计数器addra的更新
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            addra <= 0;    // 复位或者I_tuser有效时，将addra清零
        end else if (valid_d0) begin
            // 当valid_d0有效时，更新addra
            addra <= (addra == IMG_WIDTH_4x - 1) ? 0 : addra + 1'b1;  // 到 IMG_WIDTH_4x-1 回绕到 0：一拍 4 个像素，所以一行的拍数就是 IMG_WIDTH_4x
            // 如果addra达到最大值（IMG_WIDTH_4x - 1），则清零，否则加1
        end
    end

    // 行结束标志tlast_lock_d0的更新
//---- 第一次写满一行后锁定 tlast_lock_d0 ----
    reg tlast_lock_d0;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            tlast_lock_d0 <= 1'b0;  // 复位或者I_tuser有效时，将tlast_lock_d0清零
        end else if ((tlast_lock_d0 == 1'b0) & (addra == IMG_WIDTH_4x - 1)) begin  // 只在 addra 第一次走到行尾时置 1，一旦置 1 就一直保持到下一帧 tuser，因此它等价于「第 1 行已经写完了」
            tlast_lock_d0 <= 1'b1;  // 当第一次addra达到最大值时，置位tlast_lock_d0
        end
    end

//---- 读使能 rd_en ----
    // 读使能信号rd_en的生成
    assign rd_en = (I_valid && tlast_lock_d0) ? 1'b1 : 1'b0;  // 必须同时满足「这一拍有输入数据」与「第 1 行已经写完」才允许读；这就是本模块相对输入整整延迟一行的地方
    // 只有当I_valid有效且tlast_lock_d0置位后，才产生读使能信号

//---- 读地址计数器 addrb：与 addra 同样的回绕规律，但只在 rd_en 有效时走 ----
    // 读地址计数器addrb的更新
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            addrb <= 0;    // 复位或者I_tuser有效时，将addrb清零
        end else begin
            // 当rd_en有效时，更新addrb
            addrb <= rd_en ? ((addrb == IMG_WIDTH_4x - 1) ? 0 : addrb + 1'b1) : addrb;  // 读地址因此始终与写地址同步推进（都从 0 走到 IMG_WIDTH_4x-1），读到的就是同一地址上一次写入的内容，即上一行同列的数据
            // 如果addrb达到最大值（IMG_WIDTH_4x - 1），则清零，否则加1
            // 如果rd_en无效，addrb保持不变
        end
    end

//---- 输出有效：与读出的数据同拍 ----
    // 输出有效信号O_valid的生成
    assign O_valid = (valid_d0 && tlast_lock_d0) ? 1'b1 : 1'b0;  // 与 O_data 同相：valid_d0 有效且第 1 行已写完时，读出的数据才是有效的上一行数据
    // 只有当valid_d0有效且tlast_lock_d0置位后，才输出有效数据

    // 实例化块存储器，用于数据的存储和读取
//---- 例化单行 BRAM（双口，读写同钟） ----
// 端口 A 负责写（clka=I_clk、wea=valid_d0、addra、dia=data_d0），端口 B 只负责读（clkb=I_clk、addrb），dob 就是读出的上一行数据。
// 本实例没有接端口 B 的写信号（dib/web）与端口 A 的读输出（doa），所以它是「A 写 B 读」的用法。
    blk_mem_gen_demosaic blk_mem_gen_demosaic_r0 (
        .clka (I_clk  ),   // 写端口时钟信号
        .wea  (valid_d0),  // 写使能信号
        .addra(addra  ),   // 写地址
        .dia (data_d0),   // 写数据
        .clkb (I_clk  ),   // 读端口时钟信号
        .addrb(addrb  ),   // 读地址
        .dob(O_data )    // 读数据输出
    );

endmodule

