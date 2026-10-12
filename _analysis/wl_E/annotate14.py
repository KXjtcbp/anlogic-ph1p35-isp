# -*- coding: utf-8 -*-
"""为 14 个目标 Verilog 文件插入文件头与段落注释。
只插入整行注释；原有行按文件自身编码逐字节原样保留。
读用 rb，写用 wb。"""
import os, sys, shutil

BASE = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
BK   = r'E:\FPGA\_backup\20261009_comments\legacy'
APOS = chr(39)

def q(s):
    """把内容里的 verilog 单引号写法写成不带反斜杠的形式"""
    return s

RUN_CHARS = u'\\u4e00'  # placeholder, unused

files = {}

def F(path, enc='utf-8', nl='\r\n'):
    d = files.setdefault(path, {'enc': enc, 'nl': nl, 'ins': []})
    d['enc'] = enc; d['nl'] = nl
    return d

def sec(path, line, title, indent=8, enc='utf-8', nl='\r\n'):
    d = F(path, enc, nl)
    d['ins'].append((line, (u' ' * indent) + u'//---- ' + title + u' ----'))

def raw(path, line, text, enc='utf-8', nl='\r\n'):
    d = F(path, enc, nl)
    for i, t in enumerate(text.split(u'\n')):
        d['ins'].append((line + i, t))

HDR = u"""//=============================================================================
// 文件      : {path}
// 模块      : {mod}
// 功能      : {func}
// 数据通路  : {dp}
// 时钟/复位 : {clk}
// 依赖      : {dep}
// 综合/实现 : {impl}
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\\FPGA\\_analysis\\rename_report.txt
//============================================================================="""

def header(path, mod, func, dp, clk, dep, impl, enc='utf-8', nl='\r\n'):
    d = F(path, enc, nl)
    txt = HDR.format(path=path.replace(u'\\', u'/'), mod=mod, func=func, dp=dp, clk=clk, dep=dep, impl=impl)
    for i, t in enumerate(txt.split(u'\n')):
        d['ins'].append((0, t))   # 0 号哨兵：永远排在文件最顶端

# ============================================================ 1 osd_char_lib.v
P = u'osd_char_lib.v'
header(P,
 mod=u'osd_char_lib ( 3 个端口，纯组合，无 clk/rst )',
 func=u'OSD 点阵字符库（字模 ROM）。输入 8bit 字符编码 I_char 与 4bit 行号 I_row，输出该字符该行的 16bit 点阵行码 O_row_bits。共 39 个字符：大写 A~Z(8h41~8h5a)、数字 0~9(8h30~8h39)、冒号 COLON(8h3a)，以及两个自定义编码 CHAR_AN=8h80（安）、CHAR_LU=8h81（路）。字模为 16 列 x 16 行，字形实际只占左侧约 12 列、上方约 13 行，其余补 0。',
 dp=u'一行点阵 = 16bit：bit15 对应该行第 0 列（最左），bit14 第 1 列 …… bit0 第 15 列（最右），即“高位在左”。取字模是两层嵌套 case：外层 case(I_char) 选字符，内层 case(I_row) 用 I_row=4d0~4d15 选行码，越界行由 default 输出 16h0000。例：某行 16h1c00 表示 bit12~bit10 亮，即第 3~5 列。字符编码到字模的映射靠上面 40 个 localparam（CHAR_A=8h41 等）完成；hdmi_mixer.v 先算出 S_pf_char 再送入本模块。',
 clk=u'无时钟、无复位：I_char/I_row 直接组合选字模，纯查找表逻辑。',
 dep=u'被 hdmi_mixer.v:641 例化为 u_osd_char_lib（.I_char/.I_row/.O_row_bits）；hdmi_mixer.v 里另有一份内容相同的 function F_osd_char16_row（第 535~632 行），但实际取模走的是本模块。',
 impl=u'纯组合查找表，综合成 LUT/ROM，无时序约束问题；本文件在 E:\\FPGA\\proj\\baseline\\lab3\\td_project\\camera_to_dsi_display.al 的编译清单中。')
sec(P, 1, u'kuai 1: duan-kou sheng-ming (I_char 8bit zi-fu ma / I_row 4bit hang-hao / O_row_bits 16bit hang-dian-zhen)', 0)
sec(P, 7, u'kuai 2: zi-fu bian-ma chang-liang (localparam, zhi = ASCII ma huo 8h80 / 8h81)', 4)
sec(P, 47, u'kuai 3: zi-mo cha-xun (case(I_char) -> case(I_row) -> 16bit hang-ma)', 4)
OSD = [
 (49, u"AN  CHAR_AN = 8h80 (zi-ku zidingyi zi)"),
 (70, u"LU  CHAR_LU = 8h81 (zi-ku zidingyi zi)"),
 (91, u"'A'"), (112, u"'B'"), (133, u"'C'"), (154, u"'D'"), (175, u"'E'"),
 (196, u"'F'"), (217, u"'G'"), (238, u"'H'"), (259, u"'I'"), (280, u"'J'"),
 (301, u"'K'"), (322, u"'L'"), (343, u"'M'"), (364, u"'N'"), (385, u"'O'"),
 (406, u"'P'"), (427, u"'Q'"), (448, u"'R'"), (469, u"'S'"), (490, u"'T'"),
 (511, u"'U'"), (532, u"'V'"), (553, u"'W'"), (574, u"'X'"), (595, u"'Y'"),
 (616, u"'Z'"),
 (637, u"'0'  8h30"), (658, u"'1'"), (679, u"'2'"), (700, u"'3'"), (721, u"'4'"),
 (742, u"'5'"), (763, u"'6'"), (784, u"'7'"), (805, u"'8'"), (826, u"'9'"),
 (847, u"COLON 8h3a (mao-hao)"),
]
for ln, name in OSD:
    sec(P, ln, name, 12)
sec(P, 869, u'kuai 4: cha-xun jie-shu (endcase) / qi-ta zi-fu fan-hui 16h0000', 8)

# ============================================================ 2 isp/data96_128/data96_128.v
P = u'isp\\data96_128\\data96_128.v'
header(P,
 mod=u'data_96bit_to_128bit（注意：模块名与文件名 data96_128.v 不一致，文件名是目录名风格）',
 func=u'位宽重切：把连续的 96bit 数据（=4 像素 x 24bit）按“先到的字放高位”的规则拼成连续位流，再每 128bit 切一片输出，供后级 128bit 位宽的数据通路使用。',
 dp=u'输入 I_96b_data[95:0]，输出 O_128b_data[127:0]。核心是 S_phase_cnt（原 S_cnt，2026-10-09 改名）：I_96b_valid 有效时每拍 +1，无效时清 0；case(S_phase_cnt) 的 4 个分支：d0 输出清零，d1 = {S_96b_data_1d, I_96b_data[95:64]}，d2 = {S_96b_data_1d[63:0], I_96b_data[95:32]}，d3 = {S_96b_data_1d[31:0], I_96b_data}（S_96b_data_1d 是上一拍输入的 96bit，用于跨拍拼接）。因此每 4 拍输入只出 3 拍有效数据。24bit 像素边界与 128bit 字边界天然不对齐（128 mod 24 = 8），所以只能用这种跨拍拼接。O_128b_frame_start 只打一拍寄存。',
 clk=u'I_clk 上升沿同步；I_rst_n 异步复位、低电平有效，但复位在本模块内未参与任何 always，只作端口保留。',
 dep=u'被 isp/isp_top.v:171 例化为 u_data_96bit_to_128bit。本文件末尾第 87~101 行是被 /* */ 注释掉的旧版 module data96_128（用 8d0 补齐的另一种写法），仅作历史保留。',
 impl=u'本文件在 camera_to_dsi_display.al 的编译清单中；根目录下同名 module 的 data_96bit_to_128bit.v 未被 .al 引用。')
