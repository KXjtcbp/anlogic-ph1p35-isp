//=============================================================================
// 文件      : hdmi_mixer.v
// 模块      : hdmi_mixer
// 功能      : 把 DDR 读回的摄像头画面与 OSD 叠加后按 HDMI 时序输出。OSD 共六层，
//             优先级从低到高（后判定的覆盖先判定的；六层窗口两两不重叠）：
//               [1] 160x160 安路 Logo（取自 anlogic_logo_rom，用 ROM 的 bit24 作有效位）
//               [2] 黄色帧计数行 "安路 CNT:xxxxxx"（16x16 点阵 + 6 位十进制，
//                   COLOR_DYN_TEXT=24'hfff200）
//               [3] 亮绿色算法状态行 "MODE n"（5x7 点阵纵向放大到 10 高，
//                   COLOR_ALG_TEXT=24'h00ff88）
//               [4] 橙色 AE/AWB 遥测行（19 字符 16x16 字距，COLOR_DBG_TEXT=24'hff8000）
//               [5] 橙色 AE 决策遥测行（同色，紧接 [4] 下方一行）
//               [6] [PAR-OSD 2026-10-15] 亮青色「实时参数行」
//                   "S-CURVE ON  LSC ON  GAIN2 AE ON "（32 字符，16x16 点阵，
//                   COLOR_PAR_TEXT=24'h00e6ff），显示四个拨动开关的「已生效」状态。
//             另有 DEBUG_MODE / SHOW_DEBUG 控制的调试彩条与状态条，默认全部关闭。
// 数据通路  : (1) I_video_rd_data(24bit,DDR 读口) --打 2 拍--> S_video_data_2d
//             (2) I_video_de/last/user 计数 -> S_x/S_y --打 2 拍--> S_x_2d/S_y_2d
//             (1)(2) 汇合：用 S_x_2d/S_y_2d 逐像素算 OSD 命中(S_osd_hit)与颜色(S_osd_color)
//             -> 与 S_video_data_2d 二选一 -> 打 1 拍 -> O_hdmi_data。
//             O_video_rd_en 直接等于 I_video_de（de 有效即向 DDR 请求像素）。
//             坐标与数据的流水级数必须一致(各 2 拍)，否则叠加的字会整体错位。
// 时钟/复位 : 单时钟 I_clk（像素域），I_rst_n 低有效异步复位。跨时钟域输入共三组：
//             (a) 24 MHz 域的 I_algo_mode_tgl / I_algo_mode_wrap（1 bit 翻转信号），
//                 本模块三级同步 + 异或取沿后在像素域本地计数，见文末 [MODE-PIPE] 段；
//             (b) 24 MHz 域的准静态遥测总线 I_dbg_vals[48:0] / I_dbg2_vals[33:0]
//                 （最慢 16.7ms 变一次），本模块 2 级 FF 同步；
//             (c) [PAR-OSD 2026-10-15] 24 MHz 域的 I_par_sw[3:0]（四开关「已生效」电平，
//                 顶层 S_gain_applied 已做 10ms 去抖锁存），同样 2 级 FF 同步。
//             (b)(c) 的跨域路径由 SDC 里既有的
//             `set_max_delay -datapath_only -from [get_clocks {pll_clk_24m}]
//              -to [get_clocks {HDMI_PIXEL_CLK}] 8.000` 覆盖，本次未新增任何 SDC 约束。
//             像素时钟的具体频率未能从代码确认（文件里只出现“24 MHz 域”这一处描述）。
// 依赖      : 子模块 anlogic_logo_rom（I_addr[14:0] -> O_pixel[24:0]，bit24=有效，
//             [23:0]=RGB888）与 osd_char_lib（I_char/I_row -> O_row_bits[15:0]），
//             两者的源码都不在本文件内，本文件只有例化。工程背景为安路 PH1P35MDG324 +
//             SC500CS(MIPI RAW10 1280x720@60) + HDMI，但器件型号与约束文件在本文件中
//             不可见（未能从代码确认）。
//             ※ 本文件内定义的字形函数只有 F_alg_char_bits 真正被调用（:1084-:1087 与 :1095-:1097）；
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
//   2026-10-15  [PAR-OSD] 新增第 6 层「实时参数行」：新端口 I_par_sw[3:0]（接顶层
//               S_gain_applied，24MHz 域已去抖锁存的那份），模块内 2 级 FF 同步 +
//               5 个字符码预译码寄存器，复用唯一的 osd_char_lib 例化（不新增 ROM/ERAM），
//               窗口 (176,200) 512x16、亮青 COLOR_PAR_TEXT=24'h00e6ff。文本依次为
//               "S-CURVE ON / OFF"、"LSC ON / OFF"、"GAIN2 / GAIN1"、"AE ON / OFF"。
//               仅用到已有字形 + osd_char_lib 本次补的 '-'；无乘法器、无新增 SDC。
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
//---- 模块接口与参数（parameter / port） ----
module hdmi_mixer #(
    parameter H_OFFSET = 128,  // 画面几何参数：H_OFFSET=横向偏移 128、V_OFFSET=纵向偏移 60、IMG_WIDTH/HEIGHT=1280x720；本模块体内未引用这 4 个参数（保留给上层覆盖），其最终作用点未能从本文件确认
    parameter V_OFFSET = 60,
    parameter IMG_WIDTH = 1280,
    parameter IMG_HEIGHT = 720,
    parameter integer DEBUG_MODE = 0,  // 调试模式选择：0=正常显示（画面+OSD，默认）；1=8 条等宽竖彩条；2=按 I_debug_status 出整屏纯色；3=4 段状态条
    // [DBG] 置 1 时，在画面左侧画出 4 根状态条，直接看 I_debug_status 的 4 个 bit：
    //   bit0 = video_in 正在往 DDR 写      (S_vi_ddr_wr_en)
    //   bit1 = video_out 正在从 DDR 读     (S_vo_ddr_rd_en)
    //   bit2 = DDR 读返回 valid            (S_ddr_user_rd_valid)
    //   bit3 = DDR 读回的数据非零          (|S_ddr_user_rd_data)
    //   亮绿 = 该 bit 为 1，暗红 = 为 0
    //   —— 原工程把 S_hdmi_debug_status 声明了却没有引到任何引脚/LED，
    //      所以早期"用 DEBUG_MODE=3 看四格"的方案在上板时根本没输出。
    //      这个参数把状态直接画进 HDMI 画面，不需要任何额外工具。
    parameter integer SHOW_DEBUG = 0  // 0=关闭；非 0 时在画面最左侧 x=0..5 画 4 根竖条，直接观察 I_debug_status 的 4 个 bit（见 :1210）
)(
    input wire        I_clk,  // 像素时钟：本模块唯一时钟，所有时序逻辑都由它驱动
    input wire        I_rst_n,  // 异步复位，低有效

    input wire        I_video_vsync,  // 视频场同步（来自 video_in 侧，只做 2 拍延迟后转发）
    input wire        I_video_hsync,  // 视频行同步
    input wire        I_video_de,  // 数据有效：既是像素有效标志，也是 DDR 读请求的源头（见 :701 的 assign）
    input wire        I_video_user,  // 帧起始脉冲：把坐标归零，并让帧计数器 +1
    input wire        I_video_last,  // 行末标志：一行的最后一个有效像素

    input wire[3:0]   I_debug_status,  // 4 bit 调试状态：bit0=DDR 正在写、bit1=DDR 正在读、bit2=读返回 valid、bit3=读回数据非零；仅 DEBUG_MODE=2/3 或 SHOW_DEBUG!=0 时使用

    // [OUR ALGO] 自研算法模式（3 bit = 5 种：0 直通/1 灰度/2 伪彩/3 二值/4 卡通），
    //   用于在画面显示 "MODE n"。
    //   注意跨时钟域协议：24 MHz 域只送出「变了没有」的 1 bit 翻转信号，
    //   本模块在像素域同步它、在本地数模式。详见模块末尾的 [MODE-PIPE] 段。
    input wire        I_algo_mode_tgl,  // 24 MHz 域送来的“模式已改变”翻转位（是 1 bit 翻转事件，不是模式值本身）
    // [OUR ALGO] 回卷翻转线：模式由 4 回到 0 时翻转一次（单 bit，跨域同 tgl）
    input wire        I_algo_mode_wrap,  // 回卷翻转位：模式由 4 回到 0 时翻转一次，用于纠正本地偶发漏计数

    // [HDR-2026-10-12k] 遥测总线（49bit，来自 24MHz/ISP 域的准静态诊断量）。
    //   打包格式（LSB 起）：
    //     [15:0]  = AWB 实际在用的 B 通道增益 [19:4]（0x1000 = 1.000x）
    //     [31:16] = AWB 实际在用的 R 通道增益 [19:4]
    //     [39:32] = AE 本帧实测帧均值
    //     [41:40] = AE 状态（0=等表 1=稳定计时 2=闭环 3=冻结）
    //     [48:42] = AE 当前模拟增益索引 0..127
    //   最慢 16.7ms 才变一次，远慢于像素时钟 ⇒ 内部 2 级 FF 同步即可，不需要握手。
    input wire [48:0] I_dbg_vals,
    input wire [33:0] I_dbg2_vals,       // [HDR-2026-10-12m] 第二行遥测：AE 决策内部量
    // [HDR-2026-10-15] 运动检测 OSD：16 列 x 9 行块掩码 + 计数
    input wire [143:0] I_mot_mask,
    input wire [7:0]   I_mot_cnt,
    input wire         I_mot_en,   // 0 = 整层不显示（SW3 关）
    input wire [143:0] I_obj_mask, // [HDR-2026-10-17] 颜色目标检测块掩码
    input wire [7:0]   I_obj_cnt,  // [HDR-2026-10-17] 命中块数

    // [PAR-OSD 2026-10-15] 第 6 层「实时参数行」的输入：四个拨动开关的「已生效」电平。
    //   ★位序与顶层 S_gain_applied 的拼接顺序严格一致★：
    //     [3]=SW1(LSC 旁路) [2]=SW2(S 曲线旁路) [1]=SW3(数字增益) [0]=SW4(AE 使能)；1 = 拨下。
    //     （顶层是 `S_gain_applied <= {S_sw1_sync1, S_sw2_sync1, S_sw3_sync1, S_sw4_sync1};`
    //       即拼接最左 = 最高位 = SW1；改写本模块的译码位时必须同步改这里。）
    //   ★不直接接 S_sw?_sync1★：那四位分属 60MHz(MIPI_RX_BYTE_CLK) 与 24MHz 两个域，
    //   而顶层的 S_gain_applied 已经在 24MHz 域内合并、并做了 10ms 去抖锁存，
    //   跨域点只有这一处（准静态，最慢 10ms 变一次）。
    input wire [3:0]  I_par_sw,

    output wire       O_video_rd_en,  // DDR 读请求使能：直接跟随 I_video_de
    input wire[23:0]  I_video_rd_data,  // DDR 读回的 24bit 像素（RGB888），进入 2 拍流水后参与叠加

    output reg        O_hdmi_vsync,  // HDMI 输出场同步（S_video_vsync_2d 打拍而来）
    output reg        O_hdmi_hsync,  // HDMI 输出行同步
    output reg        O_hdmi_de,  // HDMI 输出数据有效
    output reg[23:0]  O_hdmi_data  // HDMI 输出像素：正常时为 OSD 覆盖后的画面，调试模式下为彩条/状态条
);

//---- 视频时序与像素数据流水寄存器（各 2 拍） ----
    reg        S_video_vsync_1d;  // 时序与数据各打 2 拍：让输出与 OSD 判定用的 S_x_2d/S_y_2d 处在同一像素时刻
    reg        S_video_vsync_2d;
    reg        S_video_hsync_1d;
    reg        S_video_hsync_2d;
    reg        S_video_de_1d;
    reg        S_video_de_2d;
    reg [23:0] S_video_data_1d;  // 像素数据第 1 拍
    reg [23:0] S_video_data_2d;
    reg [11:0] S_x;  // 当前像素坐标：de 期间自增，行末回卷（见 :717-:730 的计数逻辑）
    reg [11:0] S_y;
    reg [11:0] S_x_1d;  // 坐标第 1 拍（与 S_video_data_1d 对齐）
    reg [11:0] S_x_2d;  // 坐标第 2 拍：OSD 组合逻辑实际使用的坐标
    reg [11:0] S_y_1d;
    reg [11:0] S_y_2d;

//---- 跨时钟域(CDC)总述：算法模式（具体实现见文末 [MODE-PIPE] 段） ----
    //------------------------------------------------------------------
    // [CDC] 算法模式的跨时钟域处理已移到本模块末尾的 [MODE-PIPE] 段：
    //   24 MHz 域那边只送 1 bit 翻转信号(I_algo_mode_tgl)，本模块
    //   在像素域同步它并本地计数出 S_algo_mode / S_algo_mode_2d。
    //   历史教训（都实测过，写在模块末尾）：
    //     - 把 I_algo_mode 直接进组合云 -> SWNS 由 +0.103ns 掉到 -4.416ns；
    //     - 只加 2 级同步器打电平 -> 仍剩 -0.085ns / 2 个违例端点。
    //------------------------------------------------------------------

//---- OSD 内部信号 ----
//   命名约定：S_logo_* = Logo 层；S_dyn_*/S_dec_digit_* = 黄色 CNT 行；
//   S_pf_* = 统一 16x16 字符库取字形通路；S_alg_* = 绿色 MODE 状态行。
//   ※ S_char_*/S_cn_*/S_lbl_*/S_dyn_char|col|row|bits|seg/S_logo_red_* 等一批信号
//     只在 always @(*) 的默认赋值里出现、没有任何读取点，属历史遗留（见行内注释）。
    reg        S_osd_hit;  // 该像素是否被任意一层 OSD 命中（组合逻辑结果）
    reg [23:0] S_osd_color;  // 命中时使用的颜色（RGB888）
    reg [11:0] S_logo_x;
    reg [11:0] S_logo_y;
    reg [3:0]  S_char_idx;  // S_char_idx..S_char_on：早期通用字符扫描用的信号，已无读取点（只被 :807-:811 赋默认值，位于 :800 起的 always @(*) 内）
    reg [2:0]  S_char_row;
    reg [2:0]  S_char_col;
    reg [4:0]  S_char_bits;
    reg        S_char_on;
    reg        S_logo_blue_on;
    reg        S_logo_red_on;
    reg [11:0] S_logo_tmp_y;
    reg [3:0]  S_logo_red_band;
    reg [11:0] S_logo_red_x_start;
    reg [11:0] S_logo_red_x_end;
    reg [14:0] S_logo_addr;  // Logo ROM 地址（线性地址 = 局部 y*LOGO_W + 局部 x，见 :866）
    wire[24:0] S_logo_pixel;
    reg [31:0] S_frame_cnt;  // 帧计数器：每帧 +1 持续累加；显示只取它的 6 位十进制拆分结果
    reg [11:0] S_dyn_x;
    reg [11:0] S_dyn_y;
    reg [3:0]  S_dyn_char;
    reg [2:0]  S_dyn_col;
    reg [2:0]  S_dyn_row;
    reg [4:0]  S_dyn_bits;
    reg        S_dyn_on;
    reg [3:0]  S_dyn_digit_idx;
    reg [11:0] S_dyn_digit_x;
    reg [6:0]  S_dyn_seg;
    reg [3:0]  S_dec_digit_0;  // 6 位十进制数字：_0 是最低位、_5 是最高位；屏上从左到右显示 _5.._0（见 :746 起的帧起始进位链）
    reg [3:0]  S_dec_digit_1;
    reg [3:0]  S_dec_digit_2;
    reg [3:0]  S_dec_digit_3;
    reg [3:0]  S_dec_digit_4;
    reg [3:0]  S_dec_digit_5;
    reg [2:0]  S_lbl_row;
    reg [2:0]  S_lbl_col;
    reg [1:0]  S_lbl_idx;
    reg [4:0]  S_lbl_bits;
    reg [6:0]  S_lbl_local_x;
    reg [3:0]  S_dyn_dec_digit;
    reg [4:0]  S_cn_local_x;
    reg [4:0]  S_cn_local_y;
    reg [3:0]  S_cn_col;
    reg [3:0]  S_cn_row;
    reg [15:0] S_cn_row_bits;  // S_cn_*/S_lbl_*/S_dyn_char|col|row|bits|seg/S_logo_red_* 系列只在组合块里被赋默认值、从未被读取（历史遗留）
    reg        S_cn_on;
    reg [9:0]  S_cn_scale_x;
    reg [9:0]  S_cn_scale_y;
    reg [7:0]  S_pf_char;
    reg [4:0]  S_pf_local_x;
    reg [4:0]  S_pf_local_y;
    reg [3:0]  S_pf_col;
    reg [3:0]  S_pf_row;
    wire [15:0] S_pf_row_bits;
    reg        S_pf_on;
    reg [9:0]  S_pf_scale_x;
    reg [9:0]  S_pf_scale_y;

