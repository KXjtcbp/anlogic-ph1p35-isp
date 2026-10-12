//=============================================================================
// 文件      : isp/demosaic_4x_2_0/bilinear_interpolation.v
// 模块      : bilinear_interpolation
// 功能      : 双线性去马赛克插值：对 3×3 窗口里的 4 个像素（matrix14..matrix17）分别算出 R/G/B 三个通道——本来就是这个颜色的像素取原值，缺的颜色用同色邻居的算术平均代替。全部运算只有加法与 >>1（除以 2）、>>2（除以 4），没有任何乘法。
// 数据通路  : matrix_last/cur/next_line[95:0] + bayer_ypos -> 拆成 3 行 × 6 像素（matrix03..matrix28）-> 按相位求部分和（sum_part0/1，9bit）-> 总和（matrix_plus，10bit）-> 均值（mean，9bit，按相位选择不除 / >>1 / >>2）-> 8bit 饱和 -> 打包成 {8'b0,R,G,B} × 4 -> rgb_data[127:0] -> O_tdata[127:0]
// 时钟/复位 : 单时钟域 I_clk；I_rst_n 低有效，异步复位。内部共 5 级流水（部分和 -> 总和 -> 均值 -> 饱和 -> 打包），输出有效信号 I_tvalid_r[4] 就是 I_tvalid 打 5 拍的结果。
// 依赖      : 无子模块、无 RAM、无 DSP（没有任何乘法）；只用 generate 按 BAYER_MODE 选择相位分支。
// 综合/实现 : ■ 四个相位分支（BGGR / GBRG / RGGB / GRBG）用 generate if / else if 并列展开，同一时刻只有一个分支会被实现；本工程由 isp_top.v:116-121 传 BAYER_MODE="BGGR"，所以实际综合出来的只有 BAYER_MODE_BGGR 这一个分支。
//           ■ 位宽关系：sum_part* 是 9bit（2 个 8bit 相加），matrix_plus 是 10bit（最多 4 个 8bit 相加），mean 是 9bit（最高位 [8] 用来判断结果是否超过 255），最后饱和成 8bit。
//           ■ 本文件自带的 version 2.0 文件头记录的是上游（官方）修正 RGGB/GBRG 分支里三元操作符判断分支写反的问题；本工程自官方 lab3 基线导入后没有再改动本文件。
//           ■ 算法性质：这是纯线性平均的双线性插值，没有沿边缘方向的梯度比较与方向修正，因此在高频细节处会产生 zipper（拉链）伪影与伪彩，详见下面「算法性质」那段注释。
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
@Time        :   2025/8 
version:     :   2.0
@Description :   由于RGGB和GBRG的Bayer格式中的三元操作符的条件判断分支是颠倒的，
                 导致在需要插值的地方使用了原始值，在有原始值的地方进行了错误的
                 平均，现在重写修改了此处，让其正确的去进行平均。
*****************************************************************/


//---- 模块参数：Bayer 相位 ----
// BAYER_MODE 决定用下面哪一个 generate 分支；本工程传 "BGGR"。
// 四个分支的差别只是「哪一路该取平均、哪一路该取原值」的相位互换，算法结构完全相同。
module bilinear_interpolation #(
    parameter BAYER_MODE = "BGGR"
)(
//---- 端口：窗口输入 + 4 像素 RGB 输出 ----
    input             I_clk            ,
    input             I_rst_n          ,

    //input
    input             I_tlast          ,
    input             I_tuser          ,
    input             I_tvalid         ,
    output            I_tready         ,
  
    input             bayer_ypos       ,
    input   [95:0]    matrix_last_line ,
    input   [95:0]    matrix_cur_line  ,
    input   [95:0]    matrix_next_line ,
  
    //output
    output            O_tlast         ,
    output            O_tuser         ,
    output [127 : 0]  O_tdata         ,
    output            O_tvalid        ,
    input             O_tready

);

//---- function 与相位常量 ----
/*********************************************************
                  function 声明
*********************************************************/
// calculate the data's bit width
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
                      RAW格式
*********************************************************/
// bayer mode 
////bayer格式
localparam RGGB = "RGGB";
localparam BGGR = "BGGR";
localparam GBRG = "GBRG";
localparam GRBG = "GRBG";



//---- 寄存器声明：三级流水对应的三组寄存器 ----
//  *_sum_part0 / *_sum_part1（9bit）：一拍最多 2 个 8bit 像素相加得到的部分和，拆成两组是为了让相加不至于一次太长；
//  *_matrix_plus（10bit）：两个部分和再相加得到的总和（最多 4 个像素之和）；
//  *_mean（9bit）：总和除以 1 / 2 / 4 之后的通道均值，最高位 [8] 留作溢出判断。
/*********************************************************
                       reg 信号声明
*********************************************************/
reg         bayer_ypos_r0,  bayer_ypos_r1;

reg [9:0]   r0_matrix_plus, g0_matrix_plus, b0_matrix_plus ;
reg [9:0]   r1_matrix_plus, g1_matrix_plus, b1_matrix_plus ;
reg [9:0]   r2_matrix_plus, g2_matrix_plus, b2_matrix_plus ;
reg [9:0]   r3_matrix_plus, g3_matrix_plus, b3_matrix_plus ;
// -----------------------------------------------------------------

reg [8:0]   r0_sum_part0, r0_sum_part1 ;
reg [8:0]   r1_sum_part0, r1_sum_part1 ;
reg [8:0]   r2_sum_part0, r2_sum_part1 ;
reg [8:0]   r3_sum_part0, r3_sum_part1 ;

reg [8:0]   g0_sum_part0, g0_sum_part1 ;
reg [8:0]   g1_sum_part0, g1_sum_part1 ;
reg [8:0]   g2_sum_part0, g2_sum_part1 ;
reg [8:0]   g3_sum_part0, g3_sum_part1 ;

reg [8:0]   b0_sum_part0, b0_sum_part1 ;
reg [8:0]   b1_sum_part0, b1_sum_part1 ;
reg [8:0]   b2_sum_part0, b2_sum_part1 ;
reg [8:0]   b3_sum_part0, b3_sum_part1 ;

