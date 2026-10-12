//=============================================================================
// 文件      : mipi_rx_error_detect.v
// 模块      : mipi_rx_error_detect
// 功能      : MIPI CSI-2 接收侧的帧结构错误检测：统计一帧内的行数（以及辅助用的列数），若帧结束时行数与预期值 832 不符，则置起 O_mipi_rx_error 供上层丢弃或回退该帧数据；帧内一旦重新收到有效数据即清除错误标志。
// 数据通路  : 输入 I_frame_start / I_frame_end / I_data_valid 为摄像头接收通路的帧头、帧尾、数据有效指示；内部用 S_col_cnt（行内数据个数）与 S_line_cnt（帧内行数）计数，比较结果写入 O_mipi_rx_error。
// 时钟/复位 : I_clk（摄像头接收时钟域，S_csi_rx_clk 一类）；I_rst_n 低电平异步复位。
// 依赖      : 例化了 ChipWatcher 调试核 cwc1（probe0..probe9 观测帧信号与计数器），属历史草稿：本工程源码树中未找到 cwc1 的模块定义，也未发现有任何模块例化本模块；video_in.v 的 I_mipi_rx_error 在 design_top_wrapper.v:637 被常量 1'b0 取代，因此本模块疑似未接入。
// 综合/实现 : 引用了不存在的 cwc1 模块定义，无法直接综合；工程文件 td_project/camera_to_dsi_display.al 未收录本文件。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================


module mipi_rx_error_detect (
    input wire    I_clk,
    input wire    I_rst_n,

    input wire    I_frame_start, 
    input wire    I_frame_end,   
    input wire    I_data_valid,  

    output reg    O_mipi_rx_error 
);


//---- 内部信号声明 ----
// S_line_cnt：帧内已统计的行数；S_col_cnt：当前行内有效数据个数（仅作观测）。
    reg[11:0] S_line_cnt;      
    reg[11:0] S_col_cnt;       
    reg       S_data_valid_1d;
    wire      S_line_end;
    
    always @ (posedge I_clk) begin
//---- I_data_valid 打拍，用于产生行结束标志 ----
    	S_data_valid_1d <= I_data_valid;
    end
    
//---- 行结束标志 ----
// 上一拍有效、这一拍无效，即一行的数据刚刚结束（下降沿）。
    assign S_line_end = ~I_data_valid & S_data_valid_1d;
    
    always @ (posedge I_clk) begin
//---- 行内计数器 S_col_cnt ----
// 数据有效期间逐拍累加，行间无效时清零，因此它的值就是本行的数据个数。
    	if(I_data_valid)
        	S_col_cnt <= S_col_cnt + 'd1;
     	else
         	S_col_cnt <= 'd0;
    end
    
    always @ (posedge I_clk) begin
//---- 帧内行计数器 S_line_cnt ----
// 帧头清零，之后每检测到一次行结束加一，帧尾时的值即本帧总行数。
    	if(I_frame_start)
        	S_line_cnt <= 'd0;
      	else if(S_line_end)
          	S_line_cnt <= S_line_cnt + 'd1;
       	else
           	S_line_cnt <= S_line_cnt;
    end

//---- 错误判定 ----
// 判据：帧尾到来时行数必须等于 832。
// 832 是本工程 1280x720 RAW10 数据流下期望的帧内行数（按实际接收通路统计值写死），
// 帧结构或分辨率改变时需要同步修改该常数，否则会误报。
// 一旦检出错误，标志保持到帧内重新出现有效数据（I_data_valid）才清除。
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            O_mipi_rx_error <= 1'b0;
        else    
            if(I_frame_end && S_line_cnt != 12'd832)
                O_mipi_rx_error <= 1'b1;
            else if(I_data_valid)
                O_mipi_rx_error <= 1'b0;
            else
                O_mipi_rx_error <= O_mipi_rx_error;
    end
	
	
reg [11:0] h_cnt;
reg [11:0] c_cnt;

//---- 辅助调试计数 h_cnt ----
// h_cnt 统计帧尾之前累计的数据有效拍数，与 c_cnt（帧尾次数）都未参与错误判定，仅用于观测。
always@(posedge I_clk)begin
	if(!I_rst_n || I_frame_end)
		h_cnt <= 12'd0;
	else if(I_data_valid)
		h_cnt <= h_cnt + 1'b1;
	else
		h_cnt <= h_cnt;
end

always@(posedge I_clk)begin
	if(!I_rst_n || I_frame_start)
		c_cnt <= 12'd0;
	else if(I_frame_end)
		c_cnt <= c_cnt + 1'b1;
	else
		c_cnt <= c_cnt;
end
    
//---- ChipWatcher 观测实例（历史草稿） ----
// cwc1 是 TD 在线调试工具 ChipWatcher 生成的观测核，把上列信号引出到探针；
// 本工程未提供 cwc1 的模块定义，本模块也未在工程中被例化，故此段按原样保留、不参与功能。
// 注意：此处探针列表中并没有任何 lane 错误相关信号。
   cwc1 cwc_inst
 (
     .probe0(I_frame_start),
     .probe1(I_frame_end),
     .probe2(I_data_valid),
     .probe3(O_mipi_rx_error),
     .probe4(S_line_cnt),
     .probe5(S_col_cnt),
     .probe6(S_data_valid_1d),
     .probe7(S_line_end),
     .probe8(h_cnt),
     .probe9(c_cnt),
     .clk(I_clk)
 );
    
endmodule