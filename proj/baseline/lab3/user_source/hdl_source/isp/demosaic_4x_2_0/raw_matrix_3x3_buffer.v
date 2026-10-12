//=============================================================================
// 文件      : isp/demosaic_4x_2_0/raw_matrix_3x3_buffer.v
// 模块      : raw_matrix_3x3_buffer
// 功能      : 3×3 邻域窗口生成：先用 mipi_to_raw_converter 把 40bit 的 RAW10 变成 32bit 的 RAW8，再用 zhenghe 做 BRAM 整合，然后用两级 line_buffer_demosaic 分别取到「上一行」「上两行」的数据；三行数据各配一个 96bit 滑窗寄存器，输出 3 行 × 6 像素的邻域窗口，并给出 Bayer 行相位 bayer_ypos，供双线性插值使用。
// 数据通路  : axi4s_video_tdata[39:0] -> mipi_to_raw_converter -> raw_data[31:0]（4 个像素 × 8bit）-> zhenghe -> data[0] -> line_buffer_demosaic ×2（generate 展开）-> data[1]（上一行）、data[2]（上两行）-> 打拍对齐 -> matrix_last_line / matrix_cur_line / matrix_next_line[95:0] + bayer_ypos
// 时钟/复位 : 单时钟域 I_clk（所有子模块与 BRAM 同钟）；I_rst_n 低有效、异步复位；帧首用 zhenghe_tuser 复位 h_cnt / v_cnt 与三行缓冲。
// 依赖      : 例化 mipi_to_raw_converter、zhenghe、line_buffer_demosaic（都在 isp/demosaic_4x_2_0/ 下）；line_buffer_demosaic 内部再例化 blk_mem_gen_demosaic。
// 综合/实现 : ■ 本文件一共例化出 3 块 BRAM IP：2 块 blk_mem_gen_demosaic（两级行缓存）+ 1 块 blk_mem_gen_zhenghe，是这条 demosaic 链路 RAM 数的主要来源；三行滑窗本身只是寄存器（移位拼接），不占 RAM。
//           ■ 参数 IMG_HEIGHT/IMG_WIDTH 默认 1080/1920，本工程由 isp_top.v:116-121 传 720/1280；IMG_WIDTH_4x = IMG_WIDTH>>2 = 320 既是每行字数，也是 h_cnt/v_cnt 的回绕值。
//           ■ 全文件没有任何乘法与除法，只有比较、拼接、移位（IMG_WIDTH>>2）与加法。
//           ■ 边界处理不用补零，而是复制边界像素（行首把第 1 个像素复制到左邻位、行尾把最后 1 个像素复制到右邻位），这样图像右/左边缘不会因为补零而出现黑边或变暗。
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


//---- 参数：图像尺寸与整合延时 ----
// IMG_HEIGHT/IMG_WIDTH 只在下面推算每行拍数（IMG_WIDTH>>2）与计数器回绕值；本工程由 isp_top.v:116-121 传 720/1280。
module raw_matrix_3x3_buffer #(
    parameter IMG_HEIGHT = 1080,  // 图像高度
    parameter IMG_WIDTH  = 1920,   // 图像宽度
    parameter data_complete_delay = 50
)
(
//---- 端口 ----
    input           I_clk   ,   // 时钟信号
    input           I_rst_n ,   // 复位信号，低有效
    input           I_blk_bypass,   // [HDR-2026-10-10] 黑电平扣除旁路（1=直通，0=扣除）

    input [39:0]                         axi4s_video_tdata ,  // AXI4-Stream视频数据
    input [9:0]                          axi4s_video_tdest ,
    input                                axi4s_video_tlast ,  // 行结束信号
    input                                axi4s_video_tvalid,  // 数据有效信号
    input                                axi4s_video_tuser ,  // 帧开始信号
    output                               axi4s_video_tready,  // 从模块准备好接受数据

    output                               O_tlast         ,   // 行结束信号输出
    output                               O_tuser         ,   // 帧开始信号输出
    output                               O_tvalid        ,   // 数据有效信号输出
    input                                O_tready        ,   // 上一级模块准备好接受数据

    output                               bayer_ypos      ,   // Bayer滤波器行位置
    output  [95:0]                       matrix_last_line,   // 上一行3x3矩阵数据
    output  [95:0]                       matrix_cur_line ,   // 当前行3x3矩阵数据
    output  [95:0]                       matrix_next_line    // 下一行3x3矩阵数据
);