// 下标约定：r0..r3 / g0..g3 / b0..b3 就是同一拍 4 个像素各自的三个通道；
// 它们与下面 96bit 窗口里的 matrix14..matrix17 一一对应（r0 对 matrix14、r1 对 matrix15、r2 对 matrix16、r3 对 matrix17）。
// -----------------------------------------------------------------
reg [8:0]   r0_mean, g0_mean, b0_mean ;
reg [8:0]   r1_mean, g1_mean, b1_mean ;
reg [8:0]   r2_mean, g2_mean, b2_mean ;
reg [8:0]   r3_mean, g3_mean, b3_mean ;
// -----------------------------------------------------------------
// 4 个像素的 RGB 打包结果，每个像素 32bit = {8'b0, R[7:0], G[7:0], B[7:0]}
reg [31:0] rgb_data0 ;
reg [31:0] rgb_data1 ;
reg [31:0] rgb_data2 ;
reg [31:0] rgb_data3 ;

// 流水线有效信号：I_tvalid_r 是 5 位移位寄存器，每位对应一级流水
//   I_tvalid      -> 求部分和；[0] -> 求总和；[1] -> 求均值；[2] -> 8bit 饱和；[3] -> 打包；[4] -> 送输出
reg   [4:0]   I_tlast_r ;
reg   [4:0]   I_tuser_r ;
reg   [4:0]   I_tvalid_r;
/*********************************************************
                    wire 信号声明
*********************************************************/

//---- 6 像素滑窗的拆线 ----
// matrix_*_line 是 96bit：[95:72] 补零、[71:64] 与 [31:24] 各只剩 1 个像素、中间 [63:32] 是 4 个像素。
// 这里把三行各自的 [71:24] 拆成 6 个 8bit 像素：
//   matrixX3 = 边界槽位 [71:64] 里的那 1 个像素（位于中心 4 像素的一侧，对应图像左还是右未能从本文件确认）
//   matrixX4..matrixX7 = 本拍要输出的 4 个像素
//   matrixX8 = 边界槽位 [31:24] 里的那 1 个像素（位于中心 4 像素的另一侧，对应图像左还是右未能从本文件确认）
// 行下标 X：0 = 上一行（空间上方）、1 = 中心行、2 = 下一行；列下标 Y 越大越靠近 MSB 端（左右对应关系同上未能确认）。
// bayer format BGGR 
wire    [7:0]   matrix03, matrix04, matrix05, matrix06, matrix07, matrix08 ;
wire    [7:0]   matrix13, matrix14, matrix15, matrix16, matrix17, matrix18 ;
wire    [7:0]   matrix23, matrix24, matrix25, matrix26, matrix27, matrix28 ;


wire    [127:0] rgb_data;
wire            rgb_data_valid ;
/*********************************************************
                        信号描述
*********************************************************/
assign {matrix03, matrix04, matrix05, matrix06, matrix07, matrix08} = matrix_last_line[71:24];
assign {matrix13, matrix14, matrix15, matrix16, matrix17, matrix18} = matrix_cur_line[71:24];
assign {matrix23, matrix24, matrix25, matrix26, matrix27, matrix28} = matrix_next_line[71:24];



//---- 信号延迟：Bayer 行相位打 2 拍 ----
// bayer_ypos_r0 是 bayer_ypos 打 1 拍、bayer_ypos_r1 再打 1 拍；
// 因为求均值那一级（用 I_tvalid_r[1] 门控）比输入晚了 2 拍，所以相位也要跟着延迟 2 拍才能对齐。
/*********************************************************
                        信号延迟
*********************************************************/
// pipleline 0
always @(posedge I_clk or negedge I_rst_n) begin
    if(!I_rst_n) begin 
        bayer_ypos_r0 <= 'b0 ;
        bayer_ypos_r1 <= 'b0 ;
    end
    else begin
        bayer_ypos_r0 <= bayer_ypos ;
        bayer_ypos_r1 <= bayer_ypos_r0 ;
    end
end

/*****************************************************************
                        BAYER_MODE_BGGR                                        
*****************************************************************/

//---- 算法性质：纯线性平均的双线性插值（这是已知的画质特性，不是缺陷报告） ----
// 本模块对每个像素只用「同色邻居的算术平均」来估计缺失的两个通道，全部运算只有加法与 >>1（除以 2）、>>2（除以 4），
// 没有任何乘法，也没有沿水平/垂直方向的梯度比较与方向修正。因此在高频细节（细密条纹、锐利边缘）处会有两类已知伪影：
//   · zipper（拉链）伪影：边缘两侧的插值结果沿边缘方向交替偏亮/偏暗，看起来像拉链；
//   · 伪彩：R/B 平面在高频处被错误平均，在边缘上出现原本并不存在的颜色。
// 这是本工程做画质调优时的已知结论，只说明机制，不代表本文件相对某个版本有缺陷。
////////////////////////////////////////////
//
//              双线性插值算法
//
////////////////////////////////////////////
// mipi ov5640 raw
//---- BGGR 相位：bayer_ypos=1 时中心行是「G R G R」，bayer_ypos=0 时是「B G B G」 ----
// 每拍对 4 个像素（matrix14..matrix17）各算 R/G/B 三个通道，取法只有四种：
//   · 像素本身就是这个颜色（例如相机阵列在该位置的滤色片就是它）-> 直接取原值，不除；
//   · 同行的左右两个同色邻居 -> 相加后 >>1（除以 2）；
//   · 上下的两个同色邻居     -> 相加后 >>1（除以 2）；
//   · 只有上/下/左/右的 4 个同色邻居 -> 相加后 >>2（除以 4）。
// 判断用哪一路，靠的就是 bayer_ypos_r1 给出的行相位加上像素在 4 个位置里的下标（列相位）。
generate if(BAYER_MODE == BGGR) begin : BAYER_MODE_BGGR
    // R Channel
