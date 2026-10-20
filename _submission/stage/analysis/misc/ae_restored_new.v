//=============================================================================
// [HDR-2026-10-09] æä»¶      : uics500regAE.v
// æ¨¡å      : uics500regAE
// åè½      : è¿è¡æ¶çæå
/å¢çå¯å­å¨è¡¨ï¼æ 16bit æå
æ¶é´ä¸ 16bit æ¨¡æå¢çç¼ç ææ 5 æ¡ I2C åæä½ï¼3e00/3e01/3e02 è£
æå
ï¼3e08/3e09 è£
å¢çï¼ã
// æ°æ®éè·¯  : I_exposure_time / I_analog_gain â æ REG_INDEX æä½ â REG_DATA
// æ¶é/å¤ä½ : ç»åé»è¾ï¼always @(*) caseï¼ï¼æ æ¶éã
// ä¾èµ      : è¢« uicfgcs500_720p.v:132-138 ä¾åï¼.I_AG / .I_AEï¼
// ç»¼å/å®ç° : â  æå
 16bit ææ 3e00[3:0]/3e01[7:0]/3e02[7:4]ï¼å¢ç 16bit ææ 3e08[7:0]/3e09[7:0]ã
//           â  æ³¨æï¼èªå¨å¢çè·¯å¾çè¾å
¥æ¥èª SC500GainTblï¼è¯¥è¡¨åªå°ç´¢å¼ 73ï¼çº¦ 4.28Ãï¼ã
//-----------------------------------------------------------------------------
// ä¿®æ¹è®°å½  :
//   2026-09-27  [230f479] å¯¼å
¥å®æ¹ lab3 åºçº¿ï¼Milianke åèä¾ç¨ï¼
//   2026-10-09  ï¼æªæäº¤ï¼æ è¯ç¬¦æ¹å 7 å¤ï¼I_AE/I_AG â I_exposure_time/I_analog_gain
//   2026-10-10d 运行时表（AE 表）由 5 条扩到 8 条：新增 3e06/3e07（数字增益）与 4501（灰度递增测试图自检）；REG_SIZE 5→8
//-----------------------------------------------------------------------------
// 2026-10-09 å
¨æ åè¿ä¸æ¬¡æ è¯ç¬¦æ¹åï¼åªæ¹åå­ä¸æ¹é»è¾ï¼è§ E:\FPGA\_analysis\rename_report.txtï¼
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
--1.ADV7611Ð¾Æ¬ÅäÖÃ¼Ä´æÆ÷ÅäÖÃ±í
*********************************************************************/

module uics500regAE
(  
input      [8 :0]  REG_INDEX,
output reg [31:0]  REG_DATA,
output     [8 :0]  REG_SIZE,
input      [15:0]  I_exposure_time,
input      [15:0]  I_analog_gain,
input      [15:0]  I_digital_gain,      // [2026-10-10d] 16bit digital gain {3e06,3e07}
input               I_test_pattern       // [2026-10-10d] 1 = write 0x4501 = 0xbc (gray ramp self-check)
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
