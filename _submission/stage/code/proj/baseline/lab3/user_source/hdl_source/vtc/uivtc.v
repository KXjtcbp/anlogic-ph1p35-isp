//=============================================================================
// 文件      : vtc/uivtc.v
// 模块      : uivtc
// 功能      : 视频时序控制器：用行计数器 hcnt 与场计数器 vcnt 产生一套完整的显示时序（行同步 HS、场同步 VS、数据有效 DE），
//             并把它转成 AXI4-Stream 风格的 video stream 时序（user=帧起始、last=行结束、valid=像素有效）送给下游 HDMI 发送。
// 数据通路  : 由 8 个 parameter 描述一种分辨率：H/V_ActiveSize 是有效像素/行数，H/V_FrameSize 是一行/一帧的总节拍数，
//             H/V_SyncStart 与 H/V_SyncEnd 给出同步脉冲的起止位置。改参数即可适配不同分辨率。
//             hcnt/vcnt 由 I_vtc_clk 驱动，输出 vtc_hs/vtc_vs/vtc_de；随后打拍生成 O_vtc_vs/hs/de_valid/user/last。
// 时钟/复位 : I_vtc_rstn 是系统复位（低有效），内部另外用 rst_cnt 做 3 拍上电同步复位（rst_sync）。
// 依赖      : 无子模块例化；仅使用 reg/wire/assign。
// 综合/实现 : 纯 RTL，可综合；已收录于 td_project/camera_to_dsi_display.al，并在 design_top_wrapper.v:774 以 u_hdmi_vtc 例化。
//             本文件的 parameter 默认值是 1080p 的示例值（H_ActiveSize=1980、H_FrameSize=1920+88+44+148、V_ActiveSize=1080、
//             V_FrameSize=1080+4+5+36 等），本工程在上层例化处把 8 个参数全部覆盖为 720p60：
//             H_ActiveSize=1280、H_FrameSize=1650、H_SyncStart=1390、H_SyncEnd=1430、
//             V_ActiveSize=720、V_FrameSize=750、V_SyncStart=725、V_SyncEnd=730，因此在板上的行为按 1280x720@60 解释。
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
*Revision: 1.1
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

/*************uivtc(video timing controller)视频时序控制器*************
--版本号1.1
--以下是米联客设计的uivtc(video timing controller)视频时序控制器
--1.代码简洁，占用极少逻辑资源，代码结构清晰，逻辑设计严谨
--2.使用方便，只需要输入6个参数既可以实现对不同视频分辨率时序的控制
--3.该视频时序控制，一个时钟对应一个像素
--4.通常我们说的像素，比如1080P代表了1920*1080是指视频的有效显示区域，实际的视频还包含不能显示的区域，比如行同步，场同步时间
--5.通常我们说的行视频信号，也称之为视频的水平像素信号；场视频信号，也称之为视频的垂直像素信号；
*********************************************************************/