//---- BGGR 的 R 通道：算出 4 个像素各自需要的 R 之和 ----
// 每个求和拆成 part0/part1 两组（各不超过 2 个像素），下一拍再相加成总和。
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_sum_part0, r0_sum_part1} <= 'd0 ; 
            r1_sum_part0  <= 'd0 ; 
            {r2_sum_part0, r2_sum_part1}  <= 'd0 ; 
            r3_sum_part0  <= 'd0 ; 
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                r0_sum_part0 <= matrix13 + matrix15 ;
                r0_sum_part1 <= 'd0 ;
        
                r1_sum_part0 <= matrix15 ;
        
                r2_sum_part0 <= matrix15 + matrix17 ;
                r2_sum_part1 <= 'd0 ;
        
                r3_sum_part0 <= matrix17 ;
            end
            else begin
                r0_sum_part0 <= matrix03 + matrix05 ;
                r0_sum_part1 <= matrix23 + matrix25 ;

                r1_sum_part0 <= matrix05 + matrix25 ;

                r2_sum_part0 <= matrix05 + matrix07 ;
                r2_sum_part1 <= matrix25 + matrix27 ;

                r3_sum_part0 <= matrix07 + matrix27 ;
            end
        end
    end

// G Channel
//---- BGGR 的 G 通道：算出 4 个像素各自需要的 G 之和 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {g0_sum_part0, g0_sum_part1} <= 'b0 ;
            {g1_sum_part0, g1_sum_part1} <= 'b0 ;
            {g2_sum_part0, g2_sum_part1} <= 'b0 ;
            {g3_sum_part0, g3_sum_part1} <= 'b0 ;
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                g0_sum_part0 <= matrix14 ;
                g0_sum_part1 <= 'd0 ;

                g1_sum_part0 <= matrix05 + matrix25 ;
                g1_sum_part1 <= matrix14 + matrix16 ;

                g2_sum_part0 <= matrix16;
                g2_sum_part1 <= 'd0 ;

                g3_sum_part0 <= matrix07 + matrix27 ; 
                g3_sum_part1 <= matrix16 + matrix18 ;
            end
            else begin
                g0_sum_part0 <= matrix04 + matrix24 ;
                g0_sum_part1 <= matrix13 + matrix15 ;

                g1_sum_part0 <= matrix15 ;
                g1_sum_part1 <= 'd0 ;

                g2_sum_part0 <= matrix06 + matrix26 ;
                g2_sum_part1 <= matrix15 + matrix17 ;

                g3_sum_part0 <= matrix17 ; 
                g3_sum_part1 <= 'd0 ;
            end
        end
    end
//B Channel
//---- BGGR 的 B 通道：算出 4 个像素各自需要的 B 之和 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            b0_sum_part0 <= 'd0 ;
            {b1_sum_part0, b1_sum_part1} <= 'd0 ;
            b2_sum_part0 <= 'd0 ;
            {b3_sum_part0, b3_sum_part1} <= 'd0 ;
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                b0_sum_part0 <= matrix04 + matrix24 ;

                b1_sum_part0 <= matrix04 + matrix06 ;
                b1_sum_part1 <= matrix24 + matrix26 ;

                b2_sum_part0 <= matrix06 + matrix26 ;

                b3_sum_part0 <= matrix06 + matrix08 ;
                b3_sum_part1 <= matrix26 + matrix28 ;
            end
            else begin
                b0_sum_part0 <= matrix14 ;

                b1_sum_part0 <= matrix14 + matrix16 ;
                b1_sum_part1 <= 'd0 ;

                b2_sum_part0 <= matrix16 ;

                b3_sum_part0 <= matrix16 + matrix18 ;
                b3_sum_part1 <= 'd0 ;
            end
        end
    end

//---- 两组部分和相加成通道总和（10bit，最多 4 个 8bit 像素） ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_matrix_plus, g0_matrix_plus, b0_matrix_plus} <= 'd0 ;
            {r1_matrix_plus, g1_matrix_plus, b1_matrix_plus} <= 'd0 ;
            {r2_matrix_plus, g2_matrix_plus, b2_matrix_plus} <= 'd0 ;
            {r3_matrix_plus, g3_matrix_plus, b3_matrix_plus} <= 'd0 ;
        end
        else if(I_tvalid_r[0])begin
            r0_matrix_plus <= r0_sum_part0 + r0_sum_part1 ;
            r1_matrix_plus <= r1_sum_part0 ;
            r2_matrix_plus <= r2_sum_part0 + r2_sum_part1 ;
            r3_matrix_plus <= r3_sum_part0 ;

            g0_matrix_plus <= g0_sum_part0 + g0_sum_part1 ;
            g1_matrix_plus <= g1_sum_part0 + g1_sum_part1 ;
            g2_matrix_plus <= g2_sum_part0 + g2_sum_part1 ;
            g3_matrix_plus <= g3_sum_part0 + g3_sum_part1 ;

            b0_matrix_plus <= b0_sum_part0 ;
            b1_matrix_plus <= b1_sum_part0 + b1_sum_part1 ;
            b2_matrix_plus <= b2_sum_part0 ;
            b3_matrix_plus <= b3_sum_part0 + b3_sum_part1 ;
        end
    end


    // pipleline 1
