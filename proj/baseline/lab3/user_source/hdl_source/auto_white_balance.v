//=============================================================================
// 文件      : auto_white_balance.v
// 模块      : auto_white_balance
// 功能      : 自动白平衡增益应用：把 96bit（4 像素 x 24bit）RGB888 数据按输入的 20bit 定点增益分别乘 R/B 通道，G 通道不乘。★全树无例化、不在 .al 编译清单中；本工程实际使用的是根目录 awb.v（在 .al 中）。
// 数据通路  : 输入 I_r_gain[19:0]/I_g_gain[19:0]/I_b_gain[19:0] 与 I_rgb888_data[95:0]；输出 O_awb_data[95:0]。把 96bit 按 24bit 一切分成 p0~p3 四组（p0=[95:72]、p1=[71:48]、p2=[47:24]、p3=[23:0]，组内 [23:16]=R、[15:8]=G、[7:0]=B）。增益乘法 S_awb_*_data_pN <= S_*_data_pN * I_*_gain，结果 28bit（注释标 fi(0,28,12)，即 28 位定点、低 12 位是小数）；饱和处理 (S_awb_*_data_pN[27:12] >= 16d255) ? 8d255 : S_awb_*_data_pN[19:12]，即先看 [27:12] 是否溢出，正常取 [19:12]（右移 12 位去掉小数）。输出再打 2 拍（S_rgb888_valid_1d/_2d -> O_awb_valid）与输入节奏对齐。
// 时钟/复位 : I_clk 上升沿同步；I_rst_n 异步复位、低电平有效。数据通路含 3 拍输出寄存器（与乘法/饱和的流水对齐）。
// 依赖      : 无子模块例化。第 155~171 行是被 // 注释掉的旧版实现（对 O_awb_data 各 24bit 段做 +1），仅作历史保留。
// 综合/实现 : ★未被 camera_to_dsi_display.al 引用、未参与综合实现；乘法为 8bit x 20bit，规模很小。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
//---- kuai 1: duan-kou sheng-ming (96bit RGB888 shu-ru + 3 ge 20bit ding-dian zeng-yi) ----


module auto_white_balance (
    input wire       I_clk,
    input wire       I_rst_n,

	input wire[19:0] I_r_gain,
    input wire[19:0] I_g_gain,
    input wire[19:0] I_b_gain,

    input wire       I_rgb888_frame_start,
    input wire       I_rgb888_frame_end,
    input wire       I_rgb888_valid,
    input wire[95:0] I_rgb888_data,
//---- kuai 2: shu-ru shu-ju chai fen (96bit -> 4 x 24bit, p0=[95:72] ... p3=[23:0]) ----

    output reg       O_awb_frame_start,
    output reg       O_awb_frame_end,
    output reg       O_awb_valid,
    output reg[95:0] O_awb_data
);


    reg        S_rgb888_valid_1d;
    reg        S_rgb888_valid_2d;

    wire[7:0]  S_r_data_p0;  
    wire[7:0]  S_g_data_p0;
    wire[7:0]  S_b_data_p0;
    wire[7:0]  S_r_data_p1;
    wire[7:0]  S_g_data_p1;
    wire[7:0]  S_b_data_p1;
    wire[7:0]  S_r_data_p2;
    wire[7:0]  S_g_data_p2;
    wire[7:0]  S_b_data_p2;
    wire[7:0]  S_r_data_p3;
    wire[7:0]  S_g_data_p3;
    wire[7:0]  S_b_data_p3;