sec(P, 3, u'kuai 1: duan-kou sheng-ming (96bit shu-ru -> 128bit shu-chu)', 0)
sec(P, 18, u'kuai 2: nei-bu ji-cun qi (S_96b_data_1d = shang yi pai shu-ru; S_phase_cnt = wei-tiao xiang-wei)', 4)
sec(P, 23, u'kuai 3: shu-ru da-pai + frame_start ji-cun', 4)
sec(P, 31, u'kuai 4: xiang-wei ji-shu (I_96b_valid you-xiao shi +1, fou-ze qing 0)', 4)
sec(P, 39, u'kuai 5: 96bit -> 128bit kua-pai pin-jie (mei 4 pai shu-ru zhi chu 3 pai you-xiao)', 4)
sec(P, 43, u"d0: shu-chu qing-ling (zhe yi pai wu you-xiao shu-chu)", 20)
sec(P, 48, u"d1: {shang yi pai 96bit, ben pai I_96b_data[95:64]} -> 128bit", 20)
sec(P, 53, u"d2: {shang yi pai [63:0], ben pai I_96b_data[95:32]} -> 128bit", 20)
sec(P, 58, u"d3: {shang yi pai [31:0], ben pai I_96b_data[95:0] } -> 128bit", 20)
sec(P, 63, u"default: qing-ling", 20)
sec(P, 70, u"else (I_96b_valid = 0): shu-chu qing-ling", 8)

# ============================================================ 3 isp/data128_96/data128_96.v
P = u'isp\\data128_96\\data128_96.v'
header(P,
 mod=u'data128_96',
 func=u'位宽重切：把 128bit 截成 96bit —— 按 32bit 一组分成 4 组，丢掉每组高 8bit，保留每组的低 24bit（一个像素）后按原顺序拼起来。',
 dp=u'输入 I_tdata[127:0]，输出 O_tdata[95:0]；O_tdata = {I_tdata[23:0], I_tdata[55:32], I_tdata[87:64], I_tdata[119:96]}，即组 0(bit23:0)->O[95:72]、组 1(bit55:32)->O[71:48]、组 2(bit87:64)->O[47:24]、组 3(bit119:96)->O[23:0]。96bit = 4 像素 x 24bit，[23:16]=R、[15:8]=G、[7:0]=B。每 128bit 的 4 个高 8bit 被丢弃，所以是单向、不可逆的缩位。',
 clk=u'无时钟、无复位：纯组合 assign。',
 dep=u'被 isp/isp_top.v:121 例化为 u_data128_96。第 17 行是注释掉的另一种写法（把 I_tdata 重复使用的那种），仅作历史保留。',
 impl=u'本文件在 camera_to_dsi_display.al 的编译清单中，纯组合、无资源问题。')
sec(P, 10, u'kuai 1: duan-kou sheng-ming (128bit shu-ru -> 96bit shu-chu)', 0)
sec(P, 16, u'kuai 2: shai-jian pin-jie (diu diao mei 32bit de gao 8bit, liu xia 4 x 24bit)', 2)

# ============================================================ 4 data_96bit_to_128bit.v (root copy)
P = u'data_96bit_to_128bit.v'
header(P,
 mod=u'data_96bit_to_128bit',
 func=u'位宽重切 96bit->128bit。★疑似历史遗留副本：本文件与 isp\\data96_128\\data96_128.v 的模块名、端口、三段 always、case 分支逐字同构（只少末尾那段 /* */ 旧代码）。本工程 .al 编译的是 isp/data96_128/data96_128.v，本文件未被引用。',
 dp=u'输入 I_96b_data[95:0]，输出 O_128b_data[127:0]；S_phase_cnt 在输入有效时每拍 +1，case 的 d1 = {S_96b_data_1d, I_96b_data[95:64]}、d2 = {S_96b_data_1d[63:0], I_96b_data[95:32]}、d3 = {S_96b_data_1d[31:0], I_96b_data}；每 4 拍输入只出 3 拍有效（d0 那拍清 0）。24bit 像素边界与 128bit 字边界不对齐（128 mod 24 = 8）。',
 clk=u'I_clk 上升沿同步；I_rst_n 为端口保留，代码内未使用（与 isp 目录下同名模块一致）。',
 dep=u'无任何模块例化它（全树 grep 只命中 module 定义本身）；不依赖其它自研模块。',
 impl=u'★未被 camera_to_dsi_display.al 引用、未参与本工程综合实现；本工程对应功能由 isp/data96_128/data96_128.v 承担。保留原因未能从代码确认。')
sec(P, 3, u'kuai 1: duan-kou sheng-ming (96bit shu-ru -> 128bit shu-chu)', 0)
sec(P, 18, u'kuai 2: nei-bu ji-cun qi (yu isp/data96_128/data96_128.v wan-quan yi-zhi)', 4)
sec(P, 23, u'kuai 3: shu-ru da-pai + frame_start ji-cun', 4)
sec(P, 31, u'kuai 4: xiang-wei ji-shu (I_96b_valid you-xiao shi +1, fou-ze qing 0)', 4)
sec(P, 39, u'kuai 5: 96bit -> 128bit kua-pai pin-jie (mei 4 pai shu-ru zhi chu 3 pai you-xiao)', 4)
sec(P, 43, u"d0: shu-chu qing-ling", 20)
sec(P, 48, u"d1: {shang yi pai 96bit, ben pai I_96b_data[95:64]} -> 128bit", 20)
sec(P, 53, u"d2: {shang yi pai [63:0], ben pai I_96b_data[95:32]} -> 128bit", 20)
sec(P, 58, u"d3: {shang yi pai [31:0], ben pai I_96b_data[95:0] } -> 128bit", 20)
sec(P, 63, u"default: qing-ling", 20)
sec(P, 70, u"else (I_96b_valid = 0): shu-chu qing-ling", 8)