//---- 算法状态行 "MODE n" 中间信号 ----
    //--------------------------------------------------------------------------
    // [OUR ALGO] 算法状态行 "MODE n" 的中间信号
    //   所有运算都在 S_x_2d / S_y_2d 与 S_video_data_2d 同一级流水上，
    //   直接复用 OSD 的 2 拍延迟，不额外增加流水级数（时序安全）
    //--------------------------------------------------------------------------
    reg [11:0] S_alg_x;
    reg [11:0] S_alg_y;
    reg [2:0]  S_alg_idx;
    reg [3:0]  S_alg_lx;
    reg [3:0]  S_alg_ly;
    reg [4:0]  S_alg_bits;
    reg        S_alg_on;
    reg [2:0]  S_algo_mode_2d;      // 提前声明：像素域本地模式值（字形表要用）

//---- OSD 窗口坐标与颜色常量 ----
    localparam LOGO_X = 12'd0;  // Logo 窗口：左上角 (0,0)，宽高各 160
    localparam LOGO_Y = 12'd0;
    localparam LOGO_W = 12'd160;
    localparam LOGO_H = 12'd160;

    localparam COLOR_LOGO_BLUE   = 24'h1f315c;  // Logo 装饰色 COLOR_LOGO_BLUE/COLOR_LOGO_RED：当前无任何引用点（历史遗留，未参与实际绘制）
    localparam COLOR_LOGO_RED    = 24'hec1c2d;
    localparam COLOR_TEXT        = 24'h00e6ff;  // COLOR_TEXT：当前无任何引用点（历史遗留）
    localparam DYN_OSD_X         = 12'd375;  // 黄色 CNT 行窗口：左上 (375,120)，宽 200 = 前缀区 108 + 数字区 90 + 余量，高 24
    localparam DYN_OSD_Y         = 12'd120;
    localparam DYN_OSD_W         = 12'd200;
    localparam DYN_OSD_H         = 12'd24;
    localparam CN_Y_OFFSET       = 12'd2;  // 标签/汉字字形在 24 高窗口内的纵向起点偏移（上下各留 2 像素余量）
    localparam COLOR_DYN_TEXT    = 24'hfff200;  // 黄色字色（RGB888）：屏上“安路 CNT:”那一行用的就是它
    localparam CHAR_AN           = 8'h80;  // 以下 CHAR_* 是 16x16 字符库的字符码：0x80='安'、0x81='路'，其余直接用 ASCII（'C'=0x43 …）
    localparam CHAR_LU           = 8'h81;
    localparam CHAR_C            = 8'h43;
    localparam CHAR_N            = 8'h4e;
    localparam CHAR_T            = 8'h54;
    localparam CHAR_0            = 8'h30;  // '0' 的 ASCII 码：数字的字符码 = CHAR_0 + 数字值（见 :1028）
    localparam CHAR_COLON        = 8'h3a;  // ':' 的 ASCII 码

//---- 算法状态行 OSD 常量（本工程在基线之上新增） ----
    //--------------------------------------------------------------------------
    // [OUR ALGO] 算法状态行 OSD 常量
    //   内容固定为 "MODE <n>"，n = S_algo_mode_2d，共 6 个字符
    //   每个字符 8x10（字形 5x7 直接放大到 10 高），字距 14 像素
    //   位置 (176,176)：在 160x160 安路 Logo 下方右侧，不与 Logo(0,0)-(160,160)
    //   和动态 CNT 区(375,120)-(575,144) 重叠
    //--------------------------------------------------------------------------
    localparam ALG_OSD_X      = 12'd176;  // 绿色状态行窗口：左上 (176,176)，宽 84 = 6 字符 x 14 字距，高 10（5x7 字形纵向放大到 10）
    localparam ALG_OSD_Y      = 12'd176;
    localparam ALG_OSD_W      = 12'd84;    // 6 字符 x 14
    localparam ALG_OSD_H      = 12'd10;
    localparam COLOR_ALG_TEXT = 24'h00ff88; // 亮绿色，和黄色 CNT、青色 Logo 字都区分得开

//---- [HDR-2026-10-12k] 第 4 行：橙色遥测行（诊断用，功能做完可以整块删掉） ----
    //--------------------------------------------------------------------------
    // 内容 19 个字符，全部用同一套 5x7 字形放大：
    //     "AExxSxMxxWxxxxBxxxx"
    //      A E <增益索引2位> S<状态1位> M<实测均值2位> W<R增益4位> B<B增益4位>
    //   例：AE7FS2M46W10531000  ⇒ 增益档 0x7F、状态 2=闭环、实测均值 0x46(=70)、
    //                            AWB 的 R 增益 0x1053(=1.020x)、B 增益 0x1000(=1.000x)
    //   位置 (376,152)-(679,161)：在 Logo(0,0)-(159,159) 右侧、CNT 行(375,120)-(574,143)
    //   下方、MODE 行(176,176)-(259,185) 右上，三者都不重叠。
    //   颜色橙色 0xff8000，与黄色 CNT、亮绿 MODE、青色 Logo 都能分开。
    //--------------------------------------------------------------------------
    localparam DBG_OSD_X      = 12'd376;
    localparam DBG_OSD_Y      = 12'd152;
    localparam DBG_OSD_W      = 12'd304;   // 19 字符 x 16 字距
    localparam DBG_OSD_H      = 12'd10;    // 字形 7 行，窗口留 10
    localparam COLOR_DBG_TEXT = 24'hff8000; // 橙色
    localparam COLOR_MOT_TEXT = 24'hff2020; // 运动块描边红
