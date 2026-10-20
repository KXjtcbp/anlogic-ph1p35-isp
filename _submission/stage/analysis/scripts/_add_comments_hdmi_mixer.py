# -*- coding: utf-8 -*-
"""只加注释：给 hdmi_mixer.v 插入文件头、段落小标题与行内注释。不改任何代码字符。"""
import sys, re

SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\hdmi_mixer.v"
BAK = r"E:\FPGA\_backup\20261009_comments\hdmi_mixer.v.bak"

HEADER = r"""//=============================================================================
// 文件      : hdmi_mixer.v
// 模块      : hdmi_mixer
// 功能      : 把 DDR 读回的摄像头画面与 OSD 叠加后按 HDMI 时序输出。OSD 共三层，
//             优先级从低到高：160x160 安路 Logo（取自 anlogic_logo_rom，用 ROM 的
//             bit24 作有效位） > 黄色帧计数行 "安路 CNT:xxxxxx"（16x16 点阵 + 6 位
//             十进制，COLOR_DYN_TEXT=24'hfff200） > 亮绿色算法状态行 "MODE n"
//             （5x7 点阵纵向放大到 10 高，COLOR_ALG_TEXT=24'h00ff88）。
//             另有 DEBUG_MODE / SHOW_DEBUG 控制的调试彩条与状态条，默认全部关闭。
// 数据通路  : (1) I_video_rd_data(24bit,DDR 读口) --打 2 拍--> S_video_data_2d
//             (2) I_video_de/last/user 计数 -> S_x/S_y --打 2 拍--> S_x_2d/S_y_2d
//             (1)(2) 汇合：用 S_x_2d/S_y_2d 逐像素算 OSD 命中(S_osd_hit)与颜色(S_osd_color)
//             -> 与 S_video_data_2d 二选一 -> 打 1 拍 -> O_hdmi_data。
//             O_video_rd_en 直接等于 I_video_de（de 有效即向 DDR 请求像素）。
//             坐标与数据的流水级数必须一致(各 2 拍)，否则叠加的字会整体错位。
// 时钟/复位 : 单时钟 I_clk（像素域），I_rst_n 低有效异步复位。唯一跨时钟域输入是
//             24 MHz 域的 I_algo_mode_tgl / I_algo_mode_wrap（1 bit 翻转信号），
//             本模块三级同步 + 异或取沿后在像素域本地计数，见文末 [MODE-PIPE] 段。
//             像素时钟的具体频率未能从代码确认（文件里只出现“24 MHz 域”这一处描述）。
// 依赖      : 子模块 anlogic_logo_rom（I_addr[14:0] -> O_pixel[24:0]，bit24=有效，
//             [23:0]=RGB888）与 osd_char_lib（I_char/I_row -> O_row_bits[15:0]），
//             两者的源码都不在本文件内，本文件只有例化。工程背景为安路 PH1P35MDG324 +
//             SC500CS(MIPI RAW10 1280x720@60) + HDMI，但器件型号与约束文件在本文件中
//             不可见（未能从代码确认）。
//             ※ 本文件内定义的字形函数只有 F_alg_char_bits 真正被调用（:1005-:1010）；
//               F_logo_text_bits / F_hex7seg / F_cnt_label_bits / F_cn16_row /
//               F_dyn_char_bits / F_osd_char16_row 均无调用点（保留代码，实际取字形
//               走 osd_char_lib 子模块）。
// 综合/实现 : 安路 TD（Tang Dynasty）工具链。时序要点见文末 [MODE-PIPE] 注释：早期把
//             模式电平直接接入组合云，会把 24m->pixel 跨域约束套到整条路上，实测
//             Setup WNS 由 +0.103ns 变为 -4.416ns（24 个违例端点）；只加 2 级同步器
//             仍剩 -0.085ns（2 个违例端点），故改为单 bit 翻转信号同步。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  在官方 lab3 基线的 HDMI 混合模块上扩展 OSD：新增“安路 CNT:”帧计数行与“MODE n”算法状态行（COLOR_ALG_TEXT=24'h00ff88）
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\reports\rename_report.txt
//============================================================================="""

