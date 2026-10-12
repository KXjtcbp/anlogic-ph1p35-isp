//=============================================================================
// 文件      : key_remove_shakes.v
// 模块      : key_remove_shakes
// 功能      : 按键消抖：把异步按键输入同步进 I_clk 时钟域，检测按下（下降沿）后启动固定长度延时计数，延时结束后输出一个时钟周期的高脉冲作为按键已确认事件。
// 数据通路  : I_key_in 为按键原始电平（按下通常为低）；四级同步寄存器滤除亚稳态，S_key_in_n_edge 检出按下沿，S_delay_cnt 计满 100000 拍后由 S_delay_en 的下降沿配合 S_key_in_sync_4d 产生 O_key_trig_out 单拍脉冲。
// 时钟/复位 : I_clk（消抖计数时钟）；I_rst_n 低电平异步复位。计数长度固定为 100000 拍：挂 24 MHz 时钟域时约 4.17 ms。
// 依赖      : 无子模块依赖。被 hdmi_tx.v:141（u_key_remove_shakes）和 my_algo/key_mode_ctrl.v:74（u_key_remove_shakes_mode）例化，两处均要求该模块挂在 24 MHz 慢时钟域。
// 综合/实现 : 纯寄存器逻辑（4 级同步 + 17 bit 计数器），无 IP 与原语依赖；已收录于 td_project/camera_to_dsi_display.al。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
/*
creat time: 2020/12/3 15:50

engineer:   xiong guo qiang

description:
对按键操作进行消抖操作，每次按下产生一个时钟周期的高脉冲

*/



//---- 模块说明 ----
// 消抖原理：真实按键会有一段时间的电平抖动，这里用固定 100000 拍的窗口把抖动整段滤掉；
// 只有窗口计满时按键仍保持按下，才认为是一次有效按键。
module key_remove_shakes( 
	input wire      I_clk,    
	input wire      I_rst_n,
	
	input wire      I_key_in,        
	
	output reg      O_key_trig_out   
);

//---- 时钟域同步与内部信号声明 ----
// 注释虽写打三拍，实际代码同步了 4 拍：前两级抑制亚稳态，后两级提供稳定的边沿检测基准。
	///同步到处理时钟域，打三拍
	reg       S_key_in_sync_1d;      
	reg       S_key_in_sync_2d;      
	reg       S_key_in_sync_3d;      
	reg	      S_key_in_sync_4d;
	wire      S_key_in_n_edge;       
			  
	reg       S_delay_en;            
	reg       S_delay_en_1d;         
	wire      S_delay_en_n_edge;     
	reg[16:0] S_delay_cnt;           
	
	
//---- 按键电平同步（4 级） ----
	always @ (posedge I_clk) begin
		S_key_in_sync_1d <= I_key_in;
		S_key_in_sync_2d <= S_key_in_sync_1d;
		S_key_in_sync_3d <= S_key_in_sync_2d;
		S_key_in_sync_4d <= S_key_in_sync_3d;
	end
	

//---- 按键按下沿检测 ----
// 3d=1、4d=0 表示上一个采样点还是高电平、现在是低电平，即检测到下降沿（按下）。
	assign S_key_in_n_edge = ~S_key_in_sync_3d & S_key_in_sync_4d;
	
	
	always @ (posedge I_clk or negedge I_rst_n) begin
		if(!I_rst_n)
			S_delay_en <= 1'b0;
		else
//---- 消抖窗口控制 S_delay_en ----
// 检测到按下沿就置位，计数到 100000 后清除，形成一个约 4.17 ms @24 MHz 的消抖窗口。
			if(S_key_in_n_edge)
				S_delay_en <= 1'b1;
			else if(S_delay_cnt == 'd100000)
				S_delay_en <= 1'b0;
			else
				S_delay_en <= S_delay_en;
	end
	
	
	always @ (posedge I_clk or negedge I_rst_n) begin
		if(!I_rst_n)
			S_delay_cnt <= 'd0;
		else
//---- 消抖计数器 S_delay_cnt ----
// 仅在窗口有效期间累加，窗口关闭时清零；17 bit 位宽足以覆盖 100000。
			if(S_delay_en)
				S_delay_cnt <= S_delay_cnt + 1'b1;
			else
				S_delay_cnt <= 'd0;
	end
	
	
//---- 窗口结束沿检测：S_delay_en 打一拍，用来做下降沿检测 ----
	always @ (posedge I_clk) begin
		S_delay_en_1d <= S_delay_en;
	end
	
	
	assign S_delay_en_n_edge = ~S_delay_en & S_delay_en_1d;
	
	
//---- 输出寄存（单拍脉冲） ----
	always @ (posedge I_clk) begin
//---- 输出单拍按键脉冲 ----
// 窗口结束时按键仍保持按下电平（!S_key_in_sync_4d），说明是真实按键而非抖动毛刺，
// 于是输出一个 I_clk 周期的高脉冲。
		if(S_delay_en_n_edge && !S_key_in_sync_4d)
			O_key_trig_out <= 1'b1;
		else
			O_key_trig_out <= 1'b0;
	end
	

endmodule