# ============================================================ 5 raw10_unpacket.v (root copy)
P = u'raw10_unpacket.v'
header(P,
 mod=u'raw10_unpacket',
 func=u'RAW10 拆包：把 32bit 的 CSI 数据流里的 8bit 主数据与 2bit LSB 重新拼成 10bit 像素。★疑似历史遗留副本：全树没有任何模块例化它，也未列入 .al 编译清单；本工程 RAW10 拆包实际由 isp/raw10_unpacket_2lane.v 承担（未逐一比对两者差异，未能确认）。本文件后半段还留着大段被 // 注释掉的旧实现。',
 dp=u'输入 I_csi_data[31:0]（2lane 拼成的 32bit）与 I_camera_black_level[9:0]；输出 O_raw10_data[39:0]（=4 像素 x 10bit，字段 [9:0]/[19:10]/[29:20]/[39:30]）。现役逻辑：先把 frame_start/frame_end/valid/data 打两拍同步；S_phase_cnt 的推进条件是 {S_csi_valid_2d,S_csi_valid_1d,I_csi_valid} == 3b101（即 valid 按 1/0/1 的节奏出现，说明 MIPI 输入不连续），在 0->4 之间循环；case(S_phase_cnt) 的 d0~d3 每拍把 4 个 32bit 字里的 8bit 主数据与 2bit LSB 拼成 4 个 10bit 像素（d0->P0~P3、d1->P4~P7、d2->P8~P11、d3->P12~P15），d4 清 0 并置 wr_en=0；最后 O_raw10_data <= {S_raw10_wr_data[9:0],[19:10],[29:20],[39:30]}（相对 P0~P15 做了一次字序翻转），O_raw10_valid <= S_raw10_wr_en。',
 clk=u'I_clk 上升沿同步；I_rst_n 只作端口保留，现役逻辑中未见使用。',
 dep=u'无模块例化它；现役代码只用自身寄存器，不依赖 IP。第 112~259 行的旧实现里例化过 w40_d512_fifo（FIFO 已随旧代码一起被注释掉，本工程 .al 中也没有该 IP），旧实现还包含黑电平 (x - I_camera_black_level) >> 2 的处理。',
 impl=u'★未被 camera_to_dsi_display.al 引用、未参与综合实现。文件内已有的 // 旧注释按要求原样保留，未做改动。')
sec(P, 1, u'kuai 1: duan-kou sheng-ming (32bit CSI shu-ru -> 40bit RAW10 shu-chu)', 0)
sec(P, 21, u'kuai 2: nei-bu ji-cun qi / xian-wang (S_phase_cnt, S_raw10_wr_data deng)', 2)
sec(P, 35, u'kuai 3: shu-ru da-pai tong-bu (valid/data da liang pai, yu MIPI bu-lian-xu jie-zou dui-qi)', 2)
sec(P, 47, u'kuai 4: xiang-wei ji-shu (tiao-jian = {2d,1d,0d} == 3b101)', 2)
sec(P, 52, u'  (0->4 xun-huan; 3b000 shi qing 0)', 4)
sec(P, 56, u'kuai 5: RAW10 chai-bao he-xin (mei pai ba 4 ge 32bit zi chai cheng 4 ge 10bit xiang-su)', 2)
sec(P, 58, u'case (S_phase_cnt)', 8)
sec(P, 59, u'd0 -> P0~P3', 8)
sec(P, 66, u'd1 -> P4~P7', 8)
sec(P, 73, u'd2 -> P8~P11', 8)
sec(P, 80, u'd3 -> P12~P15', 8)
sec(P, 87, u'd4 -> qing-ling bing wr_en = 0', 8)
sec(P, 95, u'else (shu-ru wu-xiao): shu-chu qing-ling', 4)
sec(P, 104, u'kuai 6: shu-chu pin-jie + xie shi-neng (40bit = 4 x 10bit, zi-xu fan-zhuan: [9:0] zai zui gao)', 2)
sec(P, 111, u'yi-xia wei bei // zhu-shi diao de jiu shi-xian (bao-liu yuan-yang, ben ci wei dong)', 0)

# ============================================================ 6 csi_unpacket.v
P = u'csi_unpacket.v'
header(P,
 mod=u'csi_unpacket',
 func=u'MIPI CSI-2 包头解析 + 2lane 数据拼接：识别帧起始/帧结束短包，按长包长度计数使能，把 2lane 的 16bit 数据拼成 32bit 输出。★全树无例化、不在 .al 编译清单中；本工程实际使用的是 isp/csi_unpacket_2lane.v。',
 dp=u'输入 I_hs_valid/I_hs_data[15:0]（MIPI 核输出）；输出 O_csi_frame_start/O_csi_frame_end/O_csi_valid/O_csi_hs/O_csi_data[31:0]。S_head_en = ~S_hs_valid_1d & I_hs_valid 抓包头那一拍的上升沿；随后比较 S_hs_data_1d[15:8]（数据类型 DT）与 localparam FRAME_DATA_DT=8h2B(RAW10)、FRAME_START_DT=8h00、FRAME_END_DT=8h01，判断帧起、帧止与长包；数据长度 S_data_length = {I_hs_data[15:8], S_hs_data_1d[7:0]} >> 1（右移 1 是因为 2lane 每拍送 2 字节，而 LENGTH 字段按字节给出）；S_data_en 由 S_data_en_cnt 计到 S_data_length-1 时关断；csi_valid_r 在 S_data_en 期间二分频产生 O_csi_valid；O_csi_data <= {O_csi_data[15:0], I_hs_data} 把两次 16bit 拼成一个 32bit 字。',
 clk=u'I_clk 上升沿同步，I_rst_n 异步复位、低电平有效。',
 dep=u'第 138~156 行例化调试核 cwc3 cwc3_inst（probe0~probe14），该模块在本目录中不存在定义，疑似安路 TD 的在线调试 IP。无其它自研依赖。',
 impl=u'★未被 camera_to_dsi_display.al 引用、未参与综合实现（若单独综合会因缺少 cwc3 定义而报未定义模块，属环境/IP 缺失，不是语法问题）。')
sec(P, 36, u'kuai 1: duan-kou sheng-ming (MIPI 2lane 16bit shu-ru -> 32bit shu-chu)', 0)
sec(P, 52, u'kuai 2: MIPI CSI-2 DT (data type) shuo-ming yu ben mo-kuai shi-yong de DT chang-liang', 0)
sec(P, 60, u"FRAME_DATA_DT = 8h2B (RAW10 chang-bao); di 61 hang zhu-shi wei 8h2A (RAW8)", 0)
sec(P, 62, u"FRAME_START_DT = 8h00 / FRAME_END_DT = 8h01 (duan-bao)", 0)
sec(P, 65, u'kuai 3: nei-bu ji-cun qi / xian-wang', 0)
sec(P, 73, u'kuai 4: bao-tou shang-sheng-yan jian-ce (S_head_en = ~1d & I_hs_valid)', 0)
sec(P, 76, u'kuai 5: zhen-qi / zhen-zhi / chang-bao shi-neng pan-duan (bi DT + chang-du ji-shu)', 0)
sec(P, 105, u'kuai 6: shu-ju chang-du ji-shu yu S_data_en guan-duan', 0)
sec(P, 118, u'kuai 7: 2lane 16bit pin-jie cheng 32bit', 0)
sec(P, 126, u'kuai 8: O_csi_valid er-fen-pin sheng-cheng (S_data_en qi-jian fan-zhuan)', 0)
sec(P, 138, u'kuai 9: tiao-shi-he cwc3 (ben mu-lu wu gai mo-kuai ding-yi, yi shi Anlogic TD zai-xian tiao-shi IP)', 0)