INSERTS = {}
INLINE = {}

INSERTS[1] = HEADER.split("\n") + [
    "//---- 模块接口与参数（parameter / port） ----",
]

INSERTS[46] = ["//---- 视频时序与像素数据流水寄存器（各 2 拍） ----"]

INSERTS[61] = ["//---- 跨时钟域(CDC)总述：算法模式（具体实现见文末 [MODE-PIPE] 段） ----"]

INSERTS[70] = [
    "//---- OSD 内部信号 ----",
    "//   命名约定：S_logo_* = Logo 层；S_dyn_*/S_dec_digit_* = 黄色 CNT 行；",
    "//   S_pf_* = 统一 16x16 字符库取字形通路；S_alg_* = 绿色 MODE 状态行。",
    "//   ※ S_char_*/S_cn_*/S_lbl_*/S_dyn_char|col|row|bits|seg/S_logo_red_* 等一批信号",
    "//     只在 always @(*) 的默认赋值里出现、没有任何读取点，属历史遗留（见行内注释）。",
]

INSERTS[128] = ['//---- 算法状态行 "MODE n" 中间信号 ----']

INSERTS[142] = ["//---- OSD 窗口坐标与颜色常量 ----"]

INSERTS[164] = ["//---- 算法状态行 OSD 常量（本工程在基线之上新增） ----"]

INSERTS[177] = [
    "//---- 字形库 A：Logo 文字 A/N/L/O/G/I/C（5x7 点阵） ----",
    "//   ※ 当前没有任何调用点：Logo 图形由 anlogic_logo_rom 子模块给出，本函数属保留代码。",
]

INSERTS[271] = [
    "//---- 字形库 B：十六进制 7 段译码表（{a,b,c,d,e,f,g}，bit6..bit0） ----",
    "//   ※ 当前没有任何调用点，属保留代码。",
]

INSERTS[297] = [
    '//---- 字形库 C："CNT:" 标签字母（5x7） ----',
    "//   ※ 当前没有任何调用点（实际字形由 osd_char_lib 子模块给出），属保留代码。",
]

INSERTS[349] = [
    '//---- 字形库 D：汉字 "安" / "路" 16x16 点阵 ----',
    "//   ※ 当前没有任何调用点，属保留代码。",
]

INSERTS[399] = [
    "//---- 字形库 E：算法状态行的 'M''O''D''E' 与数字 0..3（5x7） ----",
    "//   这是全文件唯一真正被调用的字形函数，调用点在 :1005-:1010。",
    "//   ★索引 4 是数字 '0' 而不是 '4'（见 :456），这正是 MODE 4 会显示成 \"MODE 0\" 的根因，",
    "//     详见 :1010 处的 BUG(待修) 注释。",
]

INSERTS[509] = [
    "//---- 字形库 F：5x7 数字 0..9 与字母 a..f（动态数字绘制用） ----",
    "//   ※ 当前没有任何调用点，属保留代码。",
]

INSERTS[534] = [
    "//---- 字形库 G：统一 16x16 字符库（an / lu / C / N / T / : 及数字） ----",
    "//   ※ 当前没有任何调用点；实际取字形走 :641 例化的 osd_char_lib 子模块，",
    "//     两者的字符码定义（CHAR_* 常量）保持一致。",
]

INSERTS[634] = ["//---- 子模块例化与读写握手 ----"]

INSERTS[647] = ["//---- 像素坐标扫描（由 de / last / user 生成 S_x / S_y） ----"]

INSERTS[667] = ["//---- 帧计数与 6 位十进制拆分（黄色 CNT 行的数据源） ----"]

INSERTS[711] = ["//---- 坐标打拍：把 S_x/S_y 延后 2 拍，与像素数据流水对齐 ----"]