//---- 除以 1 / 2 / 4 得到通道均值：整段只用 >>1 与 >>2，没有乘法 ----
// 每个均值都是一句三元表达式：bayer_ypos_r1 为真时走一支、为假时走另一支，
// 「不移位」表示这一路本来就是原值，「>>1」表示 2 个同色邻居的平均，「>>2」表示 4 个同色邻居的平均。
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_mean, g0_mean, b0_mean} <= 'd0 ;
            {r1_mean, g1_mean, b1_mean} <= 'd0 ;
            {r2_mean, g2_mean, b2_mean} <= 'd0 ;
            {r3_mean, g3_mean, b3_mean} <= 'd0 ;
        end
        else if(I_tvalid_r[1]) begin
            r0_mean <= bayer_ypos_r1 ? r0_matrix_plus >> 1 : r0_matrix_plus >> 2 ;  // r0=matrix14：中心行是 G R G R 时，它的 R 只能取本行左右两个 R（2 个样本 -> >>1 除以 2）；是 B G B G 时取 4 个对角 R（4 个样本 -> >>2 除以 4）
            g0_mean <= bayer_ypos_r1 ? g0_matrix_plus      : g0_matrix_plus >> 2 ;  // g0=matrix14：前一种相位它本身就是 G（取原值，不移位）；后一种相位取上/下/左/右 4 个 G（>>2 除以 4）
            b0_mean <= bayer_ypos_r1 ? b0_matrix_plus >> 1 : b0_matrix_plus      ;  // b0=matrix14：前一种相位取上下两个 B（>>1 除以 2）；后一种相位它本身就是 B（取原值）

            r1_mean <= bayer_ypos_r1 ? r1_matrix_plus      : r1_matrix_plus >> 1 ;  // r1=matrix15：G R G R 行里它本身就是 R（原值）；B G B G 行里取上下两个 R（>>1 除以 2）
            g1_mean <= bayer_ypos_r1 ? g1_matrix_plus >> 2 : g1_matrix_plus ;  // g1=matrix15：G R G R 行里它本身是 R，要取上/下连同行的 4 个 G（>>2 除以 4）；B G B G 行里它本身就是 G（原值）
            b1_mean <= bayer_ypos_r1 ? b1_matrix_plus >> 2 : b1_matrix_plus >> 1 ;  // b1=matrix15：G R G R 行里取 4 个对角 B（>>2 除以 4）；B G B G 行里取同行左右两个 B（>>1 除以 2）

            r2_mean <= bayer_ypos_r1 ? r2_matrix_plus >> 1 : r2_matrix_plus >> 2;  // r2=matrix16：与 r0 同构，只是邻像素取的是 matrix15/matrix17 那一侧
            g2_mean <= bayer_ypos_r1 ? g2_matrix_plus      : g2_matrix_plus >> 2;     // g2=matrix16：与 g0 同构
            b2_mean <= bayer_ypos_r1 ? b2_matrix_plus >> 1 : b2_matrix_plus ;  // b2=matrix16：与 b0 同构

            r3_mean <= bayer_ypos_r1 ? r3_matrix_plus      : r3_matrix_plus >> 1 ;  // r3=matrix17：与 r1 同构（它是这一拍 4 个像素里最右边那个）
            g3_mean <= bayer_ypos_r1 ? g3_matrix_plus >> 2 : g3_matrix_plus ;  // g3=matrix17：与 g1 同构
            b3_mean <= bayer_ypos_r1 ? b3_matrix_plus >> 2 : b3_matrix_plus >> 1 ;  // b3=matrix17：与 b1 同构
        end
    end
end


/*****************************************************************
                        BAYER_MODE_GBRG                                             
*****************************************************************/



//---- GBRG 分支：算法结构与 BGGR 完全相同，但相位条件整体取反 ----
// 本分支的三元表达式写成 bayer_ypos_r1 ? 平均 : 原值 或 (!bayer_ypos_r1) ? ... : ...，
// 与 BGGR 的写法相反（文件头 version 2.0 提到的「RGGB/GBRG 的条件判断分支颠倒」就是指这里）；
// 阅读时请把每个「?」与「:」的两支和 BGGR 对照，注意哪一支是原值、哪一支是 >>1/>>2 的平均。
    else if(BAYER_MODE == GBRG)
    begin:BAYER_MODE_GBRG

    // R Channel
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_sum_part0, r0_sum_part1} <= 'd0 ; 
            {r1_sum_part0, r1_sum_part1}  <= 'd0 ; 
            r2_sum_part0  <= 'd0 ; 
            {r3_sum_part0, r3_sum_part1}  <= 'd0 ; 
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                r0_sum_part0 <= matrix14 ;
                r0_sum_part1 <= 'd0;

                r1_sum_part0 <= matrix14 + matrix16;
                r1_sum_part1 <= 'd0;

                r2_sum_part0 <= matrix16;

                r3_sum_part0 <= matrix16 + matrix18 ;
                r3_sum_part1 <= 'd0;
            end
            else begin
                r0_sum_part0 <= 'd0;
                r0_sum_part1 <= matrix04 + matrix24;

                r1_sum_part0 <= matrix04 + matrix06 ;
                r1_sum_part1 <= matrix24 + matrix26 ;

                r2_sum_part0 <= matrix06 + matrix26 ;

                r3_sum_part0 <= matrix06 + matrix26 ;
                r3_sum_part1 <= matrix08 + matrix28 ;
            end
        end
    end
// G Channel
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {g0_sum_part0, g0_sum_part1} <= 'b0 ;
            {g1_sum_part0, g1_sum_part1} <= 'b0 ;
            {g2_sum_part0, g2_sum_part1} <= 'b0 ;
            {g3_sum_part0, g3_sum_part1} <= 'b0 ;
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                g0_sum_part0 <= matrix04 + matrix24;
                g0_sum_part1 <= matrix13 + matrix15;

                g1_sum_part0 <= matrix15;
                g1_sum_part1 <= 'd0 ;

                g2_sum_part0 <= matrix06 + matrix26 ;
                g2_sum_part1 <= matrix15 + matrix17 ;

                g3_sum_part0 <= matrix17  ; 
                g3_sum_part1 <= 'd0 ;
            end
            else begin
                g0_sum_part0 <= matrix14 ;
                g0_sum_part1 <= 'd0;

                g1_sum_part0 <= matrix05 + matrix25;
                g1_sum_part1 <= matrix14 + matrix16;

                g2_sum_part0 <= matrix16 ;
                g2_sum_part1 <= 'd0;

                g3_sum_part0 <= matrix07 + matrix27; 
                g3_sum_part1 <= matrix16 + matrix18;
            end
        end
    end
