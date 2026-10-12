//=============================================================================
// 文件      : signal_delay.v
// 模块      : signal_delay #( IMG_HEIGHT=1080, IMG_WIDTH=1920, DATA_WIDTH=96, DELAY_CYCLE=50 )
// 功能      : 整行信号延时：用一块双口 BRAM 把像素流（含 valid/tuser）延后 DELAY_CYCLE 行，好让 awb 的除法器算完增益后再对齐施加到同一像素上。★与 isp\awb\signal_delay.v 同名但内容不同。核实结论：本文件在 .al 编译清单中，被 awb.v:186 与 awb.v:225 各例化一次，是本工程当前在用的实现（isp/awb/ 下的同名文件不在 .al 中）。
// 数据通路  : 输入 I_clk/I_rst_n/I_tuser/I_valid/I_data[DATA_WIDTH-1:0]，输出 O_valid/O_data/O_tuser。localparam IMG_WIDTH_4x = (IMG_WIDTH >> 2)（1280 -> 320，因为每拍 4 个像素）；h_cnt 在 I_valid_r 时按 IMG_WIDTH_4x 环回、v_cnt 在行尾时按 IMG_HEIGHT 环回，组成写地址基准；rd_valid 在 h_cnt == DELAY_CYCLE - 3（= 47）时拉高，rd_cnt 计到 IMG_WIDTH_4x-1 清 0，作为读地址基准；addra（写指针）与 addrb（读指针）都在 IMG_WIDTH_4x 内环回（11bit，深度覆盖一行）；O_valid = rd_valid_d（打一拍），O_tuser = (v_cnt==0)&&(rd_cnt==1)（读侧第 0 行第 1 拍重新产生行首标志）。写侧 I_valid_r 打拍后驱动 BRAM 的 wea，数据 I_data_r 驱动 dia；读侧 dob 直接接到 O_data。
// 时钟/复位 : I_clk 同时作 BRAM 的 clka 与 clkb（同步双口），I_rst_n 异步复位、低电平有效；延时量由 DELAY_CYCLE 参数（例化时为 50 行）决定。
// 依赖      : 例化 blk_mem_gen_awb_delay_signal（真双口块 RAM，11bit 地址 x 96bit 数据）。该 BRAM 的源文件在 E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\awb\ram\blk_mem_gen_awb_delay_signal.v，而该路径不在 camera_to_dsi_display.al 中，本工程应是在 .al 里以 IP 形式提供该 BRAM（未能从 .al 逐字确认，属未确认点）。
// 综合/实现 : 本文件在 camera_to_dsi_display.al 的编译清单中；综合结果是一块 320 x 96bit 的双口 BRAM（约 30Kbit）。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
//---- kuai 1: duan-kou sheng-ming (xiang-su liu + tuser de zheng-hang yan-shi) ----
/*****************************************************************
Company : MiLianKe Electronic Technology Co., Ltd.
WebSite:https://www.milianke.com
TechWeb:https://www.uisrc.com
tmall-shop:https://milianke.tmall.com
jd-shop:https://milianke.jd.com
taobao-shop: https://milianke.taobao.com
Description: 
The reference demo provided by Milianke is only used for learning. 
We cannot ensure that the demo itself is free of bugs, so users 
should be responsible for the technical problems and consequences
caused by the use of their own products.
@Author      :   XiaoQingquan 
@Time        :   2025/01 
version:     :   
@Description :   
*****************************************************************/
module signal_delay #(
    parameter IMG_HEIGHT = 1080,
    parameter IMG_WIDTH  = 1920,
    parameter DATA_WIDTH = 96,
    parameter DELAY_CYCLE = 50
) (
    input                        I_clk,
    input                        I_rst_n,
    input                        I_tuser,  //synthesis keep 
    input  wire                  I_valid,  //synthesis keep 
    input  wire [DATA_WIDTH-1:0] I_data,   //synthesis keep 
    output wire                  O_valid,  //synthesis keep 
    output wire [DATA_WIDTH-1:0] O_data ,  //synthesis keep 
    output wire                  O_tuser   //synthesis keep 
);

    //---- kuai 2: xie/du di-zhi yu qi-dong xin-hao (rd_valid / rd_cnt / addra / addrb) ----
    wire        rd_en;  //synthesis keep 

    reg  [10:0] addra;  //synthesis keep 
    reg  [10:0] addrb;  //synthesis keep 


    reg  [13:0] h_cnt;
    reg  [13:0] v_cnt;
    reg  [13:0] rd_cnt;
    
    reg  [DATA_WIDTH-1:0] I_data_r;
    reg         rd_valid,I_valid_r;

    //---- kuai 3: hang-lie ji-shu (IMG_WIDTH_4x = IMG_WIDTH >> 2, yin wei mei pai 4 xiang-su) ----
    localparam IMG_WIDTH_4x = (IMG_WIDTH >> 2);
    //---- kuai 4: xie-ce shi-neng da-pai I_valid_r ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n ) begin
            I_valid_r <= 0;
            I_data_r  <= 0;
        end
        else begin
            I_valid_r <= I_valid;
            I_data_r  <= I_data;
        end
    end

    //---- kuai 5: hang/lie ji-shu (h_cnt an IMG_WIDTH_4x huan-hui, v_cnt an IMG_HEIGHT huan-hui) ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            h_cnt <= 0;
            v_cnt <= 0;
        end
        else begin
            h_cnt <= I_valid_r ? ((h_cnt == IMG_WIDTH_4x-1) ? 0 : h_cnt + 1) : h_cnt;
            v_cnt <= I_valid_r &&(h_cnt == IMG_WIDTH_4x-1) ? ((v_cnt == IMG_HEIGHT - 1) ? 0 : v_cnt + 1) : v_cnt;
        end
    end
    
    //---- kuai 6: du qi-dong (h_cnt == DELAY_CYCLE - 3 shi la-di, ji yan shi DELAY_CYCLE hang) ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            rd_valid <= 0;
        end
        else if(h_cnt == DELAY_CYCLE - 3)begin
            rd_valid <= 1;
        end
        else if(rd_cnt == IMG_WIDTH_4x - 1) 
            rd_valid <= 0;
    end

    //---- kuai 7: du-ce hang-shou ji-shu rd_cnt (ji dao yi-hang jie-shu qing 0) ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            rd_cnt <= 0;
        end
        else if(rd_cnt == IMG_WIDTH_4x )
            rd_cnt <= 0;
        else if(rd_valid)begin
            rd_cnt <= rd_cnt + 1;
        end
    end

    //---- kuai 8: BRAM xie di-zhi addra (zai yi-hang nei huan-hui) ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n || I_tuser) begin
            addra <= 0;
        end else if (I_valid_r) begin
            addra <= (addra == IMG_WIDTH_4x - 1) ? 'b0 : addra + 1'b1;
        end
    end

  
    //---- kuai 9: BRAM du di-zhi addrb (sui rd_valid zai yi-hang nei huan-hui) ----
    always @(posedge I_clk or negedge I_rst_n) begin
      if (!I_rst_n || I_tuser) begin
        addrb <= 0;
      end else begin
        addrb <= rd_valid ? (addrb == IMG_WIDTH_4x - 1) ? 'b0 : addrb + 1'b1 : addrb;
      end
    end
    
    //---- kuai 10: shu-chu you-xiao da-pai (O_valid = rd_valid_d) ----
    reg rd_valid_d;
    always @(posedge I_clk or negedge I_rst_n) begin
      if (!I_rst_n) begin
        rd_valid_d <= 0;
      end else begin
        rd_valid_d <= rd_valid;
      end
    end
    //---- kuai 11: shu-chu shou-wo (O_valid / O_tuser: di 0 hang di 1 pai chong-xin chan-sheng hang-shou) ----
    assign O_valid = rd_valid_d;
    assign O_tuser = (v_cnt == 0) && (rd_cnt == 1);

    //---- kuai 12: shuang-kou BRAM shi-li-hua (yuan-wen-jian isp/awb/ram/blk_mem_gen_awb_delay_signal.v, bu zai .al qing-dan zhong) ----
    blk_mem_gen_awb_delay_signal blk_mem_gen_awb_delay_signal_d (
      .clka (I_clk   ),  // input wire clka
      .wea  (I_valid_r),  // input wire [0 : 0] wea
      .addra(addra   ),  // input wire [10 : 0] addra
      .dia  (I_data_r ),  // input wire [95 : 0] dina
      .clkb (I_clk   ),  // input wire clkb
      .addrb(addrb   ),  // input wire [10 : 0] addrb
      .dob  (O_data  )   // output wire [95 : 0] doutb
    );


endmodule