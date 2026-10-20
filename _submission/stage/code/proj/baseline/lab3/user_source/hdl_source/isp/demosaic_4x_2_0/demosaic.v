//=============================================================================
// 文件      : isp/demosaic_4x_2_0/demosaic.v
// 模块      : demosaic
// 功能      : 去马赛克（demosaic）链路的小顶层：把 40bit/拍的 RAW10 输入（4 个像素 × 10bit）经过 3×3 邻域窗口缓存与双线性插值，还原成 128bit/拍的 RGB888 输出（4 个像素 × 32bit，每像素 {8'b0, R, G, B}）。
// 数据通路  : axi4s_video_tdata[39:0]（RAW10×4）-> raw_matrix_3x3_buffer_d（内含 mipi_to_raw_converter + zhenghe + 2 级 line_buffer_demosaic，输出 bayer_ypos 与 matrix_last/cur/next_line[95:0]）-> bilinear_interpolation_d -> O_tdata[127:0]
// 时钟/复位 : 单时钟域，I_clk 在工程中接 axi4s_video_aclk；I_rst_n 低有效，异步复位。两个子模块用同一个 I_clk / I_rst_n。
// 依赖      : 例化 raw_matrix_3x3_buffer、bilinear_interpolation（都在 isp/demosaic_4x_2_0/ 下）。本文件本身不含任何厂商原语，RAM 都在子模块里。
// 综合/实现 : ■ 本文件没有 always 块、没有 assign、没有寄存器，只有 wire 声明与两个模块例化，所以它的综合结果就是这两个实例以及它们之间的连线。
//           ■ 工程实际参数由上层决定：isp_top.v:116-121 传 IMG_HEIGHT=720 / IMG_WIDTH=1280 / data_complete_delay=50 / BAYER_MODE="BGGR"，因此本文件里 1080/1920 的默认值在本工程不生效。
//           ■ IMG_WIDTH=1280 时 IMG_WIDTH_4x=(IMG_WIDTH>>2)=320，即一拍 4 个像素、每行 320 拍；行缓存内部硬编码的地址位宽 [10:0] 只用到其中 320 个地址。
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
version:     :   1.1
@Description :   该模块主要是用于3x3矩阵的形成，以及对图像边界像素的处理
                 在原基础上优化了时序，把原来的一些未完全对齐的信号进行对齐。
*****************************************************************/

//---- 模块参数：图像尺寸、整合延时与 Bayer 相位 ----
// IMG_HEIGHT/IMG_WIDTH 在这条链路上只用来推算「一拍 4 像素之后每行有多少拍」（IMG_WIDTH>>2）与行数，不决定任何存储深度。
// 本工程由 isp_top.v:116-121 传入 720 / 1280 / 50 / "BGGR"（SC500CS 输出为 BGGR 相位）；本文件默认的 1080 / 1920 在本工程不生效。
module demosaic #(
    parameter IMG_HEIGHT          = 1080,  // 图像高度
    parameter IMG_WIDTH           = 1920,   // 图像宽度
    parameter data_complete_delay = 50  ,
    parameter BAYER_MODE          = "BGGR"
)
(
//---- 时钟与复位 ----
// 单时钟域：I_clk 在工程中接 axi4s_video_aclk，两个子模块共用它；I_rst_n 低有效、异步复位（posedge I_clk or negedge I_rst_n）。
    input           I_clk   ,   // 时钟信号
    input           I_rst_n ,   // 复位信号，低有效
    input           I_blk_bypass,   // [HDR-2026-10-10] 黑电平扣除旁路（1=直通，0=扣除）

//---- AXI4-Stream 输入：RAW10，4 个像素/拍 ----
// axi4s_video_tdata[39:0] 是 4 个像素 × 10bit（每个 10bit 一个像素，取高 8 位用）；
// axi4s_video_tdest[9:0] 在本链路里没有被消费；tuser 标帧首、tlast 标行尾、tvalid 标数据有效，tready 由本模块回压给上一级。
    input [39:0]            axi4s_video_tdata ,  // AXI4-Stream视频数据
    input [9:0]             axi4s_video_tdest ,
    input                   axi4s_video_tlast ,  // 行结束信号
    input                   axi4s_video_tvalid,  // 数据有效信号
    input                   axi4s_video_tuser ,  // 帧开始信号
    output                  axi4s_video_tready,  // 从模块准备好接受数据

//---- AXI4-Stream 输出：RGB888，4 个像素/拍 ----
// O_tdata[127:0] = 4 个像素 × 32bit，每 32bit 是 {8'b0, R[7:0], G[7:0], B[7:0]}，即高 8 位恒为 0。
    output                  O_tlast  ,  // 输出行结束信号
    output                  O_tuser  ,  // 输出帧开始信号
    output [127:0]          O_tdata  ,  // 输出数据
    output                  O_tvalid ,  // 输出数据有效信号
    input                   O_tready    // 输出数据准备好信号
);