INSERTS[726] = [
    "//---- 组合逻辑：逐像素 OSD 判定与取字形 ----",
    "//   三层依次判定、后面的覆盖前面的：Logo -> 黄色 CNT 行 -> 绿色 MODE 状态行。",
    "//   每层都是“窗口命中 -> 求局部坐标 -> 取字形行 -> 判该列是否点亮”四步。",
    "//   本块用 S_x_2d/S_y_2d，所以结果与 S_video_data_2d 是同一个像素。",
]

INSERTS[786] = ["//------ 第 1 层：安路 Logo（窗口 160x160，图形来自 ROM） ------"]
INSERTS[798] = ['//------ 第 2 层：黄色帧计数行 "安路 CNT:xxxxxx" ------']
INSERTS[989] = ['//------ 第 3 层：绿色算法状态行 "MODE n"（优先级最高，最后判定） ------']

INSERTS[1004] = [
    "                    // 6 个字符位从左到右：0='M' 1='O' 2='D' 3='E' 4=空格 5=模式数字",
    "                    // 每个分支返回该字符在 S_alg_ly 行上的 5 bit 点阵，未命中返回全 0",
]

INSERTS[1010] = [
    "                        // BUG(待修): 状态行最后一个字符位取字形时，MODE 4 走的是索引 4'd4，",
    "                        //   而 F_alg_char_bits 的索引 4 是数字 '0'（见 :456），于是 MODE 4 在屏上",
    "                        //   显示成 \"MODE 0\"，与真正的 MODE 0 完全无法区分。",
    "                        //   正确修法：往字符库补一个数字 '4' 的字形（新索引 8），并把取索引统一",
    "                        //   改成 4+mode（即 ({1'b0,S_algo_mode_2d} + 4'd4)），之后删掉这里的特例。",
    "                        //   本次只标注，不改代码。",
]

INSERTS[1037] = ["//---- 输出流水与像素选择（正常叠加 / 调试彩条 / 调试状态条） ----"]
INSERTS[1118] = ["//------ 正常显示分支（DEBUG_MODE==0）：可选调试条 + OSD 叠加 + 画面透传 ------"]
INSERTS[1143] = ["//---- 模式打拍流水：跨域同步 -> 本地计数 -> 二级流水 ----"]

INLINE[2] = "  // 画面几何参数：H_OFFSET=横向偏移 128、V_OFFSET=纵向偏移 60、IMG_WIDTH/HEIGHT=1280x720；本模块体内未引用这 4 个参数（保留给上层覆盖），其最终作用点未能从本文件确认"
INLINE[6] = "  // 调试模式选择：0=正常显示（画面+OSD，默认）；1=8 条等宽竖彩条；2=按 I_debug_status 出整屏纯色；3=4 段状态条"
INLINE[16] = "  // 0=关闭；非 0 时在画面最左侧 x=0..5 画 4 根竖条，直接观察 I_debug_status 的 4 个 bit（见 :1123）"

INLINE[18] = "  // 像素时钟：本模块唯一时钟，所有时序逻辑都由它驱动"
INLINE[19] = "  // 异步复位，低有效"
INLINE[21] = "  // 视频场同步（来自 video_in 侧，只做 2 拍延迟后转发）"
INLINE[22] = "  // 视频行同步"
INLINE[23] = "  // 数据有效：既是像素有效标志，也是 DDR 读请求的源头（见 :634）"
INLINE[24] = "  // 帧起始脉冲：把坐标归零，并让帧计数器 +1"
INLINE[25] = "  // 行末标志：一行的最后一个有效像素"
INLINE[27] = "  // 4 bit 调试状态：bit0=DDR 正在写、bit1=DDR 正在读、bit2=读返回 valid、bit3=读回数据非零；仅 DEBUG_MODE=2/3 或 SHOW_DEBUG!=0 时使用"
INLINE[33] = "  // 24 MHz 域送来的“模式已改变”翻转位（是 1 bit 翻转事件，不是模式值本身）"
INLINE[35] = "  // 回卷翻转位：模式由 4 回到 0 时翻转一次，用于纠正本地偶发漏计数"
INLINE[37] = "  // DDR 读请求使能：直接跟随 I_video_de"
INLINE[38] = "  // DDR 读回的 24bit 像素（RGB888），进入 2 拍流水后参与叠加"
INLINE[40] = "  // HDMI 输出场同步（S_video_vsync_2d 打拍而来）"
INLINE[41] = "  // HDMI 输出行同步"
INLINE[42] = "  // HDMI 输出数据有效"
INLINE[43] = "  // HDMI 输出像素：正常时为 OSD 覆盖后的画面，调试模式下为彩条/状态条"

