//=============================================================================
// 文件      : isp/BLC/BLC.v
// 模块      : BLC
// 功能      : 黑电平校正(Black Level Correction)：对 40bit 数据里的 4 个 10bit 像素各自减去一组可配置偏移量，结果为负则钳位到 0。★★本工程未例化、未接入数据通路：全树搜索不到对 BLC 的例化（仅本文件的 module 声明），属备用/未接入模块。
// 数据通路  : I_tdata(40bit = 4×10bit) → 拆成 I_blc_data[0..3] → generate 展开 4 路并行的“减法 + 下钳位”(偏移取 parameter Black_level_offset_r0..r3) → 拼回 O_tdata；tlast/tuser/tvalid 打 1 拍跟随输出。
// 时钟/复位 : I_clk 单时钟；I_rst_n 低电平异步复位（只清 tlast/tuser/tvalid 打拍寄存器）；减法 always 块只有 posedge I_clk、以 I_tvalid 为使能且无复位。
// 依赖      : 无子模块例化。
// 综合/实现 : generate for 展开 4 路；4 组偏移量默认均为 15(10bit 域)。O_tdest 输出在文件内未见赋值(无驱动)、I_tdest 输入未被引用，即这两个端口实际未参与运算。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
/*****************************************************************
Company : Nanjing Weiku Robot Technology Co., Ltd.
Brand   : VLKUS
Technical forum:www.uisrc.com
@Author      :   XiaoQingquan 
@Time        :   2024/09/11 
@Description :   ISP_black_level_correction
*****************************************************************/
`timescale 1ns / 1ps

module BLC #(
    parameter [9:0]  Black_level_offset_r0 = 15,  // 第0路偏移；4 路对应 40bit 中的 4 个像素（是否对应 Bayer 的 R/Gr/Gb/B 未能从代码确认）
    parameter [9:0]  Black_level_offset_r1 = 15,
    parameter [9:0]  Black_level_offset_r2 = 15,
    parameter [9:0]  Black_level_offset_r3 = 15  // 第3路偏移
)
(
    input                   I_clk  ,
    input                   I_rst_n,

    input                   I_tlast   ,
    input                   I_tuser   ,
    input  [39:0]           I_tdata   ,
    input                   I_tvalid  , 
    input  [9:0]            I_tdest   ,  // 本文件内未被引用
    output                  I_tready  ,

    output                  O_tlast   ,
    output                  O_tuser   ,
    output [39:0]           O_tdata   ,
    output                  O_tvalid  ,
    output [9:0]            O_tdest   ,  // 本文件内未见对该输出的赋值（无驱动）
    input                   O_tready  

);


//---- 控制信号寄存器 ----
    reg                   I_tlast_r    ;
    reg                   I_tuser_r    ;
    reg                   I_tvalid_r   ;

//---- 偏移量：parameter → 4 路数组 ----
    wire [9:0]  I_blc_data[3:0];
    wire [9:0]  black_level_offset[3:0] ;
    assign black_level_offset[0] = Black_level_offset_r0;  // parameter 常量映射为数组，便于 generate 索引
    assign black_level_offset[1] = Black_level_offset_r1;
    assign black_level_offset[2] = Black_level_offset_r2;
    assign black_level_offset[3] = Black_level_offset_r3;

//---- 数据拆分（40bit → 4×10bit）与输出寄存器 ----
    reg  [9:0]  data_out[3:0];

    assign I_blc_data[0] = I_tdata[9:0]  ;  // 字段分布：[9:0] / [19:10] / [29:20] / [39:30]
    assign I_blc_data[1] = I_tdata[19:10];
    assign I_blc_data[2] = I_tdata[29:20];
    assign I_blc_data[3] = I_tdata[39:30];
    
//---- 逐像素减法 + 下钳位（generate 展开 4 路并行） ----
    genvar i;
    generate for(i=0;i<4;i=i+1)
        begin:
        BLACK_LEVEL_OFFSET
        always @(posedge I_clk)begin 
            if (I_tvalid) begin
                // ִ�кڵ�ƽ��������ֹ���ָ���
                if (I_blc_data[i] > black_level_offset[i]) begin  // 严格大于才相减，避免无符号下溢回绕
                    data_out[i] <= I_blc_data[i] - black_level_offset[i];
                end 
                else begin
                    data_out[i] <= 10'd0; // ������ü�Ϊ0����ֹ����  // 不足则钳到 0
                end
            end
        end
        end
    endgenerate


//---- 控制信号打 1 拍 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            {I_tlast_r,I_tuser_r,I_tvalid_r} <= 0;
        else begin
            I_tlast_r <= I_tlast;
            I_tuser_r <= I_tuser;
            I_tvalid_r <= I_tvalid;
        end
    end


//---- 输出拼接与握手 ----
    assign  O_tlast      = I_tlast_r;   
    assign  O_tuser      = I_tuser_r;   
    assign  O_tvalid     = I_tvalid_r;

    assign  O_tdata      = {data_out[3],data_out[2],data_out[1],data_out[0]};  // 4 个 10bit 拼回 40bit
    // assign O_t_data = {R_new[7-:5],G_new[7-:6],B_new[7-:5]};
    assign  I_tready     = O_tready;  // 直通反压


endmodule