`timescale 1ns / 1ns //仿真时间刻度/精度

//---- 参数与端口说明（8 个 parameter 描述一种分辨率） ----
// 命名规律：H_ 为一行内的水平方向，V_ 为一帧内的垂直方向；
//   *_ActiveSize ：有效像素数 / 有效行数（= 分辨率）；
//   *_FrameSize  ：一行 / 一帧总共占用的时钟节拍数（有效 + 各种消隐）；
//   *_SyncStart / *_SyncEnd ：同步脉冲的起止计数值。
// 本文件顶部的默认值取自 1080p 官方例程；本工程在 design_top_wrapper.v:774 例化时全部覆盖为 720p60，
// 即一行 1650 拍、一帧 750 行。
module uivtc#
(
parameter H_ActiveSize  =   1980,               //视频时间参数,行视频信号，一行有效(需要显示的部分)像素所占的时钟数，一个时钟对应一个有效像素
parameter H_FrameSize   =   1920+88+44+148,     //视频时间参数,行视频信号，一行视频信号总计占用的时钟数
parameter H_SyncStart   =   1920+88,            //视频时间参数,行同步开始，即多少时钟数后开始产生行同步信号 
parameter H_SyncEnd     =   1920+88+44,         //视频时间参数,行同步结束，即多少时钟数后停止产生行同步信号，之后就是行有效数据部分

parameter V_ActiveSize  =   1080,               //视频时间参数,场视频信号，一帧图像所占用的有效(需要显示的部分)行数量，通常说的视频分辨率即H_ActiveSize*V_ActiveSize
parameter V_FrameSize   =   1080+4+5+36,        //视频时间参数,场视频信号，一帧视频信号总计占用的行数量
parameter V_SyncStart   =   1080+4,             //视频时间参数,场同步开始，即多少行数后开始产生场同步信号 
parameter V_SyncEnd     =   1080+4+5            //视频时间参数,场同步结束，即多少场数后停止产生场同步信号，之后就是场有效数据部分
)
(
input           I_vtc_rstn,     //系统复位
input			I_vtc_clk,      //系统时钟
output			O_vtc_vs,       //场同步输出
output          O_vtc_hs,       //行同步输出
output          O_vtc_de_valid, //视频数据有效	
output          O_vtc_user,     //满足stream时序产生 user 信号,用于帧同步
output          O_vtc_last      //满足stream时序产生 later 信号,用于每行结束
);




reg [11:0] hcnt = 12'd0;    //视频水平方向，列计数器，寄存器
reg [11:0] vcnt = 12'd0;    //视频垂直方向，行计数器，寄存器   
//---- 上电同步复位 ----
// 只用 I_vtc_rstn 直接复位的话，寄存器会立刻开始计数，而 PLL/时钟刚稳定时可能不可靠，
// 所以这里用一个 3 位计数器 rst_cnt 数 4 拍，rst_sync 取最高位 rst_cnt[2]，作为内部逻辑的同步释放复位。
reg [2 :0] rst_cnt = 3'd0;  //复位计数器，寄存器
wire rst_sync = rst_cnt[2]; //同步复位

always @(posedge I_vtc_clk or negedge I_vtc_rstn)begin //通过计数器产生同步复位
    if(I_vtc_rstn == 1'b0)
        rst_cnt <= 3'd0;
    else if(rst_cnt[2] == 1'b0)
        rst_cnt <= rst_cnt + 1'b1;
end    


//视频水平方向，列计数器
always @(posedge I_vtc_clk)begin
    if(rst_sync == 1'b0) //复位
        hcnt <= 12'd0;
//---- 行计数器 hcnt（水平方向，0 ~ H_FrameSize-1） ----
// 每个像素时钟加 1，计满一行（720p 为 1650 拍）后回零；
// 它同时决定了行同步的位置、一行的有效像素区间和换行的时刻。
// 注意：本工程实际使用的一组参数是 720p60（H_ActiveSize=1280、H_FrameSize=1650、
//   H_SyncStart=1390、H_SyncEnd=1430、V_ActiveSize=720、V_FrameSize=750、V_SyncStart=725、V_SyncEnd=730），
//   由 design_top_wrapper.v:774 例化时覆盖；本文件顶部的默认值是 1080p 官方示例值。
    else if(hcnt < (H_FrameSize - 1'b1))//计数范围从0 ~ H_FrameSize-1
        hcnt <= hcnt + 1'b1;
    else 
        hcnt <= 12'd0;
end         

//视频垂直方向，行计数器，用于计数已经完成的行视频信号
always @(posedge I_vtc_clk)begin
    if(rst_sync == 1'b0)
//---- 场计数器 vcnt（垂直方向，0 ~ V_FrameSize-1） ----
// vcnt 不是每个时钟都加，而是等一行走完（hcnt 数到 H_ActiveSize-1、即最后一个有效像素）时才加 1；
// 计满一帧（750）后回零，所以它代表 当前正在第几行。
        vcnt <= 12'd0;
    else if(hcnt == (H_ActiveSize  - 1'b1)) begin//视频水平方向，是否一行结束
           vcnt <= (vcnt == (V_FrameSize - 1'b1)) ? 12'd0 : vcnt + 1'b1;//视频垂直方向，行计数器加1，计数范围0~V_FrameSize - 1
    end
end 

//---- 有效区间与同步脉冲的产生 ----
// hs_valid / vs_valid：当前是否落在有效像素区（不是消隐区）；
// vtc_hs：行同步，hcnt 落在 [H_SyncStart, H_SyncEnd) 区间内有效（720p 即计数 1390~1429，宽 40 拍）；
// vtc_vs：场同步，vcnt 落在 (V_SyncStart, V_SyncEnd] 区间内有效（720p 即第 726~730 行，宽 5 行）；
// vtc_de：只有行、场同时处在有效区才为 1，也就是真正需要送出的像素区间。
wire hs_valid  =  hcnt < H_ActiveSize; //行信号有效像素部分
wire vs_valid  =  vcnt < V_ActiveSize; //场信号有效像素部分
wire vtc_hs    =  (hcnt >= H_SyncStart && hcnt < H_SyncEnd);//产生hs，行同步信号
wire vtc_vs	   =  (vcnt > V_SyncStart && vcnt <= V_SyncEnd);//产生vs，场同步信号      
wire vtc_de    =  hs_valid && vs_valid;//只有当视频水平方向，列有效和视频垂直方向，行同时有效，视频数据部分才是有效

//**********************  video stream video rgb  ***************************
//如果是输入RGB时序，那么转为stream时序
reg   vtc_vs_r1  ;
reg   vtc_hs_r1  ;
reg   vtc_de_r1  ;
reg   vtc_user_r1 ,vtc_user_r2;
reg   vtc_valid_r1,vtc_valid_r2;
reg   vtc_last_r2;
reg   vs_start;
 
always @(posedge I_vtc_clk )begin
    if(rst_sync == 1'b0) //复位
//---- 转 video stream 时序 ----
// 下游（HDMI 发送）使用的是 AXI4-Stream 风格的接口：user 标记一帧的开始、last 标记一行的结束。
// vs_start 用来把 场同步的上升沿 变成一帧的起始标志：检测到 vtc_vs 上升沿时置 1，
// 等 user 已经送出（vtc_user_r1 有效）再清 0，保证每帧只产生一次 user。
        vs_start <= 1'b0;
    else if(vtc_user_r1)//清除VS帧同步
        vs_start <= 1'b0;
    else if(vtc_vs && vtc_vs_r1==1'b0)//当vtc_vs发生上升沿跳变代表一帧开始
        vs_start <= 1'b1;
end  
      
always @(posedge I_vtc_clk  )begin
    vtc_vs_r1    <= vtc_vs;
    vtc_hs_r1    <= vtc_hs;
    vtc_user_r1  <= ~vtc_user_r1 & vs_start & vtc_de;//vtc_user延迟1拍
    vtc_last_r2  <= ~vtc_de & vtc_valid_r1; //产生stream video last 延迟于数据输入2拍
    vtc_valid_r1 <= vtc_de;//vtc_valid延迟1拍
    vtc_valid_r2 <= vtc_valid_r1;//vtc_valid对输入信号延迟2拍，以和vtc_last_r2信号配套同步
    vtc_user_r2  <= vtc_user_r1; //vtc_user 对输入信号延迟2拍，以和vtc_last_r2信号配套同步    
end    

//---- 输出（同步信号与 stream 信号统一打拍对齐） ----
// valid / user / last 都经过两级寄存，使它们与已打一拍的像素数据保持同一节拍，
// 这样下游看到的 de_valid、user、last 与像素是严格对齐的。
assign O_vtc_vs       =  vtc_vs_r1;
assign O_vtc_hs       =  vtc_hs_r1;
assign O_vtc_de_valid =  vtc_valid_r2;
assign O_vtc_user     =  vtc_user_r2;
assign O_vtc_last     =  vtc_last_r2;


endmodule


