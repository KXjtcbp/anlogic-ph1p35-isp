//=============================================================================
// 文件      : isp/data96_128/data96_128.v
// 模块      : data_96bit_to_128bit（注意：模块名与文件名 data96_128.v 不一致，文件名是目录名风格）
// 功能      : 位宽重切：把连续的 96bit 数据（=4 像素 x 24bit）按“先到的字放高位”的规则拼成连续位流，再每 128bit 切一片输出，供后级 128bit 位宽的数据通路使用。
// 数据通路  : 输入 I_96b_data[95:0]，输出 O_128b_data[127:0]。核心是 S_phase_cnt（原 S_cnt，2026-10-09 改名）：I_96b_valid 有效时每拍 +1，无效时清 0；case(S_phase_cnt) 的 4 个分支：d0 输出清零，d1 = {S_96b_data_1d, I_96b_data[95:64]}，d2 = {S_96b_data_1d[63:0], I_96b_data[95:32]}，d3 = {S_96b_data_1d[31:0], I_96b_data}（S_96b_data_1d 是上一拍输入的 96bit，用于跨拍拼接）。因此每 4 拍输入只出 3 拍有效数据。24bit 像素边界与 128bit 字边界天然不对齐（128 mod 24 = 8），所以只能用这种跨拍拼接。O_128b_frame_start 只打一拍寄存。
// 时钟/复位 : I_clk 上升沿同步；I_rst_n 异步复位、低电平有效，但复位在本模块内未参与任何 always，只作端口保留。
// 依赖      : 被 isp/isp_top.v:171 例化为 u_data_96bit_to_128bit。本文件末尾第 87~101 行是被 /* */ 注释掉的旧版 module data96_128（用 8d0 补齐的另一种写法），仅作历史保留。
// 综合/实现 : 本文件在 camera_to_dsi_display.al 的编译清单中；根目录下同名 module 的 data_96bit_to_128bit.v 未被 .al 引用。
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



    //---- kuai 2: nei-bu ji-cun qi (S_96b_data_1d = shang yi pai shu-ru; S_phase_cnt = wei-tiao xiang-wei) ----
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
                    //---- d0: shu-chu qing-ling (zhe yi pai wu you-xiao shu-chu) ----
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







/*
module data96_128 (

    input wire [95:0] I_tdata,

    output wire [127:0] O_tdata

);

  assign O_tdata = {
    {8'd0}, I_tdata[95:72], {8'd0}, I_tdata[71:48], {8'd0}, I_tdata[47:24], {8'd0}, I_tdata[23:0]
  };
 
endmodule
*/