# ============================================================ 7 raw8_to_rgb888.v
P = u'raw8_to_rgb888.v'
header(P,
 mod=u'raw8_to_rgb888',
 func=u'RAW8 转 RGB888 的简易去马赛克（demosaic）：把每拍 4 个 8bit 的 Bayer RAW8 像素插值成每拍 4 个 24bit RGB888 像素。★未被 isp_top.v 使用、全树无例化、也不在 .al 编译清单中，属备用路径。',
 dp=u'输入 I_raw8_data[31:0]（4 个 8bit 像素）；输出 O_rgb888_data[95:0]（4 像素 x 24bit，[23:16]=R、[15:8]=G、[7:0]=B）。先用两个 PH1P_LOGIC_SHIFTER#(.DATA_WIDTH(32),.DATA_DEPTH(258),.SHIFT_TYPE("FIXED"))（U0/U1，第 106~135 行）级联，得到当前行、前一行、前两行共 3 行数据 S_conv_data_1/2/3；S_raw8_line_end = ~I_raw8_valid & S_raw8_valid_1d 检测行尾并给 S_line_cnt 计数；S_line_cnt >= 2 后 S_conv_en 拉高，S_conv_line_odd_even 每行尾翻转，得到奇/偶行两套公式（第 219~236 行奇行、第 238~254 行偶行）；两套都是 4 邻域相加 >> 2（或 2 邻域 >> 1）的平均插值，即用同色邻域的平均值补出缺失的两个分量。输出前打 3 级流水（S_conv_*_1d/_2d），最后把 4 个像素各自取 [7:0] 拼成 96bit（高 8bit 被丢弃）。',
 clk=u'I_clk 上升沿同步；I_rst_n 异步复位、低电平有效（只用于复位 S_line_cnt 等计数器）。',
 dep=u'例化 PH1P_LOGIC_SHIFTER（PH1P 系列的行移位 IP），另有旧版本注释掉的 w32_d962_shifter 例化（第 99~104 行，仅注释保留）。该 IP 的定义不在本目录，未能确认其所属 IP 库。',
 impl=u'★未被 camera_to_dsi_display.al 引用、未参与综合实现；本工程 RAW8 通路实际由 isp/demosaic_4x_2_0/ 下的模块承担（未逐一比对，未能确认）。')
sec(P, 45, u'kuai 1: duan-kou sheng-ming (32bit RAW8 shu-ru -> 96bit RGB888 shu-chu)', 0)
sec(P, 56, u'kuai 2: nei-bu ji-cun qi / xian-wang (S_line_cnt, S_conv_* deng)', 0)
sec(P, 68, u'kuai 3: shu-ru da-pai + frame_start/end tou-ming chuan-di', 0)
sec(P, 79, u'kuai 4: hang-wei jian-ce (S_raw8_line_end = ~I_raw8_valid & 1d)', 0)
sec(P, 86, u'kuai 5: hang-ji-shu S_line_cnt (zhen-qi qing 0, xing-wei +1)', 0)
sec(P, 99, u'kuai 6: bei zhu-shi diao de jiu-ban shifter shi-li-hua (jin bao-liu)', 0)
sec(P, 106, u'kuai 7: 3 hang shu-ju huan-cun (liang ji PH1P_LOGIC_SHIFTER, DATA_DEPTH=258 = yi hang 256+2)', 0)
sec(P, 122, u'kuai 8: di er ji shifter (shu-chu shi zai shang yi hang)', 0)
sec(P, 137, u'kuai 9: S_conv_en (deng 2 hang shu-ju dou jin lai hou cai qi-dong cha-zhi)', 0)
sec(P, 144, u'kuai 10: qi/ou hang biao-zhi S_conv_line_odd_even (mei hang-wei fan-zhuan)', 0)
sec(P, 154, u'kuai 11: 3 hang shu-ju dui-qi (data_1 = shang shang hang, data_2 = shang hang, data_3 = dang-qian hang)', 0)
sec(P, 172, u'kuai 12: 3 ji liu-shui (wei cha-zhi gong-shi ti-gong shang/zhong/xia san hang de dui-qi shu-ju)', 0)
sec(P, 219, u'kuai 13: qu-ma-sai-ke qi hang gong-shi (4 lin-yu >> 2 huo 2 lin-yu >> 1 ping-jun cha-zhi)', 0)
sec(P, 238, u'kuai 14: qu-ma-sai-ke ou hang gong-shi (tong li, lin-yu fang-xiang xiang-fan)', 0)
sec(P, 279, u'kuai 15: shu-chu pin-jie (4 xiang-su x 24bit, [23:16]=R [15:8]=G [7:0]=B)', 0)

# ============================================================ 8 auto_white_balance.v
P = u'auto_white_balance.v'
header(P,
 mod=u'auto_white_balance',
 func=u'自动白平衡增益应用：把 96bit（4 像素 x 24bit）RGB888 数据按输入的 20bit 定点增益分别乘 R/B 通道，G 通道不乘。★全树无例化、不在 .al 编译清单中；本工程实际使用的是根目录 awb.v（在 .al 中）。',
 dp=u'输入 I_r_gain[19:0]/I_g_gain[19:0]/I_b_gain[19:0] 与 I_rgb888_data[95:0]；输出 O_awb_data[95:0]。把 96bit 按 24bit 一切分成 p0~p3 四组（p0=[95:72]、p1=[71:48]、p2=[47:24]、p3=[23:0]，组内 [23:16]=R、[15:8]=G、[7:0]=B）。增益乘法 S_awb_*_data_pN <= S_*_data_pN * I_*_gain，结果 28bit（注释标 fi(0,28,12)，即 28 位定点、低 12 位是小数）；饱和处理 (S_awb_*_data_pN[27:12] >= 16d255) ? 8d255 : S_awb_*_data_pN[19:12]，即先看 [27:12] 是否溢出，正常取 [19:12]（右移 12 位去掉小数）。输出再打 2 拍（S_rgb888_valid_1d/_2d -> O_awb_valid）与输入节奏对齐。',
 clk=u'I_clk 上升沿同步；I_rst_n 异步复位、低电平有效。数据通路含 3 拍输出寄存器（与乘法/饱和的流水对齐）。',
 dep=u'无子模块例化。第 155~171 行是被 // 注释掉的旧版实现（对 O_awb_data 各 24bit 段做 +1），仅作历史保留。',
 impl=u'★未被 camera_to_dsi_display.al 引用、未参与综合实现；乘法为 8bit x 20bit，规模很小。')