localparam COLOR_OBJ_TEXT = 24'h00ff40; // [HDR-2026-10-17] 目标检测框绿

    reg [48:0] S_dbg_1d;   // 遥测总线 2 级同步（准静态信号，无需握手）
    reg [48:0] S_dbg_2d;
    reg [33:0] S_dbg2_1d;             // [HDR-2026-10-12m] 第二行遥测同步链
    reg [33:0] S_dbg2_2d;
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            S_dbg_1d <= 49'd0;
            S_dbg_2d <= 49'd0;
            S_dbg2_1d <= 34'd0;
            S_dbg2_2d <= 34'd0;
        end
        else begin
            S_dbg_1d <= I_dbg_vals;
            S_dbg_2d <= S_dbg_1d;
            S_dbg2_1d <= I_dbg2_vals;
            S_dbg2_2d <= S_dbg2_1d;
        end
    end

    wire [6:0]  S_dbg_gi = S_dbg_2d[48:42];  // AE 模拟增益索引 0..127
    wire [1:0]  S_dbg_st = S_dbg_2d[41:40];  // AE 状态
    wire [7:0]  S_dbg_ml = S_dbg_2d[39:32];  // AE 实测帧均值
    wire [15:0] S_dbg_gr = S_dbg_2d[31:16];  // AWB R 增益 [19:4]
    wire [15:0] S_dbg_gb = S_dbg_2d[15:0];   // AWB B 增益 [19:4]

    //------------------------------------------------------------------------
    // [HDR-2026-10-12m] 第 5 层：第二行橙色遥测（AE 决策链内部量）
    //------------------------------------------------------------------------
    localparam DBG2_OSD_X     = 12'd376;
    localparam DBG2_OSD_Y     = 12'd164;   // 第一行在 152..161，MODE 在 176..185
    localparam DBG2_OSD_W     = 12'd304;   // 19 字符 x 16 字距
    localparam DBG2_OSD_H     = 12'd10;

    wire       S_d2_can = S_dbg2_2d[4];
    wire       S_d2_frm = S_dbg2_2d[3];
    wire       S_d2_req = S_dbg2_2d[2];
    wire       S_d2_aec = S_dbg2_2d[1];
    wire       S_d2_cam = S_dbg2_2d[0];
    wire [7:0] S_d2_set = S_dbg2_2d[12:5];
    wire [6:0] S_d2_nxt = S_dbg2_2d[19:13];
    wire [6:0] S_d2_dec = S_dbg2_2d[26:20];
    wire [6:0] S_d2_inc = S_dbg2_2d[33:27];
    reg [11:0] S_dbg2_x;
    reg [11:0] S_dbg2_y;
    reg [4:0]  S_dbg2_idx;
    reg [3:0]  S_dbg2_lx;
    reg [3:0]  S_dbg2_ly;
    reg [4:0]  S_dbg2_gl;
    reg [4:0]  S_dbg2_bits;
    reg        S_dbg2_on;

    reg [11:0] S_dbg_x;
    reg [11:0] S_dbg_y;
    reg [4:0]  S_dbg_idx;
    reg [3:0]  S_dbg_lx;
    reg [3:0]  S_dbg_ly;
    reg [4:0]  S_dbg_gl;
    reg [4:0]  S_dbg_bits;
    reg        S_dbg_on;
    
    // [HDR-2026-10-15] 运动块描边：块索引与块内偏移，全组合、零除法器
    reg  [4:0]  S_mot_bx;
    reg  [3:0]  S_mot_by;
    reg  [11:0] S_mot_xoff;
    reg  [11:0] S_mot_yoff;
    reg         S_mot_on;
    reg  [4:0]  S_obj_bx;   // [HDR-2026-10-17] 第 7 层：目标检测框
    reg  [3:0]  S_obj_by;
    reg  [11:0] S_obj_xoff;
    reg  [11:0] S_obj_yoff;
    reg         S_obj_on;

    // ★ [HDR-2026-10-17-bb] 只画「命中块集合的外轮廓」+ 每块内缩 10px ★
    //   原实现每个命中块都画一个 80x80 的整框 ⇒ 一片参差小框、且框比目标宽 1~3 倍。
    //   现在：只在「该块与相邻块不同时命中」的那一侧画边，并把边内缩 10px（屏幕 15px），
    //   视觉上变成一个连成一体、贴着目标轮廓的紧框。
    wire [8:0] O_self = {1'b0, S_obj_by, S_obj_bx[3:0]};
    wire [8:0] O_left = (S_obj_bx[3:0] == 4'd0 ) ? 9'h1FF : {1'b0, S_obj_by, S_obj_bx[3:0] - 4'd1};
    wire [8:0] O_rgt  = (S_obj_bx[3:0] == 4'd15) ? 9'h1FF : {1'b0, S_obj_by, S_obj_bx[3:0] + 4'd1};
    wire [8:0] O_up   = (S_obj_by      == 4'd0 ) ? 9'h1FF : {1'b0, S_obj_by - 4'd1, S_obj_bx[3:0]};
    wire [8:0] O_dn   = (S_obj_by      == 4'd8 ) ? 9'h1FF : {1'b0, S_obj_by + 4'd1, S_obj_bx[3:0]};
    wire       obj_self = I_obj_mask[O_self];
    wire       obj_lft  = (O_left == 9'h1FF) ? 1'b0 : I_obj_mask[O_left];
    wire       obj_rgt  = (O_rgt  == 9'h1FF) ? 1'b0 : I_obj_mask[O_rgt ];
    wire       obj_up   = (O_up   == 9'h1FF) ? 1'b0 : I_obj_mask[O_up  ];
    wire       obj_dn   = (O_dn   == 9'h1FF) ? 1'b0 : I_obj_mask[O_dn  ];
    wire       obj_in   = (S_obj_xoff >= 12'd10) && (S_obj_xoff <= 12'd69) &&
                          (S_obj_yoff >= 12'd10) && (S_obj_yoff <= 12'd69);

    //------------------------------------------------------------------------
    // [PAR-OSD 2026-10-15] 第 6 层：实时参数行（四个拨动开关的已生效状态 + 数字增益档）
    //   定长 32 字符，索引 0..31：
    //     0..7   "S-CURVE "        8..11  "ON  " / "OFF "
    //     12..15 "LSC "            16..19 "ON  " / "OFF "
    //     20..24 "GAIN2" / "GAIN1" 25     " "
    //     26..31 "AE ON " / "AE OFF"
    //   整行由 case(S_par_idx) 拼字；动态字符只有 7 个（idx 9/10/17/18/24/30/31），
    //   它们单独用寄存器预译码（S_par_c*），使像素域关键路径里只剩
    //   「坐标 -> 字符码 mux -> osd_char_lib -> 16 选 1 列选」，与既有黄色 CNT 行同深度。
    //------------------------------------------------------------------------
    localparam PAR_OSD_X      = 12'd176;
    localparam PAR_OSD_Y      = 12'd200;
    localparam PAR_OSD_W      = 12'd512;    // 32 字符 x 16 字距
    localparam PAR_OSD_H      = 12'd16;
    localparam COLOR_PAR_TEXT = 24'h00e6ff; // 亮青（= 本文件历史遗留常量 COLOR_TEXT 的取值，与黄/绿/橙都不撞）

    reg [3:0] S_par_sw_1d;   // I_par_sw 的 2 级同步（准静态信号，做法同 I_dbg_vals）
    reg [3:0] S_par_sw_2d;
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            S_par_sw_1d <= 4'b1111;   // 复位 = 与顶层 S_gain_applied 的复位值一致（四开关全「下」）
            S_par_sw_2d <= 4'b1111;
        end
        else begin
            S_par_sw_1d <= I_par_sw;
            S_par_sw_2d <= S_par_sw_1d;
        end
    end

    // 7 个动态字符的预译码：只在开关变化那一拍更新，不参与像素坐标路径
    reg [7:0] S_par_c9;    // "S-CURVE ON/OFF" 的 'N' / 'F'
    reg [7:0] S_par_c10;   // "S-CURVE ON/OFF" 的 ' ' / 'F'
    reg [7:0] S_par_c17;   // "LSC ON/OFF" 的 'N' / 'F'
    reg [7:0] S_par_c18;   // "LSC ON/OFF" 的 ' ' / 'F'
    reg [7:0] S_par_c24;   // "GAIN2" / "GAIN1"
    reg [7:0] S_par_c30;   // "AE ON/OFF" 的 'N' / 'F'
    reg [7:0] S_par_c31;   // "AE ON/OFF" 的 ' ' / 'F'（"OFF" 的第 3 个字符）
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            S_par_c9  <= 8'h4e;   // 'N'
            S_par_c10 <= 8'h20;   // 空格
            S_par_c17 <= 8'h4e;   // 'N'
            S_par_c18 <= 8'h20;   // 空格
            S_par_c24 <= 8'h30;   // '0'  [PAR-OSD 改] 复位默认 MOT OFF
            S_par_c30 <= 8'h20;   // ' '  [PAR-OSD 改]
            S_par_c31 <= 8'h4c;   // 'L'  [PAR-OSD 改] 复位默认宽松档
        end
        else begin
            S_par_c9  <= S_par_sw_2d[2] ? 8'h46 : 8'h4e;   // SW2 拨下 = S 曲线旁路 = OFF
            S_par_c10 <= S_par_sw_2d[2] ? 8'h46 : 8'h20;
            S_par_c17 <= S_par_sw_2d[3] ? 8'h46 : 8'h4e;   // SW1 拨下 = LSC 直通 = OFF
            S_par_c18 <= S_par_sw_2d[3] ? 8'h46 : 8'h20;
            S_par_c24 <= S_par_sw_2d[1] ? 8'h30 : 8'h31;   // [PAR-OSD 改] SW3 拨下=逻辑 1=运动检测关='0'
            S_par_c30 <= 8'h20;   // [PAR-OSD 改] 固定空格
            S_par_c31 <= S_par_sw_2d[0] ? 8'h4c : 8'h48;   // [PAR-OSD 改] SW4 拨下=宽松='L'
        end
    end

    reg [4:0]  S_par_idx;   // 字符位 0..31
    reg [3:0]  S_par_col;   // 字形列 0..15（bit15 = 该行最左列）
    reg [3:0]  S_par_row;   // 字形行 0..15

    // 遥测行专用字形库：0..9 = '0'..'9'，10..15 = 'A'..'F'，16='M' 17='S' 18='W'，
    //   其余（含空格）= 全 0。
    //   每个字形 35bit = 7 行 x 5 列，行 0 在 bit[34:30]，行 6 在 bit[4:0]，
    //   每行 bit[4] 是最左列（与 F_alg_char_bits 的约定一致）。
    function [34:0] F_dbg_glyph;
        input [4:0] I_c;
        begin
            case(I_c)
                5'd0 : F_dbg_glyph = 35'b01110_10001_10001_10001_10001_10001_01110; // 0
                5'd1 : F_dbg_glyph = 35'b00100_01100_00100_00100_00100_00100_01110; // 1
                5'd2 : F_dbg_glyph = 35'b01110_10001_00001_00010_00100_01000_11111; // 2
                5'd3 : F_dbg_glyph = 35'b11111_00010_00100_00010_00001_10001_01110; // 3
                5'd4 : F_dbg_glyph = 35'b00010_00110_01010_10010_11111_00010_00010; // 4
                5'd5 : F_dbg_glyph = 35'b11111_10000_11110_00001_00001_10001_01110; // 5
                5'd6 : F_dbg_glyph = 35'b00110_01000_10000_11110_10001_10001_01110; // 6
                5'd7 : F_dbg_glyph = 35'b11111_00001_00010_00100_01000_01000_01000; // 7
                5'd8 : F_dbg_glyph = 35'b01110_10001_10001_01110_10001_10001_01110; // 8
                5'd9 : F_dbg_glyph = 35'b01110_10001_10001_01111_00001_00010_01100; // 9
                5'd10: F_dbg_glyph = 35'b01110_10001_10001_11111_10001_10001_10001; // A
                5'd11: F_dbg_glyph = 35'b11110_10001_10001_11110_10001_10001_11110; // B
                5'd12: F_dbg_glyph = 35'b01111_10000_10000_10000_10000_10000_01111; // C
                5'd13: F_dbg_glyph = 35'b11110_10001_10001_10001_10001_10001_11110; // D
                5'd14: F_dbg_glyph = 35'b11111_10000_10000_11110_10000_10000_11111; // E
                5'd15: F_dbg_glyph = 35'b11111_10000_10000_11110_10000_10000_10000; // F
                5'd16: F_dbg_glyph = 35'b10001_11011_10101_10001_10001_10001_10001; // M
                5'd17: F_dbg_glyph = 35'b01111_10000_10000_01110_00001_00001_11110; // S
                5'd18: F_dbg_glyph = 35'b10001_10001_10001_10101_10101_11011_10001; // W
                    5'd19: F_dbg_glyph = 35'b11111_00100_00100_00100_00100_00100_00100; // T
                    5'd20: F_dbg_glyph = 35'b10001_11001_11001_10101_10011_10001_10001; // N
                    5'd21: F_dbg_glyph = 35'b10001_10001_10001_10001_10001_10001_01110; // U
                default: F_dbg_glyph = 35'b00000_00000_00000_00000_00000_00000_00000; // 空格
            endcase
        end
    endfunction

    // 取某个字形在第 I_row(0..6) 行上的 5bit 点阵（用固定分段，避免综合出桶形移位器）
    function [4:0] F_dbg_rowbits;
        input [4:0] I_c;
        input [2:0] I_row;
        reg [34:0] g;
        begin
            g = F_dbg_glyph(I_c);
            case(I_row)
                3'd0:    F_dbg_rowbits = g[34:30];
                3'd1:    F_dbg_rowbits = g[29:25];
                3'd2:    F_dbg_rowbits = g[24:20];
                3'd3:    F_dbg_rowbits = g[19:15];
                3'd4:    F_dbg_rowbits = g[14:10];
                3'd5:    F_dbg_rowbits = g[9:5];
                default: F_dbg_rowbits = g[4:0];
            endcase
        end
    endfunction

//---- 字形库 A：Logo 文字 A/N/L/O/G/I/C（5x7 点阵） ----
//   ※ 当前没有任何调用点：Logo 图形由 anlogic_logo_rom 子模块给出，本函数属保留代码。
    function [4:0] F_logo_text_bits;  // 取字形：I_char 选字符、I_row(0..6) 选行；返回值 5 bit，bit[4] = 最左列
        input [3:0] I_char;
        input [2:0] I_row;
        begin
            case(I_char)
                4'd0: begin
                    case(I_row) // A
                        3'd0: F_logo_text_bits = 5'b01110;
                        3'd1: F_logo_text_bits = 5'b10001;
                        3'd2: F_logo_text_bits = 5'b10001;
                        3'd3: F_logo_text_bits = 5'b11111;
                        3'd4: F_logo_text_bits = 5'b10001;
                        3'd5: F_logo_text_bits = 5'b10001;
                        3'd6: F_logo_text_bits = 5'b10001;
                        default: F_logo_text_bits = 5'b00000;
                    endcase
                end
                4'd1: begin
                    case(I_row) // N
                        3'd0: F_logo_text_bits = 5'b10001;
                        3'd1: F_logo_text_bits = 5'b11001;
                        3'd2: F_logo_text_bits = 5'b10101;
                        3'd3: F_logo_text_bits = 5'b10011;
                        3'd4: F_logo_text_bits = 5'b10001;
                        3'd5: F_logo_text_bits = 5'b10001;
                        3'd6: F_logo_text_bits = 5'b10001;
                        default: F_logo_text_bits = 5'b00000;
                    endcase
                end
                4'd2: begin
                    case(I_row) // L
                        3'd0: F_logo_text_bits = 5'b10000;
                        3'd1: F_logo_text_bits = 5'b10000;
                        3'd2: F_logo_text_bits = 5'b10000;
                        3'd3: F_logo_text_bits = 5'b10000;
                        3'd4: F_logo_text_bits = 5'b10000;
                        3'd5: F_logo_text_bits = 5'b10000;
                        3'd6: F_logo_text_bits = 5'b11111;
                        default: F_logo_text_bits = 5'b00000;
                    endcase
                end
                4'd3: begin
                    case(I_row) // O
                        3'd0: F_logo_text_bits = 5'b01110;
                        3'd1: F_logo_text_bits = 5'b10001;
                        3'd2: F_logo_text_bits = 5'b10001;
                        3'd3: F_logo_text_bits = 5'b10001;
                        3'd4: F_logo_text_bits = 5'b10001;
                        3'd5: F_logo_text_bits = 5'b10001;
                        3'd6: F_logo_text_bits = 5'b01110;
                        default: F_logo_text_bits = 5'b00000;
                    endcase
                end
                4'd4: begin
                    case(I_row) // G
                        3'd0: F_logo_text_bits = 5'b01110;
                        3'd1: F_logo_text_bits = 5'b10001;
                        3'd2: F_logo_text_bits = 5'b10000;
                        3'd3: F_logo_text_bits = 5'b10111;
                        3'd4: F_logo_text_bits = 5'b10001;
                        3'd5: F_logo_text_bits = 5'b10001;
                        3'd6: F_logo_text_bits = 5'b01110;
                        default: F_logo_text_bits = 5'b00000;
                    endcase
                end
                4'd5: begin
                    case(I_row) // I
                        3'd0: F_logo_text_bits = 5'b11111;
                        3'd1: F_logo_text_bits = 5'b00100;
                        3'd2: F_logo_text_bits = 5'b00100;
                        3'd3: F_logo_text_bits = 5'b00100;
                        3'd4: F_logo_text_bits = 5'b00100;
                        3'd5: F_logo_text_bits = 5'b00100;
                        3'd6: F_logo_text_bits = 5'b11111;
                        default: F_logo_text_bits = 5'b00000;
                    endcase
                end
                4'd6: begin
                    case(I_row) // C
                        3'd0: F_logo_text_bits = 5'b01110;
                        3'd1: F_logo_text_bits = 5'b10001;
                        3'd2: F_logo_text_bits = 5'b10000;
                        3'd3: F_logo_text_bits = 5'b10000;
                        3'd4: F_logo_text_bits = 5'b10000;
                        3'd5: F_logo_text_bits = 5'b10001;
                        3'd6: F_logo_text_bits = 5'b01110;
                        default: F_logo_text_bits = 5'b00000;
                    endcase
                end
                default: F_logo_text_bits = 5'b00000;
            endcase
        end
    endfunction

//---- 字形库 B：十六进制 7 段译码表（{a,b,c,d,e,f,g}，bit6..bit0） ----
//   ※ 当前没有任何调用点，属保留代码。
    // 7-seg bit mapping: {a,b,c,d,e,f,g}
    function [6:0] F_hex7seg;  // 位序约定 {a,b,c,d,e,f,g} 对应 bit6..bit0；当前无调用点
        input [3:0] I_hex;
        begin
            case(I_hex)
                4'h0: F_hex7seg = 7'b1111110;
                4'h1: F_hex7seg = 7'b0110000;
                4'h2: F_hex7seg = 7'b1101101;
                4'h3: F_hex7seg = 7'b1111001;
                4'h4: F_hex7seg = 7'b0110011;
                4'h5: F_hex7seg = 7'b1011011;
                4'h6: F_hex7seg = 7'b1011111;
                4'h7: F_hex7seg = 7'b1110000;
                4'h8: F_hex7seg = 7'b1111111;
                4'h9: F_hex7seg = 7'b1111011;
                4'ha: F_hex7seg = 7'b1110111;
                4'hb: F_hex7seg = 7'b0011111;
                4'hc: F_hex7seg = 7'b1001110;
                4'hd: F_hex7seg = 7'b0111101;
                4'he: F_hex7seg = 7'b1001111;
                4'hf: F_hex7seg = 7'b1000111;
                default: F_hex7seg = 7'b0000000;
            endcase
        end
    endfunction

//---- 字形库 C："CNT:" 标签字母（5x7） ----
//   ※ 当前没有任何调用点（实际字形由 osd_char_lib 子模块给出），属保留代码。
    function [4:0] F_cnt_label_bits;  // I_idx: 0='C'、1='N'、2='T'、3=':'（即屏上 “CNT:” 标签的 4 个字符位）
        input [1:0] I_idx;
        input [2:0] I_row;
        begin
            case(I_idx)
                2'd0: begin // C
                    case(I_row)
                        3'd0: F_cnt_label_bits = 5'b01110;
                        3'd1: F_cnt_label_bits = 5'b10001;
                        3'd2: F_cnt_label_bits = 5'b10000;
                        3'd3: F_cnt_label_bits = 5'b10000;
                        3'd4: F_cnt_label_bits = 5'b10000;
                        3'd5: F_cnt_label_bits = 5'b10001;
                        3'd6: F_cnt_label_bits = 5'b01110;
                        default: F_cnt_label_bits = 5'b00000;
                    endcase
                end
                2'd1: begin // N
                    case(I_row)
                        3'd0: F_cnt_label_bits = 5'b10001;
                        3'd1: F_cnt_label_bits = 5'b11001;
                        3'd2: F_cnt_label_bits = 5'b10101;
                        3'd3: F_cnt_label_bits = 5'b10011;
                        3'd4: F_cnt_label_bits = 5'b10001;
                        3'd5: F_cnt_label_bits = 5'b10001;
                        3'd6: F_cnt_label_bits = 5'b10001;
                        default: F_cnt_label_bits = 5'b00000;
                    endcase
                end
                2'd2: begin // T
                    case(I_row)
                        3'd0: F_cnt_label_bits = 5'b11111;
                        3'd1: F_cnt_label_bits = 5'b00100;
                        3'd2: F_cnt_label_bits = 5'b00100;
                        3'd3: F_cnt_label_bits = 5'b00100;
                        3'd4: F_cnt_label_bits = 5'b00100;
                        3'd5: F_cnt_label_bits = 5'b00100;
                        3'd6: F_cnt_label_bits = 5'b00100;
                        default: F_cnt_label_bits = 5'b00000;
                    endcase
                end
                default: begin // ':'
                    case(I_row)
                        3'd2: F_cnt_label_bits = 5'b00100;
                        3'd5: F_cnt_label_bits = 5'b00100;
                        default: F_cnt_label_bits = 5'b00000;
                    endcase
                end
            endcase
        end
    endfunction

//---- 字形库 D：汉字 "安" / "路" 16x16 点阵 ----
//   ※ 当前没有任何调用点，属保留代码。
    // Minimal 16x16 Chinese bitmap rows for "an" and "lu".
    function [15:0] F_cn16_row;  // I_char=0 为“安”、1 为“路”；每行 16 bit 中 bit[15] 是最左像素
        input I_char; // 0: an, 1: lu
        input [3:0] I_row;
        begin
            if(!I_char) begin
                case(I_row)
                    4'd0:  F_cn16_row = 16'h0200;
                    4'd1:  F_cn16_row = 16'h7ff0;
                    4'd2:  F_cn16_row = 16'h4410;
                    4'd3:  F_cn16_row = 16'h0400;
                    4'd4:  F_cn16_row = 16'h7ff0;
                    4'd5:  F_cn16_row = 16'h0840;
                    4'd6:  F_cn16_row = 16'h1040;
                    4'd7:  F_cn16_row = 16'h1c80;
                    4'd8:  F_cn16_row = 16'h0300;
                    4'd9:  F_cn16_row = 16'h0cc0;
                    4'd10: F_cn16_row = 16'h7020;
                    4'd11: F_cn16_row = 16'h0000;
                    4'd12: F_cn16_row = 16'h0000;
                    4'd13: F_cn16_row = 16'h0000;
                    4'd14: F_cn16_row = 16'h0000;
                    4'd15: F_cn16_row = 16'h0000;
                    default: F_cn16_row = 16'h0000;
                endcase
            end
            else begin
                case(I_row)
                    4'd0:  F_cn16_row = 16'h79e0;
                    4'd1:  F_cn16_row = 16'h4a20;
                    4'd2:  F_cn16_row = 16'h4d40;
                    4'd3:  F_cn16_row = 16'h7880;
                    4'd4:  F_cn16_row = 16'h1140;
                    4'd5:  F_cn16_row = 16'h1630;
                    4'd6:  F_cn16_row = 16'h5be0;
                    4'd7:  F_cn16_row = 16'h5220;
                    4'd8:  F_cn16_row = 16'h5220;
                    4'd9:  F_cn16_row = 16'h5be0;
                    4'd10: F_cn16_row = 16'h6220;
                    4'd11: F_cn16_row = 16'h0000;
                    4'd12: F_cn16_row = 16'h0000;
                    4'd13: F_cn16_row = 16'h0000;
                    4'd14: F_cn16_row = 16'h0000;
                    4'd15: F_cn16_row = 16'h0000;
                    default: F_cn16_row = 16'h0000;
                endcase
            end
        end
    endfunction

//---- 字形库 E：算法状态行的 'M''O''D''E' 与数字 0..3（5x7） ----
//   这是全文件唯一真正被调用的字形函数，调用点在 :1084-:1087 与 :1095-:1097。
//   ★索引 4 是数字 '0' 而不是 '4'（见 :517），这正是 MODE 4 会显示成 "MODE 0" 的根因，
//     详见 :1089 处的 BUG(待修) 注释。
    //--------------------------------------------------------------------------
    // [OUR ALGO] 算法状态行字形表（5x7 点阵，位[4] = 最左列）
    //   idx 0='M' 1='O' 2='D' 3='E' 4='0' 5='1' 6='2' 7='3' 8='4'
    //--------------------------------------------------------------------------
    function [4:0] F_alg_char_bits;  // I_char: 0='M' 1='O' 2='D' 3='E' 4='0' 5='1' 6='2' 7='3' 8='4'（'4' 是 2026-10-10 补的）
        input [3:0] I_char;
        input [3:0] I_row;
        begin
            case(I_char)
                4'd0: begin // M
                    case(I_row)
                        4'd0: F_alg_char_bits = 5'b10001;
                        4'd1: F_alg_char_bits = 5'b11011;
                        4'd2: F_alg_char_bits = 5'b10101;
                        4'd3: F_alg_char_bits = 5'b10101;
                        4'd4: F_alg_char_bits = 5'b10001;
                        4'd5: F_alg_char_bits = 5'b10001;
                        4'd6: F_alg_char_bits = 5'b10001;
                        default: F_alg_char_bits = 5'b00000;
                    endcase
                end
                4'd1: begin // O
                    case(I_row)
                        4'd0: F_alg_char_bits = 5'b01110;
                        4'd1: F_alg_char_bits = 5'b10001;
                        4'd2: F_alg_char_bits = 5'b10001;
                        4'd3: F_alg_char_bits = 5'b10001;
                        4'd4: F_alg_char_bits = 5'b10001;
                        4'd5: F_alg_char_bits = 5'b10001;
                        4'd6: F_alg_char_bits = 5'b01110;
                        default: F_alg_char_bits = 5'b00000;
                    endcase
                end
                4'd2: begin // D
                    case(I_row)
                        4'd0: F_alg_char_bits = 5'b11110;
                        4'd1: F_alg_char_bits = 5'b10001;
                        4'd2: F_alg_char_bits = 5'b10001;
                        4'd3: F_alg_char_bits = 5'b10001;
                        4'd4: F_alg_char_bits = 5'b10001;
                        4'd5: F_alg_char_bits = 5'b10001;
                        4'd6: F_alg_char_bits = 5'b11110;
                        default: F_alg_char_bits = 5'b00000;
                    endcase
                end
                4'd3: begin // E
                    case(I_row)
                        4'd0: F_alg_char_bits = 5'b11111;
                        4'd1: F_alg_char_bits = 5'b10000;
                        4'd2: F_alg_char_bits = 5'b10000;
                        4'd3: F_alg_char_bits = 5'b11110;
                        4'd4: F_alg_char_bits = 5'b10000;
                        4'd5: F_alg_char_bits = 5'b10000;
                        4'd6: F_alg_char_bits = 5'b11111;
                        default: F_alg_char_bits = 5'b00000;
                    endcase
                end
                4'd4: begin // 0
                    case(I_row)
                        4'd0: F_alg_char_bits = 5'b01110;
                        4'd1: F_alg_char_bits = 5'b10001;
                        4'd2: F_alg_char_bits = 5'b10011;
                        4'd3: F_alg_char_bits = 5'b10101;
                        4'd4: F_alg_char_bits = 5'b11001;
                        4'd5: F_alg_char_bits = 5'b10001;
                        4'd6: F_alg_char_bits = 5'b01110;
                        default: F_alg_char_bits = 5'b00000;
                    endcase
                end
                4'd5: begin // 1
                    case(I_row)
                        4'd0: F_alg_char_bits = 5'b00100;
                        4'd1: F_alg_char_bits = 5'b01100;
                        4'd2: F_alg_char_bits = 5'b00100;
                        4'd3: F_alg_char_bits = 5'b00100;
                        4'd4: F_alg_char_bits = 5'b00100;
                        4'd5: F_alg_char_bits = 5'b00100;
                        4'd6: F_alg_char_bits = 5'b01110;
                        default: F_alg_char_bits = 5'b00000;
                    endcase
                end
                4'd6: begin // 2
                    case(I_row)
                        4'd0: F_alg_char_bits = 5'b01110;
                        4'd1: F_alg_char_bits = 5'b10001;
                        4'd2: F_alg_char_bits = 5'b00001;
                        4'd3: F_alg_char_bits = 5'b00110;
                        4'd4: F_alg_char_bits = 5'b01000;
                        4'd5: F_alg_char_bits = 5'b10000;
                        4'd6: F_alg_char_bits = 5'b11111;
                        default: F_alg_char_bits = 5'b00000;
                    endcase
                end
                4'd7: begin // 3
                    case(I_row)
                        4'd0: F_alg_char_bits = 5'b11110;
                        4'd1: F_alg_char_bits = 5'b00001;
                        4'd2: F_alg_char_bits = 5'b00001;
                        4'd3: F_alg_char_bits = 5'b01110;
                        4'd4: F_alg_char_bits = 5'b00001;
                        4'd5: F_alg_char_bits = 5'b00001;
                        4'd6: F_alg_char_bits = 5'b11110;
                        default: F_alg_char_bits = 5'b00000;
                    endcase
                end
                4'd8: begin // 4   （2026-10-10 新增：MODE 4 的状态显示需要）
                    case(I_row)
                        4'd0: F_alg_char_bits = 5'b10001;   // 左竖 + 右竖
                        4'd1: F_alg_char_bits = 5'b10001;
                        4'd2: F_alg_char_bits = 5'b10001;
                        4'd3: F_alg_char_bits = 5'b01111;   // 横杠（含右竖交点）
                        4'd4: F_alg_char_bits = 5'b00001;   // 只留右竖
                        4'd5: F_alg_char_bits = 5'b00001;
                        4'd6: F_alg_char_bits = 5'b00001;
                        default: F_alg_char_bits = 5'b00000;
                    endcase
                end
                default: F_alg_char_bits = 5'b00000;
            endcase
        end
    endfunction

//---- 字形库 F：5x7 数字 0..9 与字母 a..f（动态数字绘制用） ----
//   ※ 当前没有任何调用点，属保留代码。
    function [4:0] F_dyn_char_bits;        input [3:0] I_char;  // 每行 5 bit，bit[4] 为最左列
        input [2:0] I_row;
        begin
            case(I_char)
                4'h0: begin case(I_row) 3'd0:F_dyn_char_bits=5'b01110; 3'd1:F_dyn_char_bits=5'b10001; 3'd2:F_dyn_char_bits=5'b10011; 3'd3:F_dyn_char_bits=5'b10101; 3'd4:F_dyn_char_bits=5'b11001; 3'd5:F_dyn_char_bits=5'b10001; 3'd6:F_dyn_char_bits=5'b01110; default:F_dyn_char_bits=5'b00000; endcase end
                4'h1: begin case(I_row) 3'd0:F_dyn_char_bits=5'b00100; 3'd1:F_dyn_char_bits=5'b01100; 3'd2:F_dyn_char_bits=5'b00100; 3'd3:F_dyn_char_bits=5'b00100; 3'd4:F_dyn_char_bits=5'b00100; 3'd5:F_dyn_char_bits=5'b00100; 3'd6:F_dyn_char_bits=5'b01110; default:F_dyn_char_bits=5'b00000; endcase end
                4'h2: begin case(I_row) 3'd0:F_dyn_char_bits=5'b01110; 3'd1:F_dyn_char_bits=5'b10001; 3'd2:F_dyn_char_bits=5'b00001; 3'd3:F_dyn_char_bits=5'b00110; 3'd4:F_dyn_char_bits=5'b01000; 3'd5:F_dyn_char_bits=5'b10000; 3'd6:F_dyn_char_bits=5'b11111; default:F_dyn_char_bits=5'b00000; endcase end
                4'h3: begin case(I_row) 3'd0:F_dyn_char_bits=5'b11110; 3'd1:F_dyn_char_bits=5'b00001; 3'd2:F_dyn_char_bits=5'b00001; 3'd3:F_dyn_char_bits=5'b01110; 3'd4:F_dyn_char_bits=5'b00001; 3'd5:F_dyn_char_bits=5'b00001; 3'd6:F_dyn_char_bits=5'b11110; default:F_dyn_char_bits=5'b00000; endcase end
                4'h4: begin case(I_row) 3'd0:F_dyn_char_bits=5'b00010; 3'd1:F_dyn_char_bits=5'b00110; 3'd2:F_dyn_char_bits=5'b01010; 3'd3:F_dyn_char_bits=5'b10010; 3'd4:F_dyn_char_bits=5'b11111; 3'd5:F_dyn_char_bits=5'b00010; 3'd6:F_dyn_char_bits=5'b00010; default:F_dyn_char_bits=5'b00000; endcase end
                4'h5: begin case(I_row) 3'd0:F_dyn_char_bits=5'b11111; 3'd1:F_dyn_char_bits=5'b10000; 3'd2:F_dyn_char_bits=5'b11110; 3'd3:F_dyn_char_bits=5'b00001; 3'd4:F_dyn_char_bits=5'b00001; 3'd5:F_dyn_char_bits=5'b10001; 3'd6:F_dyn_char_bits=5'b01110; default:F_dyn_char_bits=5'b00000; endcase end
                4'h6: begin case(I_row) 3'd0:F_dyn_char_bits=5'b00110; 3'd1:F_dyn_char_bits=5'b01000; 3'd2:F_dyn_char_bits=5'b10000; 3'd3:F_dyn_char_bits=5'b11110; 3'd4:F_dyn_char_bits=5'b10001; 3'd5:F_dyn_char_bits=5'b10001; 3'd6:F_dyn_char_bits=5'b01110; default:F_dyn_char_bits=5'b00000; endcase end
                4'h7: begin case(I_row) 3'd0:F_dyn_char_bits=5'b11111; 3'd1:F_dyn_char_bits=5'b00001; 3'd2:F_dyn_char_bits=5'b00010; 3'd3:F_dyn_char_bits=5'b00100; 3'd4:F_dyn_char_bits=5'b01000; 3'd5:F_dyn_char_bits=5'b01000; 3'd6:F_dyn_char_bits=5'b01000; default:F_dyn_char_bits=5'b00000; endcase end
                4'h8: begin case(I_row) 3'd0:F_dyn_char_bits=5'b01110; 3'd1:F_dyn_char_bits=5'b10001; 3'd2:F_dyn_char_bits=5'b10001; 3'd3:F_dyn_char_bits=5'b01110; 3'd4:F_dyn_char_bits=5'b10001; 3'd5:F_dyn_char_bits=5'b10001; 3'd6:F_dyn_char_bits=5'b01110; default:F_dyn_char_bits=5'b00000; endcase end
                4'h9: begin case(I_row) 3'd0:F_dyn_char_bits=5'b01110; 3'd1:F_dyn_char_bits=5'b10001; 3'd2:F_dyn_char_bits=5'b10001; 3'd3:F_dyn_char_bits=5'b01111; 3'd4:F_dyn_char_bits=5'b00001; 3'd5:F_dyn_char_bits=5'b00010; 3'd6:F_dyn_char_bits=5'b11100; default:F_dyn_char_bits=5'b00000; endcase end
                4'ha: begin case(I_row) 3'd0:F_dyn_char_bits=5'b01110; 3'd1:F_dyn_char_bits=5'b10001; 3'd2:F_dyn_char_bits=5'b10001; 3'd3:F_dyn_char_bits=5'b11111; 3'd4:F_dyn_char_bits=5'b10001; 3'd5:F_dyn_char_bits=5'b10001; 3'd6:F_dyn_char_bits=5'b10001; default:F_dyn_char_bits=5'b00000; endcase end
                4'hb: begin case(I_row) 3'd0:F_dyn_char_bits=5'b11110; 3'd1:F_dyn_char_bits=5'b10001; 3'd2:F_dyn_char_bits=5'b10001; 3'd3:F_dyn_char_bits=5'b11110; 3'd4:F_dyn_char_bits=5'b10001; 3'd5:F_dyn_char_bits=5'b10001; 3'd6:F_dyn_char_bits=5'b11110; default:F_dyn_char_bits=5'b00000; endcase end
                4'hc: begin case(I_row) 3'd0:F_dyn_char_bits=5'b01110; 3'd1:F_dyn_char_bits=5'b10001; 3'd2:F_dyn_char_bits=5'b10000; 3'd3:F_dyn_char_bits=5'b10000; 3'd4:F_dyn_char_bits=5'b10000; 3'd5:F_dyn_char_bits=5'b10001; 3'd6:F_dyn_char_bits=5'b01110; default:F_dyn_char_bits=5'b00000; endcase end
                4'hd: begin case(I_row) 3'd0:F_dyn_char_bits=5'b11110; 3'd1:F_dyn_char_bits=5'b10001; 3'd2:F_dyn_char_bits=5'b10001; 3'd3:F_dyn_char_bits=5'b10001; 3'd4:F_dyn_char_bits=5'b10001; 3'd5:F_dyn_char_bits=5'b10001; 3'd6:F_dyn_char_bits=5'b11110; default:F_dyn_char_bits=5'b00000; endcase end
                4'he: begin case(I_row) 3'd0:F_dyn_char_bits=5'b11111; 3'd1:F_dyn_char_bits=5'b10000; 3'd2:F_dyn_char_bits=5'b10000; 3'd3:F_dyn_char_bits=5'b11110; 3'd4:F_dyn_char_bits=5'b10000; 3'd5:F_dyn_char_bits=5'b10000; 3'd6:F_dyn_char_bits=5'b11111; default:F_dyn_char_bits=5'b00000; endcase end
                4'hf: begin case(I_row) 3'd0:F_dyn_char_bits=5'b11111; 3'd1:F_dyn_char_bits=5'b10000; 3'd2:F_dyn_char_bits=5'b10000; 3'd3:F_dyn_char_bits=5'b11110; 3'd4:F_dyn_char_bits=5'b10000; 3'd5:F_dyn_char_bits=5'b10000; 3'd6:F_dyn_char_bits=5'b10000; default:F_dyn_char_bits=5'b00000; endcase end
                default: F_dyn_char_bits = 5'b00000;
            endcase
        end
    endfunction

//---- 字形库 G：统一 16x16 字符库（an / lu / C / N / T / : 及数字） ----
//   ※ 当前没有任何调用点；实际取字形走 :708 例化的 osd_char_lib 子模块，
//     两者的字符码定义（CHAR_* 常量）保持一致。
    // Unified prefix character library (16x16 rows): an/lu/C/N/T/:
    function [15:0] F_osd_char16_row;  // I_char 用 8bit 字符码、I_row 0..15；返回一行的 16 bit 点阵（bit[15]=最左像素）
        input [7:0] I_char;
        input [3:0] I_row;
        begin
            case(I_char)
                CHAR_AN: begin
                    case(I_row)
                        4'd0:  F_osd_char16_row = 16'h0200;
                        4'd1:  F_osd_char16_row = 16'h7ff0;
                        4'd2:  F_osd_char16_row = 16'h4410;
                        4'd3:  F_osd_char16_row = 16'h0400;
                        4'd4:  F_osd_char16_row = 16'h7ff0;
                        4'd5:  F_osd_char16_row = 16'h0840;
                        4'd6:  F_osd_char16_row = 16'h1040;
                        4'd7:  F_osd_char16_row = 16'h1c80;
                        4'd8:  F_osd_char16_row = 16'h0300;
                        4'd9:  F_osd_char16_row = 16'h0cc0;
                        4'd10: F_osd_char16_row = 16'h7020;
                        default: F_osd_char16_row = 16'h0000;
                    endcase
                end
                CHAR_LU: begin
                    case(I_row)
                        4'd0:  F_osd_char16_row = 16'h79e0;
                        4'd1:  F_osd_char16_row = 16'h4a20;
                        4'd2:  F_osd_char16_row = 16'h4d40;
                        4'd3:  F_osd_char16_row = 16'h7880;
                        4'd4:  F_osd_char16_row = 16'h1140;
                        4'd5:  F_osd_char16_row = 16'h1630;
                        4'd6:  F_osd_char16_row = 16'h5be0;
                        4'd7:  F_osd_char16_row = 16'h5220;
                        4'd8:  F_osd_char16_row = 16'h5220;
                        4'd9:  F_osd_char16_row = 16'h5be0;
                        4'd10: F_osd_char16_row = 16'h6220;
                        default: F_osd_char16_row = 16'h0000;
                    endcase
                end
                CHAR_C: begin
                    case(I_row)
                        4'd2:  F_osd_char16_row = 16'h03f0;
                        4'd3:  F_osd_char16_row = 16'h0c0c;
                        4'd4:  F_osd_char16_row = 16'h1800;
                        4'd5:  F_osd_char16_row = 16'h3000;
                        4'd6:  F_osd_char16_row = 16'h3000;
                        4'd7:  F_osd_char16_row = 16'h3000;
                        4'd8:  F_osd_char16_row = 16'h3000;
                        4'd9:  F_osd_char16_row = 16'h3000;
                        4'd10: F_osd_char16_row = 16'h1800;
                        4'd11: F_osd_char16_row = 16'h0c0c;
                        4'd12: F_osd_char16_row = 16'h03f0;
                        default: F_osd_char16_row = 16'h0000;
                    endcase
                end
                CHAR_N: begin
                    case(I_row)
                        4'd2:  F_osd_char16_row = 16'h300c;
                        4'd3:  F_osd_char16_row = 16'h380c;
                        4'd4:  F_osd_char16_row = 16'h3c0c;
                        4'd5:  F_osd_char16_row = 16'h360c;
                        4'd6:  F_osd_char16_row = 16'h330c;
                        4'd7:  F_osd_char16_row = 16'h318c;
                        4'd8:  F_osd_char16_row = 16'h30cc;
                        4'd9:  F_osd_char16_row = 16'h306c;
                        4'd10: F_osd_char16_row = 16'h303c;
                        4'd11: F_osd_char16_row = 16'h301c;
                        4'd12: F_osd_char16_row = 16'h300c;
                        default: F_osd_char16_row = 16'h0000;
                    endcase
                end
                CHAR_T: begin
                    case(I_row)
                        4'd2:  F_osd_char16_row = 16'h3ffc;
                        4'd3:  F_osd_char16_row = 16'h03c0;
                        4'd4:  F_osd_char16_row = 16'h03c0;
                        4'd5:  F_osd_char16_row = 16'h03c0;
                        4'd6:  F_osd_char16_row = 16'h03c0;
                        4'd7:  F_osd_char16_row = 16'h03c0;
                        4'd8:  F_osd_char16_row = 16'h03c0;
                        4'd9:  F_osd_char16_row = 16'h03c0;
                        4'd10: F_osd_char16_row = 16'h03c0;
                        4'd11: F_osd_char16_row = 16'h03c0;
                        4'd12: F_osd_char16_row = 16'h03c0;
                        default: F_osd_char16_row = 16'h0000;
                    endcase
                end
                CHAR_COLON: begin
                    case(I_row)
                        4'd6:  F_osd_char16_row = 16'h0180;
                        4'd7:  F_osd_char16_row = 16'h0180;
                        4'd10: F_osd_char16_row = 16'h0180;
                        4'd11: F_osd_char16_row = 16'h0180;
                        default: F_osd_char16_row = 16'h0000;
                    endcase
                end
                default: F_osd_char16_row = 16'h0000;
            endcase
        end
    endfunction

//---- 子模块例化与读写握手 ----
    assign O_video_rd_en = I_video_de;  // 读请求 = de：de 有效期间持续向 DDR 要像素，不做缓冲

    anlogic_logo_rom u_anlogic_logo_rom(  // Logo 位图 ROM：地址由坐标拼出，输出 {有效位, RGB888}
        .I_addr  ( S_logo_addr  ),
        .O_pixel ( S_logo_pixel )
    );

    osd_char_lib u_osd_char_lib(  // 统一 16x16 字符库：黄色 CNT 行与第 6 层参数行共用这一份例化
        .I_char     ( S_pf_char     ),
        .I_row      ( S_pf_row      ),
        .O_row_bits ( S_pf_row_bits )
    );

//---- 像素坐标扫描（由 de / last / user 生成 S_x / S_y） ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            S_x <= 12'd0;
            S_y <= 12'd0;
        end
        else if(I_video_user) begin  // I_video_user = 帧起始：坐标清零
            S_x <= 12'd0;
            S_y <= 12'd0;
        end
        else if(I_video_de) begin  // de 有效才计数（消隐期间坐标保持不变）
            if(I_video_last) begin  // 行末：x 归零且 y 加一；否则 x 加一
                S_x <= 12'd0;
                S_y <= S_y + 12'd1;
            end
            else begin
                S_x <= S_x + 12'd1;
            end
        end
    end

//---- 帧计数与 6 位十进制拆分（黄色 CNT 行的数据源） ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            S_frame_cnt <= 32'd0;
            S_dec_digit_0 <= 4'd0;
            S_dec_digit_1 <= 4'd0;
            S_dec_digit_2 <= 4'd0;
            S_dec_digit_3 <= 4'd0;
            S_dec_digit_4 <= 4'd0;
            S_dec_digit_5 <= 4'd0;
        end
        else if(I_video_user) begin  // 帧起始：每帧处理一次
            S_frame_cnt <= S_frame_cnt + 32'd1;  // 帧计数自增（用来确认画面确实在刷新，约 60 fps 递增）
            if(S_dec_digit_0 == 4'd9) begin  // 级联十进制进位链：本位到 9 就清零并向高位进 1，逐级传递到 _5；_5 到 9 直接回 0
                S_dec_digit_0 <= 4'd0;
                if(S_dec_digit_1 == 4'd9) begin
                    S_dec_digit_1 <= 4'd0;
                    if(S_dec_digit_2 == 4'd9) begin
                        S_dec_digit_2 <= 4'd0;
                        if(S_dec_digit_3 == 4'd9) begin
                            S_dec_digit_3 <= 4'd0;
                            if(S_dec_digit_4 == 4'd9) begin
                                S_dec_digit_4 <= 4'd0;
                                if(S_dec_digit_5 == 4'd9)
                                    S_dec_digit_5 <= 4'd0;
                                else
                                    S_dec_digit_5 <= S_dec_digit_5 + 4'd1;
                            end
                            else
                                S_dec_digit_4 <= S_dec_digit_4 + 4'd1;
                        end
                        else
                            S_dec_digit_3 <= S_dec_digit_3 + 4'd1;
                    end
                    else
                        S_dec_digit_2 <= S_dec_digit_2 + 4'd1;
                end
                else
                    S_dec_digit_1 <= S_dec_digit_1 + 4'd1;
            end
            else
                S_dec_digit_0 <= S_dec_digit_0 + 4'd1;
        end
    end

//---- 坐标打拍：把 S_x/S_y 延后 2 拍，与像素数据流水对齐 ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            S_x_1d <= 12'd0;
            S_x_2d <= 12'd0;
            S_y_1d <= 12'd0;
            S_y_2d <= 12'd0;
        end
        else begin
            S_x_1d <= S_x;  // 坐标延迟 2 拍 = 像素数据的流水级数，保证两者同拍参与运算
            S_x_2d <= S_x_1d;
            S_y_1d <= S_y;
            S_y_2d <= S_y_1d;
        end
    end

//---- 组合逻辑：逐像素 OSD 判定与取字形 ----
//   三层依次判定、后面的覆盖前面的：Logo -> 黄色 CNT 行 -> 绿色 MODE 状态行。
//   每层都是“窗口命中 -> 求局部坐标 -> 取字形行 -> 判该列是否点亮”四步。
//   本块用 S_x_2d/S_y_2d，所以结果与 S_video_data_2d 是同一个像素。
    always @(*) begin  // 纯组合块：用第 2 拍坐标判 OSD，结果与 S_video_data_2d 属同一像素
        S_osd_hit   = 1'b0;  // 组合默认值（全部赋 0，避免综合出锁存器）
        S_osd_color = 24'd0;
        S_logo_addr = 15'd0;
        // [HDR-2026-10-12k] 第 4 层遥测行的组合默认值
        S_dbg_x    = 12'd0;
        S_dbg_y    = 12'd0;
        S_dbg_idx  = 5'd0;
        S_dbg_lx   = 4'd0;
        S_dbg_ly   = 4'd0;
        S_dbg_gl   = 5'd0;
        S_dbg_bits = 5'd0;
            S_dbg2_x    = 12'd0;
            S_dbg2_y    = 12'd0;
            S_dbg2_idx  = 5'd0;
            S_dbg2_lx   = 4'd0;
            S_dbg2_ly   = 4'd0;
            S_dbg2_gl   = 5'd0;
            S_dbg2_bits = 5'd0;
            S_dbg2_on   = 1'b0;
        S_dbg_on   = 1'b0;

        S_logo_x = 12'd0;
        S_logo_y = 12'd0;
        S_char_idx = 4'd0;
        S_char_row = 3'd0;
        S_char_col = 3'd0;
        S_char_bits = 5'd0;
        S_char_on = 1'b0;
        S_logo_blue_on = 1'b0;
        S_logo_red_on = 1'b0;
        S_logo_tmp_y = 12'd0;
        S_logo_red_band = 4'd0;
        S_logo_red_x_start = 12'd0;
        S_logo_red_x_end = 12'd0;
        S_dyn_x = 12'd0;
        S_dyn_y = 12'd0;
        S_dyn_char = 4'd0;
        S_dyn_col = 3'd0;
        S_dyn_row = 3'd0;
        S_dyn_bits = 5'd0;
        S_dyn_on = 1'b0;
        S_dyn_digit_idx = 4'd0;
        S_dyn_digit_x = 12'd0;
        S_dyn_seg = 7'd0;
        S_lbl_row = 3'd0;
        S_lbl_col = 3'd0;
        S_lbl_idx = 2'd0;
        S_lbl_bits = 5'd0;
        S_lbl_local_x = 7'd0;
        S_dyn_dec_digit = 4'd0;
        S_cn_local_x = 5'd0;
        S_cn_local_y = 5'd0;
        S_cn_col = 4'd0;
        S_cn_row = 4'd0;
        S_cn_row_bits = 16'd0;
        S_cn_on = 1'b0;
        S_cn_scale_x = 10'd0;
        S_cn_scale_y = 10'd0;
        S_pf_char = 8'd0;
        S_pf_local_x = 5'd0;
        S_pf_local_y = 5'd0;
        S_pf_col = 4'd0;
        S_pf_row = 4'd0;
        S_pf_on = 1'b0;
        S_pf_scale_x = 10'd0;
        S_pf_scale_y = 10'd0;

        // [OUR ALGO] 算法状态行默认值（全部赋初值，避免综合出锁存器）
        S_alg_x    = 12'd0;
        S_alg_y    = 12'd0;
        S_alg_idx  = 3'd0;
        S_alg_lx   = 4'd0;
        S_alg_ly   = 4'd0;
        S_alg_bits = 5'd0;
        S_alg_on   = 1'b0;

        // [PAR-OSD 2026-10-15] 实时参数行默认值（全部赋初值，避免综合出锁存器）
        S_par_idx  = 5'd0;
        S_par_col  = 4'd0;
        S_par_row  = 4'd0;

//------ 第 1 层：安路 Logo（窗口 160x160，图形来自 ROM） ------
        if(S_video_de_2d) begin  // 只在 de 有效的流水级做判定（消隐期不产生 OSD）
            if((S_x_2d >= LOGO_X) && (S_x_2d < (LOGO_X + LOGO_W)) &&  // Logo 窗口命中判定（左闭右开）
               (S_y_2d >= LOGO_Y) && (S_y_2d < (LOGO_Y + LOGO_H))) begin
                S_logo_x = S_x_2d - LOGO_X;  // 窗口内局部坐标
                S_logo_y = S_y_2d - LOGO_Y;
                // [HDR-2026-10-10e 时序修复] 原式 S_logo_y * LOGO_W + S_logo_x（LOGO_W=160 常量）被综合器
                //   做成了 DSP 乘法 + DSP 加法（DSPMULT 1.19ns + add 0.63ns + 高速网线，见
                //   phy_1/final_timing.rpt 中 slack=-0.543ns 那条路径，其起点 mult0 就在本行）。
                //   160 = 128 + 32，改为两次常量左移相加：数学等价（y<=159 ⇒ 真值 <= 25599 < 32768，
                //   15 bit 的 S_logo_addr 不会溢出），且常量移位不消耗 LUT，把 DSP 及其高扇出网从
                //   HDMI_PIXEL_CLK(75MHz,13.333ns) 的关键路径上摘掉。
                S_logo_addr = (S_logo_y << 7) + (S_logo_y << 5) + S_logo_x;  // = y*160 + x
                if(S_logo_pixel[24]) begin  // bit24 是该像素的“有效/不透明”标志，只有为 1 才覆盖画面
                    S_osd_hit   = 1'b1;
                    S_osd_color = S_logo_pixel[23:0];
                end
            end

//------ 第 2 层：黄色帧计数行 "安路 CNT:xxxxxx" ------
            if((!S_osd_hit) &&  // Logo 未命中时才判 CNT 行（Logo 优先级更高）
               (S_x_2d >= DYN_OSD_X) && (S_x_2d < (DYN_OSD_X + DYN_OSD_W)) &&
               (S_y_2d >= DYN_OSD_Y) && (S_y_2d < (DYN_OSD_Y + DYN_OSD_H))) begin
                S_dyn_x = S_x_2d - DYN_OSD_X;  // CNT 窗口内的局部坐标（x 0..199，y 0..23）
                S_dyn_y = S_y_2d - DYN_OSD_Y;

                // Unified prefix render using one character library.
                // an:[0..23], lu:[24..47], C:[52..67], N:[68..83], T:[84..99], :[100..107]
                if((S_dyn_x < 12'd108) && (S_dyn_y < 12'd24)) begin  // 前缀区分配：0..23='安'、24..47='路'、52..67='C'、68..83='N'、84..99='T'、100..107=':'
                    if((S_dyn_x < 12'd24) || ((S_dyn_x >= 12'd24) && (S_dyn_x < 12'd48))) begin
                        if(S_dyn_y >= CN_Y_OFFSET)
                            S_pf_local_y = S_dyn_y - CN_Y_OFFSET;
                        else
                            S_pf_local_y = 5'd31;

                        if(S_dyn_x < 12'd24) begin
                            S_pf_char = CHAR_AN;
                            S_pf_local_x = S_dyn_x;
                        end
                        else begin
                            S_pf_char = CHAR_LU;
                            S_pf_local_x = S_dyn_x - 12'd24;
                        end

                        if((S_pf_local_x < 5'd24) && (S_pf_local_y < 5'd24)) begin
                            S_pf_scale_x = S_pf_local_x * 10'd16;  // 放大：局部坐标 x16 再 /24，得到 16x16 字形内部的列/行（字形被放大成 24x24）
                            S_pf_scale_y = S_pf_local_y * 10'd16;
                            S_pf_col = S_pf_scale_x / 10'd24;
                            S_pf_row = S_pf_scale_y / 10'd24;
                            case(S_pf_col)
                                4'd0:  S_pf_on = S_pf_row_bits[15];
                                4'd1:  S_pf_on = S_pf_row_bits[14];
                                4'd2:  S_pf_on = S_pf_row_bits[13];
                                4'd3:  S_pf_on = S_pf_row_bits[12];
                                4'd4:  S_pf_on = S_pf_row_bits[11];
                                4'd5:  S_pf_on = S_pf_row_bits[10];
                                4'd6:  S_pf_on = S_pf_row_bits[9];
                                4'd7:  S_pf_on = S_pf_row_bits[8];
                                4'd8:  S_pf_on = S_pf_row_bits[7];
                                4'd9:  S_pf_on = S_pf_row_bits[6];
                                4'd10: S_pf_on = S_pf_row_bits[5];
                                4'd11: S_pf_on = S_pf_row_bits[4];
                                4'd12: S_pf_on = S_pf_row_bits[3];
                                4'd13: S_pf_on = S_pf_row_bits[2];
                                4'd14: S_pf_on = S_pf_row_bits[1];
                                4'd15: S_pf_on = S_pf_row_bits[0];
                                default: S_pf_on = 1'b0;
                            endcase
                        end
                    end
                    else if((S_dyn_x >= 12'd52) && (S_dyn_x < 12'd100) && (S_dyn_y >= 12'd4) && (S_dyn_y < 12'd20)) begin
                        if(S_dyn_x < 12'd68) begin
                            S_pf_char = CHAR_C;
                            S_pf_local_x = S_dyn_x - 12'd52;
                        end
                        else if(S_dyn_x < 12'd84) begin
                            S_pf_char = CHAR_N;
                            S_pf_local_x = S_dyn_x - 12'd68;
                        end
                        else begin
                            S_pf_char = CHAR_T;
                            S_pf_local_x = S_dyn_x - 12'd84;
                        end
                        S_pf_local_y = S_dyn_y - 12'd4;
                        S_pf_col = S_pf_local_x[3:0];  // 'C''N''T' 三个字母是 1:1 点阵（局部 x 只有 0..15），列号取低 4 位即等于原值
                        S_pf_row = S_pf_local_y[3:0];
                        case(S_pf_col)
                            4'd0:  S_pf_on = S_pf_row_bits[15];
                            4'd1:  S_pf_on = S_pf_row_bits[14];
                            4'd2:  S_pf_on = S_pf_row_bits[13];
                            4'd3:  S_pf_on = S_pf_row_bits[12];
                            4'd4:  S_pf_on = S_pf_row_bits[11];
                            4'd5:  S_pf_on = S_pf_row_bits[10];
                            4'd6:  S_pf_on = S_pf_row_bits[9];
                            4'd7:  S_pf_on = S_pf_row_bits[8];
                            4'd8:  S_pf_on = S_pf_row_bits[7];
                            4'd9:  S_pf_on = S_pf_row_bits[6];
                            4'd10: S_pf_on = S_pf_row_bits[5];
                            4'd11: S_pf_on = S_pf_row_bits[4];
                            4'd12: S_pf_on = S_pf_row_bits[3];
                            4'd13: S_pf_on = S_pf_row_bits[2];
                            4'd14: S_pf_on = S_pf_row_bits[1];
                            4'd15: S_pf_on = S_pf_row_bits[0];
                            default: S_pf_on = 1'b0;
                        endcase
                    end
                    else if((S_dyn_x >= 12'd100) && (S_dyn_x < 12'd108) && (S_dyn_y >= 12'd4) && (S_dyn_y < 12'd20)) begin
                        S_pf_char = CHAR_COLON;
                        S_pf_local_x = S_dyn_x - 12'd100;
                        S_pf_local_y = S_dyn_y - 12'd4;
                        S_pf_scale_x = S_pf_local_x * 10'd16;
                        S_pf_col = S_pf_scale_x / 10'd8;  // 冒号只有 2 列宽：横向放大 8 倍映射到 16 列字形（局部 x * 16 / 8）
                        S_pf_row = S_pf_local_y[3:0];
                        case(S_pf_col)
                            4'd0:  S_pf_on = S_pf_row_bits[15];
                            4'd1:  S_pf_on = S_pf_row_bits[14];
                            4'd2:  S_pf_on = S_pf_row_bits[13];
                            4'd3:  S_pf_on = S_pf_row_bits[12];
                            4'd4:  S_pf_on = S_pf_row_bits[11];
                            4'd5:  S_pf_on = S_pf_row_bits[10];
                            4'd6:  S_pf_on = S_pf_row_bits[9];
                            4'd7:  S_pf_on = S_pf_row_bits[8];
                            4'd8:  S_pf_on = S_pf_row_bits[7];
                            4'd9:  S_pf_on = S_pf_row_bits[6];
                            4'd10: S_pf_on = S_pf_row_bits[5];
                            4'd11: S_pf_on = S_pf_row_bits[4];
                            4'd12: S_pf_on = S_pf_row_bits[3];
                            4'd13: S_pf_on = S_pf_row_bits[2];
                            4'd14: S_pf_on = S_pf_row_bits[1];
                            4'd15: S_pf_on = S_pf_row_bits[0];
                            default: S_pf_on = 1'b0;
                        endcase
                    end

                    if(S_pf_on)
                        S_dyn_on = 1'b1;
                end

                // Decimal 6 digits starts at x=110. Each digit is 15x24.
                if((S_dyn_x >= 12'd110) && (S_dyn_x < 12'd200)) begin  // 十进制数字区 x=110..199：共 6 位，每位 15 像素宽
                    if(S_dyn_x < 12'd125) begin
                        S_dyn_digit_idx = 4'd0;
                        S_dyn_digit_x = S_dyn_x - 12'd110;
                        S_dyn_dec_digit = S_dec_digit_5;  // 屏上最左边那位显示的是最高位 _5（大端输出）
                    end
                    else if(S_dyn_x < 12'd140) begin
                        S_dyn_digit_idx = 4'd1;
                        S_dyn_digit_x = S_dyn_x - 12'd125;
                        S_dyn_dec_digit = S_dec_digit_4;
                    end
                    else if(S_dyn_x < 12'd155) begin
                        S_dyn_digit_idx = 4'd2;
                        S_dyn_digit_x = S_dyn_x - 12'd140;
                        S_dyn_dec_digit = S_dec_digit_3;
                    end
                    else if(S_dyn_x < 12'd170) begin
                        S_dyn_digit_idx = 4'd3;
                        S_dyn_digit_x = S_dyn_x - 12'd155;
                        S_dyn_dec_digit = S_dec_digit_2;
                    end
                    else if(S_dyn_x < 12'd185) begin
                        S_dyn_digit_idx = 4'd4;
                        S_dyn_digit_x = S_dyn_x - 12'd170;
                        S_dyn_dec_digit = S_dec_digit_1;
                    end
                    else begin
                        S_dyn_digit_idx = 4'd5;
                        S_dyn_digit_x = S_dyn_x - 12'd185;
                        S_dyn_dec_digit = S_dec_digit_0;
                    end

                    // Render decimal digits through unified 16x16 character library.
                    // Keep enlarged 15x24 box for readability.
                    if((S_dyn_digit_x < 12'd15) && (S_dyn_y < 12'd24)) begin
                        S_pf_char = CHAR_0 + {4'd0, S_dyn_dec_digit};  // 字符码 = '0' + 数字值（以 CHAR_0=8'h30 为基址）
                        S_pf_local_x = S_dyn_digit_x[4:0];
                        S_pf_local_y = S_dyn_y[4:0];
                        S_pf_scale_x = S_pf_local_x * 10'd16;
                        S_pf_scale_y = S_pf_local_y * 10'd16;
                        S_pf_col = S_pf_scale_x / 10'd15;  // 每位数字的显示框是 15x24：横向按 16/15 略微放大
                        S_pf_row = S_pf_scale_y / 10'd24;  // 纵向按 16/24 缩小（16 行字形撑满 24 像素高）
                        case(S_pf_col)
                            4'd0:  S_pf_on = S_pf_row_bits[15];
                            4'd1:  S_pf_on = S_pf_row_bits[14];
                            4'd2:  S_pf_on = S_pf_row_bits[13];
                            4'd3:  S_pf_on = S_pf_row_bits[12];
                            4'd4:  S_pf_on = S_pf_row_bits[11];
                            4'd5:  S_pf_on = S_pf_row_bits[10];
                            4'd6:  S_pf_on = S_pf_row_bits[9];
                            4'd7:  S_pf_on = S_pf_row_bits[8];
                            4'd8:  S_pf_on = S_pf_row_bits[7];
                            4'd9:  S_pf_on = S_pf_row_bits[6];
                            4'd10: S_pf_on = S_pf_row_bits[5];
                            4'd11: S_pf_on = S_pf_row_bits[4];
                            4'd12: S_pf_on = S_pf_row_bits[3];
                            4'd13: S_pf_on = S_pf_row_bits[2];
                            4'd14: S_pf_on = S_pf_row_bits[1];
                            4'd15: S_pf_on = S_pf_row_bits[0];
                            default: S_pf_on = 1'b0;
                        endcase
                        if(S_pf_on)
                            S_dyn_on = 1'b1;
                    end
                end

                if(S_dyn_on) begin
                    S_osd_hit = 1'b1;  // CNT 行命中：整行使用黄色 COLOR_DYN_TEXT
                    S_osd_color = COLOR_DYN_TEXT;
                end
            end

//------ 第 3 层：绿色算法状态行 "MODE n"（优先级最高，最后判定） ------
            //------------------------------------------------------------------
            // [OUR ALGO] 算法状态行 "MODE n"
            //   放在最后 = 优先级最高，不会被 Logo 或 CNT 覆盖
            //   区域 (176,176)-(259,185)，与 Logo(0,0)-(159,159)、
            //   CNT(375,120)-(574,143) 均不重叠，正常情况下也互不遮挡
            //------------------------------------------------------------------
            if((S_x_2d >= ALG_OSD_X) && (S_x_2d < (ALG_OSD_X + ALG_OSD_W)) &&  // 状态行窗口命中判定（宽 84 = 6 字符 x 14 字距）
               (S_y_2d >= ALG_OSD_Y) && (S_y_2d < (ALG_OSD_Y + ALG_OSD_H))) begin
                S_alg_x    = S_x_2d - ALG_OSD_X;  // 窗口内局部坐标
                S_alg_y    = S_y_2d - ALG_OSD_Y;
                S_alg_lx   = S_alg_x[3:0] % 4'd14;   // 字距 14  // 取局部 x 低 4 位再对 14 取模，得到字符内列偏移（0..13，其中 0..4 才落在字形上）
                S_alg_ly   = S_alg_y[3:0];  // 行号 = 局部 y（窗口高度只有 10，取低 4 位足够）
                S_alg_idx  = S_alg_x[6:4];           // 第几个字符：0..5  // 第几个字符：局部 x 的 bit[6:4] 即 x/16，恰好得到 0..5 共 6 个字符位

                if(S_alg_lx < 4'd5) begin  // 字形只有 5 列宽：lx<5 才是字形内部，lx>=5 是字间空隙（不点亮）
                    // 6 个字符位从左到右：0='M' 1='O' 2='D' 3='E' 4=空格 5=模式数字
                    // 每个分支返回该字符在 S_alg_ly 行上的 5 bit 点阵，未命中返回全 0
                    case(S_alg_idx)
                        3'd0: S_alg_bits = F_alg_char_bits(4'd0, {1'b0,S_alg_ly[2:0]}); // M
                        3'd1: S_alg_bits = F_alg_char_bits(4'd1, {1'b0,S_alg_ly[2:0]}); // O
                        3'd2: S_alg_bits = F_alg_char_bits(4'd2, {1'b0,S_alg_ly[2:0]}); // D
                        3'd3: S_alg_bits = F_alg_char_bits(4'd3, {1'b0,S_alg_ly[2:0]}); // E
                        3'd4: S_alg_bits = 5'b00000;                                    // 空格
                        // [2026-10-10 已修] 原来 MODE 4 走的是索引 4'd4，而 F_alg_char_bits 的
                        //   索引 4 是数字 '0'，导致 MODE 4 在屏上显示成 "MODE 0"，与真正的
                        //   MODE 0 无法区分 —— 这直接违反评分项「多算法切换与★状态显示★」,
                        //   也会让评委以为卡通化没生效。
                        //   修法：字形库补了数字 '4'（新索引 4'd8），这里统一用 4+mode 取索引，
                        //   MODE 0..4 -> 字形 '0'..'4' 全部正确。
                        3'd5: S_alg_bits = F_alg_char_bits({1'b0, S_algo_mode_2d} + 4'd4,
                                                          {1'b0,S_alg_ly[2:0]});  // 数字 0..4
                        default: S_alg_bits = 5'b00000;
                    endcase

                    case(S_alg_lx[2:0])  // 5 位列选择：bits[4] 是最左列，所以从 bit4 依次取到 bit0
                        3'd0: S_alg_on = S_alg_bits[4];
                        3'd1: S_alg_on = S_alg_bits[3];
                        3'd2: S_alg_on = S_alg_bits[2];
                        3'd3: S_alg_on = S_alg_bits[1];
                        3'd4: S_alg_on = S_alg_bits[0];
                        default: S_alg_on = 1'b0;
                    endcase
                end
                else begin
                    S_alg_on = 1'b0;
                end

                if(S_alg_on) begin  // 命中：用亮绿色覆盖（本层最后判定，优先级最高）
                    S_osd_hit   = 1'b1;
                    S_osd_color = COLOR_ALG_TEXT;
                end
            end

//------ 第 4 层：橙色遥测行（诊断用，最后判定 = 优先级最高） ------
            //------------------------------------------------------------------
            // [HDR-2026-10-12k] 19 字符遥测行 "AExxSxMxxWxxxxBxxxx"
            //   窗口 (376,152)-(679,161)，与 Logo(0,0)-(159,159)、
            //   CNT(375,120)-(574,143)、MODE(176,176)-(259,185) 都不重叠。
            //   ★这一行纯粹是诊断手段：AE/AWB 定案之后可以整块删掉★
            //------------------------------------------------------------------
            if((S_x_2d >= DBG_OSD_X) && (S_x_2d < (DBG_OSD_X + DBG_OSD_W)) &&
               (S_y_2d >= DBG_OSD_Y) && (S_y_2d < (DBG_OSD_Y + DBG_OSD_H))) begin
                S_dbg_x   = S_x_2d - DBG_OSD_X;
                S_dbg_y   = S_y_2d - DBG_OSD_Y;
                S_dbg_idx = S_dbg_x[8:4];   // 第几个字符：字距 16 ⇒ 局部 x/16，0..18
                S_dbg_lx  = S_dbg_x[3:0];   // 字符内列偏移 0..15（只有 0..4 落在字形上）
                S_dbg_ly  = S_dbg_y[3:0];   // 行号 0..9（字形只占 0..6）

                case(S_dbg_idx)
                    5'd0 : S_dbg_gl = 5'd10;                     // 'A'
                    5'd1 : S_dbg_gl = 5'd14;                     // 'E'
                    5'd2 : S_dbg_gl = {2'b00, S_dbg_gi[6:4]};    // 增益索引 高位
                    5'd3 : S_dbg_gl = {1'b0,  S_dbg_gi[3:0]};    // 增益索引 低位
                    5'd4 : S_dbg_gl = 5'd17;                     // 'S'
                    5'd5 : S_dbg_gl = {3'b000, S_dbg_st};        // 状态 0..3
                    5'd6 : S_dbg_gl = 5'd16;                     // 'M'
                    5'd7 : S_dbg_gl = {1'b0,  S_dbg_ml[7:4]};    // 实测均值 高位
                    5'd8 : S_dbg_gl = {1'b0,  S_dbg_ml[3:0]};    // 实测均值 低位
                    5'd9 : S_dbg_gl = 5'd18;                     // 'W'
                    5'd10: S_dbg_gl = {1'b0,  S_dbg_gr[15:12]};  // R 增益 4 位
                    5'd11: S_dbg_gl = {1'b0,  S_dbg_gr[11:8]};
                    5'd12: S_dbg_gl = {1'b0,  S_dbg_gr[7:4]};
                    5'd13: S_dbg_gl = {1'b0,  S_dbg_gr[3:0]};
                    5'd14: S_dbg_gl = 5'd11;                     // 'B'
                    5'd15: S_dbg_gl = {1'b0,  S_dbg_gb[15:12]};  // B 增益 4 位
                    5'd16: S_dbg_gl = {1'b0,  S_dbg_gb[11:8]};
                    5'd17: S_dbg_gl = {1'b0,  S_dbg_gb[7:4]};
                    default: S_dbg_gl = {1'b0, S_dbg_gb[3:0]};
                endcase

                if(S_dbg_lx < 4'd5) begin   // 字形只有 5 列宽
                    S_dbg_bits = F_dbg_rowbits(S_dbg_gl, S_dbg_ly[2:0]);
                    case(S_dbg_lx[2:0])
                        3'd0: S_dbg_on = S_dbg_bits[4];
                        3'd1: S_dbg_on = S_dbg_bits[3];
                        3'd2: S_dbg_on = S_dbg_bits[2];
                        3'd3: S_dbg_on = S_dbg_bits[1];
                        3'd4: S_dbg_on = S_dbg_bits[0];
                        default: S_dbg_on = 1'b0;
                    endcase
                end
                else begin
                    S_dbg_on = 1'b0;
                end

                if(S_dbg_on) begin
                    S_osd_hit   = 1'b1;
                    S_osd_color = COLOR_DBG_TEXT;
                end
            end

            //------------------------------------------------------------------
            // [HDR-2026-10-12m] 第 5 层：第二行橙色遥测 "FcbnamTssNnnDnnUnn"
            //   F + 5 位标志 c=can_act b=frame_ok n=req_pend a=ae_cfg_done m=cam_cfg_done
            //   T ss = S_settle（正常 3C=60）  N nn = S_gi_next
            //   D nn = S_gi_dec               U nn = S_gi_inc
            //   窗口 (376,164)-(679,173)，与第 4 层(152..161)、MODE(176..185) 不重叠。
            //   ★纯诊断，AE 定案后整块删掉★
            //------------------------------------------------------------------
            if((S_x_2d >= DBG2_OSD_X) && (S_x_2d < (DBG2_OSD_X + DBG2_OSD_W)) &&
               (S_y_2d >= DBG2_OSD_Y) && (S_y_2d < (DBG2_OSD_Y + DBG2_OSD_H))) begin
                S_dbg2_x   = S_x_2d - DBG2_OSD_X;
                S_dbg2_y   = S_y_2d - DBG2_OSD_Y;
                S_dbg2_idx = S_dbg2_x[8:4];
                S_dbg2_lx  = S_dbg2_x[3:0];
                S_dbg2_ly  = S_dbg2_y[3:0];

                case(S_dbg2_idx)
                    5'd0 : S_dbg2_gl = 5'd15;                        // 'F'
                    5'd1 : S_dbg2_gl = S_d2_can ? 5'd1 : 5'd0;
                    5'd2 : S_dbg2_gl = S_d2_frm ? 5'd1 : 5'd0;
                    5'd3 : S_dbg2_gl = S_d2_req ? 5'd1 : 5'd0;
                    5'd4 : S_dbg2_gl = S_d2_aec ? 5'd1 : 5'd0;
                    5'd5 : S_dbg2_gl = S_d2_cam ? 5'd1 : 5'd0;
                    5'd6 : S_dbg2_gl = 5'd19;                        // 'T'
                    5'd7 : S_dbg2_gl = {1'b0, S_d2_set[7:4]};
                    5'd8 : S_dbg2_gl = {1'b0, S_d2_set[3:0]};
                    5'd9 : S_dbg2_gl = 5'd20;                        // 'N'
                    5'd10: S_dbg2_gl = {2'b00, S_d2_nxt[6:4]};
                    5'd11: S_dbg2_gl = {1'b0,  S_d2_nxt[3:0]};
                    5'd12: S_dbg2_gl = 5'd13;                        // 'D'
                    5'd13: S_dbg2_gl = {2'b00, S_d2_dec[6:4]};
                    5'd14: S_dbg2_gl = {1'b0,  S_d2_dec[3:0]};
                    5'd15: S_dbg2_gl = 5'd21;                        // 'U'
                    5'd16: S_dbg2_gl = {2'b00, S_d2_inc[6:4]};
                    default: S_dbg2_gl = {1'b0, S_d2_inc[3:0]};
                endcase

                if(S_dbg2_lx < 4'd5) begin
                    S_dbg2_bits = F_dbg_rowbits(S_dbg2_gl, S_dbg2_ly[2:0]);
                    case(S_dbg2_lx[2:0])
                        3'd0: S_dbg2_on = S_dbg2_bits[4];
                        3'd1: S_dbg2_on = S_dbg2_bits[3];
                        3'd2: S_dbg2_on = S_dbg2_bits[2];
                        3'd3: S_dbg2_on = S_dbg2_bits[1];
                        3'd4: S_dbg2_on = S_dbg2_bits[0];
                        default: S_dbg2_on = 1'b0;
                    endcase
                end
                else begin
                    S_dbg2_on = 1'b0;
                end

                if(S_dbg2_on) begin
                    S_osd_hit   = 1'b1;
                    S_osd_color = COLOR_DBG_TEXT;
                end
            end

//------ 第 6 层：[PAR-OSD 2026-10-15] 实时参数行 "S-CURVE ON  LSC ON  GAIN2 AE ON " ------
//   最后判定 ⇒ 优先级最高。窗口 (176,200) 512x16，与其余五层都不重叠
//   （Logo y0..159 / CNT y120..143 / DBG y152..161 / DBG2 y164..173 / MODE y176..185）。
            if((S_x_2d >= PAR_OSD_X) && (S_x_2d < (PAR_OSD_X + PAR_OSD_W)) &&
               (S_y_2d >= PAR_OSD_Y) && (S_y_2d < (PAR_OSD_Y + PAR_OSD_H))) begin
                // ★局部坐标不用 12bit 减法★ PAR_OSD_X=176=11*16、PAR_OSD_Y=200=12*16+8：
                //     (x-176)/16 = x/16 - 11 ，(x-176)%16 = x%16（列号直接取低位）
                //     (y-200)%16 = y%16 - 8
                //   窗口内 x<688、y<216，5bit/4bit 无符号回卷正好给出 0..31 / 0..15。
                //   ★S_par_idx 必须 5bit★：窗口宽 512 > 256，若写成 S_x_2d[7:4]，索引在
                //   x>=432 处会丢高位回卷到 0，后半行的字会显示成前面的字。
                S_par_idx = {1'b0, S_x_2d[8:4]} - 5'd11;
                S_par_col = S_x_2d[3:0];
                S_par_row = S_y_2d[3:0] - 4'd8;

                case(S_par_idx)
                    5'd0 :   S_pf_char = 8'h53;        // 'S'
                    5'd1 :   S_pf_char = 8'h2d;        // '-'（osd_char_lib 本次新增的字形）
                    5'd2 :   S_pf_char = 8'h43;        // 'C'
                    5'd3 :   S_pf_char = 8'h55;        // 'U'
                    5'd4 :   S_pf_char = 8'h52;        // 'R'
                    5'd5 :   S_pf_char = 8'h56;        // 'V'
                    5'd6 :   S_pf_char = 8'h45;        // 'E'
                    5'd7 :   S_pf_char = 8'h20;        // 空格
                    5'd8 :   S_pf_char = 8'h4f;        // 'O'
                    5'd9 :   S_pf_char = S_par_c9;     // 'N'(ON) / 'F'(OFF)
                    5'd10:   S_pf_char = S_par_c10;    // ' ' / 'F'
                    5'd11:   S_pf_char = 8'h20;        // 空格
                    5'd12:   S_pf_char = 8'h4c;        // 'L'
                    5'd13:   S_pf_char = 8'h53;        // 'S'
                    5'd14:   S_pf_char = 8'h43;        // 'C'
                    5'd15:   S_pf_char = 8'h20;        // 空格
                    5'd16:   S_pf_char = 8'h4f;        // 'O'
                    5'd17:   S_pf_char = S_par_c17;    // 'N' / 'F'
                    5'd18:   S_pf_char = S_par_c18;    // ' ' / 'F'
                    5'd19:   S_pf_char = 8'h20;        // 空格
                    5'd20:   S_pf_char = 8'h47;        // 'G'
                    5'd21:   S_pf_char = 8'h4f;        // 'O'  [PAR-OSD 改] 原 'A'
                    5'd22:   S_pf_char = 8'h54;        // 'T'  [PAR-OSD 改] 原 'I'
                    5'd23:   S_pf_char = 8'h3a;        // ':'  [PAR-OSD 改] 原 'N'
                    5'd24:   S_pf_char = S_par_c24;    // [PAR-OSD 改] '1'=MOT ON / '0'=MOT OFF
                    5'd25:   S_pf_char = 8'h20;        // 空格
                    5'd26:   S_pf_char = 8'h53;        // 'S'  [PAR-OSD 改] 原 'A'
                    5'd27:   S_pf_char = 8'h45;        // 'E'
                    5'd28:   S_pf_char = 8'h4e;        // 'N'  [PAR-OSD 改] 原空格
                    5'd29:   S_pf_char = 8'h53;        // 'S'  [PAR-OSD 改] 原 'O'
                    5'd30:   S_pf_char = S_par_c30;    // [PAR-OSD 改] 固定空格
                    5'd31:   S_pf_char = S_par_c31;    // [PAR-OSD 改] 'H'=严格 / 'L'=宽松
                    default: S_pf_char = 8'h20;        // 越界补空格
                endcase

                S_pf_row = S_par_row;
                case(S_par_col)   // 16 选 1：bit15 = 该行最左列（与其余各层同一约定）
                    4'd0 :   S_pf_on = S_pf_row_bits[15];
                    4'd1 :   S_pf_on = S_pf_row_bits[14];
                    4'd2 :   S_pf_on = S_pf_row_bits[13];
                    4'd3 :   S_pf_on = S_pf_row_bits[12];
                    4'd4 :   S_pf_on = S_pf_row_bits[11];
                    4'd5 :   S_pf_on = S_pf_row_bits[10];
                    4'd6 :   S_pf_on = S_pf_row_bits[9];
                    4'd7 :   S_pf_on = S_pf_row_bits[8];
                    4'd8 :   S_pf_on = S_pf_row_bits[7];
                    4'd9 :   S_pf_on = S_pf_row_bits[6];
                    4'd10:   S_pf_on = S_pf_row_bits[5];
                    4'd11:   S_pf_on = S_pf_row_bits[4];
                    4'd12:   S_pf_on = S_pf_row_bits[3];
                    4'd13:   S_pf_on = S_pf_row_bits[2];
                    4'd14:   S_pf_on = S_pf_row_bits[1];
                    4'd15:   S_pf_on = S_pf_row_bits[0];
                    default: S_pf_on = 1'b0;
                endcase

                if(S_pf_on) begin
                    S_osd_hit   = 1'b1;
                    S_osd_color = COLOR_PAR_TEXT;
                end
            end
        end
        // ---- [HDR-2026-10-15] \u7b2c 5 \u5c42\uff1a\u8fd0\u52a8\u5757\u8fb9\u754c\u63cf\u8fb9\uff08\u6700\u4f4e\u4f18\u5148\u7ea7\uff0c\u4e0d\u906e\u9065\u6d4b\u6587\u5b57\uff09----
        //   \u5757\u7f51\u683c 16x9\u3001\u5757\u5c3a\u5bf8 80x80\uff0c\u4e0e motion_detect.v \u7684 BEATS_PER_BLK=20*4px \u5bf9\u9f50\u3002
        //   \u5757\u7d22\u5f15 = 15+8 \u4e2a\u6bd4\u8f83\u5668\u6c42\u548c\uff1b\u5757\u5185\u504f\u79fb\u7528 bx*80=(bx<<6)+(bx<<4) \u8fd8\u539f => \u96f6\u9664\u6cd5\u5668\u3002
        // \u5757\u7d22\u5f15\uff1a\u6bcf\u4e00\u9879\u663e\u5f0f\u8865\u96f6\u5230\u76ee\u6807\u4f4d\u5bbd\uff0c\u907f\u514d Verilog \u628a 1bit \u52a0\u6cd5\u94fe\u6309 1bit \u8ba1\u7b97
        S_mot_bx = 5'd0
                 + {4'b0,(S_x_2d>=12'd80 )} + {4'b0,(S_x_2d>=12'd160)}
                 + {4'b0,(S_x_2d>=12'd240)} + {4'b0,(S_x_2d>=12'd320)}
                 + {4'b0,(S_x_2d>=12'd400)} + {4'b0,(S_x_2d>=12'd480)}
                 + {4'b0,(S_x_2d>=12'd560)} + {4'b0,(S_x_2d>=12'd640)}
                 + {4'b0,(S_x_2d>=12'd720)} + {4'b0,(S_x_2d>=12'd800)}
                 + {4'b0,(S_x_2d>=12'd880)} + {4'b0,(S_x_2d>=12'd960)}
                 + {4'b0,(S_x_2d>=12'd1040)}+ {4'b0,(S_x_2d>=12'd1120)}
                 + {4'b0,(S_x_2d>=12'd1200)};
        S_mot_by = 4'd0
                 + {3'b0,(S_y_2d>=12'd80 )} + {3'b0,(S_y_2d>=12'd160)}
                 + {3'b0,(S_y_2d>=12'd240)} + {3'b0,(S_y_2d>=12'd320)}
                 + {3'b0,(S_y_2d>=12'd400)} + {3'b0,(S_y_2d>=12'd480)}
                 + {3'b0,(S_y_2d>=12'd560)} + {3'b0,(S_y_2d>=12'd640)};
        // \u5757\u5185\u504f\u79fb\uff1abx*80 = (bx<<6)+(bx<<4)\uff0c\u65e0\u9664\u6cd5\u5668
        S_mot_xoff = S_x_2d - {S_mot_bx, 6'b0} - {{1'b0, S_mot_bx}, 4'b0};
        S_mot_yoff = S_y_2d - {S_mot_by, 6'b0} - {1'b0, S_mot_by, 4'b0};
        // \u63a9\u7801\u5e03\u5c40\u662f idx = by*16 + bx\uff08\u89c1 motion_detect.v\uff09\uff0cbx \u53d6\u4f4e 4 \u4f4d
        S_mot_on   = I_mot_en && I_mot_mask[{1'b0, S_mot_by, S_mot_bx[3:0]}] &&
                     ( (S_mot_xoff < 12'd3) || (S_mot_xoff > 12'd76) ||
                       (S_mot_yoff < 12'd3) || (S_mot_yoff > 12'd76) );
        if(S_mot_on) begin
            S_osd_hit   = 1'b1;
            S_osd_color = COLOR_MOT_TEXT;
        end
        // ---- [HDR-2026-10-17] 第 7 层：颜色目标检测块描边（绿色，优先级低于运动框）----
        //   与第 5 层同一套块索引逻辑，只换掩码源与颜色；块网格 16x9、块尺寸 80x80。
        S_obj_bx = 5'd0
                 + {4'b0,(S_x_2d>=12'd80 )} + {4'b0,(S_x_2d>=12'd160)}
                 + {4'b0,(S_x_2d>=12'd240)} + {4'b0,(S_x_2d>=12'd320)}
                 + {4'b0,(S_x_2d>=12'd400)} + {4'b0,(S_x_2d>=12'd480)}
                 + {4'b0,(S_x_2d>=12'd560)} + {4'b0,(S_x_2d>=12'd640)}
                 + {4'b0,(S_x_2d>=12'd720)} + {4'b0,(S_x_2d>=12'd800)}
                 + {4'b0,(S_x_2d>=12'd880)} + {4'b0,(S_x_2d>=12'd960)}
                 + {4'b0,(S_x_2d>=12'd1040)}+ {4'b0,(S_x_2d>=12'd1120)}
                 + {4'b0,(S_x_2d>=12'd1200)};
        S_obj_by = 4'd0
                 + {3'b0,(S_y_2d>=12'd80 )} + {3'b0,(S_y_2d>=12'd160)}
                 + {3'b0,(S_y_2d>=12'd240)} + {3'b0,(S_y_2d>=12'd320)}
                 + {3'b0,(S_y_2d>=12'd400)} + {3'b0,(S_y_2d>=12'd480)}
                 + {3'b0,(S_y_2d>=12'd560)} + {3'b0,(S_y_2d>=12'd640)};
        S_obj_xoff = S_x_2d - {S_obj_bx, 6'b0} - {{1'b0, S_obj_bx}, 4'b0};
        S_obj_yoff = S_y_2d - {S_obj_by, 6'b0} - {1'b0, S_obj_by, 4'b0};
        S_obj_on   = obj_self && obj_in && (
                   ( ((S_obj_xoff == 12'd10) || (S_obj_xoff == 12'd11)) && ~obj_lft ) ||
                   ( ((S_obj_xoff == 12'd68) || (S_obj_xoff == 12'd69)) && ~obj_rgt ) ||
                   ( ((S_obj_yoff == 12'd10) || (S_obj_yoff == 12'd11)) && ~obj_up  ) ||
                   ( ((S_obj_yoff == 12'd68) || (S_obj_yoff == 12'd69)) && ~obj_dn  ) );
        if(S_obj_on) begin
            S_osd_hit   = 1'b1;
            S_osd_color = COLOR_OBJ_TEXT;
        end
    end

//---- 输出流水与像素选择（正常叠加 / 调试彩条 / 调试状态条） ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            S_video_vsync_1d <= 1'b0;  // 复位：输出同步信号与像素数据全部清零
            S_video_vsync_2d <= 1'b0;
            S_video_hsync_1d <= 1'b0;
            S_video_hsync_2d <= 1'b0;
            S_video_de_1d    <= 1'b0;
            S_video_de_2d    <= 1'b0;
            O_hdmi_vsync     <= 1'b0;
            O_hdmi_hsync     <= 1'b0;
            O_hdmi_de        <= 1'b0;
            O_hdmi_data      <= 24'd0;
        end
        else begin
            S_video_vsync_1d <= I_video_vsync;  // vsync/hsync/de 各打 2 拍，与数据及 OSD 判定同相位
            S_video_vsync_2d <= S_video_vsync_1d;
            O_hdmi_vsync     <= S_video_vsync_2d;

            S_video_hsync_1d <= I_video_hsync;
            S_video_hsync_2d <= S_video_hsync_1d;
            O_hdmi_hsync     <= S_video_hsync_2d;

            S_video_de_1d    <= I_video_de;
            S_video_de_2d    <= S_video_de_1d;
            O_hdmi_de        <= S_video_de_2d;
            S_video_data_1d  <= I_video_rd_data;
            S_video_data_2d  <= S_video_data_1d;

            if(DEBUG_MODE == 1) begin  // 调试模式 1：8 条等宽竖彩条，每条 128 像素（红/绿/蓝/黄/青/品红/白/暗灰）
                if(S_video_de_2d) begin
                    if(S_x < 12'd128)
                        O_hdmi_data <= 24'hff0000;
                    else if(S_x < 12'd256)
                        O_hdmi_data <= 24'h00ff00;
                    else if(S_x < 12'd384)
                        O_hdmi_data <= 24'h0000ff;
                    else if(S_x < 12'd512)
                        O_hdmi_data <= 24'hffff00;
                    else if(S_x < 12'd640)
                        O_hdmi_data <= 24'h00ffff;
                    else if(S_x < 12'd768)
                        O_hdmi_data <= 24'hff00ff;
                    else if(S_x < 12'd896)
                        O_hdmi_data <= 24'hffffff;
                    else
                        O_hdmi_data <= 24'h202020;
                end
                else begin
                    O_hdmi_data <= 24'd0;
                end
            end
            else if(DEBUG_MODE == 2) begin  // 调试模式 2：按 I_debug_status 给整屏纯色；4'b1111 视为“全好”并透传真实像素
                if(S_video_de_2d) begin
                    case (I_debug_status)
                        4'b0000: O_hdmi_data <= 24'h000000;
                        4'b0001: O_hdmi_data <= 24'hff0000;
                        4'b0011: O_hdmi_data <= 24'hffff00;
                        4'b0111: O_hdmi_data <= 24'h00ff00;
                        4'b1111: O_hdmi_data <= I_video_rd_data;
                        default: O_hdmi_data <= 24'h0000ff;
                    endcase
                end
                else begin
                    O_hdmi_data <= 24'd0;
                end
            end
            else if(DEBUG_MODE == 3) begin  // 调试模式 3：4 段各 256 宽的状态条，每段对应 1 个 debug bit（亮=1，暗=0）
                if(S_video_de_2d) begin
                    if(S_x < 12'd256)
                        O_hdmi_data <= I_debug_status[0] ? 24'hff8000 : 24'h201000;
                    else if(S_x < 12'd512)
                        O_hdmi_data <= I_debug_status[1] ? 24'hffff00 : 24'h202000;
                    else if(S_x < 12'd768)
                        O_hdmi_data <= I_debug_status[2] ? 24'hff0000 : 24'h200000;
                    else
                        O_hdmi_data <= I_debug_status[3] ? 24'h00ffff : 24'h002020;
                end
                else begin
                    O_hdmi_data <= 24'd0;
                end
            end
//------ 正常显示分支（DEBUG_MODE==0）：可选调试条 + OSD 叠加 + 画面透传 ------
            else begin
                //--------------------------------------------------------------
                // [DBG] 调试状态条：4 根竖条贴在画面最左侧 x=0..5
                //   优先级最高，方便一眼看到 DDR 写/读/返回/非零 四个状态
                //--------------------------------------------------------------
                if(SHOW_DEBUG != 0 && S_video_de_2d && (S_x_2d < 12'd6)) begin  // 正常模式下的可选调试条：x=0..5 的 4 根竖条，绿=bit 为 1、暗红=0；y>=480 之后透传画面
                    if(S_y_2d < 12'd120)
                        O_hdmi_data <= I_debug_status[0] ? 24'h00ff00 : 24'h401010;
                    else if(S_y_2d < 12'd240)
                        O_hdmi_data <= I_debug_status[1] ? 24'h00ff00 : 24'h401010;
                    else if(S_y_2d < 12'd360)
                        O_hdmi_data <= I_debug_status[2] ? 24'h00ff00 : 24'h401010;
                    else if(S_y_2d < 12'd480)
                        O_hdmi_data <= I_debug_status[3] ? 24'h00ff00 : 24'h401010;
                    else
                        O_hdmi_data <= S_video_data_2d;
                end
                else if(S_osd_hit)  // OSD 命中就覆盖，否则直接透传 DDR 读回的像素
                    O_hdmi_data <= S_osd_color;
                else
                    O_hdmi_data <= S_video_data_2d;
            end
        end
    end

//---- 模式打拍流水：跨域同步 -> 本地计数 -> 二级流水 ----
    //==================================================================
    // [MODE-PIPE] 算法模式：跨域 -> 本地计数 -> 第二级流水
    //
    //  为什么不像以前那样把 I_algo_mode 直接当电平用：
    //    1) 直接送组合云会让工具按 24m -> pixel 的跨域约束检查整条路，
    //       实测 Setup WNS = -4.416ns / 24 个违例端点；
    //    2) 只加 2 级同步器也不够：预算里"接收沿必须紧跟发射沿"的那
    //       0.653ns 框住了同步器第一级，仍剩 -0.085ns / 2 个违例端点
    //       （路径起点 u_key_mode_ctrl/O_mode_reg[*]，终点
    //         u_hdmi_mixer/S_algo_mode_sync1_reg[*]，Logic Level = 0）。
    //    3) 只跨域的应该是"变了没有"这件事。所以改成：
    //         - 24m 域(key_mode_ctrl)只发 1 bit 翻转信号,再转成 1 拍脉冲；
    //         - 本模块只同步这 1 bit，在"本域时钟"上数模式。
    //       单 bit 翻转天然无多 bit 不一致问题，且同步器第一级现在
    //       连着 42ns 周期的慢域寄存器，余量充裕，能过。
    //
    //  同时把 2 bit 模式值打一拍再进组合云：
    //    组合云(取字形)与最终输出之间已有 S_video_data_2d 的一级流水，
    //    模式值同样延迟 1 拍才能对齐；顺带把
    //    "模式寄存器 -> 组合取字形 -> 输出寄存器" 的关键路径拆成两半。
    //==================================================================
    reg S_algo_tgl_sync1;  // 三级同步链：前两级做 CDC 同步，第三级与第二级异或用来取边沿
    reg S_algo_tgl_sync2;
    reg S_algo_tgl_sync3;
    wire S_algo_tgl_pulse = S_algo_tgl_sync2 ^ S_algo_tgl_sync3;  // 相邻两级不同 = 发生过一次翻转，产生 1 个时钟宽的脉冲（只在像素域有效）

    // [OUR ALGO] 第二根跨域线：回卷（4→0）。协议与上面完全一致。
    reg S_algo_wrap_sync1;  // 回卷线使用完全相同的“同步 + 取沿”结构
    reg S_algo_wrap_sync2;
    reg S_algo_wrap_sync3;
    wire S_algo_wrap_pulse = S_algo_wrap_sync2 ^ S_algo_wrap_sync3;

    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            S_algo_tgl_sync1 <= 1'b0;
            S_algo_tgl_sync2 <= 1'b0;
            S_algo_tgl_sync3 <= 1'b0;
            S_algo_wrap_sync1 <= 1'b0;
            S_algo_wrap_sync2 <= 1'b0;
            S_algo_wrap_sync3 <= 1'b0;
        end
        else begin
            S_algo_tgl_sync1 <= I_algo_mode_tgl;  // 逐级打拍：既做同步，也保留历史值供异或取沿
            S_algo_tgl_sync2 <= S_algo_tgl_sync1;
            S_algo_tgl_sync3 <= S_algo_tgl_sync2;
            S_algo_wrap_sync1 <= I_algo_mode_wrap;
            S_algo_wrap_sync2 <= S_algo_wrap_sync1;
            S_algo_wrap_sync3 <= S_algo_wrap_sync2;
        end
    end

    reg [2:0] S_algo_mode;  // 本地模式寄存器：真正的模式值在像素域数出来，不从跨域电平直接取
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            S_algo_mode <= 3'd0;              // 上电默认 MODE0，与 key_mode_ctrl / my_algo.MODE_INIT 保持一致
        else if(S_algo_wrap_pulse)  // 回卷事件优先处理：强制回 0，纠正漏计数造成的错位
            S_algo_mode <= 3'd0;              // 回卷事件：强制回到 0，纠正漏计数
        else if(S_algo_tgl_pulse)
            S_algo_mode <= (S_algo_mode == 3'd4) ? 3'd0 : (S_algo_mode + 3'd1); // 0→1→2→3→4→0
    end

    // [已提前到文件前部声明，见 S_alg_on 之后]
    always @(posedge I_clk or negedge I_rst_n) begin  // 再打一拍：与像素数据/坐标的第二级流水对齐，供组合逻辑取字形使用
        if(!I_rst_n)
            S_algo_mode_2d <= 3'd0;
        else
            S_algo_mode_2d <= S_algo_mode;  // 组合取字形时实际使用的模式值
    end

endmodule