//---- 功能函数：clog2b（本文件内没有被调用） ----
// 这是一个「求表示 depth 需要多少 bit」的函数，但下面没有任何地方调用它，也没有用它推导过任何位宽；
// 位宽在本文件里都是直接写死的（见常数声明）。
/*********************************************************
******************1.功能声明*******************************
*********************************************************/
// 计算数据的位宽
function integer clog2b(
    input integer depth
);
    begin
        for(clog2b=0; depth>0; clog2b=clog2b+1)begin
            depth = depth >> 1;
        end
    end    
endfunction

/*********************************************************
******************2.常数声明*******************************
*********************************************************/
//---- 常数声明 ----
// N=3 是 3×3 矩阵的边长；DATA_WIDTH=32 是一拍 4 个 8bit 像素；
// IMG_WIDTH_4x = IMG_WIDTH>>2 是「一拍 4 像素」之后每行的字数（本工程 1280 => 320），下面 h_cnt/v_cnt 的回绕值就用它。
localparam N = 3;  // 矩阵大小为3x3

localparam DATA_WIDTH   = 32;  // 数据位宽

localparam IMG_WIDTH_4x = (IMG_WIDTH >> 2);  // 图像宽度除以4，得到每个数据块的数量

//---- 线网（wire）声明 ----
/*********************************************************
******************3.信号声明*******************************
*********************************************************/
// 定义线网信号
wire                        zhenghe_tlast ;    // 合并后的行结束信号
wire                        zhenghe_tuser ;    // 合并后的帧开始信号
wire  [31:0]                zhenghe_tdata ;    // 合并后的数据
wire                        zhenghe_tvalid;    // 合并后的数据有效信号

wire  [DATA_WIDTH-1:0]      raw_data        ;  // 原始数据
wire                        raw_data_valid  ;  // 原始数据有效信号

wire                valid   [0:N-1] ;          // 有效信号数组
wire [DATA_WIDTH:0] data    [0:N-1] ;          // 数据数组（包含tuser位）

wire                O_raw_tlast_d0;            // 行结束信号，延迟0周期
wire                O_raw_tuser_d0;            // 帧开始信号，延迟0周期
wire                I_raw_tready;              // 模块准备好接受原始数据
wire [32:0]         next_line_data;            // 下一行数据
wire [32:0]         data_d2;                   // 数据延迟2个周期
wire                next_line_start;           // 下一行的开始信号
wire                bayer_ypos_d0;             // Bayer位置，延迟0周期

//---- 寄存器声明 ----
// matrix_*_line_buffer 是 96bit 滑窗（不是 RAM）：中间 4 个字节是本拍输出的 4 个像素，左右各 1 个字节是插值要用的邻像素。
/*********************************************************
******************4.寄存器信号声明*************************
*********************************************************/
// 定义寄存器信号
reg [95:0]      matrix_cur_line_buffer       ; // 当前行的3x3矩阵缓冲
reg [95:0]      matrix_last_line_buffer      ; // 上一行的3x3矩阵缓冲
reg [95:0]      matrix_next_line_buffer      ; // 下一行的3x3矩阵缓冲
reg             tlast_d0,tlast_d1,tlast_d2;     // 行结束信号延迟寄存器
reg             tuser_d0,tuser_d1,tuser_d2;     // 帧开始信号延迟寄存器
reg             ch_valid;                       // 数据通道有效信号
reg [13:0]      h_cnt;                          // 水平像素计数器
reg [13:0]      v_cnt,v_cnt_d;                  // 垂直像素计数器及其延迟
reg             next_line_data_valid;           // 下一行数据有效信号
reg             valid_d0,valid_d1;              // 有效信号延迟寄存器
reg             bayer_ypos_d;                   // Bayer位置延迟寄存器
reg  [32:0]     data_d0_d,data_d0;              // 数据延迟寄存器
reg  [32:0]     data_d1;

//---- 组合逻辑 ----
/*********************************************************
******************5.组合逻辑******************************
*********************************************************/
// 将数据和有效信号进行连接
assign data[0]  = {zhenghe_tuser, zhenghe_tdata};  // 将tuser和数据拼接
assign valid[0] = zhenghe_tvalid;                  // 第一个有效信号