INLINE[46] = "  // 时序与数据各打 2 拍：让输出与 OSD 判定用的 S_x_2d/S_y_2d 处在同一像素时刻"
INLINE[52] = "  // 像素数据第 1 拍"
INLINE[54] = "  // 当前像素坐标：de 期间自增，行末回卷（见 :647 的计数逻辑）"
INLINE[56] = "  // 坐标第 1 拍（与 S_video_data_1d 对齐）"
INLINE[57] = "  // 坐标第 2 拍：OSD 组合逻辑实际使用的坐标"

INLINE[70] = "  // 该像素是否被任意一层 OSD 命中（组合逻辑结果）"
INLINE[71] = "  // 命中时使用的颜色（RGB888）"
INLINE[74] = "  // S_char_idx..S_char_on：早期通用字符扫描用的信号，已无读取点（只被 :733-:737 赋默认值）"
INLINE[85] = "  // Logo ROM 地址（线性地址 = 局部 y*LOGO_W + 局部 x，见 :791）"
INLINE[87] = "  // 帧计数器：每帧 +1 持续累加；显示只取它的 6 位十进制拆分结果"
INLINE[98] = "  // 6 位十进制数字：_0 是最低位、_5 是最高位；屏上从左到右显示 _5.._0（见 :917）"
INLINE[114] = "  // S_cn_*/S_lbl_*/S_dyn_char|col|row|bits|seg/S_logo_red_* 系列只在组合块里被赋默认值、从未被读取（历史遗留）"
INLINE[142] = "  // Logo 窗口：左上角 (0,0)，宽高各 160"
INLINE[147] = "  // Logo 装饰色 COLOR_LOGO_BLUE/COLOR_LOGO_RED：当前无任何引用点（历史遗留，未参与实际绘制）"
INLINE[149] = "  // COLOR_TEXT：当前无任何引用点（历史遗留）"
INLINE[150] = "  // 黄色 CNT 行窗口：左上 (375,120)，宽 200 = 前缀区 108 + 数字区 90 + 余量，高 24"
INLINE[154] = "  // 标签/汉字字形在 24 高窗口内的纵向起点偏移（上下各留 2 像素余量）"
INLINE[155] = "  // 黄色字色（RGB888）：屏上“安路 CNT:”那一行用的就是它"
INLINE[156] = "  // 以下 CHAR_* 是 16x16 字符库的字符码：0x80='安'、0x81='路'，其余直接用 ASCII（'C'=0x43 …）"
INLINE[161] = "  // '0' 的 ASCII 码：数字的字符码 = CHAR_0 + 数字值（见 :952）"
INLINE[162] = "  // ':' 的 ASCII 码"
INLINE[171] = "  // 绿色状态行窗口：左上 (176,176)，宽 84 = 6 字符 x 14 字距，高 10（5x7 字形纵向放大到 10）"
INLINE[177] = "  // 取字形：I_char 选字符、I_row(0..6) 选行；返回值 5 bit，bit[4] = 最左列"
INLINE[272] = "  // 位序约定 {a,b,c,d,e,f,g} 对应 bit6..bit0；当前无调用点"
INLINE[297] = "  // I_idx: 0='C'、1='N'、2='T'、3=':'（即屏上 “CNT:” 标签的 4 个字符位）"
INLINE[350] = "  // I_char=0 为“安”、1 为“路”；每行 16 bit 中 bit[15] 是最左像素"
INLINE[403] = "  // I_char: 0='M' 1='O' 2='D' 3='E' 4='0' 5='1' 6='2' 7='3'（注意：没有数字 '4' 的字形）"
INLINE[509] = "  // 每行 5 bit，bit[4] 为最左列"
INLINE[535] = "  // I_char 用 8bit 字符码、I_row 0..15；返回一行的 16 bit 点阵（bit[15]=最左像素）"