sec(P, 1, u'kuai 1: duan-kou sheng-ming (96bit RGB888 shu-ru + 3 ge 20bit ding-dian zeng-yi)', 0)
sec(P, 15, u'kuai 2: shu-ru shu-ju chai fen (96bit -> 4 x 24bit, p0=[95:72] ... p3=[23:0])', 0)
sec(P, 38, u'kuai 3: zeng-yi cheng-fa (24bit x 20bit ding-dian, 28bit jie-guo, fi(0,28,12))', 0)
sec(P, 66, u'kuai 4: bao-he chu-li (xian kan [27:12] shi-fou yi-chu, zheng-chang qu [19:12] ji you-yi 12 wei)', 0)
sec(P, 94, u'kuai 5: shu-chu ji-cun yu pin-jie (da 2 pai, yu shu-ru jie-zou dui-qi)', 0)
sec(P, 155, u'kuai 6: bei zhu-shi diao de jiu-ban shi-xian (jin bao-liu, ben ci wei dong)', 0)

# ============================================================ 9 image_correction.v  (GB18030)
P = u'image_correction.v'
GB = u'gb18030'
header(P,
 enc=GB,
 mod=u'image_correction #( parameter DATA_WIDTH = 40 )',
 func=u'图像裁剪/开窗（不是色彩或镜头校正）：只放行画面中 600 行 x 256 列的一块区域，其余数据清零。★全树无例化、不在 .al 编译清单中，属未接入模块；文件名与功能并不完全对应，注释按代码实际行为描述。',
 dp=u'输入 I_raw_data[39:0]、I_raw_valid、I_raw_frame_start；输出 O_raw_tdata[39:0]/O_raw_tlast/O_raw_tvalid/O_raw_tuser，另有一个方向相反的 input O_raw_tready（命名沿用了原作者的写法）。I_raw_tvalid_d/I_raw_tdata_r 先把输入打一拍；cnt 在 !I_raw_valid 时自增，wire last = (cnt == 10) 作为行内节拍（常量 10 与 40bit=4 像素的打包粒度有关，具体依据未能从代码确认）；v_cnt 在 last 时 +1、I_raw_frame_start 时清 0，V_valid = (v_cnt >= 0) && (v_cnt <= 599) 只放行 600 行；h_cnt 在 last 或帧起始清 0、I_raw_tvalid_d 时 +1，H_valid = (h_cnt <= 255) && (h_cnt >= 0) 只放行 256 列；tuser = (h_cnt==0)&&(v_cnt==0)&&I_raw_tvalid_d；O_raw_tdata 在 V_valid&&H_valid 时给数据否则给 0；O_raw_tlast = V_valid && (h_cnt==255) && I_raw_tvalid_d；I_raw_tready 直接回连 O_raw_tready。',
 clk=u'I_clk 上升沿同步；I_rst_n 异步复位、低电平有效；h_cnt/v_cnt 都是 15bit 计数器，行首节拍由 last 产生。',
 dep=u'第 79~93 行是注释掉的调试核例化 cwc cwc_inst，本目录无该模块定义（疑似安路调试 IP）；无其它自研依赖。',
 impl=u'★未被 camera_to_dsi_display.al 引用、未参与综合实现。本文件为 GB18030 编码，本次插入的注释按 GB18030 写回，原有字节未改动。')
sec(P, 20, u'kuai 1: nei-bu ji-cun qi / xian-wang', 4, enc=GB)
sec(P, 26, u'kuai 2: shu-ru da-pai (I_raw_tvalid_d / I_raw_tdata_r)', 4, enc=GB)
sec(P, 37, u'kuai 3: hang-nei jie-pai ji-shu (cnt == 10 wei last)', 4, enc=GB)
sec(P, 50, u'kuai 4: chui-zhi fang-xiang kai-chuang (v_cnt 0~599, ji 600 hang)', 4, enc=GB)
sec(P, 58, u'kuai 5: V_valid (zhi fang-xing 0~599 hang)', 4, enc=GB)
sec(P, 60, u'kuai 6: shui-ping fang-xiang kai-chuang (h_cnt 0~255, ji 256 lie)', 4, enc=GB)
sec(P, 79, u'kuai 7: bei zhu-shi diao de tiao-shi-he cwc (jin zhu-shi bao-liu)', 4, enc=GB)

# ============================================================ 10 awb.v (root, IN .al)
P = u'awb.v'
header(P,
 mod=u'awb #( parameter IMG_HEIGHT = 1080, IMG_WIDTH = 1920 )',
 func=u'自动白平衡增益：按 R/G/B 三通道累加和算出 R、B 相对 G 的增益，再对延时对齐后的 96bit（4 像素 x 24bit）数据逐像素施加增益。★与 isp\\awb\\awb.v 同名但内容不同（本文件 383 行、那份 490 行，属另一版本）。核实结论：本文件在 .al 编译清单中，被 isp_top.v:126 例化为 awb，是本工程当前在用的白平衡实现（isp/awb/ 下的同名文件不在 .al 中）。',
 dp=u'输入 I_tdata[95:0]（每 24bit 一个像素：[23:16]=R、[15:8]=G、[7:0]=B）、I_tvalid/I_tuser/I_tlast；输出 O_tdata[95:0] 及 O_tvalid/O_tuser/O_tlast，另有 output I_tready 与 input O_tready（方向命名沿用原作者写法，实际是同一对握手）。①累加区：rgb_sum[0] = r+g+b（注释说“削弱白色”，即用亮度阈值排除过亮像素），sum_r/sum_g/sum_b 在 I_tuser 或复位时置 1（避免除零），在 I_tvalid_r0 && (rgb_sum[0] < 720) 时累加（720 是经验阈值）；②除法区：例化两个 divider（div_gen_G_R_r1 / divide_G_B_r1），.numerator({sum_g[0],16d0})、.denominator(sum_r[0])/(sum_b[0])、.start(I_tvalid_r1)，得到 48bit 的 dout_R[0]/dout_B[0]；③延时区：例化 signal_delay #(.IMG_HEIGHT,.IMG_WIDTH,.DATA_WIDTH(96),.DELAY_CYCLE(50))，用 BRAM 把像素流延后若干行，等增益算完再对齐；④增益寄存器 in_r_r1/in_b_r1 复位与 I_tuser 时为 20h10000（=1.0 的定点表示），done[0] 时若 |in_r_x1[47:20] 非零则饱和到 20hfffff，否则取 in_r_x1[19:0]；⑤增益乘：R_new_rN <= in_r_r1 * rgb888_r_d1[N-1]，G 不乘，B 乘 in_b_r1；⑥输出饱和 assign R_new_xN = (R_new_rN[27:24]) ? 255 : R_new_rN[23:16]（G 直接取），最后把 4 像素拼回 96bit；O_tlast = (valid_d1==0)&&(valid_d2==1)（在 valid 下降沿产生行结束），O_tuser = I_tuser，O_tvalid = valid_d2，I_tready = O_tready。',
 clk=u'I_clk 上升沿同步；I_rst_n 异步复位、低电平有效；内部有 r0/r1/d1/d2 多级流水与 signal_delay 的整行延时，所以输出相对输入整体延后若干行。',
 dep=u'例化 divider（除法器 IP，两处）与 signal_delay（本目录 signal_delay.v，内部再例化 BRAM blk_mem_gen_awb_delay_signal）。第 46~55 行有被 // 注释掉的 RGB565->RGB888 代码，仅作历史保留。',
 impl=u'本文件在 camera_to_dsi_display.al 的编译清单中，参与本工程综合实现；用到除法器与 BRAM，是本工程资源占用较大的模块之一。')