//---- kuai 3: zeng-yi cheng-fa (24bit x 20bit ding-dian, 28bit jie-guo, fi(0,28,12)) ----

    reg[27:0]  S_awb_r_data_p0;  ///fi(0,28,12)
    reg[27:0]  S_awb_g_data_p0;  ///fi(0,28,12)
    reg[27:0]  S_awb_b_data_p0;  ///fi(0,28,12)
    reg[27:0]  S_awb_r_data_p1;  ///fi(0,28,12)
    reg[27:0]  S_awb_g_data_p1;  ///fi(0,28,12)
    reg[27:0]  S_awb_b_data_p1;  ///fi(0,28,12)
    reg[27:0]  S_awb_r_data_p2;  ///fi(0,28,12)
    reg[27:0]  S_awb_g_data_p2;  ///fi(0,28,12)
    reg[27:0]  S_awb_b_data_p2;  ///fi(0,28,12)
    reg[27:0]  S_awb_r_data_p3;  ///fi(0,28,12)
    reg[27:0]  S_awb_g_data_p3;  ///fi(0,28,12)
    reg[27:0]  S_awb_b_data_p3;  ///fi(0,28,12)

    reg[7:0]   S_awb_r_data_p0_limit;   
    reg[7:0]   S_awb_g_data_p0_limit;  
    reg[7:0]   S_awb_b_data_p0_limit;  
    reg[7:0]   S_awb_r_data_p1_limit;  
    reg[7:0]   S_awb_g_data_p1_limit;  
    reg[7:0]   S_awb_b_data_p1_limit;  
    reg[7:0]   S_awb_r_data_p2_limit;  
    reg[7:0]   S_awb_g_data_p2_limit;  
    reg[7:0]   S_awb_b_data_p2_limit;  
    reg[7:0]   S_awb_r_data_p3_limit;  
    reg[7:0]   S_awb_g_data_p3_limit;  
    reg[7:0]   S_awb_b_data_p3_limit;  

    assign S_r_data_p0 = I_rgb888_data[95:88];
//---- kuai 4: bao-he chu-li (xian kan [27:12] shi-fou yi-chu, zheng-chang qu [19:12] ji you-yi 12 wei) ----
    assign S_g_data_p0 = I_rgb888_data[87:80];
    assign S_b_data_p0 = I_rgb888_data[79:72];

    assign S_r_data_p1 = I_rgb888_data[71:64];
    assign S_g_data_p1 = I_rgb888_data[63:56];
    assign S_b_data_p1 = I_rgb888_data[55:48];

    assign S_r_data_p2 = I_rgb888_data[47:40];
    assign S_g_data_p2 = I_rgb888_data[39:32];
    assign S_b_data_p2 = I_rgb888_data[31:24];

    assign S_r_data_p3 = I_rgb888_data[23:16];
    assign S_g_data_p3 = I_rgb888_data[15:8];
    assign S_b_data_p3 = I_rgb888_data[7:0];


	always @(posedge I_clk) begin
        if(I_rgb888_valid)
            begin
                S_awb_r_data_p0 <= S_r_data_p0 * I_r_gain; 
                S_awb_g_data_p0 <= S_g_data_p0 * I_g_gain;
                S_awb_b_data_p0 <= S_b_data_p0 * I_b_gain;

                S_awb_r_data_p1 <= S_r_data_p1 * I_r_gain;
                S_awb_g_data_p1 <= S_g_data_p1 * I_g_gain;
                S_awb_b_data_p1 <= S_b_data_p1 * I_b_gain;

                S_awb_r_data_p2 <= S_r_data_p2 * I_r_gain;
