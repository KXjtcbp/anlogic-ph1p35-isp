//=============================================================================
// 文件      : lane_lvds_10_1.v
// 模块      : lane_lvds_10_1
// 功能      : TMDS 串行发送的最小单元（1 条 lane）：把 10 bit 并行 TMDS 字符按像素时钟节拍装入移位寄存器，在串行时钟域每拍左移 2 bit，最后借助器件 ODDR 原语以双沿方式输出，得到串行 TMDS 码流。
// 数据通路  : I_data_in[9:0]（来自 hdmi_phy_wrapper 位序重排后的 TMDS 字符）→ S_shift_data 移位 → S_oddr_data[1:0] → ODDR 的 d1/d0 → O_serial_out。串行时钟是像素时钟的 5 倍（10 bit = 5 个串行周期 × 双沿 2 bit）。
// 时钟/复位 : I_pixel_clk（装载节拍，来自 HDMI_PIXEL_CLK）；I_serial_clk（移位时钟，来自 HDMI_SERIAL_CLK，本工程 375 MHz）；I_rst 高电平异步复位，分别复位像素域与串行域逻辑。
// 依赖      : 依赖 TD 原语 EF2_LOGIC_ODDR / EF3_ / EF4_ / SF1_ / EG_ / PH1_ / PH1P_ / DR1_LOGIC_ODDR，由 parameter DEVICE 选择（本工程 hdmi_phy_wrapper 传 DEVICE="PH1P"）。被 hdmi_phy_wrapper.v:71/83/95/107 例化 4 次（ch0/ch1/ch2/clk）。
// 综合/实现 : 含器件专属 ODDR 原语，只能由 TD 综合；generate 里没有 else 分支，DEVICE 取值不在列表中时不会产生任何输出。已收录于 td_project/camera_to_dsi_display.al。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================




//---- 模块说明 ----
// 10 bit TMDS 字符无法由普通寄存器直接串出，这里采用像素域装载 + 5 倍串行域移位 + ODDR 双沿输出的结构：
// 每个像素周期装载一次，随后 5 个串行时钟周期正好把 10 bit 全部移出。
module lane_lvds_10_1 #(
    parameter DEVICE = "EG"
    )(
    input wire      I_pixel_clk,
    input wire      I_serial_clk,
    input wire      I_rst,

    input wire[9:0] I_data_in,

    output wire     O_serial_out
);

//---- 内部信号声明 ----
    reg      S_odd_even;     
    reg      S_odd_even_1d;  
    reg      S_odd_even_2d;  
    reg      S_load_en;      
    reg      S_load_en_1d;   
    reg      S_load_en_2d;   
    reg[9:0] S_shift_data;   
    reg[1:0] S_oddr_data;    


//---- 像素域节拍标志 S_odd_even ----
// 在像素时钟域每个周期翻转一次，用于把每像素装载一次这个事件搬移到串行时钟域。
    always @(posedge I_pixel_clk or posedge I_rst) begin
        if(I_rst)
            S_odd_even <= 1'b0;
        else
            S_odd_even <= ~S_odd_even;
    end

//---- 跨时钟域同步（像素域 -> 串行域） ----
    always @(posedge I_serial_clk) begin
        S_odd_even_1d <= S_odd_even;
        S_odd_even_2d <= S_odd_even_1d;
    end

    always @(posedge I_serial_clk) begin
//---- 装载使能产生 ----
// 两级同步后的异或即边沿检测：S_odd_even 每像素周期翻转一次，
// 所以 S_load_en 在串行域里每个像素周期出现一次高电平，作为装载脉冲。
        S_load_en    <= S_odd_even_1d ^ S_odd_even_2d;
        S_load_en_1d <= S_load_en;
        S_load_en_2d <= S_load_en_1d;
    end

//---- 并串移位寄存器 S_shift_data ----
// S_load_en_2d 有效时把 10 bit 并行数据整体装入；
// 其余串行周期每次左移 2 bit，为 ODDR 的双沿输出每次提供 2 bit。
// 装载 1 次 + 移位 5 次正好把 10 bit 全部送出。
    always @(posedge I_serial_clk or posedge I_rst) begin
        if(I_rst)
            S_shift_data <= 'd0;
        else
            if(S_load_en_2d)
                S_shift_data <= I_data_in;
            else 
                S_shift_data <= S_shift_data << 2;
    end

    always @(posedge I_serial_clk) begin
