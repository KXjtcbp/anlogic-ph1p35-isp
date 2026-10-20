//=============================================================================
// [HDR-2026-10-09] 文件      : ae_set.v
// 模块      : ae_set
// 功能      : 按键触发的手动曝光/模拟增益调节器：给「曝光 +/−」和「增益 +/−」按键各做一个步进计数器，输出目标曝光值与目标增益档位。
// 数据通路  : 按键(边沿) → r_exposure_step / r_analog_gain_step 单拍脉冲 → 步进加减 r_exposure_set / r_analog_gain_set → 与当前值比较后请求下发（O_ae_req）→ 输出 r_exposure / r_analog_gain
// 时钟/复位 : 24 MHz 按键/配置域；复位低有效。
// 依赖      : 被 design_top_wrapper.v:462-471 例化（u_ae_set），输出送 uicfgcs500_720p 的曝光/增益接口
// 综合/实现 : ■ ★★本模块有三处已知隐患（只标注，本次不改）：
//           1. (:73) 复位值 r_exposure_set = 3000 **超过手册最大曝光 1990**；(:88) 的 AE 加上限 2246 同样超限。
//           2. (:109-114) 复位后 r_exposure == r_exposure_set 且 r_analog_gain == r_analog_gain_set，条件 `(r_ae != r_ae_set) || (r_ag != r_ag_set)` 不成立 ⇒ r_ae_req 永不置位 ⇒ AE 寄存器组从不下发。
//           3. 一旦按下 AE 键，上述条件成立，会把 2999+ 的非法曝光值写进传感器，//              并把模拟增益覆盖回 SC500GainTbl 的 0x0F20（4.000×）。
//              ⇒ 现场调试期间「只按模式切换键 KEY1(I_button[1]/D5)，不要按 AE/AG 键」。
//-----------------------------------------------------------------------------
// 修改记录  :
//   2026-09-27  [230f479] 导入官方 lab3 基线（Milianke 参考例程）
//   2026-10-09  （未提交）标识符改名 56 处：O_ae/O_ag → O_exposure_time/O_analog_gain、r_ae_set/r_ag_set → r_exposure_set/r_analog_gain_set、r_ae_tick/r_ag_tick/rc_ag_tick → r_exposure_step/r_analog_gain_step/r_analog_gain_accum，无逻辑改动
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑，见 E:\FPGA\_analysis\rename_report.txt）
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
*Revision: 1.0
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
/*********ae_set �ֶ��������AE ***********
--�汾��1.0
*********************************************************************/

module ae_set
(
input wire I_clk,
input wire I_rst,
input wire [3:0]I_btn,
input wire I_ae_cfg_done,
input wire I_cam_cfg_done,
output wire O_ae_req,
output wire [15:0] O_exposure_time,
output wire [15:0] O_analog_gain
);
	

reg 	[19:0] 	rc_ae_tick = 0; 
reg 			r_exposure_step = 0; 
reg 	[4:0] 	r_analog_gain_accum = 0; 
reg 			r_analog_gain_step = 0; 
	
always @(posedge I_clk or posedge I_rst) begin
	if(I_rst) begin
		rc_ae_tick <= 0; 
		r_exposure_step <= 0; 
		r_analog_gain_accum <= 0; 
		r_analog_gain_step <= 0; 
	end else begin
	//	Trigger AE Inc / Dec per 1 ms. 
		rc_ae_tick <= rc_ae_tick + 1; 
		r_exposure_step <= 0; 
		if(rc_ae_tick >= 99999) begin
			rc_ae_tick <= 0; 
			r_exposure_step <= 1; 
		end 
	//	Trigger AG Inc / Dec per 32 ms. 
		r_analog_gain_accum <= r_analog_gain_accum + r_exposure_step; 
		r_analog_gain_step <= (&r_analog_gain_accum) && r_exposure_step; 
	end
end
	
//	Use button to add / sub idelay values. I_button[0]:IncDatDly, [1]DecDatDly, [2]IncI_clkDly, [3]DecI_clkDly
reg 	[3:0] 	r_button_0 = 0, r_button_1 = 0; 
reg 	[15:0] 	r_exposure_set = 3000, r_analog_gain_set = 80; 
always @(posedge I_clk or posedge I_rst) begin
	if(I_rst) begin
		r_button_0 <= 0; 
		r_button_1 <= 0; 
		r_exposure_set <= 3000; 
		r_analog_gain_set <= 80; 
	end else begin
	//	When button pressed, r_button_1 bit is 1. 
		r_button_0 <= ~I_btn; 
		r_button_1 <= r_button_0; 
	
		if(r_button_1[0]) begin
			r_exposure_set <= (r_exposure_set > 2) ? r_exposure_set - r_exposure_step : r_exposure_set; 
		end else if(r_button_1[1]) begin
			r_exposure_set <= (r_exposure_set < 2246) ? r_exposure_set + r_exposure_step : r_exposure_set; 
		end 
		if(r_button_1[2]) begin
				r_analog_gain_set <= (r_analog_gain_set > 16) ? r_analog_gain_set - r_analog_gain_step : r_analog_gain_set; 
		end else if(r_button_1[3]) begin
				r_analog_gain_set <= (r_analog_gain_set < 89) ? r_analog_gain_set + r_analog_gain_step : r_analog_gain_set; 
		end 
		end
	end
	
//	Update AG / AE when changed. 
reg 	[15:0] 	r_exposure ; 
reg 	[15:0] 	r_analog_gain ; 
reg 			r_ae_req = 0; //synthesis keep
assign O_exposure_time = r_exposure;
assign O_analog_gain = r_analog_gain;
assign O_ae_req = r_ae_req;

always @(posedge I_clk or posedge I_rst) begin
	if(I_rst) begin
		r_ae_req <= 0; 
		r_exposure     <= 3000; 
		r_analog_gain     <= 80; 
	end else if(r_ae_req) begin
		r_ae_req <= 0; 
	end else if(((r_exposure != r_exposure_set) || (r_analog_gain != r_analog_gain_set))&&(I_cam_cfg_done==1'b1)&&(I_ae_cfg_done==1'b1)) begin
		r_exposure     <= r_exposure_set; 
		r_analog_gain     <= r_analog_gain_set; 
		r_ae_req <= 1; 
	end
end


endmodule


	