//B Channel
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {b0_sum_part0, b0_sum_part1} <= 'd0 ;
            {b1_sum_part0, b1_sum_part1} <= 'd0 ;
            {b2_sum_part0, b2_sum_part1} <= 'd0 ;
            {b3_sum_part0, b3_sum_part1} <= 'd0 ;
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                b0_sum_part0 <= matrix03 + matrix23 ;//????
                b0_sum_part1 <= matrix05 + matrix25 ;//????

                b1_sum_part0 <= 'd0;//????
                b1_sum_part1 <= matrix05 + matrix25 ;

                b2_sum_part0 <= matrix05 + matrix25 ;
                b2_sum_part1 <= matrix07 + matrix27 ;

                b3_sum_part0 <= 'd0 ;//????
                b3_sum_part1 <= matrix07 + matrix27 ;
            end
            else begin
                b0_sum_part0 <= matrix13 + matrix15 ;
                b0_sum_part1 <= 'd0;

                b1_sum_part0 <= matrix15 ;
                b1_sum_part1 <= 'd0 ;

                b2_sum_part0 <= matrix15 +  matrix17;
                b2_sum_part1 <= 'd0;

                b3_sum_part0 <= matrix17 ;
                b3_sum_part1 <= 'd0 ;
            end
        end
    end

    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_matrix_plus, g0_matrix_plus, b0_matrix_plus} <= 'd0 ;
            {r1_matrix_plus, g1_matrix_plus, b1_matrix_plus} <= 'd0 ;
            {r2_matrix_plus, g2_matrix_plus, b2_matrix_plus} <= 'd0 ;
            {r3_matrix_plus, g3_matrix_plus, b3_matrix_plus} <= 'd0 ;
        end
        else if(I_tvalid_r[0])begin
            r0_matrix_plus <= r0_sum_part0 + r0_sum_part1 ;
            r1_matrix_plus <= r1_sum_part0 + r1_sum_part1 ;
            r2_matrix_plus <= r2_sum_part0   ;
            r3_matrix_plus <= r3_sum_part0 + r3_sum_part1 ;

            g0_matrix_plus <= g0_sum_part0 + g0_sum_part1 ;
            g1_matrix_plus <= g1_sum_part0 + g1_sum_part1 ;
            g2_matrix_plus <= g2_sum_part0 + g2_sum_part1 ;
            g3_matrix_plus <= g3_sum_part0 + g3_sum_part1 ;

            b0_matrix_plus <= b0_sum_part0 + b0_sum_part1 ;
            b1_matrix_plus <= b1_sum_part0 + b1_sum_part1 ;
            b2_matrix_plus <= b2_sum_part0 + b2_sum_part1 ;
            b3_matrix_plus <= b3_sum_part0 + b3_sum_part1 ;
        end
    end


    // pipleline 1
//---- GBRG 的均值级：同样只用 >>1 与 >>2，条件取反 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_mean, g0_mean, b0_mean} <= 'd0 ;
            {r1_mean, g1_mean, b1_mean} <= 'd0 ;
            {r2_mean, g2_mean, b2_mean} <= 'd0 ;
            {r3_mean, g3_mean, b3_mean} <= 'd0 ;
        end
        else if(I_tvalid_r[1])begin
            r0_mean <= bayer_ypos_r1    ? r0_matrix_plus      : r0_matrix_plus >> 1 ;
            g0_mean <= (!bayer_ypos_r1) ? g0_matrix_plus      : g0_matrix_plus >> 2 ;
            b0_mean <= bayer_ypos_r1    ? b0_matrix_plus >> 2 : b0_matrix_plus >> 1 ;

            r1_mean <= bayer_ypos_r1    ? r1_matrix_plus >> 1 : r1_matrix_plus >> 2 ;
            g1_mean <= (!bayer_ypos_r1) ? g1_matrix_plus >> 2 : g1_matrix_plus      ;
            b1_mean <= bayer_ypos_r1 ? b1_matrix_plus >> 1 : b1_matrix_plus      ;

            r2_mean <= bayer_ypos_r1    ? r2_matrix_plus      : r2_matrix_plus >> 1 ;
            g2_mean <= (!bayer_ypos_r1) ? g2_matrix_plus      : g2_matrix_plus >> 2 ;   
            b2_mean <= bayer_ypos_r1    ? b2_matrix_plus >> 2 : b2_matrix_plus >> 1 ;

            r3_mean <= bayer_ypos_r1    ? r3_matrix_plus >> 1 : r3_matrix_plus >> 2 ;
            g3_mean <= (!bayer_ypos_r1) ? g3_matrix_plus >> 2 : g3_matrix_plus      ;
            b3_mean <= bayer_ypos_r1    ? b3_matrix_plus >> 1 : b3_matrix_plus      ;
        end
    end
end

/*****************************************************************
                       BAYER_MODE_RGGB                             
*****************************************************************/

//---- RGGB 分支：结构同 BGGR，条件同样写成 (!bayer_ypos_r1)，即与 BGGR 相反 ----
// 文件头 version 2.0 的修改说明就是针对 RGGB / GBRG 这两个分支的条件写法。
    else if(BAYER_MODE == RGGB)
    begin:BAYER_MODE_RGGB

    // R Channel
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_sum_part0, r0_sum_part1} <= 'd0 ; 
            {r1_sum_part0, r1_sum_part1}  <= 'd0 ; 
            r2_sum_part0  <= 'd0 ; 
            {r3_sum_part0, r3_sum_part1}  <= 'd0 ; 
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                r0_sum_part0 <= matrix04 + matrix24;//
                r0_sum_part1 <= 'd0;

                r1_sum_part0 <= matrix04 + matrix24;
                r1_sum_part1 <= matrix06 + matrix26;

                r2_sum_part0 <= matrix06 + matrix26;

                r3_sum_part0 <= matrix06 + matrix26;
                r3_sum_part1 <= matrix08 + matrix28;
            end
            else begin
                r0_sum_part0 <= matrix14;
                r0_sum_part1 <= 'd0;

                r1_sum_part0 <= matrix14 + matrix16;
                r1_sum_part1 <= 'd0;

                r2_sum_part0 <= matrix16  ;

                r3_sum_part0 <= matrix16 + matrix18 ;
                r3_sum_part1 <= 'd0 ;
            end
        end
    end
