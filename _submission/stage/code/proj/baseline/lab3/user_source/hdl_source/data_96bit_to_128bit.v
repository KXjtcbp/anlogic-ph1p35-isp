//=============================================================================
// 文件      : data_96bit_to_128bit.v
// 模块      : data_96bit_to_128bit
// 功能      : 位宽重切 96bit->128bit。★疑似历史遗留副本：本文件与 isp\data96_128\data96_128.v 的模块名、端口、三段 always、case 分支逐字同构（只少末尾那段 /* */ 旧代码）。本工程 .al 编译的是 isp/data96_128/data96_128.v，本文件未被引用。
// 数据通路  : 输入 I_96b_data[95:0]，输出 O_128b_data[127:0]；S_phase_cnt 在输入有效时每拍 +1，case 的 d1 = {S_96b_data_1d, I_96b_data[95:64]}、d2 = {S_96b_data_1d[63:0], I_96b_data[95:32]}、d3 = {S_96b_data_1d[31:0], I_96b_data}；每 4 拍输入只出 3 拍有效（d0 那拍清 0）。24bit 像素边界与 128bit 字边界不对齐（128 mod 24 = 8）。
// 时钟/复位 : I_clk 上升沿同步；I_rst_n 为端口保留，代码内未使用（与 isp 目录下同名模块一致）。
// 依赖      : 无任何模块例化它（全树 grep 只命中 module 定义本身）；不依赖其它自研模块。
// 综合/实现 : ★未被 camera_to_dsi_display.al 引用、未参与本工程综合实现；本工程对应功能由 isp/data96_128/data96_128.v 承担。保留原因未能从代码确认。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================


//---- kuai 1: duan-kou sheng-ming (96bit shu-ru -> 128bit shu-chu) ----
module data_96bit_to_128bit (
    input wire        I_clk,
    input wire        I_rst_n,
   
    input wire        I_96b_frame_start,
    input wire        I_96b_valid,
    input wire[95:0]  I_96b_data,
  
    output reg        O_128b_frame_start,
    output reg        O_128b_valid,
    output reg[127:0] O_128b_data
);



    //---- kuai 2: nei-bu ji-cun qi (yu isp/data96_128/data96_128.v wan-quan yi-zhi) ----
    reg[95:0]  S_96b_data_1d;
    reg        S_96b_valid_1d;
    reg[1:0]   S_phase_cnt;


    //---- kuai 3: shu-ru da-pai + frame_start ji-cun ----
    always @(posedge I_clk) begin
        S_96b_valid_1d <= I_96b_valid;
        S_96b_data_1d  <= I_96b_data;

		O_128b_frame_start <= I_96b_frame_start;
    end


    //---- kuai 4: xiang-wei ji-shu (I_96b_valid you-xiao shi +1, fou-ze qing 0) ----
    always @(posedge I_clk) begin
        if(I_96b_valid)
            S_phase_cnt <= S_phase_cnt + 'd1;
        else
            S_phase_cnt <= 'd0;
    end


    //---- kuai 5: 96bit -> 128bit kua-pai pin-jie (mei 4 pai shu-ru zhi chu 3 pai you-xiao) ----
    always @(posedge I_clk) begin
        if(I_96b_valid)
            begin
                case(S_phase_cnt)
                    //---- d0: shu-chu qing-ling ----
                    'd0 : 
                        begin
                            O_128b_valid <= 1'b0;
                            O_128b_data  <= 'd0;
                        end
                    //---- d1: {shang yi pai 96bit, ben pai I_96b_data[95:64]} -> 128bit ----
                    'd1 :
                        begin
                            O_128b_valid <= 1'b1;
                            O_128b_data  <= {S_96b_data_1d,I_96b_data[95:64]};
                        end
                    //---- d2: {shang yi pai [63:0], ben pai I_96b_data[95:32]} -> 128bit ----
                    'd2 :
                        begin
                            O_128b_valid <= 1'b1;
                            O_128b_data  <= {S_96b_data_1d[63:0],I_96b_data[95:32]};
                        end
                    //---- d3: {shang yi pai [31:0], ben pai I_96b_data[95:0] } -> 128bit ----
                    'd3 :
                        begin
                            O_128b_valid <= 1'b1;
                            O_128b_data  <= {S_96b_data_1d[31:0],I_96b_data};
                        end
                    //---- default: qing-ling ----
                    default:
                        begin
                            O_128b_valid <= 1'b0;
                            O_128b_data  <= 'd0;
                        end
                endcase
            end
        //---- else (I_96b_valid = 0): shu-chu qing-ling ----
        else
            begin
                O_128b_valid <= 1'b0;
                O_128b_data  <= 'd0;
            end
    end

    

endmodule