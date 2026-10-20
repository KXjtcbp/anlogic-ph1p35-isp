//=============================================================================
// 文件      : raw8_to_rgb888.v
// 模块      : raw8_to_rgb888
// 功能      : RAW8 转 RGB888 的简易去马赛克（demosaic）：把每拍 4 个 8bit 的 Bayer RAW8 像素插值成每拍 4 个 24bit RGB888 像素。★未被 isp_top.v 使用、全树无例化、也不在 .al 编译清单中，属备用路径。
// 数据通路  : 输入 I_raw8_data[31:0]（4 个 8bit 像素）；输出 O_rgb888_data[95:0]（4 像素 x 24bit，[23:16]=R、[15:8]=G、[7:0]=B）。先用两个 PH1P_LOGIC_SHIFTER#(.DATA_WIDTH(32),.DATA_DEPTH(258),.SHIFT_TYPE("FIXED"))（U0/U1，第 106~135 行）级联，得到当前行、前一行、前两行共 3 行数据 S_conv_data_1/2/3；S_raw8_line_end = ~I_raw8_valid & S_raw8_valid_1d 检测行尾并给 S_line_cnt 计数；S_line_cnt >= 2 后 S_conv_en 拉高，S_conv_line_odd_even 每行尾翻转，得到奇/偶行两套公式（第 219~236 行奇行、第 238~254 行偶行）；两套都是 4 邻域相加 >> 2（或 2 邻域 >> 1）的平均插值，即用同色邻域的平均值补出缺失的两个分量。输出前打 3 级流水（S_conv_*_1d/_2d），最后把 4 个像素各自取 [7:0] 拼成 96bit（高 8bit 被丢弃）。
// 时钟/复位 : I_clk 上升沿同步；I_rst_n 异步复位、低电平有效（只用于复位 S_line_cnt 等计数器）。
// 依赖      : 例化 PH1P_LOGIC_SHIFTER（PH1P 系列的行移位 IP），另有旧版本注释掉的 w32_d962_shifter 例化（第 99~104 行，仅注释保留）。该 IP 的定义不在本目录，未能确认其所属 IP 库。
// 综合/实现 : ★未被 camera_to_dsi_display.al 引用、未参与综合实现；本工程 RAW8 通路实际由 isp/demosaic_4x_2_0/ 下的模块承担（未逐一比对，未能确认）。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================


module raw8_to_rgb888 (
    input wire        I_clk,
    input wire        I_rst_n,

    input wire        I_raw8_frame_start,
    input wire        I_raw8_frame_end,
    input wire        I_raw8_valid,     
    input wire[31:0]  I_raw8_data,      

    output reg        O_rgb888_frame_start,
    output reg        O_rgb888_frame_end,
    output reg        O_rgb888_valid,
    output reg[95:0]  O_rgb888_data
);


     reg[11:0]  S_line_cnt;
     reg        S_raw8_valid_1d;
	 reg        S_raw8_valid_2d;
     reg[31:0]  S_raw8_data_1d;
	 reg[31:0]  S_raw8_data_2d;
     wire       S_raw8_line_end;
     reg        S_raw8_line_end_1d;
     reg        S_raw8_line_end_2d;
     wire[31:0] S_shift_0_data; 
	 reg[31:0]  S_shift_0_data_1d;
     wire[31:0] S_shift_1_data; 
     reg        S_conv_valid;
     reg[31:0]  S_conv_data_1;
     reg[31:0]  S_conv_data_2;
     reg[31:0]  S_conv_data_3;
     reg        S_conv_en;
     reg        S_conv_line_odd_even;
     reg        S_conv_valid_1d;
     reg[31:0]  S_conv_data_1_1d;
     reg[31:0]  S_conv_data_2_1d;
     reg[31:0]  S_conv_data_3_1d;
     reg        S_conv_valid_2d;
     reg[31:0]  S_conv_data_1_2d;
     reg[31:0]  S_conv_data_2_2d;
     reg[31:0]  S_conv_data_3_2d;
     reg        S_conv_cal_valid;
//---- kuai 1: duan-kou sheng-ming (32bit RAW8 shu-ru -> 96bit RGB888 shu-chu) ----
     reg        S_conv_cal_valid_1d;
     reg[31:0]  S_conv_cal_data_1_1;
     reg[31:0]  S_conv_cal_data_1_2;
     reg[31:0]  S_conv_cal_data_1_3;
     reg[31:0]  S_conv_cal_data_2_1;
     reg[31:0]  S_conv_cal_data_2_2;
     reg[31:0]  S_conv_cal_data_2_3;
     reg[31:0]  S_conv_cal_data_3_1;
     reg[31:0]  S_conv_cal_data_3_2;
     reg[31:0]  S_conv_cal_data_3_3;
     reg[9:0]   S_r_data_p0;