// G Channel
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {g0_sum_part0, g0_sum_part1} <= 'b0 ;
            {g1_sum_part0, g1_sum_part1} <= 'b0 ;
            {g2_sum_part0, g2_sum_part1} <= 'b0 ;
            {g3_sum_part0, g3_sum_part1} <= 'b0 ;
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                g0_sum_part0 <= matrix14 ;
                g0_sum_part1 <= 'd0;

                g1_sum_part0 <= matrix05 + matrix25;
                g1_sum_part1 <= matrix14 + matrix16;

                g2_sum_part0 <= matrix16 ;
                g2_sum_part1 <= 'd0;

                g3_sum_part0 <= matrix07 + matrix27; 
                g3_sum_part1 <= matrix16 + matrix18;
            end
            else begin
                g0_sum_part0 <= matrix04 + matrix24;
                g0_sum_part1 <= matrix13 + matrix15;

                g1_sum_part0 <= matrix15;
                g1_sum_part1 <= 'd0 ;

                g2_sum_part0 <= matrix06 + matrix26 ;
                g2_sum_part1 <= matrix15 + matrix17 ;

                g3_sum_part0 <= matrix17  ; 
                g3_sum_part1 <= 'd0 ;
            end
        end
    end
//B Channel
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {b0_sum_part0, b0_sum_part1} <= 'd0 ;
            {b1_sum_part0, b1_sum_part1} <= 'd0 ;
            {b2_sum_part0, b2_sum_part1} <= 'd0 ;
            {b3_sum_part0, b3_sum_part1} <= 'd0 ;
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                b0_sum_part0 <= matrix13 + matrix15 ;
                b0_sum_part1 <= 'd0;

                b1_sum_part0 <= matrix15 ;
                b1_sum_part1 <= 'd0 ;

                b2_sum_part0 <= matrix15 +  matrix17;
                b2_sum_part1 <= 'd0;

                b3_sum_part0 <= matrix17 ;
                b3_sum_part1 <= 'd0 ;
            end
            else begin
                b0_sum_part0 <= matrix03 + matrix23 ;//????
                b0_sum_part1 <= matrix05 + matrix25 ;//????

                b1_sum_part0 <= 'd0;//????
                b1_sum_part1 <= matrix05 + matrix25 ;

                b2_sum_part0 <= matrix05 + matrix25 ;
                b2_sum_part1 <= matrix07 + matrix27 ;

                b3_sum_part0 <= 'd0 ;//????
                b3_sum_part1 <= matrix07 + matrix27 ;
            end
        end
    end

    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_matrix_plus, g0_matrix_plus, b0_matrix_plus} <= 'd0 ;
            {r1_matrix_plus, g1_matrix_plus, b1_matrix_plus} <= 'd0 ;
            {r2_matrix_plus, g2_matrix_plus, b2_matrix_plus} <= 'd0 ;
            {r3_matrix_plus, g3_matrix_plus, b3_matrix_plus} <= 'd0 ;
        end
        else if(I_tvalid_r[0])begin
            r0_matrix_plus <= r0_sum_part0 + r0_sum_part1 ;
            r1_matrix_plus <= r1_sum_part0 + r1_sum_part1 ;
            r2_matrix_plus <= r2_sum_part0   ;
            r3_matrix_plus <= r3_sum_part0 + r3_sum_part1 ;

            g0_matrix_plus <= g0_sum_part0 + g0_sum_part1 ;
            g1_matrix_plus <= g1_sum_part0 + g1_sum_part1 ;
            g2_matrix_plus <= g2_sum_part0 + g2_sum_part1 ;
            g3_matrix_plus <= g3_sum_part0 + g3_sum_part1 ;

            b0_matrix_plus <= b0_sum_part0 + b0_sum_part1 ;
            b1_matrix_plus <= b1_sum_part0 + b1_sum_part1 ;
            b2_matrix_plus <= b2_sum_part0 + b2_sum_part1 ;
            b3_matrix_plus <= b3_sum_part0 + b3_sum_part1 ;
        end
    end


    // pipleline 1
//---- RGGB 的均值级：条件取反，注意「原值」与「平均」两支的位置 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_mean, g0_mean, b0_mean} <= 'd0 ;
            {r1_mean, g1_mean, b1_mean} <= 'd0 ;
            {r2_mean, g2_mean, b2_mean} <= 'd0 ;
            {r3_mean, g3_mean, b3_mean} <= 'd0 ;
        end
        else if(I_tvalid_r[1])begin
            r0_mean <= (!bayer_ypos_r1) ? r0_matrix_plus      : r0_matrix_plus >> 1 ;
            g0_mean <= bayer_ypos_r1    ? g0_matrix_plus      : g0_matrix_plus >> 2 ;
            b0_mean <= (!bayer_ypos_r1) ? b0_matrix_plus >> 2 : b0_matrix_plus >> 1 ;

            r1_mean <= (!bayer_ypos_r1) ? r1_matrix_plus >> 1 : r1_matrix_plus >> 2 ;
            g1_mean <= bayer_ypos_r1    ? g1_matrix_plus >> 2 : g1_matrix_plus      ;
            b1_mean <= (!bayer_ypos_r1) ? b1_matrix_plus >> 1 : b1_matrix_plus      ;

            r2_mean <= (!bayer_ypos_r1) ? r2_matrix_plus      : r2_matrix_plus >> 1 ;
            g2_mean <= bayer_ypos_r1    ? g2_matrix_plus      : g2_matrix_plus >> 2 ;   
            b2_mean <= (!bayer_ypos_r1) ? b2_matrix_plus >> 2 : b2_matrix_plus >> 1 ;

            r3_mean <= (!bayer_ypos_r1) ? r3_matrix_plus >> 1 : r3_matrix_plus >> 2 ;
            g3_mean <= bayer_ypos_r1    ? g3_matrix_plus >> 2 : g3_matrix_plus      ;
            b3_mean <= (!bayer_ypos_r1) ? b3_matrix_plus >> 1 : b3_matrix_plus      ;
        end
    end