sec(P, 1, u'kuai 1: duan-kou sheng-ming (96bit RGB888 liu-shui + tvalid/tuser/tlast shou-wo)', 0)
sec(P, 46, u'kuai 2: bei // zhu-shi diao de RGB565 -> RGB888 dai-ma (jin bao-liu)', 0)
sec(P, 56, u'kuai 3: R/G/B lei-jia (ji suan zeng-yi yi-ju; sum_* fu-zhi 1 yi bi-mian chu-ling)', 0)
sec(P, 120, u'kuai 4: chu-fa-qi (suan G/R yu G/B bi-zhi, 48bit shu-chu)', 0)
sec(P, 160, u'kuai 5: xiang-su liu yan-shi (signal_delay + BRAM, deng zeng-yi suan-wan zai dui-qi)', 0)
sec(P, 186, u'kuai 6: di yi ci shi-li-hua signal_delay (yan shi xiang-su liu)', 0)
sec(P, 225, u'kuai 7: di er ci shi-li-hua signal_delay', 0)
sec(P, 262, u'kuai 8: zeng-yi ji-cun qi (fu-wei/tuser shi 20h10000 = 1.0 ding-dian; done shi bao-he)', 0)
sec(P, 306, u'kuai 9: zeng-yi cheng-fa (R/B cheng zeng-yi, G bu cheng) + bao-he', 0)
sec(P, 352, u'kuai 10: shu-chu shou-wo / pin-jie (O_tvalid = valid_d2, O_tdata an 4 xiang-su pin-jie)', 0)

# ============================================================ 11 signal_delay.v (root, IN .al)
P = u'signal_delay.v'
header(P,
 mod=u'signal_delay #( IMG_HEIGHT=1080, IMG_WIDTH=1920, DATA_WIDTH=96, DELAY_CYCLE=50 )',
 func=u'整行信号延时：用一块双口 BRAM 把像素流（含 valid/tuser）延后 DELAY_CYCLE 行，好让 awb 的除法器算完增益后再对齐施加到同一像素上。★与 isp\\awb\\signal_delay.v 同名但内容不同。核实结论：本文件在 .al 编译清单中，被 awb.v:186 与 awb.v:225 各例化一次，是本工程当前在用的实现（isp/awb/ 下的同名文件不在 .al 中）。',
 dp=u'输入 I_clk/I_rst_n/I_tuser/I_valid/I_data[DATA_WIDTH-1:0]，输出 O_valid/O_data/O_tuser。localparam IMG_WIDTH_4x = (IMG_WIDTH >> 2)（1280 -> 320，因为每拍 4 个像素）；h_cnt 在 I_valid_r 时按 IMG_WIDTH_4x 环回、v_cnt 在行尾时按 IMG_HEIGHT 环回，组成写地址基准；rd_valid 在 h_cnt == DELAY_CYCLE - 3（= 47）时拉高，rd_cnt 计到 IMG_WIDTH_4x-1 清 0，作为读地址基准；addra（写指针）与 addrb（读指针）都在 IMG_WIDTH_4x 内环回（11bit，深度覆盖一行）；O_valid = rd_valid_d（打一拍），O_tuser = (v_cnt==0)&&(rd_cnt==1)（读侧第 0 行第 1 拍重新产生行首标志）。写侧 I_valid_r 打拍后驱动 BRAM 的 wea，数据 I_data_r 驱动 dia；读侧 dob 直接接到 O_data。',
 clk=u'I_clk 同时作 BRAM 的 clka 与 clkb（同步双口），I_rst_n 异步复位、低电平有效；延时量由 DELAY_CYCLE 参数（例化时为 50 行）决定。',
 dep=u'例化 blk_mem_gen_awb_delay_signal（真双口块 RAM，11bit 地址 x 96bit 数据）。该 BRAM 的源文件在 E:\\FPGA\\proj\\baseline\\lab3\\user_source\\hdl_source\\isp\\awb\\ram\\blk_mem_gen_awb_delay_signal.v，而该路径不在 camera_to_dsi_display.al 中，本工程应是在 .al 里以 IP 形式提供该 BRAM（未能从 .al 逐字确认，属未确认点）。',
 impl=u'本文件在 camera_to_dsi_display.al 的编译清单中；综合结果是一块 320 x 96bit 的双口 BRAM（约 30Kbit）。')
sec(P, 1, u'kuai 1: duan-kou sheng-ming (xiang-su liu + tuser de zheng-hang yan-shi)', 0)
sec(P, 34, u'kuai 2: xie/du di-zhi yu qi-dong xin-hao (rd_valid / rd_cnt / addra / addrb)', 4)
sec(P, 47, u'kuai 3: hang-lie ji-shu (IMG_WIDTH_4x = IMG_WIDTH >> 2, yin wei mei pai 4 xiang-su)', 4)
sec(P, 48, u'kuai 4: xie-ce shi-neng da-pai I_valid_r', 4)
sec(P, 59, u'kuai 5: hang/lie ji-shu (h_cnt an IMG_WIDTH_4x huan-hui, v_cnt an IMG_HEIGHT huan-hui)', 4)
sec(P, 70, u'kuai 6: du qi-dong (h_cnt == DELAY_CYCLE - 3 shi la-di, ji yan shi DELAY_CYCLE hang)', 4)
sec(P, 81, u'kuai 7: du-ce hang-shou ji-shu rd_cnt (ji dao yi-hang jie-shu qing 0)', 4)
sec(P, 92, u'kuai 8: BRAM xie di-zhi addra (zai yi-hang nei huan-hui)', 4)
sec(P, 101, u'kuai 9: BRAM du di-zhi addrb (sui rd_valid zai yi-hang nei huan-hui)', 4)
sec(P, 109, u'kuai 10: shu-chu you-xiao da-pai (O_valid = rd_valid_d)', 4)
sec(P, 117, u'kuai 11: shu-chu shou-wo (O_valid / O_tuser: di 0 hang di 1 pai chong-xin chan-sheng hang-shou)', 4)
sec(P, 120, u'kuai 12: shuang-kou BRAM shi-li-hua (yuan-wen-jian isp/awb/ram/blk_mem_gen_awb_delay_signal.v, bu zai .al qing-dan zhong)', 4)

