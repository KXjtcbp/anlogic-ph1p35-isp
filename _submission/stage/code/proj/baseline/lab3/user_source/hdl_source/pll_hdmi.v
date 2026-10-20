//=============================================================================
// 文件      : pll_hdmi.v
// 模块      : pll_hdmi
// 功能      : HDMI 通路专用 PLL（由安路 TD 6.1.155545 的 IP 生成器生成）：把 50 MHz 参考时钟倍频/分频出 4 路时钟，
//             其中 C0=75.000000 MHz 作为 HDMI 像素时钟、C1=375.000000 MHz 作为 TMDS 串行时钟，
//             C2=70.312500 MHz、C3=23.936170 MHz 为生成的其余两路输出（本文件中未做进一步处理，直接引出）。
// 数据通路  : refclk -> PLL 的 clk0/1/2/3_out -> 分别经 PH1P_LOGIC_BUFG（C0/C2）和 PH1P_PHY_MLCLK（C3）后输出；
//             C1 不经过 BUFG 直接输出；C0 同时经 bufg_feedback 回灌到 PLL 的 fbclk 完成外部反馈。
// 时钟/复位 : 输入 50 MHz（20 ns，与约束里的 sys_clk_50m 一致）；输出 4 路时钟 + lock 指示；无复位端口。
// 依赖      : 依赖：器件原语 PH1P_LOGIC_BUFG、PH1P_PHY_MLCLK 与 PLL 原语 ph1p_phy_pll_wrapper_27c53fedd344（由安路 TD 提供）。
// 综合/实现 : TD 生成的参数化原语，需结合安路器件库/仿真模型编译；本文件在工程 .al 中未以 .v 形式收录
//             （工程里以 ip_source/PLL/PLL.xml 的 IP 形式存在），因此未能确认它是否已被实际接入本次设计，本文件按原样保留。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
/************************************************************\
**	Copyright (c) 2012-2025 Anlogic Inc.
**	All Right Reserved.
\************************************************************/
/************************************************************\
**	Build time: Jun 14 2025 22:20:07
**	TD version	:	6.1.155545
************************************************************/
///////////////////////////////////////////////////////////////////////////////
//	Input frequency:                50.000000000 MHz
//	Clock multiplication factor: 3
//	Clock division factor:       2
//	Clock information:
//		Clock name	| Frequency 	| Phase shift 
//		C0        	| 75.000000   MHz	    |  0.0000 DEG 
//		C1        	| 375.000000   MHz	    |  0.0000 DEG 
//		C2        	| 70.312500   MHz		|  0.0000 DEG 
//		C3        	| 23.936170   MHz		|  0.0000 DEG 
///////////////////////////////////////////////////////////////////////////////
`timescale 1 ns / 100 fs 

//---- 模块说明 ----
// 下面文件头的时钟表由 TD 的 PLL IP 生成器自动生成，含义是：
//   输入 50 MHz，整体倍频系数 3、分频系数 2，得到 4 路输出（相位均为 0 度）；
//   C0 = 75.000000 MHz —— 给 HDMI 像素逻辑用；
//   C1 = 375.000000 MHz —— 给 TMDS 串行化用（= 像素时钟的 5 倍）；
//   C2 = 70.312500 MHz、C3 = 23.936170 MHz —— 另外两路输出，本文件直接引出。
// PLL 的参考输入是 refclk，lock 指示锁定状态（锁定后才允许下游逻辑复位释放）。
module pll_hdmi
(
  input                         refclk,
  output                        clk0_out,
  output                        clk1_out,
  output                        clk2_out,
  output                        clk3_out,
  output                        lock
);
//---- 输出时钟缓冲与反馈 ----
// C0 先经过 PH1P_LOGIC_BUFG 到 clk0_out，同时把该输出回灌给 PLL 的 fbclk，
// 形成 外部反馈（FBKCLK=CLKC0_EXT），使 PLL 把输出现场的走线延迟也计入相位控制。
  wire							  clk0_buf;
PH1P_LOGIC_BUFG bufg_feedback (
 .i(clk0_buf), 
 .o(clk0_out) 
 ); 

 
  wire							  clk2_buf;
PH1P_LOGIC_BUFG bufg_c2 (
 .i(clk2_buf), 
 .o(clk2_out) 
 ); 

  wire							  clk3_buf;
PH1P_PHY_MLCLK mlclk_c3 (
 .ce(1'b1), 
 .clkin(clk3_buf), 
 .clkout(clk3_out) 
 ); 





//---- PLL 原语例化（TD 生成，参数与 IP 配置一一对应） ----
// 关键参数含义：FIN=50 MHz 参考频率；REFCLK_DIV=2、FBCLK_DIV=3（分数分频比 3/2）；
// CLKC0_DIV=15/CPHASE=14 → C0=75 MHz；CLKC1_DIV=3/CPHASE=2 → C1=375 MHz；
// CLKC2_DIV=16/CPHASE=15 → C2=70.3125 MHz；CLKC3_DIV=47/CPHASE=46 → C3≈23.936 MHz；
// DUTY50=ENABLE 表示各路都输出 50% 占空比；FEEDBK_MODE=NORMAL、PLL_FASTLOOP=ENABLE。
  ph1p_phy_pll_wrapper_27c53fedd344
  #(
      .FBKCLK("CLKC0_EXT"),
      .FBKCLK_INT("CLKC0_EXT"),
      .FIN("50.000000000"),
      .REFCLK_DIV(2),
      .FBCLK_DIV(3),
      .CLKC0_ENABLE("ENABLE"),
      .CLKC0_DIV(15),
      .CLKC0_CPHASE(14),
      .CLKC0_FPHASE(0),
      .CLKC0_FPHASE_RSTSEL(0),
      .CLKC0_DUTY50("ENABLE"),
      .CLKC0_DUTY_INT(8),
      .CLKC1_ENABLE("ENABLE"),
      .CLKC1_DIV(3),
      .CLKC1_CPHASE(2),
      .CLKC1_FPHASE(0),
      .CLKC1_FPHASE_RSTSEL(0),
      .CLKC1_DUTY50("ENABLE"),
      .CLKC1_DUTY_INT(2),
      .CLKC2_ENABLE("ENABLE"),
      .CLKC2_DIV(16),
      .CLKC2_CPHASE(15),
      .CLKC2_FPHASE(0),
      .CLKC2_FPHASE_RSTSEL(0),
      .CLKC2_DUTY50("ENABLE"),
      .CLKC2_DUTY_INT(8),
      .CLKC3_ENABLE("ENABLE"),
      .CLKC3_DIV(47),
      .CLKC3_CPHASE(46),
      .CLKC3_FPHASE(0),
      .CLKC3_FPHASE_RSTSEL(0),
      .CLKC3_DUTY50("ENABLE"),
      .CLKC3_DUTY_INT(24),
      .PLL_USR_RST("DISABLE"),
      .PLL_FEED_TYPE("EXTERNAL"),
      .PLL_FASTLOOP("ENABLE"),
      .LPF_RES(0),
      .LPF_CAP(25),
      .ICP_CUR(29),
      .PHASE_PATH_SEL(0),
      .DYN_PHASE_PATH_SEL("DISABLE"),
      .DYN_FPHASE_EN("DISABLE"),
      .PI_OUT_SEL("NORMAL"),
      .PI_FRAC_EN("DISABLE"),
      .CLKC0_PI_SHIFT_EN("DISABLE"),
      .FEEDBK_MODE("NORMAL"),
      .DYN_CPHASE_EN("DISABLE")
  )ph1p_phy_pll_wrapper_27c53fedd344_Inst
  (
//---- 未使用的资源与非必要端口的固定接法 ----
// clk4/clk5/clk6 三路不使用（en 接 0、输出悬空）；DRP 动态重配置端口全部接常量、输出悬空；
// 相位移动（ps*）与扩频（ssc_reset）也全部关闭；pllpd/reset 接 0 表示常开不复位。
// 真正使用的只有 clk0/1/2/3 四路输出与 lock，其中 clk0/2/3 分别写到对应的 *_buf 再经缓冲输出。
      .clk4_en(1'b0),
      .clk4_out(),
      .clkb4_out(),
      .clk5_en(1'b0),
      .clk5_out(),
      .clkb5_out(),
      .clk6_en(1'b0),
      .clk6_out(),
      .clkb6_out(),
      .refclk(refclk),
      .drp_clk(1'b0),
      .drp_rstn(1'b1),
      .drp_sel(1'b0),
      .drp_rd(1'b0),
      .drp_wr(1'b0),
      .drp_addr(8'b00000000),
      .drp_wdata(8'b00000000),
      .drp_err(),
      .drp_rdy(),
      .drp_rdata(),
      .psclk(1'b0),
      .psclksel(3'b000),
      .psstep(1'b0),
      .psdown(1'b0),
      .cps_step(1'b0),
      .psdone(),
      .ssc_reset(1'b0),
	  .clkc_rst(2'b00),
      .pllpd(1'b0),
      .reset(1'b0),
      .fbclk(clk0_out),
      .wakeup(1'b1),
      .refclk_rst(1'b0),
      .clk0_en(1'b1),
      .clkb0_out(),
      .clk0_out(clk0_buf),
      .clk1_en(1'b1),
      .clkb1_out(),
      .clk1_out(clk1_out),
      .clk2_en(1'b1),
      .clkb2_out(),
      .clk2_out(clk2_buf),
      .clk3_en(1'b1),
      .clkb3_out(),
      .clk3_out(clk3_buf),
      .lock(lock)
  );
endmodule