//---- kuai 2: nei-bu ji-cun qi / xian-wang (S_line_cnt, S_conv_* deng) ----
     reg[9:0]   S_g_data_p0;
     reg[9:0]   S_b_data_p0;
     reg[9:0]   S_r_data_p1;
     reg[9:0]   S_g_data_p1;
     reg[9:0]   S_b_data_p1;
     reg[9:0]   S_r_data_p2;
     reg[9:0]   S_g_data_p2;
     reg[9:0]   S_b_data_p2;
     reg[9:0]   S_r_data_p3;
     reg[9:0]   S_g_data_p3;
     reg[9:0]   S_b_data_p3;

//---- kuai 3: shu-ru da-pai + frame_start/end tou-ming chuan-di ----
     always @(posedge I_clk) begin
         O_rgb888_frame_start <= I_raw8_frame_start;
         O_rgb888_frame_end   <= I_raw8_frame_end;
         S_raw8_valid_1d      <= I_raw8_valid;
		 S_raw8_valid_2d      <= S_raw8_valid_1d;
         S_raw8_data_1d       <= I_raw8_data;
		 S_raw8_data_2d       <= S_raw8_data_1d;

		 S_shift_0_data_1d    <= S_shift_0_data;
     end

//---- kuai 4: hang-wei jian-ce (S_raw8_line_end = ~I_raw8_valid & 1d) ----
     assign S_raw8_line_end = ~I_raw8_valid & S_raw8_valid_1d;

     always @(posedge I_clk) begin
         S_raw8_line_end_1d <= S_raw8_line_end;
         S_raw8_line_end_2d <= S_raw8_line_end_1d;
     end

//---- kuai 5: hang-ji-shu S_line_cnt (zhen-qi qing 0, xing-wei +1) ----
     always @(posedge I_clk or negedge I_rst_n) begin
         if(!I_rst_n)
             S_line_cnt <= 'd0;
         else
             if(I_raw8_frame_start)
                 S_line_cnt <= 'd0;
             else if(S_raw8_line_end_2d)
                 S_line_cnt <= S_line_cnt + 'd1;
             else
                 S_line_cnt <= S_line_cnt;
     end


//---- kuai 6: bei zhu-shi diao de jiu-ban shifter shi-li-hua (jin bao-liu) ----
    //   w32_d962_shifter U0_w32_d962_shifter(
    //       .clk     ( I_clk          ),
    //       .en      ( I_raw8_valid   ),
    //       .datain  ( I_raw8_data    ),
    //       .dataout ( S_shift_0_data )
    //   );