INLINE[634] = "  // 读请求 = de：de 有效期间持续向 DDR 要像素，不做缓冲"
INLINE[636] = "  // Logo 位图 ROM：地址由坐标拼出，输出 {有效位, RGB888}"
INLINE[641] = "  // 统一 16x16 字符库：当前只用于给黄色 CNT 行取字形"

INLINE[652] = "  // I_video_user = 帧起始：坐标清零"
INLINE[656] = "  // de 有效才计数（消隐期间坐标保持不变）"
INLINE[657] = "  // 行末：x 归零且 y 加一；否则 x 加一"

INLINE[677] = "  // 帧起始：每帧处理一次"
INLINE[678] = "  // 帧计数自增（用来确认画面确实在刷新，约 60 fps 递增）"
INLINE[679] = "  // 级联十进制进位链：本位到 9 就清零并向高位进 1，逐级传递到 _5；_5 到 9 直接回 0"

INLINE[719] = "  // 坐标延迟 2 拍 = 像素数据的流水级数，保证两者同拍参与运算"
INLINE[726] = "  // 纯组合块：用第 2 拍坐标判 OSD，结果与 S_video_data_2d 属同一像素"
INLINE[727] = "  // 组合默认值（全部赋 0，避免综合出锁存器）"

INLINE[786] = "  // 只在 de 有效的流水级做判定（消隐期不产生 OSD）"
INLINE[787] = "  // Logo 窗口命中判定（左闭右开）"
INLINE[789] = "  // 窗口内局部坐标"
INLINE[791] = "  // ROM 线性地址 = 局部 y * 行宽 160 + 局部 x"
INLINE[792] = "  // bit24 是该像素的“有效/不透明”标志，只有为 1 才覆盖画面"
INLINE[798] = "  // Logo 未命中时才判 CNT 行（Logo 优先级更高）"
INLINE[801] = "  // CNT 窗口内的局部坐标（x 0..199，y 0..23）"
INLINE[806] = "  // 前缀区分配：0..23='安'、24..47='路'、52..67='C'、68..83='N'、84..99='T'、100..107=':'"
INLINE[823] = "  // 放大：局部坐标 x16 再 /24，得到 16x16 字形内部的列/行（字形被放大成 24x24）"
INLINE[862] = "  // 'C''N''T' 三个字母是 1:1 点阵（局部 x 只有 0..15），列号取低 4 位即等于原值"
INLINE[889] = "  // 冒号只有 2 列宽：横向放大 8 倍映射到 16 列字形（局部 x * 16 / 8）"
INLINE[917] = "  // 十进制数字区 x=110..199：共 6 位，每位 15 像素宽"
INLINE[921] = "  // 屏上最左边那位显示的是最高位 _5（大端输出）"
INLINE[952] = "  // 字符码 = '0' + 数字值（以 CHAR_0=8'h30 为基址）"
INLINE[957] = "  // 每位数字的显示框是 15x24：横向按 16/15 略微放大"
INLINE[958] = "  // 纵向按 16/24 缩小（16 行字形撑满 24 像素高）"
INLINE[984] = "  // CNT 行命中：整行使用黄色 COLOR_DYN_TEXT"
INLINE[995] = "  // 状态行窗口命中判定（宽 84 = 6 字符 x 14 字距）"
INLINE[997] = "  // 窗口内局部坐标"
INLINE[999] = "  // 取局部 x 低 4 位再对 14 取模，得到字符内列偏移（0..13，其中 0..4 才落在字形上）"
INLINE[1000] = "  // 行号 = 局部 y（窗口高度只有 10，取低 4 位足够）"
INLINE[1001] = "  // 第几个字符：局部 x 的 bit[6:4] 即 x/16，恰好得到 0..5 共 6 个字符位"
INLINE[1003] = "  // 字形只有 5 列宽：lx<5 才是字形内部，lx>=5 是字间空隙（不点亮）"
INLINE[1016] = "  // 5 位列选择：bits[4] 是最左列，所以从 bit4 依次取到 bit0"
INLINE[1029] = "  // 命中：用亮绿色覆盖（本层最后判定，优先级最高）"