//---- kuai 5: shu-chu ji-cun yu pin-jie (da 2 pai, yu shu-ru jie-zou dui-qi) ----
                S_awb_g_data_p2 <= S_g_data_p2 * I_g_gain;
                S_awb_b_data_p2 <= S_b_data_p2 * I_b_gain;

                S_awb_r_data_p3 <= S_r_data_p3 * I_r_gain;
                S_awb_g_data_p3 <= S_g_data_p3 * I_g_gain;
                S_awb_b_data_p3 <= S_b_data_p3 * I_b_gain;
            end
        else
            begin
                S_awb_r_data_p0 <= 'd0; 
                S_awb_g_data_p0 <= 'd0;
                S_awb_b_data_p0 <= 'd0;

                S_awb_r_data_p1 <= 'd0;
                S_awb_g_data_p1 <= 'd0;
                S_awb_b_data_p1 <= 'd0;

                S_awb_r_data_p2 <= 'd0;
                S_awb_g_data_p2 <= 'd0;
                S_awb_b_data_p2 <= 'd0;

                S_awb_r_data_p3 <= 'd0;
                S_awb_g_data_p3 <= 'd0;
                S_awb_b_data_p3 <= 'd0;
            end
    end


    always @(posedge I_clk) begin
        S_awb_r_data_p0_limit <= (S_awb_r_data_p0[27:12] >= 16'd255) ? 8'd255 : S_awb_r_data_p0[19:12]; 
        S_awb_g_data_p0_limit <= (S_awb_g_data_p0[27:12] >= 16'd255) ? 8'd255 : S_awb_g_data_p0[19:12]; 
        S_awb_b_data_p0_limit <= (S_awb_b_data_p0[27:12] >= 16'd255) ? 8'd255 : S_awb_b_data_p0[19:12]; 

        S_awb_r_data_p1_limit <= (S_awb_r_data_p1[27:12] >= 16'd255) ? 8'd255 : S_awb_r_data_p1[19:12]; 
        S_awb_g_data_p1_limit <= (S_awb_g_data_p1[27:12] >= 16'd255) ? 8'd255 : S_awb_g_data_p1[19:12]; 
        S_awb_b_data_p1_limit <= (S_awb_b_data_p1[27:12] >= 16'd255) ? 8'd255 : S_awb_b_data_p1[19:12]; 

        S_awb_r_data_p2_limit <= (S_awb_r_data_p2[27:12] >= 16'd255) ? 8'd255 : S_awb_r_data_p2[19:12]; 
        S_awb_g_data_p2_limit <= (S_awb_g_data_p2[27:12] >= 16'd255) ? 8'd255 : S_awb_g_data_p2[19:12]; 
        S_awb_b_data_p2_limit <= (S_awb_b_data_p2[27:12] >= 16'd255) ? 8'd255 : S_awb_b_data_p2[19:12]; 

        S_awb_r_data_p3_limit <= (S_awb_r_data_p3[27:12] >= 16'd255) ? 8'd255 : S_awb_r_data_p3[19:12]; 
        S_awb_g_data_p3_limit <= (S_awb_g_data_p3[27:12] >= 16'd255) ? 8'd255 : S_awb_g_data_p3[19:12]; 
        S_awb_b_data_p3_limit <= (S_awb_b_data_p3[27:12] >= 16'd255) ? 8'd255 : S_awb_b_data_p3[19:12]; 
    end

    always @(posedge I_clk) begin
        S_rgb888_valid_1d <= I_rgb888_valid;
        S_rgb888_valid_2d <= S_rgb888_valid_1d;
        O_awb_valid       <= S_rgb888_valid_2d;

        O_awb_frame_start <= I_rgb888_frame_start;
        O_awb_frame_end   <= I_rgb888_frame_end;

        O_awb_data        <= {S_awb_r_data_p0_limit,S_awb_g_data_p0_limit,S_awb_b_data_p0_limit,
                              S_awb_r_data_p1_limit,S_awb_g_data_p1_limit,S_awb_b_data_p1_limit,
                              S_awb_r_data_p2_limit,S_awb_g_data_p2_limit,S_awb_b_data_p2_limit,
                              S_awb_r_data_p3_limit,S_awb_g_data_p3_limit,S_awb_b_data_p3_limit};
    end


//---- kuai 6: bei zhu-shi diao de jiu-ban shi-xian (jin bao-liu, ben ci wei dong) ----
//    always @(posedge I_clk) begin
//        if(I_rgb888_frame_start)
//            begin
//                O_awb_data <= 'd0;
//            end
//        else if(S_rgb888_valid_2d)
//            begin
//                O_awb_data[23:0]  <= O_awb_data[23:0]  + 'd1;
//                O_awb_data[47:24] <= O_awb_data[47:24] + 'd1;
//                O_awb_data[71:48] <= O_awb_data[71:48] + 'd1;
//                O_awb_data[95:72] <= O_awb_data[95:72] + 'd1;
//            end
//        else
//            begin
//                O_awb_data <= O_awb_data;
//            end
//    end
    
endmodule