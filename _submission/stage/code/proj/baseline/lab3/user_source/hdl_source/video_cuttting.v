//=============================================================================
// 文件      : video_cuttting.v
// 模块      : video_cutting
// 功能      : RAW8 图像裁剪（ROI 提取）：在有效期内只放行指定行列窗口内的像素，窗口外输出 valid 拉低、data 清零。
//             本文件只做行列计数与窗口门控，不含任何图像算法。
//             注意：文件名拼写为 video_cuttting.v（三个 t），而模块名是 video_cutting（两个 t），不一致属历史遗留。
// 数据通路  : I_raw8_data[31:0]（一拍一个 RAW8 像素）-> 行/列计数器定位 -> 窗口门控 -> O_raw8_data[31:0]。
//             O_raw8_frame_start / O_raw8_frame_end 仅打一拍透传，用于保持帧边界与像素流的相对时序。
// 时钟/复位 : 单一时钟域 I_clk；I_rst_n 低有效异步复位，但只用于 S_line_cnt 的复位。
//             S_col_cnt / S_line_en / 输出寄存器没有复位，靠帧起始与 valid 下降沿自然归位。
// 依赖      : 无子模块例化；纯 RTL，无器件原语、无 IP。
// 综合/实现 : 可综合。未被 td_project/camera_to_dsi_display.al 收录；全树未搜索到 video_cutting 的例化点，
//             疑似未接入本工程（未能确认是否被例化）。
//-----------------------------------------------------------------------------
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================




//---- 模块说明 ----
// 本模块把 RAW8 数据流裁剪成一个矩形 ROI：
//   行方向：S_line_cnt 落在 126..727 之间的行才允许输出（裁剪后有效高度 727-126+1 = 602 行）；
//   列方向：行内第 100..357 个像素才允许输出（裁剪后有效宽度 357-100+1 = 258 列）。
// 窗口内的像素原样送出并置高 O_raw8_valid，窗口外的像素被丢弃（valid 拉低、data 清零），
// 这样后级拿到的就是一帧固定的 258 x 602 子图。
module video_cutting (
    input wire       I_clk,
    input wire       I_rst_n,

    input wire       I_raw8_frame_start,
    input wire       I_raw8_frame_end,
    input wire       I_raw8_valid,
    input wire[31:0] I_raw8_data,

    output reg       O_raw8_frame_start,
    output reg       O_raw8_frame_end,
    output reg       O_raw8_valid,
    output reg[31:0] O_raw8_data
);


//---- 内部信号声明 ----
// S_col_cnt：行内像素（列）计数器，valid 期间累加、valid 无效时清零；
// S_line_cnt：已完成的行（行）计数器，帧起始清零；
// S_line_en：由 S_line_cnt 译码出的行窗口使能；
// S_raw8_valid_n_edge：valid 的下降沿，代表一行数据结束。
    reg[11:0] S_col_cnt;
    reg[11:0] S_line_cnt;
    reg       S_raw8_valid_1d;
    wire      S_raw8_valid_n_edge;
    reg       S_line_en;

    always @(posedge I_clk) begin
        S_raw8_valid_1d <= I_raw8_valid;
    end

//---- valid 下降沿检测 ----
// 打一拍后与本拍反相相与，得到 valid 的下降沿；
// RAW8 是一行连续若干个有效拍，下降沿即这一行数据送完，用它给行计数器加一。
    assign S_raw8_valid_n_edge = ~I_raw8_valid & S_raw8_valid_1d;


//---- 行内列计数器 S_col_cnt ----
// valid 有效时逐拍累加，代表当前像素在本行中的列号（从 0 开始）；
// valid 无效（行间隙）时清零，为下一行重新计数。
    always @(posedge I_clk) begin
        if(I_raw8_valid)
            S_col_cnt <= S_col_cnt + 'd1;
        else
            S_col_cnt <= 'd0;
    end

    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            S_line_cnt <= 'd0;
        else
            if(I_raw8_frame_start)
                S_line_cnt <= 'd0;
            else if(S_raw8_valid_n_edge)
                S_line_cnt <= S_line_cnt + 'd1;
            else
                S_line_cnt <= S_line_cnt;
    end


//---- 行窗口使能打拍 ----
// 把组合译码出的行窗口标志打一拍，供像素输出级使用。
    always @(posedge I_clk) begin
//---- 行窗口译码 ----
// 只保留第 126 行到第 727 行（含端点）之间的图像行，其余行整行丢弃；
// 常量含义：裁掉上下两侧的无效/黑边区域，裁剪后有效高度 = 727-126+1 = 602 行。
        if(S_line_cnt >= 'd126 && S_line_cnt <= 'd727)
            S_line_en <= 1'b1;
        else
            S_line_en <= 1'b0;
    end

//---- 裁剪后像素输出 ----
    always @(posedge I_clk) begin
//---- 像素输出门控 ----
// 三个条件同时满足才算窗口内像素：本拍 valid、列号在 100..357 之间、当前行在行窗口内；
// 常量含义：裁掉左右两侧，裁剪后有效宽度 = 357-100+1 = 258 列；
// 条件不满足时输出清零而不是保持，避免后级把窗口外的数据当成有效像素。
        if(I_raw8_valid && S_col_cnt >= 'd100 && S_col_cnt <= 'd357 && S_line_en)
            begin
                O_raw8_valid <= 1'b1;
                O_raw8_data  <= I_raw8_data;
            end
        else    
            begin
                O_raw8_valid <= 1'b0;
                O_raw8_data  <= 'd0;
            end
    end

//---- 帧起始/结束透传 ----
// frame_start / frame_end 与像素流一起打一拍，保证帧边界与裁剪后的像素流保持同一节拍；
// 这里不做任何修饰，只让它们的延时与 O_raw8_valid / O_raw8_data 一致。
    always @(posedge I_clk) begin
        O_raw8_frame_start <= I_raw8_frame_start;
        O_raw8_frame_end   <= I_raw8_frame_end;
    end
//---- 已废弃的 ChipWatcher 调试例化（保留作历史记录，不参与综合） ----
// 这是当时用 TD ChipWatcher 在线抓信号的草稿：
// 把本模块的输入、输出与全部内部计数器接到 probe0..probe12 上观察窗口边界；
// 整段都在注释里，故 cwc2 模块是否存在都不影响本文件的编译。
//  cwc2 cwc2_inst
//(
//    .probe0(I_raw8_frame_start),
//    .probe1(I_raw8_frame_end),
//    .probe2(I_raw8_valid),
//    .probe3(I_raw8_data),
//    .probe4(O_raw8_frame_start),
//    .probe5(O_raw8_frame_end),
//    .probe6(O_raw8_valid),
//    .probe7(O_raw8_data),
//    .probe8(S_col_cnt),
//    .probe9(S_line_cnt),
//    .probe10(S_raw8_valid_1d),
//    .probe11(S_raw8_valid_n_edge),
//    .probe12(S_line_en),
//    .clk(I_clk)
//);
    
endmodule