//---- kuai 7: 3 hang shu-ju huan-cun (liang ji PH1P_LOGIC_SHIFTER, DATA_DEPTH=258 = yi hang 256+2) ----
    PH1P_LOGIC_SHIFTER#(
        .DATA_WIDTH ( 32     ),
        .DATA_DEPTH ( 258    ),
        .INIT_FILE  ( "NONE" ),
        .SHIFT_TYPE ( "FIXED"))
    U0_w32_d962_shifter(
        .clk     ( I_clk          ),

        .en      ( I_raw8_valid   ),
        .depth   ( 1'b0           ),
        .datain  ( I_raw8_data    ),

        .dataout ( S_shift_0_data )
    );


//---- kuai 8: di er ji shifter (shu-chu shi zai shang yi hang) ----
    PH1P_LOGIC_SHIFTER#(
        .DATA_WIDTH ( 32     ),
        .DATA_DEPTH ( 258    ),
        .INIT_FILE  ( "NONE" ),
        .SHIFT_TYPE ( "FIXED"))
    U1_w32_d962_shifter(
        .clk     ( I_clk          ),

        .en      ( I_raw8_valid   ),
        .depth   ( 1'b0           ),
        .datain  ( S_shift_0_data ),

        .dataout ( S_shift_1_data )
    );

//---- kuai 9: S_conv_en (deng 2 hang shu-ju dou jin lai hou cai qi-dong cha-zhi) ----
     always @(posedge I_clk) begin
         if(S_line_cnt >= 'd2)
             S_conv_en <= 1'b1;
         else
             S_conv_en <= 1'b0;
     end

//---- kuai 10: qi/ou hang biao-zhi S_conv_line_odd_even (mei hang-wei fan-zhuan) ----
     always @(posedge I_clk) begin
         if(S_conv_en)
             if(S_raw8_line_end_2d)
                 S_conv_line_odd_even <= ~S_conv_line_odd_even;
             else
                 S_conv_line_odd_even <= S_conv_line_odd_even;
         else
             S_conv_line_odd_even <= 1'b0;
     end

//---- kuai 11: 3 hang shu-ju dui-qi (data_1 = shang shang hang, data_2 = shang hang, data_3 = dang-qian hang) ----
     always @(posedge I_clk) begin
         if(S_conv_en)
             begin
				 S_conv_valid  <= I_raw8_valid;
                 S_conv_data_1 <= S_shift_1_data;
                 S_conv_data_2 <= S_shift_0_data;
                 S_conv_data_3 <= I_raw8_data;
             end
         else
             begin
                 S_conv_valid  <= 1'b0;
                 S_conv_data_1 <= 'd0;
                 S_conv_data_2 <= 'd0;
                 S_conv_data_3 <= 'd0;
             end
     end


//---- kuai 12: 3 ji liu-shui (wei cha-zhi gong-shi ti-gong shang/zhong/xia san hang de dui-qi shu-ju) ----
     always @(posedge I_clk) begin
         S_conv_valid_1d  <=  S_conv_valid ;
         S_conv_data_1_1d <=  S_conv_data_1;
         S_conv_data_2_1d <=  S_conv_data_2;
         S_conv_data_3_1d <=  S_conv_data_3;

         S_conv_valid_2d  <=  S_conv_valid_1d ;
         S_conv_data_1_2d <=  S_conv_data_1_1d;
         S_conv_data_2_2d <=  S_conv_data_2_1d;
         S_conv_data_3_2d <=  S_conv_data_3_1d;
     end

     always @(posedge I_clk) begin
         if(S_conv_valid && S_conv_valid_1d && S_conv_valid_2d)
             begin
                 S_conv_cal_valid    <= 1'b1;
                 S_conv_cal_data_1_1 <= S_conv_data_1_2d;
                 S_conv_cal_data_1_2 <= S_conv_data_1_1d;
                 S_conv_cal_data_1_3 <= S_conv_data_1;
                 S_conv_cal_data_2_1 <= S_conv_data_2_2d;
                 S_conv_cal_data_2_2 <= S_conv_data_2_1d;
                 S_conv_cal_data_2_3 <= S_conv_data_2;
                 S_conv_cal_data_3_1 <= S_conv_data_3_2d;
                 S_conv_cal_data_3_2 <= S_conv_data_3_1d;
                 S_conv_cal_data_3_3 <= S_conv_data_3;
             end
         else
             begin
                 S_conv_cal_valid    <= 1'b0;
                 S_conv_cal_data_1_1 <= 'd0;
                 S_conv_cal_data_1_2 <= 'd0;
                 S_conv_cal_data_1_3 <= 'd0;
                 S_conv_cal_data_2_1 <= 'd0;
                 S_conv_cal_data_2_2 <= 'd0;
                 S_conv_cal_data_2_3 <= 'd0;
                 S_conv_cal_data_3_1 <= 'd0;
                 S_conv_cal_data_3_2 <= 'd0;
                 S_conv_cal_data_3_3 <= 'd0;
             end
     end


     always @(posedge I_clk) begin
         if(S_conv_cal_valid)
             begin
                 S_conv_cal_valid_1d <= S_conv_cal_valid;

//---- kuai 13: qu-ma-sai-ke qi hang gong-shi (4 lin-yu >> 2 huo 2 lin-yu >> 1 ping-jun cha-zhi) ----
                 if(S_conv_line_odd_even)
                     begin
                         S_r_data_p0 <= (S_conv_cal_data_1_2[31:24] + S_conv_cal_data_3_2[31:24]) >> 1;
                         S_g_data_p0 <= S_conv_cal_data_2_2[31:24];
                         S_b_data_p0 <= (S_conv_cal_data_2_1[7:0] + S_conv_cal_data_2_2[23:16]) >> 1;

                         S_r_data_p1 <= (S_conv_cal_data_1_2[31:24] + S_conv_cal_data_1_2[15:8] + S_conv_cal_data_3_2[31:24] + S_conv_cal_data_3_2[15:8]) >> 2;  
                         S_g_data_p1 <= (S_conv_cal_data_1_2[23:16] + S_conv_cal_data_2_2[31:24] + S_conv_cal_data_2_2[15:8] + S_conv_cal_data_3_2[23:16]) >> 2;  
                         S_b_data_p1 <= S_conv_cal_data_2_2[23:16];

                         S_r_data_p2 <= (S_conv_cal_data_1_2[15:8] + S_conv_cal_data_3_2[15:8]) >> 1;
                         S_g_data_p2 <= S_conv_cal_data_2_2[15:8];
                         S_b_data_p2 <= (S_conv_cal_data_2_2[23:16] + S_conv_cal_data_2_2[7:0]) >> 1;

                         S_r_data_p3 <= (S_conv_cal_data_1_2[15:8] + S_conv_cal_data_1_3[31:24] + S_conv_cal_data_3_2[15:8] + S_conv_cal_data_3_3[31:24]) >> 2;  
                         S_g_data_p3 <= (S_conv_cal_data_1_2[7:0] + S_conv_cal_data_2_2[15:8] + S_conv_cal_data_2_3[31:24] + S_conv_cal_data_3_2[7:0]) >> 2;  
                         S_b_data_p3 <= S_conv_cal_data_2_2[7:0];
                     end
                 else
//---- kuai 14: qu-ma-sai-ke ou hang gong-shi (tong li, lin-yu fang-xiang xiang-fan) ----
                     begin
                         S_r_data_p0 <= S_conv_cal_data_2_2[31:24];
                         S_g_data_p0 <= (S_conv_cal_data_1_2[31:24] + S_conv_cal_data_2_1[7:0] + S_conv_cal_data_2_2[23:16] + S_conv_cal_data_3_2[31:24]) >> 2;  
                         S_b_data_p0 <= (S_conv_cal_data_1_1[7:0] + S_conv_cal_data_1_2[23:16] + S_conv_cal_data_3_1[7:0] + S_conv_cal_data_3_2[23:16]) >> 2;

                         S_r_data_p1 <= (S_conv_cal_data_2_2[31:24] + S_conv_cal_data_2_2[15:8]) >> 1;
                         S_g_data_p1 <= S_conv_cal_data_2_2[23:16];
                         S_b_data_p1 <= (S_conv_cal_data_1_2[23:16] + S_conv_cal_data_3_2[23:16]) >> 1;

                         S_r_data_p2 <= S_conv_cal_data_2_2[15:8];
                         S_g_data_p2 <= (S_conv_cal_data_1_2[15:8] + S_conv_cal_data_2_2[23:16] + S_conv_cal_data_2_2[7:0] + S_conv_cal_data_3_2[15:8]) >> 2;  
                         S_b_data_p2 <= (S_conv_cal_data_1_2[23:16] + S_conv_cal_data_1_2[7:0] + S_conv_cal_data_3_2[23:16] + S_conv_cal_data_3_2[7:0]) >> 2;  

                         S_r_data_p3 <= (S_conv_cal_data_2_2[15:8] + S_conv_cal_data_2_3[31:24]) >> 1;
                         S_g_data_p3 <= S_conv_cal_data_2_2[7:0];
                         S_b_data_p3 <= (S_conv_cal_data_1_2[7:0] + S_conv_cal_data_3_2[7:0]) >> 1;
                     end
             end
         else
             begin
                 S_conv_cal_valid_1d <= 1'b0;
                 S_r_data_p0 <= 'd0;
                 S_g_data_p0 <= 'd0;
                 S_b_data_p0 <= 'd0;
                 S_r_data_p1 <= 'd0;
                 S_g_data_p1 <= 'd0;
                 S_b_data_p1 <= 'd0;
                 S_r_data_p2 <= 'd0;
                 S_g_data_p2 <= 'd0;
                 S_b_data_p2 <= 'd0;
                 S_r_data_p3 <= 'd0;
                 S_g_data_p3 <= 'd0;
                 S_b_data_p3 <= 'd0;
             end
     end


     always @(posedge I_clk) begin
         if(S_conv_cal_valid_1d)
             begin
                 O_rgb888_valid <= 1'b1;
//---- kuai 15: shu-chu pin-jie (4 xiang-su x 24bit, [23:16]=R [15:8]=G [7:0]=B) ----
                 O_rgb888_data  <= {S_r_data_p0[7:0],S_g_data_p0[7:0],S_b_data_p0[7:0],
                                    S_r_data_p1[7:0],S_g_data_p1[7:0],S_b_data_p1[7:0],
                                    S_r_data_p2[7:0],S_g_data_p2[7:0],S_b_data_p2[7:0],
                                    S_r_data_p3[7:0],S_g_data_p3[7:0],S_b_data_p3[7:0]};
             end
         else
             begin
                 O_rgb888_valid <= 1'b0;
                 O_rgb888_data  <= 'd0;
             end
     end
    
endmodule