//---- 内部互连：两个子模块之间的全部信号 ----
wire demosaic_tlast ; 
wire demosaic_tuser ; 
wire demosaic_tvalid; 
wire demosaic_tready; 

wire        bayer_ypos      ;
// 下面三根 96bit 各是一个「6 像素」滑窗：[71:64] 与 [31:24] 各只有 1 个像素，是插值时额外要用的两个边界像素
// （在 bilinear_interpolation.v 里被拆成 matrix13 与 matrix18；这两个槽位谁对应图像左、谁对应图像右，未能从本文件确认）；
// 中间的 [63:32] 才是这一拍输出的 4 个像素，对应插值模块里的 matrix14..matrix17。
wire [95:0] matrix_last_line;
wire [95:0] matrix_cur_line ;
wire [95:0] matrix_next_line;

//---- 例化 1：3×3 窗口缓存（里面含 RAW10 -> RAW8、BRAM 整合与两级行缓存） ----
// 它同时给出 bayer_ypos（Bayer 行相位）与三行窗口；详细机制见 raw_matrix_3x3_buffer.v 的注释。
raw_matrix_3x3_buffer #(
    .IMG_HEIGHT         (IMG_HEIGHT         ),  // 图像高度
    .IMG_WIDTH          (IMG_WIDTH          ),   // 图像宽度
    .data_complete_delay(data_complete_delay)
)raw_matrix_3x3_buffer_d
(
    /*input           */.I_clk    (I_clk   ),   // 时钟信号
    /*input           */.I_rst_n  (I_rst_n ),   // 复位信号，低有效
    /*input           */.I_blk_bypass(I_blk_bypass),  // [HDR-2026-10-10] 黑电平扣除旁路透传

   /*input [39:0]    */.axi4s_video_tdata (axi4s_video_tdata ),  // AXI4-Stream视频数据
   /*input [9:0]     */.axi4s_video_tdest (axi4s_video_tdest ),
   /*input           */.axi4s_video_tlast (axi4s_video_tlast ),  // 行结束信号
   /*input           */.axi4s_video_tvalid(axi4s_video_tvalid),  // 数据有效信号
   /*input           */.axi4s_video_tuser (axi4s_video_tuser ),  // 帧开始信号
   /*output          */.axi4s_video_tready(axi4s_video_tready),  // 从模块准备好接受数据

   /*output          */.O_tlast         (demosaic_tlast ),   // 行结束信号输出
   /*output          */.O_tuser         (demosaic_tuser ),   // 帧开始信号输出
   /*output          */.O_tvalid        (demosaic_tvalid),   // 数据有效信号输出
   /*input           */.O_tready        (demosaic_tready),   // 上一级模块准备好接受数据

   /*output          */.bayer_ypos      (bayer_ypos      ),   // Bayer滤波器行位置
   /*output  [95:0]  */.matrix_last_line(matrix_last_line),   // 上一行3x3矩阵数据
   /*output  [95:0]  */.matrix_cur_line (matrix_cur_line ),   // 当前行3x3矩阵数据
   /*output  [95:0]  */.matrix_next_line(matrix_next_line)    // 下一行3x3矩阵数据
);

//---- 例化 2：双线性插值 ----
// BAYER_MODE 原样透传给插值模块，由它内部用 generate 选中对应相位分支；本工程是 "BGGR"。
// 整条链路的时延 = 窗口缓存内部的时延 + 插值模块内部的 5 级流水（见 bilinear_interpolation.v）。
bilinear_interpolation #(
    .BAYER_MODE (BAYER_MODE)
)bilinear_interpolation_d(
    /*input            */.I_clk            (I_clk   ),
    /*input            */.I_rst_n          (I_rst_n ),

    /*//input
    /*input            */.I_tlast      (demosaic_tlast )    ,
    /*input            */.I_tuser      (demosaic_tuser )    ,
    /*input            */.I_tvalid     (demosaic_tvalid)    ,
    /*output           */.I_tready     (demosaic_tready)    ,
  
    /*input            */.bayer_ypos       (bayer_ypos       ),
    /*input   [95:0]   */.matrix_last_line (matrix_last_line ),
    /*input   [95:0]   */.matrix_cur_line  (matrix_cur_line  ),
    /*input   [95:0]   */.matrix_next_line (matrix_next_line ),
  
    /*//output
    /*output           */.O_tlast (O_tlast ),
    /*output           */.O_tuser (O_tuser ),
    /*output [127 : 0] */.O_tdata (O_tdata ),
    /*output           */.O_tvalid(O_tvalid),
    /*input            */.O_tready(O_tready)

);



endmodule