end


/*****************************************************************
                       BAYER_MODE_GRBG                             
*****************************************************************/


//---- GRBG 分支：结构同 BGGR，条件同样取反（GRBG 与 BGGR 的相位正好相差一个像素） ----
    else if(BAYER_MODE == GRBG)
    begin:BAYER_MODE_GRBG

    // R Channel
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_sum_part0, r0_sum_part1} <= 'd0 ; 
            {r1_sum_part0, r1_sum_part1}  <= 'd0 ; 
            {r2_sum_part0, r2_sum_part1} <= 'd0 ; 
            {r3_sum_part0, r3_sum_part1}  <= 'd0 ; 
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                r0_sum_part0 <= matrix03 + matrix05 ;
                r0_sum_part1 <= matrix23 + matrix25 ;

                r1_sum_part0 <= matrix05 + matrix25 ;
                r1_sum_part1 <= 'd0;

                r2_sum_part0 <= matrix05 + matrix07 ;
                r2_sum_part1 <= matrix25 + matrix27 ;

                r3_sum_part0 <= matrix07 + matrix27 ;       
                r3_sum_part1 <= 'd0 ;                                                                 
            end
            else begin
                r0_sum_part0 <= matrix13 + matrix15 ;
                r0_sum_part1 <= 'd0 ;

                r1_sum_part0 <= matrix15 ;
                r1_sum_part1 <= 'd0;

                r2_sum_part0 <= matrix15 + matrix17 ;
                r2_sum_part1 <= 'd0 ;

                r3_sum_part0 <= matrix17 ;
                r3_sum_part1 <= 'd0 ;  
            end
        end
    end
// G Channel
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {g0_sum_part0, g0_sum_part1} <= 'b0 ;
            {g1_sum_part0, g1_sum_part1} <= 'b0 ;
            {g2_sum_part0, g2_sum_part1} <= 'b0 ;
            {g3_sum_part0, g3_sum_part1} <= 'b0 ;
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                g0_sum_part0 <= matrix04 + matrix24;
                g0_sum_part1 <= matrix13 + matrix15;

                g1_sum_part0 <= matrix15;
                g1_sum_part1 <= 'd0 ;

                g2_sum_part0 <= matrix06 + matrix26 ;
                g2_sum_part1 <= matrix15 + matrix17 ;

                g3_sum_part0 <= matrix17  ; 
                g3_sum_part1 <= 'd0 ;
            end
            else begin
                g0_sum_part0 <= matrix14 ;
                g0_sum_part1 <= 'd0;

                g1_sum_part0 <= matrix05 + matrix25;
                g1_sum_part1 <= matrix14 + matrix16;

                g2_sum_part0 <= matrix16 ;
                g2_sum_part1 <= 'd0;

                g3_sum_part0 <= matrix07 + matrix27; 
                g3_sum_part1 <= matrix16 + matrix18;
            end
        end
    end
//B Channel
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {b0_sum_part0, b0_sum_part1} <= 'd0 ;
            {b1_sum_part0, b1_sum_part1} <= 'd0 ;
            {b2_sum_part0, b2_sum_part1} <= 'd0 ;
            {b3_sum_part0, b3_sum_part1} <= 'd0 ;
        end
        else if(I_tvalid)begin
            if(bayer_ypos) begin
                b0_sum_part0 <= matrix14 ;
                b0_sum_part1 <= 'd0;

                b1_sum_part0 <= matrix14 + matrix16 ;
                b1_sum_part1 <= 'd0 ;

                b2_sum_part0 <= matrix16 ;
                b2_sum_part1 <= 'd0;

                b3_sum_part0 <= matrix16 + matrix18 ;
                b3_sum_part1 <= 'd0 ;
            end
            else begin
                b0_sum_part0 <= matrix04 + matrix24 ;
                b0_sum_part1 <= 'd0;

                b1_sum_part0 <= matrix04 + matrix06 ;
                b1_sum_part1 <= matrix24 + matrix26 ;

                b2_sum_part0 <= matrix06 + matrix26 ;
                b2_sum_part1 <= 'd0;

                b3_sum_part0 <= matrix06 + matrix08 ;
                b3_sum_part1 <= matrix26 + matrix28 ;
            end
        end
    end

    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_matrix_plus, g0_matrix_plus, b0_matrix_plus} <= 'd0 ;
            {r1_matrix_plus, g1_matrix_plus, b1_matrix_plus} <= 'd0 ;
            {r2_matrix_plus, g2_matrix_plus, b2_matrix_plus} <= 'd0 ;
            {r3_matrix_plus, g3_matrix_plus, b3_matrix_plus} <= 'd0 ;
        end
        else if(I_tvalid_r[0])begin
            r0_matrix_plus <= r0_sum_part0 + r0_sum_part1 ;
            r1_matrix_plus <= r1_sum_part0 + r1_sum_part1 ;
            r2_matrix_plus <= r2_sum_part0 + r2_sum_part1 ;
            r3_matrix_plus <= r3_sum_part0 + r3_sum_part1 ;

            g0_matrix_plus <= g0_sum_part0 + g0_sum_part1 ;
            g1_matrix_plus <= g1_sum_part0 + g1_sum_part1 ;
            g2_matrix_plus <= g2_sum_part0 + g2_sum_part1 ;
            g3_matrix_plus <= g3_sum_part0 + g3_sum_part1 ;

            b0_matrix_plus <= b0_sum_part0 + b0_sum_part1 ;
            b1_matrix_plus <= b1_sum_part0 + b1_sum_part1 ;
            b2_matrix_plus <= b2_sum_part0 + b2_sum_part1 ;
            b3_matrix_plus <= b3_sum_part0 + b3_sum_part1 ;
        end
    end


    // pipleline 1