# ============================================================ 12 uics500_cfg/uii2c.v (GB18030, IN .al)
P = u'uics500_cfg\\uii2c.v'
header(P,
 enc=GB,
 mod=u'uii2c #( parameter integer WMEN_LEN = 8d0, RMEN_LEN = 8d0, CLK_DIV = 16d499 )',
 func=u'通用 I2C 主机（MASTER）：按请求发起一次写或读传输，支持 WMEN_LEN 字节写、RMEN_LEN 字节读，用于配置 SC500 摄像头寄存器。本工程实际使用的就是这一份。',
 dp=u'端口：I_clk/I_rstn、O_iic_scl、inout IO_iic_sda、I_wr_data[WMEN_LEN*8-1:0]、I_wr_cnt[7:0]、O_rd_data[RMEN_LEN*8-1:0]、I_rd_cnt[7:0]、I_iic_req、I_iic_mode（1=连续读、0=当前寄存器地址读）、O_iic_busy、O_iic_bus_error、IO_iic_sda_dg。时序：SCL 由 scl_clk 分频得到，localparam SCL_DIV = CLK_DIV/2 是半个 SCL 周期的计数；localparam OFFSET = SCL_DIV - SCL_DIV/4 让外部 SCL 相对内部节拍延后 3/4 个半周期，以拉开 SCL 与 SDA 的建立/保持时间。状态机 localparam：IDLE=4d0、START=1、W_WAIT=2、W_ACK=3、R_WAIT=4、R_ACK=5、STOP1=6、STOP2=7（声明为 reg [2:0] IIC_S 却赋 4d 常量，位宽偏紧但 0~7 都能表示，本次只加注释未改代码）。SDA 是开漏输出：assign IO_iic_sda = (sda_o == 1b0) ? 1b0 : 1bz（0 拉低、否则高阻靠外部上拉），assign sda_i = IO_iic_sda 回读。发送在 always @(posedge scl_clk)、接收在 always @(negedge scl_clk)，读回数据按字节存放 O_rd_data[((rcnt-1b1)*8) +: 8] <= sda_i_r[7:0]；在 W_ACK 状态若 sda_i == 1b1（从机未应答）则置 O_iic_bus_error。',
 clk=u'I_clk 为系统时钟，I_rstn 异步复位、低电平有效；SCL 频率 = I_clk / CLK_DIV（本文件默认 CLK_DIV=499，实际分频常数由上层 uicfgcs500_720p.v 传入，例化时取 999）。',
 dep=u'第 94~107 行是注释掉的 //PULLUP PULLUP_inst 与整段 Xilinx IOBUF #(...) IOBUF_inst (.O(sda_i), ... .I(sda_o), .T(sda_o));（端口名全在注释中），仅供历史参考，本次未改动注释内任何名字。被 uics500_cfg/uicfgcs500_720p.v:100 例化为 uii2c_inst（WMEN_LEN=4/RMEN_LEN=1）。',
 impl=u'本文件在 camera_to_dsi_display.al 的编译清单中；SCL 与 SDA 走普通 IO（无专用 IOBUF 例化），无其它 IP 依赖。本文件为 GB18030 编码，本次插入的注释按 GB18030 写回，原有字节未改动。')
sec(P, 39, u"timescale (shi-jian dan-wei / jing-du)", 0, enc=GB)
sec(P, 41, u'kuai 1: can-shu (WMEN_LEN xie zi-jie shu / RMEN_LEN du zi-jie shu / CLK_DIV SCL fen-pin xi-shu)', 0, enc=GB)
sec(P, 47, u'kuai 2: duan-kou sheng-ming (SCL + kai-lou SDA + xie/du shu-ju yu qing-qiu shou-wo)', 0, enc=GB)
sec(P, 63, u'kuai 3: zhuang-tai-bian-liang (IDLE/START/W_WAIT/W_ACK/R_WAIT/R_ACK/STOP1/STOP2)', 0, enc=GB)
sec(P, 70, u'kuai 4: SCL fen-pin chang-liang (SCL_DIV = CLK_DIV/2; OFFSET = SCL_DIV - SCL_DIV/4 rang SCL yan-hou 3/4 ge ban-zhou-qi, bao-zheng SCL/SDA jian-li-bao-chi shi-jian)', 0, enc=GB)
sec(P, 72, u'kuai 5: SDA kai-lou shu-chu yu hui-du (0 la-di, 1 gao-zu kao wai-bu shang-la)', 0, enc=GB)
sec(P, 94, u'kuai 6: bei zhu-shi diao de PULLUP / Xilinx IOBUF shi-li-hua (.I/.O/.T duan-kou ming zi jin zai zhu-shi zhong, ben ci wei dong)', 0, enc=GB)
sec(P, 108, u'kuai 7: shi-zhong fen-pin yu SCL sheng-cheng', 0, enc=GB)
sec(P, 157, u'kuai 8: xie-fa shi-xu (always @(posedge scl_clk))', 0, enc=GB)
sec(P, 197, u'kuai 9: jie-shou shi-xu / du hui shu-ju (always @(negedge scl_clk), an zi-jie cun-fang)', 0, enc=GB)
sec(P, 220, u'kuai 10: ACK jian-ce yu zong-xian cuo-wu biao-zhi (W_ACK zhuang-tai sda_i == 1 ze O_iic_bus_error)', 0, enc=GB)

# ============================================================ 13 uics500_cfg/uics500reg.v  (LF only)
P = u'uics500_cfg\\uics500reg.v'
header(P, nl=u'\n',
 mod=u'uics500reg',
 func=u'SC500 摄像头寄存器配置表（常量表/ROM）：用 REG_INDEX 索引取出 32bit 寄存器数据，表长 121 条。★未确认是否为当前使用的寄存器表：本文件 175 行、共 121 条（REG_SIZE = 120 + 1），全树没有任何模块例化它，也不在 .al 编译清单中；本工程当前在用的是 uics500_cfg/uics500reg_720p60.v（在 .al 中）。',
 dp=u'端口 input [8:0] REG_INDEX -> output reg [31:0] REG_DATA、output [8:0] REG_SIZE。assign REG_SIZE = 120 + 1 即 121 条；always@(*) case(REG_INDEX) 里 0..120 每条形如 REG_DATA = {16h0103, 8h01}，default 输出 {16h0000, 8h00}。注意 REG_DATA 声明为 32bit 但每条只赋 24bit（高 8bit 补零），上层 uicfgcs500.v 正是按 [23:16]/[15:8]/[7:0] 三个字节拆开送给 I2C 的。',
 clk=u'无时钟、无复位：纯组合查找表（always @(*)）。本文件为纯 LF 换行、UTF-8 无 BOM，插入的注释也按 LF 写回。',
 dep=u'无子模块；被 uics500_cfg/uicfgcs500.v:146 例化为 uics500reg_inst，而 uicfgcs500.v 本身不在 .al 编译清单中。',
 impl=u'★未被 camera_to_dsi_display.al 引用、未参与本工程综合实现；若综合则是 121 x 32bit 的常量表。')