// 将准备信号连接到上级模块
assign axi4s_video_tready = O_tready;

//---- 矩阵滑窗输出：三行窗口直接送给插值模块 ----
/*********************************************************/
// 将矩阵缓冲输出
assign matrix_last_line = matrix_last_line_buffer;
assign matrix_cur_line  = matrix_cur_line_buffer ;
assign matrix_next_line = matrix_next_line_buffer;

//---- Bayer 行相位判断 ----
// bayer_ypos_d0 = !v_cnt_d[0] & ch_valid：用「中心行的行号最低位」来区分两种行相位。
// BGGR 下同一行里 R/G/B 由列位置决定，而列位置就是下面滑窗里 matrix1x 的下标：
//   下标 4、6 与 5、7 交替，相邻两列必为一色一 G；
//   再配合行相位（本信号），就能确定每个位置到底是 R、Gr、Gb 还是 B。
// v_cnt_d 与 ch_valid 都是打 1 拍之后的量，所以它与同一拍输出的 matrix_*_line 描述的是同一行。
// 计算Bayer滤波器的行位置
assign bayer_ypos_d0 = !v_cnt_d[0] & ch_valid;  // 1 = 中心行处于「含 R、G」的行相位；0 = 「含 B、G」的行相位（插值模块里的 bayer_ypos_r1 就是它再打 2 拍）

/*********************************************************
******************6.模块实例化*****************************
*********************************************************/
//---- 例化 1：RAW10 -> RAW8（4 个 8bit/拍） ----
// 实例化mipi_to_raw_converter模块，将MIPI协议的数据转换为RAW数据
mipi_to_raw_converter mipi_to_raw_converter_r0(
    .I_clk       (I_clk  ),              // 时钟信号
    .I_rst_n     (I_rst_n),              // 复位信号，低有效
    .I_blk_bypass(I_blk_bypass),         // [HDR-2026-10-10] 黑电平扣除旁路透传
    .I_raw_tdata (axi4s_video_tdata ),   // 输入原始数据
    .I_raw_tdest (axi4s_video_tdest ),   // 输入目的地地址
    .I_raw_tlast (axi4s_video_tlast ),   // 输入行结束信号
    .I_raw_tvalid(axi4s_video_tvalid),   // 输入数据有效信号
    .I_raw_tuser (axi4s_video_tuser),    // 输入帧开始信号
    .I_raw_tready(I_raw_tready  ),       // 输出准备好信号
    .O_raw_tdata (raw_data      ),       // 输出原始数据
    .O_raw_tlast (O_raw_tlast_d0),       // 输出行结束信号
    .O_raw_tvalid(raw_data_valid),       // 输出数据有效信号
    .O_raw_tuser (O_raw_tuser_d0),       // 输出帧开始信号
    .O_raw_tready(1)                     // 模块始终准备好接受数据
);

//---- 例化 2：zhenghe（BRAM 弹性整合） ----
// 这里把 DATA_WIDTH 覆盖成 32（与 raw_data 位宽一致），IMG_WIDTH/IMG_HEIGHT 传工程实际值。
// 实例化“zhenghe”模块，将数据进行合并处理
zhenghe#(
    .IMG_WIDTH ( IMG_WIDTH ),
    .IMG_HEIGHT( IMG_HEIGHT),
    .DATA_WIDTH( 32),
    .data_complete_delay (data_complete_delay)
) 
zhenghe_d(
    .I_clk    (I_clk   ),               // 时钟信号
    .I_rst_n  (I_rst_n ),               // 复位信号，低有效

    .I_tlast  (O_raw_tlast_d0 ),        // 输入行结束信号
    .I_tuser  (O_raw_tuser_d0 ),        // 输入帧开始信号
    .I_tdata  (raw_data ),              // 输入原始数据
    .I_tvalid (raw_data_valid),         // 输入数据有效信号

    .O_tlast  (zhenghe_tlast ),         // 输出合并后的行结束信号
    .O_tuser  (zhenghe_tuser ),         // 输出合并后的帧开始信号
    .O_tdata  (zhenghe_tdata ),         // 输出合并后的数据
    .O_tvalid (zhenghe_tvalid)          // 输出合并后的数据有效信号
);

