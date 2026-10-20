//=============================================================================
// 文件      : osd_char_lib.v
// 模块      : osd_char_lib ( 3 个端口，纯组合，无 clk/rst )
// 功能      : OSD 点阵字符库（字模 ROM）。输入 8bit 字符编码 I_char 与 4bit 行号 I_row，输出该字符该行的 16bit 点阵行码 O_row_bits。共 41 个字符：大写 A~Z(8h41~8h5a)、数字 0~9(8h30~8h39)、冒号 COLON(8h3a)、[HDR-2026-10-15b] 新增连字符 MINUS(8h2d) 与小数点 DOT(8h2e)，以及两个自定义编码 CHAR_AN=8h80（安）、CHAR_LU=8h81（路）。字模为 16 列 x 16 行，字形实际只占左侧约 12 列、上方约 13 行，其余补 0。★注意：没有小写字母★（参数行里的 "x" 一律用大写 X=8h58 代替）。
// 数据通路  : 一行点阵 = 16bit：bit15 对应该行第 0 列（最左），bit14 第 1 列 …… bit0 第 15 列（最右），即“高位在左”。取字模是两层嵌套 case：外层 case(I_char) 选字符，内层 case(I_row) 用 I_row=4d0~4d15 选行码，越界行由 default 输出 16h0000。例：某行 16h1c00 表示 bit12~bit10 亮，即第 3~5 列。字符编码到字模的映射靠上面 40 个 localparam（CHAR_A=8h41 等）完成；hdmi_mixer.v 先算出 S_pf_char 再送入本模块。
// 时钟/复位 : 无时钟、无复位：I_char/I_row 直接组合选字模，纯查找表逻辑。
// 依赖      : 被 hdmi_mixer.v:641 例化为 u_osd_char_lib（.I_char/.I_row/.O_row_bits）；hdmi_mixer.v 里另有一份内容相同的 function F_osd_char16_row（第 535~632 行），但实际取模走的是本模块。
// 综合/实现 : 纯组合查找表，综合成 LUT/ROM，无时序约束问题；本文件在 E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display.al 的编译清单中。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
//---- kuai 1: duan-kou sheng-ming (I_char 8bit zi-fu ma / I_row 4bit hang-hao / O_row_bits 16bit hang-dian-zhen) ----
module osd_char_lib (
    input wire [7:0] I_char,
    input wire [3:0] I_row,
    output reg [15:0] O_row_bits
);

    //---- kuai 2: zi-fu bian-ma chang-liang (localparam, zhi = ASCII ma huo 8h80 / 8h81) ----
    localparam CHAR_AN    = 8'h80;
    localparam CHAR_LU    = 8'h81;
    localparam CHAR_A     = 8'h41;
    localparam CHAR_B     = 8'h42;
    localparam CHAR_C     = 8'h43;
    localparam CHAR_D     = 8'h44;
    localparam CHAR_E     = 8'h45;
    localparam CHAR_F     = 8'h46;
    localparam CHAR_G     = 8'h47;
    localparam CHAR_H     = 8'h48;
    localparam CHAR_I     = 8'h49;
    localparam CHAR_J     = 8'h4a;
    localparam CHAR_K     = 8'h4b;
    localparam CHAR_L     = 8'h4c;
    localparam CHAR_M     = 8'h4d;
    localparam CHAR_N     = 8'h4e;
    localparam CHAR_O     = 8'h4f;
    localparam CHAR_P     = 8'h50;
    localparam CHAR_Q     = 8'h51;
    localparam CHAR_R     = 8'h52;
    localparam CHAR_S     = 8'h53;
    localparam CHAR_T     = 8'h54;
    localparam CHAR_U     = 8'h55;
    localparam CHAR_V     = 8'h56;
    localparam CHAR_W     = 8'h57;
    localparam CHAR_X     = 8'h58;
    localparam CHAR_Y     = 8'h59;
    localparam CHAR_Z     = 8'h5a;
    localparam CHAR_0     = 8'h30;
    localparam CHAR_1     = 8'h31;
    localparam CHAR_2     = 8'h32;
    localparam CHAR_3     = 8'h33;
    localparam CHAR_4     = 8'h34;
    localparam CHAR_5     = 8'h35;
    localparam CHAR_6     = 8'h36;
    localparam CHAR_7     = 8'h37;
    localparam CHAR_8     = 8'h38;
    localparam CHAR_9     = 8'h39;
    localparam CHAR_COLON = 8'h3a;
    //---- [HDR-2026-10-15b] 新增两个标点字模：参数行 "S-ON BL-ON G31.5X" 需要 '-' 和 '.' ----
    localparam CHAR_MINUS = 8'h2d;
    localparam CHAR_DOT   = 8'h2e;

    //---- kuai 3: zi-mo cha-xun (case(I_char) -> case(I_row) -> 16bit hang-ma) ----
    always @(*) begin
        case(I_char)
            //---- AN  CHAR_AN = 8h80 (zi-ku zidingyi zi) ----
            CHAR_AN: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0200;
                    4'd1: O_row_bits = 16'h7ff0;
                    4'd2: O_row_bits = 16'h4410;
                    4'd3: O_row_bits = 16'h0400;
                    4'd4: O_row_bits = 16'h7ff0;
                    4'd5: O_row_bits = 16'h0840;
                    4'd6: O_row_bits = 16'h1040;
                    4'd7: O_row_bits = 16'h1c80;
                    4'd8: O_row_bits = 16'h0300;
                    4'd9: O_row_bits = 16'h0cc0;
                    4'd10: O_row_bits = 16'h7020;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- LU  CHAR_LU = 8h81 (zi-ku zidingyi zi) ----
            CHAR_LU: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h79e0;
                    4'd1: O_row_bits = 16'h4a20;
                    4'd2: O_row_bits = 16'h4d40;
                    4'd3: O_row_bits = 16'h7880;
                    4'd4: O_row_bits = 16'h1140;
                    4'd5: O_row_bits = 16'h1630;
                    4'd6: O_row_bits = 16'h5be0;
                    4'd7: O_row_bits = 16'h5220;
                    4'd8: O_row_bits = 16'h5220;
                    4'd9: O_row_bits = 16'h5be0;
                    4'd10: O_row_bits = 16'h6220;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'A' ----
            CHAR_A: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h1c00;
                    4'd3: O_row_bits = 16'h1400;
                    4'd4: O_row_bits = 16'h1400;
                    4'd5: O_row_bits = 16'h1400;
                    4'd6: O_row_bits = 16'h3600;
                    4'd7: O_row_bits = 16'h3e00;
                    4'd8: O_row_bits = 16'h2200;
                    4'd9: O_row_bits = 16'h2200;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'B' ----
            CHAR_B: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3e00;
                    4'd3: O_row_bits = 16'h3300;
                    4'd4: O_row_bits = 16'h3300;
                    4'd5: O_row_bits = 16'h3e00;
                    4'd6: O_row_bits = 16'h3300;
                    4'd7: O_row_bits = 16'h3300;
                    4'd8: O_row_bits = 16'h3300;
                    4'd9: O_row_bits = 16'h3e00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'C' ----
            CHAR_C: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h03f0;
                    4'd3: O_row_bits = 16'h0c0c;
                    4'd4: O_row_bits = 16'h1800;
                    4'd5: O_row_bits = 16'h3000;
                    4'd6: O_row_bits = 16'h3000;
                    4'd7: O_row_bits = 16'h3000;
                    4'd8: O_row_bits = 16'h3000;
                    4'd9: O_row_bits = 16'h3000;
                    4'd10: O_row_bits = 16'h1800;
                    4'd11: O_row_bits = 16'h0c0c;
                    4'd12: O_row_bits = 16'h03f0;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'D' ----
            CHAR_D: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3e00;
                    4'd3: O_row_bits = 16'h3300;
                    4'd4: O_row_bits = 16'h3300;
                    4'd5: O_row_bits = 16'h3300;
                    4'd6: O_row_bits = 16'h3300;
                    4'd7: O_row_bits = 16'h3300;
                    4'd8: O_row_bits = 16'h3600;
                    4'd9: O_row_bits = 16'h3c00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'E' ----
            CHAR_E: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3e00;
                    4'd3: O_row_bits = 16'h3000;
                    4'd4: O_row_bits = 16'h3000;
                    4'd5: O_row_bits = 16'h3e00;
                    4'd6: O_row_bits = 16'h3000;
                    4'd7: O_row_bits = 16'h3000;
                    4'd8: O_row_bits = 16'h3000;
                    4'd9: O_row_bits = 16'h3e00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'F' ----
            CHAR_F: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3e00;
                    4'd3: O_row_bits = 16'h3000;
                    4'd4: O_row_bits = 16'h3000;
                    4'd5: O_row_bits = 16'h3000;
                    4'd6: O_row_bits = 16'h3e00;
                    4'd7: O_row_bits = 16'h3000;
                    4'd8: O_row_bits = 16'h3000;
                    4'd9: O_row_bits = 16'h3000;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'G' ----
            CHAR_G: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h1c00;
                    4'd3: O_row_bits = 16'h3200;
                    4'd4: O_row_bits = 16'h6000;
                    4'd5: O_row_bits = 16'h6000;
                    4'd6: O_row_bits = 16'h6e00;
                    4'd7: O_row_bits = 16'h6600;
                    4'd8: O_row_bits = 16'h3600;
                    4'd9: O_row_bits = 16'h1e00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'H' ----
            CHAR_H: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3300;
                    4'd3: O_row_bits = 16'h3300;
                    4'd4: O_row_bits = 16'h3300;
                    4'd5: O_row_bits = 16'h3f00;
                    4'd6: O_row_bits = 16'h3300;
                    4'd7: O_row_bits = 16'h3300;
                    4'd8: O_row_bits = 16'h3300;
                    4'd9: O_row_bits = 16'h3300;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'I' ----
            CHAR_I: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h1e00;
                    4'd3: O_row_bits = 16'h0c00;
                    4'd4: O_row_bits = 16'h0c00;
                    4'd5: O_row_bits = 16'h0c00;
                    4'd6: O_row_bits = 16'h0c00;
                    4'd7: O_row_bits = 16'h0c00;
                    4'd8: O_row_bits = 16'h0c00;
                    4'd9: O_row_bits = 16'h1e00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'J' ----
            CHAR_J: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3e00;
                    4'd3: O_row_bits = 16'h0600;
                    4'd4: O_row_bits = 16'h0600;
                    4'd5: O_row_bits = 16'h0600;
                    4'd6: O_row_bits = 16'h0600;
                    4'd7: O_row_bits = 16'h0600;
                    4'd8: O_row_bits = 16'h2600;
                    4'd9: O_row_bits = 16'h1c00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'K' ----
            CHAR_K: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3300;
                    4'd3: O_row_bits = 16'h3600;
                    4'd4: O_row_bits = 16'h3400;
                    4'd5: O_row_bits = 16'h3c00;
                    4'd6: O_row_bits = 16'h3c00;
                    4'd7: O_row_bits = 16'h3400;
                    4'd8: O_row_bits = 16'h3600;
                    4'd9: O_row_bits = 16'h3300;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'L' ----
            CHAR_L: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3000;
                    4'd3: O_row_bits = 16'h3000;
                    4'd4: O_row_bits = 16'h3000;
                    4'd5: O_row_bits = 16'h3000;
                    4'd6: O_row_bits = 16'h3000;
                    4'd7: O_row_bits = 16'h3000;
                    4'd8: O_row_bits = 16'h3000;
                    4'd9: O_row_bits = 16'h3e00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'M' ----
            CHAR_M: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3600;
                    4'd3: O_row_bits = 16'h3600;
                    4'd4: O_row_bits = 16'h3600;
                    4'd5: O_row_bits = 16'h3600;
                    4'd6: O_row_bits = 16'h2a00;
                    4'd7: O_row_bits = 16'h2a00;
                    4'd8: O_row_bits = 16'h2200;
                    4'd9: O_row_bits = 16'h2200;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'N' ----
            CHAR_N: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h300c;
                    4'd3: O_row_bits = 16'h380c;
                    4'd4: O_row_bits = 16'h3c0c;
                    4'd5: O_row_bits = 16'h360c;
                    4'd6: O_row_bits = 16'h330c;
                    4'd7: O_row_bits = 16'h318c;
                    4'd8: O_row_bits = 16'h30cc;
                    4'd9: O_row_bits = 16'h306c;
                    4'd10: O_row_bits = 16'h303c;
                    4'd11: O_row_bits = 16'h301c;
                    4'd12: O_row_bits = 16'h300c;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'O' ----
            CHAR_O: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h1e00;
                    4'd3: O_row_bits = 16'h3200;
                    4'd4: O_row_bits = 16'h6300;
                    4'd5: O_row_bits = 16'h6300;
                    4'd6: O_row_bits = 16'h6300;
                    4'd7: O_row_bits = 16'h6300;
                    4'd8: O_row_bits = 16'h3600;
                    4'd9: O_row_bits = 16'h3c00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'P' ----
            CHAR_P: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3e00;
                    4'd3: O_row_bits = 16'h3300;
                    4'd4: O_row_bits = 16'h3300;
                    4'd5: O_row_bits = 16'h3300;
                    4'd6: O_row_bits = 16'h3e00;
                    4'd7: O_row_bits = 16'h3000;
                    4'd8: O_row_bits = 16'h3000;
                    4'd9: O_row_bits = 16'h3000;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'Q' ----
            CHAR_Q: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h1e00;
                    4'd3: O_row_bits = 16'h3200;
                    4'd4: O_row_bits = 16'h6300;
                    4'd5: O_row_bits = 16'h6300;
                    4'd6: O_row_bits = 16'h6300;
                    4'd7: O_row_bits = 16'h6300;
                    4'd8: O_row_bits = 16'h7600;
                    4'd9: O_row_bits = 16'h3c00;
                    4'd10: O_row_bits = 16'h0c00;
                    4'd11: O_row_bits = 16'h0700;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'R' ----
            CHAR_R: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3e00;
                    4'd3: O_row_bits = 16'h3300;
                    4'd4: O_row_bits = 16'h3300;
                    4'd5: O_row_bits = 16'h3300;
                    4'd6: O_row_bits = 16'h3c00;
                    4'd7: O_row_bits = 16'h3600;
                    4'd8: O_row_bits = 16'h3600;
                    4'd9: O_row_bits = 16'h3200;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'S' ----
            CHAR_S: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h1e00;
                    4'd3: O_row_bits = 16'h3000;
                    4'd4: O_row_bits = 16'h3000;
                    4'd5: O_row_bits = 16'h3c00;
                    4'd6: O_row_bits = 16'h0f00;
                    4'd7: O_row_bits = 16'h0300;
                    4'd8: O_row_bits = 16'h0300;
                    4'd9: O_row_bits = 16'h3e00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'T' ----
            CHAR_T: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3ffc;
                    4'd3: O_row_bits = 16'h03c0;
                    4'd4: O_row_bits = 16'h03c0;
                    4'd5: O_row_bits = 16'h03c0;
                    4'd6: O_row_bits = 16'h03c0;
                    4'd7: O_row_bits = 16'h03c0;
                    4'd8: O_row_bits = 16'h03c0;
                    4'd9: O_row_bits = 16'h03c0;
                    4'd10: O_row_bits = 16'h03c0;
                    4'd11: O_row_bits = 16'h03c0;
                    4'd12: O_row_bits = 16'h03c0;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'U' ----
            CHAR_U: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3300;
                    4'd3: O_row_bits = 16'h3300;
                    4'd4: O_row_bits = 16'h3300;
                    4'd5: O_row_bits = 16'h3300;
                    4'd6: O_row_bits = 16'h3300;
                    4'd7: O_row_bits = 16'h3300;
                    4'd8: O_row_bits = 16'h3300;
                    4'd9: O_row_bits = 16'h1e00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'V' ----
            CHAR_V: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h2200;
                    4'd3: O_row_bits = 16'h2200;
                    4'd4: O_row_bits = 16'h3600;
                    4'd5: O_row_bits = 16'h3600;
                    4'd6: O_row_bits = 16'h1400;
                    4'd7: O_row_bits = 16'h1400;
                    4'd8: O_row_bits = 16'h1c00;
                    4'd9: O_row_bits = 16'h1c00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'W' ----
            CHAR_W: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h2200;
                    4'd3: O_row_bits = 16'h2200;
                    4'd4: O_row_bits = 16'h2a00;
                    4'd5: O_row_bits = 16'h2a00;
                    4'd6: O_row_bits = 16'h3600;
                    4'd7: O_row_bits = 16'h3600;
                    4'd8: O_row_bits = 16'h3600;
                    4'd9: O_row_bits = 16'h3600;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'X' ----
            CHAR_X: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3e00;
                    4'd3: O_row_bits = 16'h1c00;
                    4'd4: O_row_bits = 16'h1c00;
                    4'd5: O_row_bits = 16'h0800;
                    4'd6: O_row_bits = 16'h1c00;
                    4'd7: O_row_bits = 16'h1400;
                    4'd8: O_row_bits = 16'h3600;
                    4'd9: O_row_bits = 16'h3200;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'Y' ----
            CHAR_Y: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3180;
                    4'd3: O_row_bits = 16'h1300;
                    4'd4: O_row_bits = 16'h1b00;
                    4'd5: O_row_bits = 16'h1e00;
                    4'd6: O_row_bits = 16'h0c00;
                    4'd7: O_row_bits = 16'h0c00;
                    4'd8: O_row_bits = 16'h0c00;
                    4'd9: O_row_bits = 16'h0c00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- 'Z' ----
            CHAR_Z: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h3e00;
                    4'd3: O_row_bits = 16'h0400;
                    4'd4: O_row_bits = 16'h0c00;
                    4'd5: O_row_bits = 16'h0800;
                    4'd6: O_row_bits = 16'h0800;
                    4'd7: O_row_bits = 16'h1800;
                    4'd8: O_row_bits = 16'h1000;
                    4'd9: O_row_bits = 16'h3e00;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '0'  8h30 ----
            CHAR_0: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h1ff8;
                    4'd2: O_row_bits = 16'h1ff8;
                    4'd3: O_row_bits = 16'h300c;
                    4'd4: O_row_bits = 16'h300c;
                    4'd5: O_row_bits = 16'h300c;
                    4'd6: O_row_bits = 16'h0000;
                    4'd7: O_row_bits = 16'h0000;
                    4'd8: O_row_bits = 16'h300c;
                    4'd9: O_row_bits = 16'h300c;
                    4'd10: O_row_bits = 16'h300c;
                    4'd11: O_row_bits = 16'h1ff8;
                    4'd12: O_row_bits = 16'h1ff8;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '1' ----
            CHAR_1: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h000c;
                    4'd2: O_row_bits = 16'h000c;
                    4'd3: O_row_bits = 16'h000c;
                    4'd4: O_row_bits = 16'h000c;
                    4'd5: O_row_bits = 16'h000c;
                    4'd6: O_row_bits = 16'h0000;
                    4'd7: O_row_bits = 16'h0000;
                    4'd8: O_row_bits = 16'h000c;
                    4'd9: O_row_bits = 16'h000c;
                    4'd10: O_row_bits = 16'h000c;
                    4'd11: O_row_bits = 16'h000c;
                    4'd12: O_row_bits = 16'h000c;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '2' ----
            CHAR_2: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h1ff8;
                    4'd2: O_row_bits = 16'h1ff8;
                    4'd3: O_row_bits = 16'h000c;
                    4'd4: O_row_bits = 16'h000c;
                    4'd5: O_row_bits = 16'h000c;
                    4'd6: O_row_bits = 16'h1ff8;
                    4'd7: O_row_bits = 16'h1ff8;
                    4'd8: O_row_bits = 16'h3000;
                    4'd9: O_row_bits = 16'h3000;
                    4'd10: O_row_bits = 16'h3000;
                    4'd11: O_row_bits = 16'h1ff8;
                    4'd12: O_row_bits = 16'h1ff8;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '3' ----
            CHAR_3: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h1ff8;
                    4'd2: O_row_bits = 16'h1ff8;
                    4'd3: O_row_bits = 16'h000c;
                    4'd4: O_row_bits = 16'h000c;
                    4'd5: O_row_bits = 16'h000c;
                    4'd6: O_row_bits = 16'h1ff8;
                    4'd7: O_row_bits = 16'h1ff8;
                    4'd8: O_row_bits = 16'h000c;
                    4'd9: O_row_bits = 16'h000c;
                    4'd10: O_row_bits = 16'h000c;
                    4'd11: O_row_bits = 16'h1ff8;
                    4'd12: O_row_bits = 16'h1ff8;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '4' ----
            CHAR_4: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h300c;
                    4'd2: O_row_bits = 16'h300c;
                    4'd3: O_row_bits = 16'h300c;
                    4'd4: O_row_bits = 16'h300c;
                    4'd5: O_row_bits = 16'h300c;
                    4'd6: O_row_bits = 16'h1ff8;
                    4'd7: O_row_bits = 16'h1ff8;
                    4'd8: O_row_bits = 16'h000c;
                    4'd9: O_row_bits = 16'h000c;
                    4'd10: O_row_bits = 16'h000c;
                    4'd11: O_row_bits = 16'h000c;
                    4'd12: O_row_bits = 16'h000c;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '5' ----
            CHAR_5: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h1ff8;
                    4'd2: O_row_bits = 16'h1ff8;
                    4'd3: O_row_bits = 16'h3000;
                    4'd4: O_row_bits = 16'h3000;
                    4'd5: O_row_bits = 16'h3000;
                    4'd6: O_row_bits = 16'h1ff8;
                    4'd7: O_row_bits = 16'h1ff8;
                    4'd8: O_row_bits = 16'h000c;
                    4'd9: O_row_bits = 16'h000c;
                    4'd10: O_row_bits = 16'h000c;
                    4'd11: O_row_bits = 16'h1ff8;
                    4'd12: O_row_bits = 16'h1ff8;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '6' ----
            CHAR_6: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h1ff8;
                    4'd2: O_row_bits = 16'h1ff8;
                    4'd3: O_row_bits = 16'h3000;
                    4'd4: O_row_bits = 16'h3000;
                    4'd5: O_row_bits = 16'h3000;
                    4'd6: O_row_bits = 16'h1ff8;
                    4'd7: O_row_bits = 16'h1ff8;
                    4'd8: O_row_bits = 16'h300c;
                    4'd9: O_row_bits = 16'h300c;
                    4'd10: O_row_bits = 16'h300c;
                    4'd11: O_row_bits = 16'h1ff8;
                    4'd12: O_row_bits = 16'h1ff8;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '7' ----
            CHAR_7: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h1ff8;
                    4'd2: O_row_bits = 16'h1ff8;
                    4'd3: O_row_bits = 16'h000c;
                    4'd4: O_row_bits = 16'h000c;
                    4'd5: O_row_bits = 16'h000c;
                    4'd6: O_row_bits = 16'h0000;
                    4'd7: O_row_bits = 16'h0000;
                    4'd8: O_row_bits = 16'h000c;
                    4'd9: O_row_bits = 16'h000c;
                    4'd10: O_row_bits = 16'h000c;
                    4'd11: O_row_bits = 16'h000c;
                    4'd12: O_row_bits = 16'h000c;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '8' ----
            CHAR_8: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h1ff8;
                    4'd2: O_row_bits = 16'h1ff8;
                    4'd3: O_row_bits = 16'h300c;
                    4'd4: O_row_bits = 16'h300c;
                    4'd5: O_row_bits = 16'h300c;
                    4'd6: O_row_bits = 16'h1ff8;
                    4'd7: O_row_bits = 16'h1ff8;
                    4'd8: O_row_bits = 16'h300c;
                    4'd9: O_row_bits = 16'h300c;
                    4'd10: O_row_bits = 16'h300c;
                    4'd11: O_row_bits = 16'h1ff8;
                    4'd12: O_row_bits = 16'h1ff8;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- '9' ----
            CHAR_9: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h1ff8;
                    4'd2: O_row_bits = 16'h1ff8;
                    4'd3: O_row_bits = 16'h300c;
                    4'd4: O_row_bits = 16'h300c;
                    4'd5: O_row_bits = 16'h300c;
                    4'd6: O_row_bits = 16'h1ff8;
                    4'd7: O_row_bits = 16'h1ff8;
                    4'd8: O_row_bits = 16'h000c;
                    4'd9: O_row_bits = 16'h000c;
                    4'd10: O_row_bits = 16'h000c;
                    4'd11: O_row_bits = 16'h1ff8;
                    4'd12: O_row_bits = 16'h1ff8;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- COLON 8h3a (mao-hao) ----
            CHAR_COLON: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h0000;
                    4'd3: O_row_bits = 16'h0000;
                    4'd4: O_row_bits = 16'h0000;
                    4'd5: O_row_bits = 16'h0000;
                    4'd6: O_row_bits = 16'h0180;
                    4'd7: O_row_bits = 16'h0180;
                    4'd8: O_row_bits = 16'h0000;
                    4'd9: O_row_bits = 16'h0000;
                    4'd10: O_row_bits = 16'h0180;
                    4'd11: O_row_bits = 16'h0180;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- [HDR-2026-10-15b] MINUS 8h2d (lian-zi-hao) ----
            //   放在第 6/7 行（数字 '0' 的中腰，见 CHAR_0 第 6/7 行为 0000），
            //   横杠占第 5~10 列共 6 列、粗细 2 行 —— 与冒号点的 2x2 粗细一致。
            CHAR_MINUS: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h0000;
                    4'd3: O_row_bits = 16'h0000;
                    4'd4: O_row_bits = 16'h0000;
                    4'd5: O_row_bits = 16'h0000;
                    4'd6: O_row_bits = 16'h07e0;
                    4'd7: O_row_bits = 16'h07e0;
                    4'd8: O_row_bits = 16'h0000;
                    4'd9: O_row_bits = 16'h0000;
                    4'd10: O_row_bits = 16'h0000;
                    4'd11: O_row_bits = 16'h0000;
                    4'd12: O_row_bits = 16'h0000;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            //---- [HDR-2026-10-15b] DOT 8h2e (xiao-shu-dian) ----
            //   坐在基线上：数字 '0' 占第 1~12 行，故小数点放第 10~12 行，
            //   占第 7~9 列共 3 列 3 行，视觉上是个方块点。
            CHAR_DOT: begin
                case(I_row)
                    4'd0: O_row_bits = 16'h0000;
                    4'd1: O_row_bits = 16'h0000;
                    4'd2: O_row_bits = 16'h0000;
                    4'd3: O_row_bits = 16'h0000;
                    4'd4: O_row_bits = 16'h0000;
                    4'd5: O_row_bits = 16'h0000;
                    4'd6: O_row_bits = 16'h0000;
                    4'd7: O_row_bits = 16'h0000;
                    4'd8: O_row_bits = 16'h0000;
                    4'd9: O_row_bits = 16'h0000;
                    4'd10: O_row_bits = 16'h01c0;
                    4'd11: O_row_bits = 16'h01c0;
                    4'd12: O_row_bits = 16'h01c0;
                    4'd13: O_row_bits = 16'h0000;
                    4'd14: O_row_bits = 16'h0000;
                    4'd15: O_row_bits = 16'h0000;
                    default: O_row_bits = 16'h0000;
                endcase
            end
            default: O_row_bits = 16'h0000;
        //---- kuai 4: cha-xun jie-shu (endcase) / qi-ta zi-fu fan-hui 16h0000 ----
        endcase
    end

endmodule