//---- ODDR 数据准备 ----
// 取最高 2 bit 交给 ODDR：d1 在时钟上升沿输出、d0 在下降沿输出（见下方端口连接）。
        S_oddr_data <= S_shift_data[9:8];
    end

//---- 器件相关 ODDR 原语选择 ----
// 同一份逻辑要在多种安路器件上综合，用 generate + parameter 字符串比较挑选对应原语；
// 各分支里实例名都叫 U_EG4_ODDR（历史沿用），只有被选中的分支才会被实例化。
// 本工程 hdmi_phy_wrapper 传 DEVICE="PH1P"，实际生效的是 PH1P_LOGIC_ODDR 那一支。
    generate
        if(DEVICE == "EF2")
            begin
                EF2_LOGIC_ODDR U_EG4_ODDR(
                    .clk   ( I_serial_clk   ),
                    .rst   ( I_rst          ),

                    .d1    ( S_oddr_data[0] ),
                    .d0    ( S_oddr_data[1] ),

                    .q     ( O_serial_out   )
                );
            end
        else if(DEVICE == "EF3")
            begin
                EF3_LOGIC_ODDR U_EG4_ODDR(
                    .clk   ( I_serial_clk   ),
                    .rst   ( I_rst          ),

                    .d1    ( S_oddr_data[0] ),
                    .d0    ( S_oddr_data[1] ),

                    .q     ( O_serial_out   )
                );
            end
        else if(DEVICE == "EF4")
            begin
                EF4_LOGIC_ODDR U_EG4_ODDR(
                    .clk   ( I_serial_clk   ),
                    .rst   ( I_rst          ),

                    .d1    ( S_oddr_data[0] ),
                    .d0    ( S_oddr_data[1] ),

                    .q     ( O_serial_out   )
                );
            end
        else if(DEVICE == "SF1")
            begin
                SF1_LOGIC_ODDR U_EG4_ODDR(
                    .clk   ( I_serial_clk   ),
                    .rst   ( I_rst          ),

                    .d1    ( S_oddr_data[0] ),
                    .d0    ( S_oddr_data[1] ),

                    .q     ( O_serial_out   )
                );
            end
        else if(DEVICE == "EG")
            begin
                EG_LOGIC_ODDR U_EG4_ODDR(
                    .clk   ( I_serial_clk   ),
                    .rst   ( I_rst          ),

                    .d1    ( S_oddr_data[0] ),
                    .d0    ( S_oddr_data[1] ),

                    .q     ( O_serial_out   )
                );
            end
        else if(DEVICE == "PH1A")
            begin
                PH1_LOGIC_ODDR U_EG4_ODDR(
                    .clk   ( I_serial_clk   ),
                    .rst   ( I_rst          ),

                    .d1    ( S_oddr_data[0] ),
                    .d0    ( S_oddr_data[1] ),

                    .q     ( O_serial_out   )
                );
            end
        else if(DEVICE == "PH1P")
            begin
                PH1P_LOGIC_ODDR U_EG4_ODDR(
                    .clk   ( I_serial_clk   ),
                    .rst   ( I_rst          ),

                    .d1    ( S_oddr_data[0] ),
                    .d0    ( S_oddr_data[1] ),

                    .q     ( O_serial_out   )
                );
            end
        else if(DEVICE == "DR1")
            begin
                DR1_LOGIC_ODDR U_EG4_ODDR(
                    .clk   ( I_serial_clk   ),
                    .rst   ( I_rst          ),

                    .d1    ( S_oddr_data[0] ),
                    .d0    ( S_oddr_data[1] ),

                    .q     ( O_serial_out   )
                );
            end
//---- 器件原语选择结束 ----
// 注意：generate 里没有 else 分支，若 DEVICE 不属于上面 8 种取值，O_serial_out 将无驱动。
    endgenerate
    
endmodule