//---- 例化 3：两级行缓存（generate 展开成 2 个 line_buffer_demosaic） ----
// i=1：把 data[0] 延迟一行得到 data[1]；i=2：把 data[1] 再延迟一行得到 data[2]。
// 因此 data[0] 是当前收到的行，data[1] 是上一行，data[2] 是上两行（也是空间上最上面那一行）。
// 注意 I_tuser 取的是 data[i-1][32] & valid[i-1]：tuser 就存在 33bit 数据的最高位里，跟着数据一起过 BRAM。
// 生成两行缓冲区，使用线性缓冲区实现3x3矩阵的行数据缓存
genvar i;
generate
    for(i=1; i<3; i=i+1)
    begin: two_line_buffer  // 模块命名为two_line_buffer
        line_buffer_demosaic #(
            .IMG_HEIGHT (IMG_HEIGHT),
            .IMG_WIDTH  (IMG_WIDTH )
        ) line_buffer_demosaic_r1 (
            .I_clk     ( I_clk      ),    // 时钟信号
            .I_rst_n   ( I_rst_n    ),    // 复位信号，低有效
            .I_tuser   ( data[i-1][32] & valid[i-1]), // 输入帧开始信号
            .I_valid   ( valid[i-1] ),    // 输入有效信号
            .I_data    ( data[i-1]  ),    // 输入数据
            .O_valid   ( valid[i]   ),    // 输出有效信号
            .O_data    ( data[i]    )     // 输出数据
        );           
    end        
endgenerate

//---- 三行数据对齐打拍 ----
// 每一级 BRAM 的读出口相对写入口会多 1 拍，所以 data[1] 比 data[0] 多 1 拍、data[2] 比 data[0] 多 2 拍。
// 为了让三行在同一拍上对应同一列，这里把 data[0] 再延 2 拍（data_d0_d -> data_d0）、把 data[1] 延 1 拍（data_d1）、data[2] 不延（data_d2）。
// 对齐完成后：data_d2 = 上两行、data_d1 = 上一行、data_d0 = 当前行，三者在同一拍上列号相同。
// 由于在BRAM中每次输出数据都会延迟一个周期，所以要使这些数据对齐，需要对这些数据进行延迟处理，其中data[0]延迟2个周期，data[1]延迟一个周期
always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n) begin
        data_d0_d <= 0;
        data_d0   <= 0;
        data_d1   <= 0;
        valid_d0  <= 0;
        valid_d1  <= 0;
    end
    else begin
        valid_d0  <= valid[0];
        valid_d1  <= valid_d0;
        data_d0_d <= data[0];
        data_d0   <= data_d0_d;
        data_d1   <= data[1];
    end
end

assign data_d2 = data[2];
//---- 3×3 矩阵的形成：滑窗与边界复制填充 ----
// 每个 matrix_*_line_buffer 是 96bit 的滑窗：每拍把 [63:0] 左移 32bit、再把本行最新的 4 个像素字补进 [31:0]。
// 于是 [71:24] 这 48bit（6 个连续像素）天然构成「中间 4 个是本拍输出的像素、两端各多 1 个边界像素」的窗口：
//   [63:32] 的 4 个字节 = 本拍输出的 4 个像素（插值模块里的 matrix14..matrix17）；
//   [71:64] 与 [31:24] 各剩 1 个像素，对应插值模块里的 matrix13 / matrix18（两者的图像左右对应关系未能从本文件确认）。
// 三个行下标：last = 空间上方那行、cur = 中心那行、next = 空间下方那行。
// 边界不补零而是复制边界像素，避免在图像边缘引入黑色边框。
/*********************************************************
***********3x3矩阵的形成，以及对边界元素的补充处理***********
*********************************************************/

always @(posedge I_clk or negedge I_rst_n) begin 
    if(!I_rst_n) begin
        matrix_last_line_buffer <= 'b0 ;
        matrix_cur_line_buffer  <= 'b0 ;
        matrix_next_line_buffer <= 'b0 ;
    end else if(valid_d1) begin
// 帧首第一行（v_cnt==0）：上下都没有真实的行，三行一律取当前行，等于「把本行同时当作上一行和下一行」
        if(v_cnt == 0) begin  // 第一行