//---- GRBG 的均值级：条件取反 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_mean, g0_mean, b0_mean} <= 'd0 ;
            {r1_mean, g1_mean, b1_mean} <= 'd0 ;
            {r2_mean, g2_mean, b2_mean} <= 'd0 ;
            {r3_mean, g3_mean, b3_mean} <= 'd0 ;
        end
        else if(I_tvalid_r[1])begin
            r0_mean <= (!bayer_ypos_r1) ? r0_matrix_plus >> 1 : r0_matrix_plus >> 2 ;
            g0_mean <= (!bayer_ypos_r1) ? g0_matrix_plus      : g0_matrix_plus >> 2 ;
            b0_mean <= (!bayer_ypos_r1) ? b0_matrix_plus >> 1 : b0_matrix_plus      ;

            r1_mean <= (!bayer_ypos_r1) ? r1_matrix_plus      : r1_matrix_plus >> 1 ;
            g1_mean <= (!bayer_ypos_r1) ? g1_matrix_plus >> 2 : g1_matrix_plus      ;
            b1_mean <= (!bayer_ypos_r1) ? b1_matrix_plus >> 2 : b1_matrix_plus >> 1 ;

            r2_mean <= (!bayer_ypos_r1) ? r2_matrix_plus >> 1 : r2_matrix_plus >> 2 ;
            g2_mean <= (!bayer_ypos_r1) ? g2_matrix_plus      : g2_matrix_plus >> 2 ;      
            b2_mean <= (!bayer_ypos_r1) ? b2_matrix_plus >> 1 : b2_matrix_plus      ;

            r3_mean <= (!bayer_ypos_r1) ? r3_matrix_plus      : r3_matrix_plus >> 1 ;
            g3_mean <= (!bayer_ypos_r1) ? g3_matrix_plus >> 2 : g3_matrix_plus      ;
            b3_mean <= (!bayer_ypos_r1) ? b3_matrix_plus >> 2 : b3_matrix_plus >> 1 ;
        end
    end
end

endgenerate 
    


//---- 8bit 饱和 ----
// 均值是 9bit，最高位 [8] 为 1 就说明结果已经超过 255（多个 8bit 相加后溢出），这时钳到 255；否则取低 8bit。
// 正常情况下 4 个样本的均值最大就是 255、2 个样本的均值也是最大 255，所以这里主要是防御性钳位。
    reg [7:0] r0_mean_d,r1_mean_d,r2_mean_d,r3_mean_d;
    reg [7:0] g0_mean_d,g1_mean_d,g2_mean_d,g3_mean_d;
    reg [7:0] b0_mean_d,b1_mean_d,b2_mean_d,b3_mean_d;
    // pipleline 2
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            {r0_mean_d,r1_mean_d,r2_mean_d,r3_mean_d} <= 'd0 ;
            {g0_mean_d,g1_mean_d,g2_mean_d,g3_mean_d} <= 'd0 ;
            {b0_mean_d,b1_mean_d,b2_mean_d,b3_mean_d} <= 'd0 ;
        end
        else if(I_tvalid_r[2])begin
            r0_mean_d <= r0_mean[8]?255:r0_mean[7:0];  // mean[8] 为 1 表示 >255：钳到 255，否则截取低 8bit（r/g/b 三通道同样的写法，共 12 行）
            g0_mean_d <= g0_mean[8]?255:g0_mean[7:0];
            b0_mean_d <= b0_mean[8]?255:b0_mean[7:0];

            r1_mean_d <= r1_mean[8]?255:r1_mean[7:0];
            g1_mean_d <= g1_mean[8]?255:g1_mean[7:0];
            b1_mean_d <= b1_mean[8]?255:b1_mean[7:0];

            r2_mean_d <= r2_mean[8]?255:r2_mean[7:0];
            g2_mean_d <= g2_mean[8]?255:g2_mean[7:0];
            b2_mean_d <= b2_mean[8]?255:b2_mean[7:0];

            r3_mean_d <= r3_mean[8]?255:r3_mean[7:0];
            g3_mean_d <= g3_mean[8]?255:g3_mean[7:0];
            b3_mean_d <= b3_mean[8]?255:b3_mean[7:0];
        end
    end

//---- 打包成 {8'b0,R,G,B}，再把 4 个像素拼成 128bit ----
    // pipleline 3
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            rgb_data0 <= 'd0 ;
            rgb_data1 <= 'd0 ;
            rgb_data2 <= 'd0 ;
            rgb_data3 <= 'd0 ;
        end
        else if(I_tvalid_r[3])begin
            rgb_data0 <= {8'b0, r0_mean_d, g0_mean_d, b0_mean_d};  // 一个像素 32bit = {8'b0, R, G, B}；rgb_data0..3 分别对应本拍的 4 个像素
            rgb_data1 <= {8'b0, r1_mean_d, g1_mean_d, b1_mean_d};
            rgb_data2 <= {8'b0, r2_mean_d, g2_mean_d, b2_mean_d};
            rgb_data3 <= {8'b0, r3_mean_d, g3_mean_d, b3_mean_d};
        end
    end

    assign rgb_data = {rgb_data3, rgb_data2, rgb_data1, rgb_data0};
//---- 输入流控信号打 5 拍，与上面 5 级流水对齐 ----
// I_tlast_r / I_tuser_r / I_tvalid_r 都是 5 位移位寄存器，[4] 出来的信号正好落在数据那一级上。
/*****************************************************************
                          信号同步                                        
*****************************************************************/

    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            {I_tlast_r,I_tuser_r,I_tvalid_r} <= 0;
        else begin
            I_tlast_r  <= {I_tlast_r[3:0],I_tlast};
            I_tuser_r  <= {I_tuser_r[3:0],I_tuser};
            I_tvalid_r <= {I_tvalid_r[3:0],I_tvalid};
        end
    end

    assign  O_tlast  = I_tlast_r[4];     // 输出行尾：与 O_tdata 同相（已延迟 5 拍）
    assign  O_tuser  = I_tuser_r[4];     // 输出帧首：与 O_tdata 同相
    assign  O_tvalid = I_tvalid_r[4];  // 输出数据有效：与 O_tdata 同相

    
    assign O_tdata  = rgb_data;  // 输出数据就是打包好的 128bit
    assign I_tready = O_tready;  // 本模块不做反压：上游 ready 直通下游 ready

endmodule