sec(P, 34, u'kuai 1: duan-kou sheng-ming (REG_INDEX 9bit suo-yin -> 32bit REG_DATA; REG_SIZE = 120+1 = 121 tiao)', 4, nl=u'\n')
sec(P, 48, u'kuai 2: zhu-ce-qi biao (jin .al zai-yong de shi uics500reg_720p60.v, ben wen-jian wei ling yi zhang biao)', 4, nl=u'\n')

# ============================================================ 14 uics500_cfg/uicfgcs500.v (GB18030)
P = u'uics500_cfg\\uicfgcs500.v'
header(P,
 enc=GB,
 mod=u'uicfgcs500 #( parameter CLK_DIV = 16d999 )',
 func=u'SC500 摄像头 I2C 配置控制：上电后按寄存器表逐条写配置，配置完成后再按 AE 请求更新曝光与模拟增益。★未被 camera_to_dsi_display.al 编译：本文件与 uics500_cfg/uicfgcs500_720p.v 同族但不是 720p 版本，全树无例化；本工程当前在用的是 uicfgcs500_720p.v。',
 dp=u'端口 I_clk/I_rst_n/I_ae_req/I_exposure_time[15:0]/I_analog_gain[15:0] -> O_cam_scl/IO_cam_sda/O_cfg_done/O_ae_cfg_done。localparam CAM_ID = 8h6C（7bit 器件地址 + 写位）。reg[7:0] rst_cnt 上电自增到 bit7=1 作为内部延时复位，等 I2C 与寄存器表稳定后再启动状态机。TS_S 是 2bit 状态机：0=取当前 REG_INDEX 对应的寄存器数据，1=总线不忙时把 4 字节组装进 wr_data 并置 iic_req，2=等 iic_busy 起来后清 iic_req，3=等 iic_busy 落下后 reg_index 加 1 回到 0（写完一轮即 O_cfg_done）。wr_data 组装（大端，寄存器地址在前、数据在后）：wr_data[7:0]<=CAM_ID、[15:8]<=REG_DATA[23:16]、[23:16]<=REG_DATA[15:8]、[31:24]<=REG_DATA[7:0]。assign REG_DATA = (O_cfg_done == 0) ? REG_DATA_REG : REG_DATA_AE，即先走配置表、配置完成后再走 AE 表。',
 clk=u'I_clk 为系统时钟，I_rst_n 异步复位、低电平有效；I2C 的 SCL 分频常数 CLK_DIV 由参数给出（默认 16d999，例化 uii2c 时透传）。',
 dep=u'例化 uii2c#(.WMEN_LEN(4),.RMEN_LEN(1),.CLK_DIV(CLK_DIV)) uii2c_inst（I_wr_cnt=8d4、I_rd_cnt=8d0、I_iic_mode=1b0，即每次写 4 字节）、uics500reg uics500reg_inst（第 146 行）、SC500GainTbl gain_tbl（.I_gain_idx(I_analog_gain - 16)）、uics500regAE uics500regAE_inst。',
 impl=u'★未被 camera_to_dsi_display.al 引用、未参与综合实现。本文件为 GB18030 编码，本次插入的注释按 GB18030 写回，原有字节未改动。')
sec(P, 35, u"timescale (shi-jian dan-wei / jing-du)", 0, enc=GB)
sec(P, 37, u'kuai 1: can-shu CLK_DIV (I2C SCL fen-pin xi-shu, mo-ren 16d999, tou-chuan gei uii2c)', 0, enc=GB)
sec(P, 42, u'kuai 2: duan-kou sheng-ming (AE qing-qiu + bao-guang/zeng-yi ru -> I2C SCL/SDA yu pei-zhi wan-cheng biao-zhi)', 0, enc=GB)
sec(P, 53, u'kuai 3: she-bei di-zhi CAM_ID = 8h6C (SC500 de I2C cong-ji di-zhi + xie wei)', 0, enc=GB)
sec(P, 54, u'kuai 4: nei-bu yan-shi fu-wei rst_cnt (shang-dian zi-zeng dao bit7=1 cai qi-dong zhuang-tai-ji)', 0, enc=GB)
sec(P, 90, u'kuai 5: zhuang-tai-ji TS_S (0=qu biao, 1=zu-zhuang wr_data bing fa qi iic_req, 2=deng busy qi lai hou qing req, 3=deng busy luo-xia hou reg_index+1)', 0, enc=GB)
sec(P, 110, u'kuai 6: wr_data zu-zhuang (da-duan: CAM_ID -> di-zhi gao/di zi-jie -> shu-ju gao/di zi-jie)', 0, enc=GB)
sec(P, 123, u'kuai 7: uii2c shi-li-hua (mei ci xie 4 zi-jie: WMEN_LEN=4, RMEN_LEN=1)', 0, enc=GB)
sec(P, 140, u'kuai 8: pei-zhi biao / AE biao xuan-ze (O_cfg_done==0 shi zou pei-zhi biao, fou-ze zou AE biao)', 0, enc=GB)

# ============================================================ execute
def main():
    order = [u'osd_char_lib.v', u'isp\\data96_128\\data96_128.v', u'isp\\data128_96\\data128_96.v',
             u'data_96bit_to_128bit.v', u'raw10_unpacket.v', u'csi_unpacket.v',
             u'raw8_to_rgb888.v', u'auto_white_balance.v', u'image_correction.v',
             u'awb.v', u'signal_delay.v', u'uics500_cfg\\uii2c.v',
             u'uics500_cfg\\uics500reg.v', u'uics500_cfg\\uicfgcs500.v']
    for p in order:
        if p not in files:
            raise SystemExit('missing ' + p)
    # 备份
    for p in order:
        src = os.path.join(BASE, p)
        dst = os.path.join(BK, p.replace(u'\\', u'__').replace(u'/', u'__') + u'.bak')
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
    # 写入
    for p in order:
        d = files[p]
        full = os.path.join(BASE, p)
        raw = open(full, 'rb').read()
        text = raw.decode(d['enc'])
        lines = text.split(u'\n')
        by = {}
        for ln, t in d['ins']:
            by.setdefault(ln, []).append(t)
        out = []
        if 0 in by:
            out.extend(by[0])
        for i, l in enumerate(lines, 1):
            if i in by:
                out.extend(by[i])
            out.append(l)
        new = u'\n'.join(out).encode(d['enc'])
        if new == raw:
            raise SystemExit('no change: ' + p)
        open(full, 'wb').write(new)
        nsec = sum(1 for ln, t in d['ins'] if t.startswith(u'//----') or u'//----' in t)
        print(u'OK %-38s bytes %d -> %d   sections=%d  inserted_lines=%d' % (p, len(raw), len(new), nsec, len(d['ins'])))
    print('backup dir:', BK)

main()