// 行首像素：边界槽位 [71:64] 不补零，直接复制本拍的第一个像素 data_d0[31:24]，输出仍是本拍这 4 个像素
            if(h_cnt == 0) begin  // 第一行的第一个像素
                matrix_last_line_buffer <= {{24{1'b0}}, data_d0[31:24], data_d0[31:0], data_d0[31:0]} ;
                matrix_cur_line_buffer  <= {{24{1'b0}}, data_d0[31:24], data_d0[31:0], data_d0[31:0]} ;
                matrix_next_line_buffer <= {{24{1'b0}}, data_d0[31:24], data_d0[31:0], data_d0[31:0]} ;
// 行尾像素：边界槽位 [31:24] 复制本行最后一个像素（先把 [63:0] 左移、再把 8bit 的边界像素塞回去），其余位补零
            end else if(h_cnt == (IMG_WIDTH_4x - 1)) begin  // 第一行的最后一个像素
                matrix_last_line_buffer <= {matrix_next_line_buffer [63:0], matrix_next_line_buffer[7:0], {24{1'b0}}} ;
                matrix_cur_line_buffer  <= {matrix_next_line_buffer [63:0], matrix_next_line_buffer[7:0], {24{1'b0}}} ;
                matrix_next_line_buffer <= {matrix_next_line_buffer [63:0], matrix_next_line_buffer[7:0], {24{1'b0}}} ;
// 行中间像素：正常滑动，把本拍 4 个像素整体移进最低 32bit
            end else begin  // 第一行的中间像素
                matrix_last_line_buffer <= {matrix_next_line_buffer[63:0], data_d0[31:0]} ;
                matrix_cur_line_buffer  <= {matrix_next_line_buffer[63:0], data_d0[31:0]} ;
                matrix_next_line_buffer <= {matrix_next_line_buffer[63:0], data_d0[31:0]} ;
            end
        end
// 第二行（v_cnt==1）：上面还没有真实行，matrix_last 跟随 matrix_cur，等于把第 1 行复制到上方做边界
        else if(v_cnt == 1) begin  // 第二行
            if(h_cnt == 0) begin  // 第二行的第一个像素
                matrix_last_line_buffer <= {{24{1'b0}}, data_d1[31:24], data_d1[31:0], data_d1[31:0]} ;
                matrix_cur_line_buffer  <= {{24{1'b0}}, data_d1[31:24], data_d1[31:0], data_d1[31:0]} ;
                matrix_next_line_buffer <= {{24{1'b0}}, data_d0[31:24], data_d0[31:0], data_d0[31:0]} ;
            end else if(h_cnt == (IMG_WIDTH_4x - 1)) begin  // 第二行的最后一个像素
                matrix_last_line_buffer <= {matrix_cur_line_buffer [63:0], matrix_cur_line_buffer[7:0], {24{1'b0}}} ;
                matrix_cur_line_buffer  <= {matrix_cur_line_buffer [63:0], matrix_cur_line_buffer[7:0], {24{1'b0}}} ;
                matrix_next_line_buffer <= {matrix_next_line_buffer [63:0], matrix_next_line_buffer[7:0], {24{1'b0}}} ;
            end else begin  // 第二行的中间像素
                matrix_last_line_buffer <= {matrix_cur_line_buffer[63:0],  data_d1[31:0]} ;
                matrix_cur_line_buffer  <= {matrix_cur_line_buffer[63:0],  data_d1[31:0]} ;
                matrix_next_line_buffer <= {matrix_next_line_buffer[63:0], data_d0[31:0]} ;
            end
        end
// 第三行及以后：last/cur/next 分别是上两行(data_d2)、上一行(data_d1)、当前行(data_d0)，三行都是真实数据
        else begin  // 第三行及以后
            if(h_cnt == 0) begin  // 第一个像素
                matrix_last_line_buffer <= {{24{1'b0}}, data_d2[31:24], data_d2[31:0], data_d2[31:0]} ;
                matrix_cur_line_buffer  <= {{24{1'b0}}, data_d1[31:24], data_d1[31:0], data_d1[31:0]} ;
                matrix_next_line_buffer <= {{24{1'b0}}, data_d0[31:24], data_d0[31:0], data_d0[31:0]} ;
            end else if(h_cnt == (IMG_WIDTH_4x - 1)) begin  // 最后一个像素
                matrix_last_line_buffer <= {matrix_last_line_buffer[63:0], matrix_last_line_buffer[7:0], {24{1'b0}}} ;
                matrix_cur_line_buffer  <= {matrix_cur_line_buffer [63:0], matrix_cur_line_buffer [7:0], {24{1'b0}}} ;
                matrix_next_line_buffer <= {matrix_next_line_buffer[63:0], matrix_next_line_buffer[7:0], {24{1'b0}}} ;
            end else begin  // 中间像素
                matrix_last_line_buffer <= {matrix_last_line_buffer[63:0], data_d2[31:0]} ;
                matrix_cur_line_buffer  <= {matrix_cur_line_buffer [63:0], data_d1[31:0]} ;
                matrix_next_line_buffer <= {matrix_next_line_buffer[63:0], data_d0[31:0]} ;
            end  
        end
    end
    else begin  // 非有效拍：三行滑窗清零，避免下游把残值当数据用
        matrix_last_line_buffer <= 'b0 ;
        matrix_cur_line_buffer  <= 'b0 ;
        matrix_next_line_buffer <= 'b0 ;
    end 
end

//---- 行列计数器 ----
// h_cnt：每个有效拍 +1，到 IMG_WIDTH_4x-1 回绕到 0。因为一拍搬 4 个像素，所以「一行的拍数」就是 IMG_WIDTH_4x。
// v_cnt：只在行尾（h_cnt 回绕的那一拍）加 1，到 IMG_HEIGHT-1 回绕到 0，因此它就是行号。
// 两者都在帧首由 zhenghe_tuser 清零；h_cnt 回绕与 v_cnt 加 1 用的是同一拍，所以行号与列位置的配合不会错位。
// 计算水平和垂直计数器
always @(posedge I_clk or negedge I_rst_n) begin
    if(!I_rst_n || zhenghe_tuser) begin
        h_cnt <= 0;
        v_cnt <= 0;
    end else begin
        h_cnt    <= valid_d1 ? ((h_cnt == IMG_WIDTH_4x - 1) ? 0 : h_cnt + 1) : h_cnt;  // h_cnt 回绕条件：IMG_WIDTH_4x-1，即每行最后一个字
        v_cnt    <= valid_d1 && (h_cnt == IMG_WIDTH_4x - 1) ? ((v_cnt == IMG_HEIGHT - 1) ? 0 : v_cnt + 1) : v_cnt;  // v_cnt 只在 h_cnt 回绕那一拍加 1；到 IMG_HEIGHT-1 回绕，保证帧内行号单调
    end
end

//---- 有效信号与行相位的延迟对齐 ----
// ch_valid 是再打 1 拍的有效信号，与同一拍输出的 matrix_*_line 严格同相；
// v_cnt_d 同样再打 1 拍，用它的最低位给出 bayer_ypos，正好对应同一行。
// 数据有效信号的延迟处理
always @(posedge I_clk or negedge I_rst_n) begin
    if(!I_rst_n) begin
        ch_valid <= 0;
        v_cnt_d <= 0;
    end else begin
        ch_valid <= valid_d1 ;
        v_cnt_d  <= v_cnt;
    end
end

assign bayer_ypos = bayer_ypos_d0 ;  // 对外的行相位就是上面算出来的 bayer_ypos_d0，它经过 ch_valid 门控，非有效拍时为 0

//---- 流控信号同步 ----
// tuser/tlast 各打 3 拍，使它们与已经过 3 拍（BRAM 打拍 + 上面的对齐打拍）的数据重新对齐，然后才输出。
// 对tuser和tlast信号进行同步处理，此时数据和流控制信号已经同步
always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n) begin
        tlast_d0 <= 0;
        tlast_d1 <= 0;
        tlast_d2 <= 0;
        tuser_d0 <= 0;
        tuser_d1 <= 0;
        tuser_d2 <= 0;
    end
    else begin
        tlast_d0 <= zhenghe_tlast;
        tlast_d1 <= tlast_d0;
        tlast_d2 <= tlast_d1;
        tuser_d0 <= zhenghe_tuser;
        tuser_d1 <= tuser_d0;
        tuser_d2 <= tuser_d1;
    end
end

// 将同步后的信号输出
assign O_tuser  = tuser_d2;  // 输出帧首（与数据同相）
assign O_tlast  = tlast_d2;  // 输出行尾（与数据同相）
assign O_tvalid = ch_valid;  // 输出数据有效：ch_valid 与 matrix_*_line 同拍


endmodule


