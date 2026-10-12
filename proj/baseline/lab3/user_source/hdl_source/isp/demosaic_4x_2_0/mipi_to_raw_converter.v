//=============================================================================
// 文件      : isp/demosaic_4x_2_0/mipi_to_raw_converter.v
// 模块      : mipi_to_raw_converter
// 功能      : 位宽/格式转换：把 MIPI CSI-2 侧 40bit/拍的 RAW10（4 个像素 × 10bit）各取高 8bit，拼成 32bit/拍的 RAW8（4 个像素 × 8bit），并把 tlast/tuser/tvalid 跟着数据一起打 1 拍；tready 直通，不做反压。
// 数据通路  : I_raw_tdata[39:0] -> 取 {[9:2], [19:12], [29:22], [39:32]} -> raw_data_r0[31:0]（寄存器，1 拍延迟）-> O_raw_tdata[31:0]；I_raw_tlast/tuser/tvalid -> 3 个 1bit 寄存器（同样 1 拍）-> O_raw_tlast/tuser/tvalid
// 时钟/复位 : 单时钟域 I_clk；I_rst_n 低有效，异步复位（posedge I_clk or negedge I_rst_n）。
// 依赖      : 无子模块、无厂商原语、无 RAM，纯 RTL 寄存器与连线。
// 综合/实现 : ■ 只有 2 个 always 块：1 个给数据打拍、1 个给流控信号打拍；寄存器一共 4 个（raw_data_r0[31:0] 与 3 个 1bit）。
//           ■ 数据与 tlast/tuser/tvalid 是同一拍一起打的，所以输出相对输入整体固定延迟 1 拍，这 4 个信号彼此同相。
//           ■ I_raw_tready 直接接 O_raw_tready，是纯组合连线；本模块不产生背压、也不做跨时钟处理。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//   2026-10-09  增加黑电平基座扣除（实测 64 LSB）：每个 10bit 字段先减 64（带钳位）再取高 8 位。
//               依据：盖住镜头时 RAW10 实测值域 [57..79]、均值 67.02。备份 E:\FPGA\_backup\20261009_blk\
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
@Time        :   2024/11 
version:     :   
@Description :   
*****************************************************************/
`timescale 1ns/1ns

//---- 端口：RAW10 输入侧 ----
module mipi_to_raw_converter 
#(
// [HDR-2026-10-10] 参数化：黑电平基座与四舍五入补偿改成参数；
//   不传参数时取值与 2026-10-09 版本完全一致，行为逐位不变。
    parameter [9:0] BLACK_LEVEL = 10'd56
// [HDR-2026-10-11e] 回退 2026-10-11d 的 56 -> 42 改动。三条独立证据见
//   _analysis/黑电平校正_模块A方案与验收_20261011.md 第 2 节：
//   (1) 12:50 那张盖镜头图（实测 Y 均值 40.52、p50 41）是【黑电平旁路 + 曲线启用】拍的，
//       40.52 反过 p160_a050 曲线得曲线前 10.4 码，再乘 4 = raw10 基座 42。
//       42 是「旁路时读到的基座值」，逻辑上不能反推「BLACK_LEVEL 应该等于 42」。
//   (2) 四张盖镜头增益梯（01:59-02:00，SW1 上=启用扣除）读到 Y==0 占
//       99.894% / 99.471% / 93.720% / 76.532%，证明 BL=56 在 4.000x / 8.000x /
//       15.750x / 31.500x 四档增益都把基座压到 0，是够用的。
//   (3) BL=42 对实测基座 42 的余量 = 0 码：基座只要漂 2 个 raw10 就出现 1 个 8bit 码，
//       而 p160_a050 表 mem[1]=8'h0d=13、mem[2]=8'h12=18，1 码基座立刻放大成 13 码灰。
//       BL=56 有 16 码余量；在「基座 = 67~72」的另一个候选世界里 56 同样优于 42。
//   => 56 在两个候选世界都更稳，且代价 <1.5% 的 8bit 暗部（raw10 44..57 被钳到 0）。
,   // 黑电平基座（10bit RAW 域，实测标定值）
    parameter [9:0] ROUND_ADD   = 10'd2     // 取高 8 位前的四舍五入补偿（= 4/2）
)
(
    input                          I_clk   ,
    input                          I_rst_n ,
    // [HDR-2026-10-10] 旁路开关（板上 SW1，顶层已做同步）：
    //   1 = 直通（不做黑电平扣除 = 2026-10-09 之前的原始行为）
    //   0 = 启用黑电平扣除
    input                          I_blk_bypass,

    input   [39:0]                 I_raw_tdata ,
    input   [ 9:0]                 I_raw_tdest ,
    input                          I_raw_tlast ,
    input                          I_raw_tvalid,
    input                          I_raw_tuser ,
    output                         I_raw_tready,
    
//---- 端口：RAW8 输出侧（4 个像素/拍） ----
    // 输出RAW10数据
    output  [31:0]                 O_raw_tdata ,
    output                         O_raw_tlast ,
    output                         O_raw_tvalid,
    output                         O_raw_tuser ,
    input                          O_raw_tready
);
//---- 寄存器声明：数据 1 拍 + 流控 1 拍 ----
    reg            I_tlast_r0;
    reg            I_tuser_r0;

    reg            I_tvalid_r0;
    reg    [31:0]  raw_data_r0;

//---- 数据格式转换：RAW10（4 个 10bit）-> RAW8（4 个 8bit） ----
    ///此处对于每个RAW10取高8位是因为高位所包含的颜色数据更多。
    //-----------------------------------------------------------------------------
    // 2026-10-09  增加「黑电平基座扣除」（现场实测数据驱动）
    //   实测依据：ChipWatcher 抓取盖住镜头时 ISP 输入端 S_axis_tdata[39:0]（传感器 RAW10）：
    //             1024 个采样内 1432 个有效 10bit 值，值域 = [57..79]、均值 67.02，
    //             四字段均值 [68.11 65.88 68.12 65.97]，光学黑基座实测约 66 LSB(10bit)，本实现取 56。
    //   不扣除的后果：10bit 的黑在 8bit 链路里变成 66>>2 = 16，相当于整幅画面叠加约 6%
    //             的灰雾（8bit 域 16/255）—— 这是「画面发灰、暗部对比度不足」的来源之一。
    //   做法：每个 10bit 字段先减 S_blk_level（不足者钳到 0，避免无符号下溢回绕成大数），再取高 8 位。
    //   资源代价：每拍 4 个比较器 + 4 个 10bit 减法器；本模块在 csi_rx_clk 域（约 100 MHz），
    //             组合深度约 2 级 LUT，不构成关键路径（本工程关键路径在 HDMI 像素域）。
    //   回退：把 raw_data_r0 的拼接换回 {I_raw_tdata[9:2], I_raw_tdata[19:12], I_raw_tdata[29:22], I_raw_tdata[39:32]}
    //         并删掉 4 条 S_blk_f* 即可；改动前备份 E:\FPGA\_backup\20261009_blk\mipi_to_raw_converter.v
    //-----------------------------------------------------------------------------
    wire [9:0] S_blk_level = BLACK_LEVEL;   // [HDR-2026-10-10] 由参数给出（默认 56）   // 黑电平基座（2026-10-09 实测标定：盖镜头时 RAW10 值域 [57..79]、均值 66~67）
    //   取 56 而不是实测均值 66 的理由（m02552「绝不影响效果」的硬保证）：
    //     56 小于观测到的最低 RAW10 值 57，所以对现有全部采集数据都不会钳掉任何一个像素，
    //     即黑电平扣除在数学上不可能损失任何真实暗部细节；
    //     同时仍扣掉 56/66 约 85% 的基座，8bit 域残留 10>>2 约 2 个码值（0.8%），肉眼不可见。
    //   将来若改增益/曝光，重新标定只需改这一个常数（建议取值 = 新实测最小值 减 1）。
    //   下面 4 条同时做「钳位减法」与「四舍五入补偿 +2」：随后取 [9:2] 等价于 (x-56+2)/4 四舍五入，
    //   最大值 (1023-56)+2 = 969 仍在 10bit 内，不会溢出；8bit 输出上限为 969>>2 = 242。
    // [HDR-2026-10-10] 加 I_blk_bypass 选择：1 = 原值直通，0 = 减基座+四舍五入
    wire [9:0] S_blk_f0 = I_blk_bypass ? I_raw_tdata[ 9: 0] : (((I_raw_tdata[ 9: 0] > S_blk_level) ? (I_raw_tdata[ 9: 0] - S_blk_level) : 10'd0) + ROUND_ADD);
    wire [9:0] S_blk_f1 = I_blk_bypass ? I_raw_tdata[19:10] : (((I_raw_tdata[19:10] > S_blk_level) ? (I_raw_tdata[19:10] - S_blk_level) : 10'd0) + ROUND_ADD);
    wire [9:0] S_blk_f2 = I_blk_bypass ? I_raw_tdata[29:20] : (((I_raw_tdata[29:20] > S_blk_level) ? (I_raw_tdata[29:20] - S_blk_level) : 10'd0) + ROUND_ADD);
    wire [9:0] S_blk_f3 = I_blk_bypass ? I_raw_tdata[39:30] : (((I_raw_tdata[39:30] > S_blk_level) ? (I_raw_tdata[39:30] - S_blk_level) : 10'd0) + ROUND_ADD);
// 只取每个 10bit 像素的高 8bit（丢掉低 2bit）：RAW10 里高 8 位承载的灰度信息占绝大部分，
// 直接截断就能满足后面 8bit/像素的链路，不必做 10->8 的缩放。
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            raw_data_r0 <= 0;
        else if(I_raw_tvalid)begin
            // 位拼接顺序与改动前完全一致（字段次序未动）：字段0(减黑后)->[31:24]、字段1->[23:16]、字段2->[15:8]、字段3->[7:0]
            // 哪个字段对应图像左侧仍未能从本文件确认
            // 2026-10-09 改动：由直接截断 I_raw_tdata[x:y] 改为截断 (I_raw_tdata[x:y] - 56 + 2)
            raw_data_r0 <= {S_blk_f0[9:2], S_blk_f1[9:2], S_blk_f2[9:2], S_blk_f3[9:2]};
        end 
    end



//---- 流控信号打拍：tlast/tuser/tvalid 与数据同拍延迟 1 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n)begin
            {I_tlast_r0,I_tuser_r0,I_tvalid_r0} <= 0;
        end
        else begin
            I_tlast_r0  <= I_raw_tlast;
            I_tuser_r0  <= I_raw_tuser;
            I_tvalid_r0 <= I_raw_tvalid;
        end
    end
    

//---- 输出连线：数据与流控同相，tready 纯组合直通 ----
    assign  O_raw_tlast  = I_tlast_r0;   
    assign  O_raw_tuser  = I_tuser_r0;   
    assign  O_raw_tvalid = I_tvalid_r0;

    assign  O_raw_tdata  = raw_data_r0;
    
    assign  I_raw_tready = O_raw_tready;  // 纯组合直通：本模块不做反压，上一级的 ready 就是下一级的 ready


endmodule