INLINE[1039] = "  // 复位：输出同步信号与像素数据全部清零"
INLINE[1051] = "  // vsync/hsync/de 各打 2 拍，与数据及 OSD 判定同相位"
INLINE[1065] = "  // 调试模式 1：8 条等宽竖彩条，每条 128 像素（红/绿/蓝/黄/青/品红/白/暗灰）"
INLINE[1088] = "  // 调试模式 2：按 I_debug_status 给整屏纯色；4'b1111 视为“全好”并透传真实像素"
INLINE[1103] = "  // 调试模式 3：4 段各 256 宽的状态条，每段对应 1 个 debug bit（亮=1，暗=0）"
INLINE[1123] = "  // 正常模式下的可选调试条：x=0..5 的 4 根竖条，绿=bit 为 1、暗红=0；y>=480 之后透传画面"
INLINE[1135] = "  // OSD 命中就覆盖，否则直接透传 DDR 读回的像素"

INLINE[1164] = "  // 三级同步链：前两级做 CDC 同步，第三级与第二级异或用来取边沿"
INLINE[1167] = "  // 相邻两级不同 = 发生过一次翻转，产生 1 个时钟宽的脉冲（只在像素域有效）"
INLINE[1170] = "  // 回卷线使用完全相同的“同步 + 取沿”结构"
INLINE[1185] = "  // 逐级打拍：既做同步，也保留历史值供异或取沿"
INLINE[1194] = "  // 本地模式寄存器：真正的模式值在像素域数出来，不从跨域电平直接取"
INLINE[1198] = "  // 回卷事件优先处理：强制回 0，纠正漏计数造成的错位"
INLINE[1205] = "  // 再打一拍：与像素数据/坐标的第二级流水对齐，供组合逻辑取字形使用"
INLINE[1209] = "  // 组合取字形时实际使用的模式值"


def main():
    raw = open(SRC, 'rb').read()
    text = raw.decode('utf-8')
    if '文件      : hdmi_mixer.v' in text:
        print("ABORT: 文件头已存在，拒绝重复插入")
        return 2
    parts = text.split('\n')
    n_orig = len(parts)
    eol = ['\r' if p.endswith('\r') else '' for p in parts]

    for k in list(INSERTS.keys()) + list(INLINE.keys()):
        if not (1 <= k <= n_orig):
            print("ABORT: 行号越界", k)
            return 2

    out = []
    n_ins = 0
    n_inl = 0
    for i, line in enumerate(parts, 1):
        if i in INSERTS:
            for c in INSERTS[i]:
                out.append(c + eol[i - 1])
                n_ins += 1
        newline = line
        if i in INLINE:
            if newline.endswith('\r'):
                newline = newline[:-1] + INLINE[i] + '\r'
            else:
                newline = newline + INLINE[i]
            n_inl += 1
        out.append(newline)

    new_text = '\n'.join(out)
    open(SRC, 'wb').write(new_text.encode('utf-8'))
    print("inserted comment lines:", n_ins, " inline comments:", n_inl)
    print("lines before:", n_orig, " after:", len(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
