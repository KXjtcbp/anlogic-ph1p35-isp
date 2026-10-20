//=============================================================================
// [HDR-2026-10-09] 文件      : uics500regAE.v
// 模块      : uics500regAE
// 功能      : 运行时的曝光/增益寄存器表：把 16bit 曝光、16bit 模拟增益、16bit 数字增益
//             拆成逐条 I2C 写（3e00/3e01/3e02 曝光，3e08/3e09 模拟增益，3e06/3e07 数字增益），
//             外加 0x4501 一条用于"运行时写通路自检"。
// 数据通路  : I_exposure_time / I_analog_gain / I_digital_gain / I_test_pattern
//             -> 按 REG_INDEX 拆位 -> REG_DATA
// 时钟/复位 : 组合逻辑（always @(*) case）；无时钟。
// 依赖      : 被 uicfgcs500_720p.v 例化
//             （.I_exposure_time / .I_analog_gain / .I_digital_gain / .I_test_pattern）
// 综合/实现 : ■ 曝光 16bit 拆成 3e00[3:0]/3e01[7:0]/3e02[7:4]；
//             模拟增益 16bit 拆成 3e08[7:0]/3e09[7:0]；数字增益 16bit 拆成 3e06[7:0]/3e07[7:0]。
//           ■ 本表只在"运行时"下发（uicfgcs500_720p 的 AE 分支）；上电初始化走
//             uics500reg_720p60 的 init 表。init 表只在复位/上电后走一遍，所以
//             开关选值的寄存器必须靠本表在运行时补发（见 design_top_wrapper.v 的 2026-10-10d 段）。
//           ■ 2026-10-10d：模拟增益不再经过 SC500GainTbl（该表只有索引 0..73，封顶 ≈4.28×），
//             改由 uicfgcs500_720p.v 直接给出寄存器原始字节。
//-----------------------------------------------------------------------------
// 修改记录  :
//   2026-09-27  [230f479] 导入官方 lab3 基线（Milianke 参考例程）
//   2026-10-09  （未提交）标识符改名 7 处：I_AE/I_AG -> I_exposure_time/I_analog_gain
//   2026-10-10d 运行时表由 5 条扩到 8 条：新增 3e06/3e07（数字增益）与 4501（灰度递增
//             测试图自检）；REG_SIZE 5->8。目的：SW3/SW4 拨动后无需断电重启即可生效。
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑，见 E:\FPGA\_analysis\rename_report.txt）
//=============================================================================
`timescale 1ns / 1ps
/*******************************MILIANKE*******************************
*Company : MiLianKe Electronic Technology Co., Ltd.
*WebSite:https://www.milianke.com
*TechWeb:https://www.uisrc.com
*tmall-shop:https://milianke.tmall.com
*jd-shop:https://milianke.jd.com
*taobao-shop1: https://milianke.taobao.com
*Create Date: 2019/12/17
*Module Name:HDMI_IN_Test
*File Name:HDMI_IN_Test.v
*Description: 
*The reference demo provided by Milianke is only used for learning. 
*We cannot ensure that the demo itself is free of bugs, so users 
*should be responsible for the technical problems and consequences
*caused by the use of their own products.
*Copyright: Copyright (c) MiLianKe
*All rights reserved.
*Revision: 1.0
*Signal description
*1) _i input
*2) _o output
*3) _n activ low
*4) _dg debug signal 
*5) _r delay or register
*6) _s state mechine
*********************************************************************/

/*******************************ui7611reg***************************
--1.ADV7611оƬ���üĴ������ñ�
*********************************************************************/

module uics500regAE
(  
input      [8 :0]  REG_INDEX,
output reg [31:0]  REG_DATA,
output     [8 :0]  REG_SIZE,
input      [15:0]  I_exposure_time,
input      [15:0]  I_analog_gain,
input      [15:0]  I_digital_gain,      // [2026-10-10d] 16bit digital gain = {3e06, 3e07}
input               I_test_pattern       // [2026-10-10d] 1 = write 0x4501 = 0xbc (gray ramp, runtime self-check)
);

assign	REG_SIZE = 9'd8;      // [2026-10-10d] 5 -> 8: + 3e06 / 3e07 / 4501
//-----------------------------------------------------------------
/////////////////////	Config Data REG	  //////////////////////////	
always@(*)
   case(REG_INDEX)
		0:	REG_DATA = {16'h3e00, 4'h0, I_exposure_time[15:12]}; 
		1:	REG_DATA = {16'h3e01, I_exposure_time[11: 4]}; 
		2:	REG_DATA = {16'h3e02, I_exposure_time[3:0], 4'h0};
		3:	REG_DATA = {16'h3e08, I_analog_gain[15:8]};
		4:	REG_DATA = {16'h3e09, I_analog_gain[7 :0]};
		5:	REG_DATA = {16'h3e06, I_digital_gain[15:8]};
		6:	REG_DATA = {16'h3e07, I_digital_gain[7 :0]};
		7:	REG_DATA = {16'h4501, I_test_pattern ? 8'hbc : 8'hb4};
		default:REG_DATA    =   {16'h0000, 8'h00};
   endcase

endmodule
