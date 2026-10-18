// ============================================================================
//  obj_detect.v  —  颜色目标检测（流式 / 分块 / 零帧缓存 / 零除法器）
//  [HDR-2026-10-17]  新增
//    对应赛题：基础扩展项 (2)「基于视频内容的目标检测与识别」
//
//  设计要点（与 motion_detect.v 同一骨架，便于复用与评审解释）
//    1. 画面切成 16 列 × 9 行 = 144 个 80x80 块（索引 idx = by*16 + bx）
//    2. 逐像素判「暖色/红色主导」：R >= LUM_MIN 且 R-G >= CHR_MIN 且 R-B >= CHR_MIN
//    3. 块内命中像素数 > HIT_MIN ⇒ 该块判为目标
//    4. 只输出 144 bit 的块掩码 + 块数 ⇒ 存储从 921600 B 降到 18 B
//    5. 无乘法器、无除法器、无 ERAM、无 DSP
//
//  接口与 awb / lsc / isp_gamma 同构（I_clk / I_tvalid / I_tuser / I_tlast / 96bit）
//   ★ 纯观察者：不参与主通路握手，不改变像素数据 ★
// ============================================================================
`timescale 1ns / 1ps

module obj_detect #(
    parameter [8:0]  H_BEATS       = 9'd320,    // 每行 beat 数（1280/4）
    parameter [11:0] V_LINES       = 12'd720,   // 每帧行数
    parameter [4:0]  BEATS_PER_BLK = 5'd20,     // 每块宽度（beat）= 80 像素
    parameter [6:0]  LINES_PER_BLK = 7'd80,     // 每块高度（行）
    parameter [7:0]  LUM_MIN       = 8'd80,     // 亮度下限（避免暗部误检）
    parameter [7:0]  CHR_MIN       = 8'd35,     // 色度下限（R 与 G/B 的最小差值）
    parameter [12:0] HIT_MIN       = 13'd40     // 块内命中像素数门限（6400 的 0.6%）
)(
    input  wire         I_clk,
    input  wire         I_rst_n,
    input  wire         I_bypass,       // 1 = 直通（清空结果，不出框）
    input  wire [95:0]  I_tdata,        // 4 像素 x 24bit，像素 0 在最低 24 位
    input  wire         I_tvalid,
    input  wire         I_tuser,
    input  wire         I_tlast,

    output reg  [143:0] O_blk_mask,     // 跨帧保持的块掩码
    output reg  [7:0]   O_blk_cnt,      // 命中块数
    output reg          O_obj_any,      // 有目标
    output reg  [15:0]  O_hit_sum       // 本帧命中像素总数（调试用，饱和到 16bit）
);

    // ------------------------------------------------------------------
    //  颜色判定：4 个像素并行
    // ------------------------------------------------------------------
    wire [7:0] p0r = I_tdata[23:16], p0g = I_tdata[15:8],  p0b = I_tdata[7:0];
    wire [7:0] p1r = I_tdata[47:40], p1g = I_tdata[39:32], p1b = I_tdata[31:24];
    wire [7:0] p2r = I_tdata[71:64], p2g = I_tdata[63:56], p2b = I_tdata[55:48];
    wire [7:0] p3r = I_tdata[95:88], p3g = I_tdata[87:80], p3b = I_tdata[79:72];

    // ★ [HDR-2026-10-17-fixwrap] 9 位扩位加法比较 ★
    //   原来用 8bit 无符号减法 p0r-p0g，当 G>R 时回绕成 200+ ⇒ 恒满足 >=CHR_MIN
    //   ⇒ 暗场景大量「R 比 G 小」的像素被判成红色 ⇒ 绿框乱跳。
    //   改成 {1'b0,R} >= {1'b0,G} + CHR_MIN，在 9 位域比较，结构上不可能回绕。
    wire h0 = (p0r >= LUM_MIN) && ({1'b0,p0r} >= ({1'b0,p0g} + {1'b0,CHR_MIN})) && ({1'b0,p0r} >= ({1'b0,p0b} + {1'b0,CHR_MIN}));
    wire h1 = (p1r >= LUM_MIN) && ({1'b0,p1r} >= ({1'b0,p1g} + {1'b0,CHR_MIN})) && ({1'b0,p1r} >= ({1'b0,p1b} + {1'b0,CHR_MIN}));
    wire h2 = (p2r >= LUM_MIN) && ({1'b0,p2r} >= ({1'b0,p2g} + {1'b0,CHR_MIN})) && ({1'b0,p2r} >= ({1'b0,p2b} + {1'b0,CHR_MIN}));
    wire h3 = (p3r >= LUM_MIN) && ({1'b0,p3r} >= ({1'b0,p3g} + {1'b0,CHR_MIN})) && ({1'b0,p3r} >= ({1'b0,p3b} + {1'b0,CHR_MIN}));
    wire [2:0] hit4 = {2'b00, h0} + {2'b00, h1} + {2'b00, h2} + {2'b00, h3};

    // ------------------------------------------------------------------
    //  坐标计数：beat / 行 / 块列 / 块行 / 块内行
    // ------------------------------------------------------------------
    reg [8:0]  S_bx;      // 0..H_BEATS-1
    reg [11:0] S_y;       // 0..V_LINES-1
    reg [4:0]  S_bxn;     // 块列 0..15
    reg [4:0]  S_bxc;     // 块内 beat 0..19
    reg [3:0]  S_byn;     // 块行 0..8
    reg [6:0]  S_lyc;     // 块内行 0..79

    // ★ [HDR-2026-10-17-rowfix] ★ 关键修正
    //   原来把 I_tlast 当成「行末」，但 AXI4-Stream 视频包里 I_tlast 是「帧末」，
    //   一帧只来一次 ⇒ S_lyc/S_byn 变成「每帧 +1」⇒ 一个帧内 S_byn 恒定，
    //   掩码只写同一行；跨 720 帧轮完 9 行后，画面上就看到「一整列贯穿全帧」。
    //   现在：行末用 S_bx 走满 H_BEATS-1 判定，I_tlast 只当帧末用。
    wire S_row_end   = (S_bx == (H_BEATS - 9'd1));              // 一行最后一个 beat
    wire S_line_end  = I_tvalid & I_tlast;                     // 帧末（保留原义）
    wire S_beat_last = (S_bxc == (BEATS_PER_BLK - 5'd1));      // 纯块列末
    wire S_lyc_last  = (S_lyc == (LINES_PER_BLK - 7'd1));      // 块内最后一行

    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            S_bx <= 9'd0; S_y <= 12'd0; S_bxn <= 5'd0; S_bxc <= 5'd0;
            S_byn <= 4'd0; S_lyc <= 7'd0;
        end else if (I_tvalid) begin
            if (I_tuser) begin
                S_bx <= 9'd0; S_y <= 12'd0; S_bxn <= 5'd0; S_bxc <= 5'd0;
                S_byn <= 4'd0; S_lyc <= 7'd0;
            end else begin
                S_bx <= S_row_end ? 9'd0 : (S_bx + 9'd1);
                if (S_row_end) begin                       // ★ 行末 ★
                    S_y   <= (S_y == (V_LINES - 12'd1)) ? 12'd0 : (S_y + 12'd1);
                    S_bxc <= 5'd0;
                    S_bxn <= 5'd0;
                    if (S_lyc_last) begin                  // 块内最后一行 ⇒ 换块行
                        S_lyc <= 7'd0;
                        S_byn <= (S_byn == 4'd8) ? 4'd0 : (S_byn + 4'd1);
                    end else begin
                        S_lyc <= S_lyc + 7'd1;
                    end
                end else if (S_beat_last) begin            // 块列末
                    S_bxc <= 5'd0;
                    S_bxn <= (S_bxn == 5'd15) ? 5'd0 : (S_bxn + 5'd1);
                end else begin
                    S_bxc <= S_bxc + 5'd1;
                end
            end
        end
    end

    // ------------------------------------------------------------------
    //  块内命中累加（16 个 13bit 累加器）
    // ------------------------------------------------------------------
    reg [12:0] S_acc0, S_acc1, S_acc2, S_acc3, S_acc4,  S_acc5,  S_acc6,  S_acc7;
    reg [12:0] S_acc8, S_acc9, S_acc10,S_acc11,S_acc12, S_acc13, S_acc14, S_acc15;

    // 当前 beat 落在哪个块列（0..15），用 one-hot 生成 +1 使能
    reg [15:0] S_col_sel;
    always @(*) begin
        case (S_bxn)
            5'd0:  S_col_sel = 16'h0001;  5'd1:  S_col_sel = 16'h0002;
            5'd2:  S_col_sel = 16'h0004;  5'd3:  S_col_sel = 16'h0008;
            5'd4:  S_col_sel = 16'h0010;  5'd5:  S_col_sel = 16'h0020;
            5'd6:  S_col_sel = 16'h0040;  5'd7:  S_col_sel = 16'h0080;
            5'd8:  S_col_sel = 16'h0100;  5'd9:  S_col_sel = 16'h0200;
            5'd10: S_col_sel = 16'h0400;  5'd11: S_col_sel = 16'h0800;
            5'd12: S_col_sel = 16'h1000;  5'd13: S_col_sel = 16'h2000;
            5'd14: S_col_sel = 16'h4000;  default: S_col_sel = 16'h8000;
        endcase
    end

    wire S_add = I_tvalid & ~I_tuser & ~I_bypass & (hit4 != 3'd0);
    wire [12:0] S_inc = {10'd0, hit4};

    // 块列边界（一个块的最后一 beat）：把累加器清零
    wire S_col_last = S_beat_last;
    wire S_blk_end  = S_beat_last & S_lyc_last;   // ★ [fix8] 80x80 块真正的最后 beat ★
    // 整帧首个有效 beat 之前的复位
    wire S_frame_start = I_tvalid & I_tuser;

    // 用「每个块列边界清零 + 其余时间累加」的方式实现 16 路累加
    // 注意：同一 always 块内同一 reg 只能有一次非阻塞赋值，所以先算 next 再统一写
    wire [12:0] S_acc0_nx  = S_col_sel[0]  ? (S_blk_end ? 13'd0 : (S_acc0  + S_inc)) : S_acc0;
    wire [12:0] S_acc1_nx  = S_col_sel[1]  ? (S_blk_end ? 13'd0 : (S_acc1  + S_inc)) : S_acc1;
    wire [12:0] S_acc2_nx  = S_col_sel[2]  ? (S_blk_end ? 13'd0 : (S_acc2  + S_inc)) : S_acc2;
    wire [12:0] S_acc3_nx  = S_col_sel[3]  ? (S_blk_end ? 13'd0 : (S_acc3  + S_inc)) : S_acc3;
    wire [12:0] S_acc4_nx  = S_col_sel[4]  ? (S_blk_end ? 13'd0 : (S_acc4  + S_inc)) : S_acc4;
    wire [12:0] S_acc5_nx  = S_col_sel[5]  ? (S_blk_end ? 13'd0 : (S_acc5  + S_inc)) : S_acc5;
    wire [12:0] S_acc6_nx  = S_col_sel[6]  ? (S_blk_end ? 13'd0 : (S_acc6  + S_inc)) : S_acc6;
    wire [12:0] S_acc7_nx  = S_col_sel[7]  ? (S_blk_end ? 13'd0 : (S_acc7  + S_inc)) : S_acc7;
    wire [12:0] S_acc8_nx  = S_col_sel[8]  ? (S_blk_end ? 13'd0 : (S_acc8  + S_inc)) : S_acc8;
    wire [12:0] S_acc9_nx  = S_col_sel[9]  ? (S_blk_end ? 13'd0 : (S_acc9  + S_inc)) : S_acc9;
    wire [12:0] S_acc10_nx = S_col_sel[10] ? (S_blk_end ? 13'd0 : (S_acc10 + S_inc)) : S_acc10;
    wire [12:0] S_acc11_nx = S_col_sel[11] ? (S_blk_end ? 13'd0 : (S_acc11 + S_inc)) : S_acc11;
    wire [12:0] S_acc12_nx = S_col_sel[12] ? (S_blk_end ? 13'd0 : (S_acc12 + S_inc)) : S_acc12;
    wire [12:0] S_acc13_nx = S_col_sel[13] ? (S_blk_end ? 13'd0 : (S_acc13 + S_inc)) : S_acc13;
    wire [12:0] S_acc14_nx = S_col_sel[14] ? (S_blk_end ? 13'd0 : (S_acc14 + S_inc)) : S_acc14;
    wire [12:0] S_acc15_nx = S_col_sel[15] ? (S_blk_end ? 13'd0 : (S_acc15 + S_inc)) : S_acc15;

    // ------------------------------------------------------------------
    // ★ [HDR-2026-10-17-fix] 块判决值必须用「含最后一 beat 的当前和」★
    //   原来的写法取 *_nx，而 *_nx 在 S_col_last 那拍被清成 0 ⇒ 判决恒为 0
    //   ⇒ 掩码永远不更新 ⇒ TD 在 RTL 优化时把整个模块当无用逻辑删掉（实测 2 LUT）。
    //   现在：*_fin = S_acc* + S_inc（最后一 beat 也算进去），判决用它；
    //         锁存改为「块结束那拍无条件写」，不再依赖最后一拍有没有命中。
    // ------------------------------------------------------------------
    wire [12:0] S_acc0_fin  = S_acc0  + S_inc;
    wire [12:0] S_acc1_fin  = S_acc1  + S_inc;
    wire [12:0] S_acc2_fin  = S_acc2  + S_inc;
    wire [12:0] S_acc3_fin  = S_acc3  + S_inc;
    wire [12:0] S_acc4_fin  = S_acc4  + S_inc;
    wire [12:0] S_acc5_fin  = S_acc5  + S_inc;
    wire [12:0] S_acc6_fin  = S_acc6  + S_inc;
    wire [12:0] S_acc7_fin  = S_acc7  + S_inc;
    wire [12:0] S_acc8_fin  = S_acc8  + S_inc;
    wire [12:0] S_acc9_fin  = S_acc9  + S_inc;
    wire [12:0] S_acc10_fin = S_acc10 + S_inc;
    wire [12:0] S_acc11_fin = S_acc11 + S_inc;
    wire [12:0] S_acc12_fin = S_acc12 + S_inc;
    wire [12:0] S_acc13_fin = S_acc13 + S_inc;
    wire [12:0] S_acc14_fin = S_acc14 + S_inc;
    wire [12:0] S_acc15_fin = S_acc15 + S_inc;

    // 块结束那拍无条件锁存（不再 & S_add）
    wire S_blk_hit = S_blk_end;

    // ★ [HDR-2026-10-18-iso] 孤立块滤除（erosion-by-neighbour）★
    //   空场景实测存在「单个孤立块」误检（13:11:45 那张，block row0/col7）。
    //   真实目标必然跨多个块（红笔竖放跨 5+ 块行），孤立单块一定是颜色噪声。
    //   规则：保留「自身命中且 4 邻域至少还有一个命中」的块；单块凸起顺便被削掉。
    function [143:0] F_iso;
        input [143:0] m;
        integer by, bx;
        reg hit;
        begin
            F_iso = 144'd0;
            for (by = 0; by < 9; by = by + 1) begin
                for (bx = 0; bx < 16; bx = bx + 1) begin
                    hit = m[by*16 + bx]
                       && ( (bx > 0  && m[by*16 + bx - 1    ])
                         || (bx < 15 && m[by*16 + bx + 1    ])
                         || (by > 0  && m[(by-1)*16 + bx    ])
                         || (by < 8  && m[(by+1)*16 + bx    ]) );
                    F_iso[by*16 + bx] = hit;
                end
            end
        end
    endfunction

    // ★ [HDR-2026-10-18-A2] 目标跟踪：漏检保持 ★
    //   目标被短暂遮挡/漏检时，把最近一次非空掩码保持 A2_HOLD 帧再消退，
    //   屏幕上表现为「框不闪、不瞬断」——这是「目标跟踪」相对「逐帧检测」的实质差别。
    localparam [5:0] A2_HOLD = 6'd60;
    reg [143:0] S_hold;     // 最近一次非空（已滤除）掩码
    reg  [5:0]  S_holdc;    // 剩余保持帧数
    wire [143:0] S_clean = F_iso(S_now & S_prev);
    reg [143:0] S_now;      // [fix8] 本帧原始判决
    reg [143:0] S_prev;     // [fix8] 上一帧原始判决

    wire [143:0] S_hit_vec = {
        (S_acc15_fin >= HIT_MIN), (S_acc14_fin >= HIT_MIN), (S_acc13_fin >= HIT_MIN), (S_acc12_fin >= HIT_MIN),
        (S_acc11_fin >= HIT_MIN), (S_acc10_fin >= HIT_MIN), (S_acc9_fin  >= HIT_MIN), (S_acc8_fin  >= HIT_MIN),
        (S_acc7_fin  >= HIT_MIN), (S_acc6_fin  >= HIT_MIN), (S_acc5_fin  >= HIT_MIN), (S_acc4_fin  >= HIT_MIN),
        (S_acc3_fin  >= HIT_MIN), (S_acc2_fin  >= HIT_MIN), (S_acc1_fin  >= HIT_MIN), (S_acc0_fin  >= HIT_MIN)
    };

    // ------------------------------------------------------------------
    //  掩码 / 计数 / 总命中数
    // ------------------------------------------------------------------
    integer i;
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            S_acc0 <= 13'd0; S_acc1 <= 13'd0; S_acc2 <= 13'd0; S_acc3 <= 13'd0;
            S_acc4 <= 13'd0; S_acc5 <= 13'd0; S_acc6 <= 13'd0; S_acc7 <= 13'd0;
            S_acc8 <= 13'd0; S_acc9 <= 13'd0; S_acc10 <= 13'd0; S_acc11 <= 13'd0;
            S_acc12 <= 13'd0; S_acc13 <= 13'd0; S_acc14 <= 13'd0; S_acc15 <= 13'd0;
            O_blk_mask <= 144'd0;
            O_blk_cnt  <= 8'd0;
            O_obj_any  <= 1'b0;
            O_hit_sum  <= 16'd0;
            S_now      <= 144'd0;
            S_prev     <= 144'd0;
            S_hold     <= 144'd0;
            S_holdc    <= 6'd0;
        end else begin
            // 累加（块列边界那拍清零，同时该块的判定结果写入下面）
            S_acc0  <= S_frame_start ? 13'd0 : S_acc0_nx;
            S_acc1  <= S_frame_start ? 13'd0 : S_acc1_nx;
            S_acc2  <= S_frame_start ? 13'd0 : S_acc2_nx;
            S_acc3  <= S_frame_start ? 13'd0 : S_acc3_nx;
            S_acc4  <= S_frame_start ? 13'd0 : S_acc4_nx;
            S_acc5  <= S_frame_start ? 13'd0 : S_acc5_nx;
            S_acc6  <= S_frame_start ? 13'd0 : S_acc6_nx;
            S_acc7  <= S_frame_start ? 13'd0 : S_acc7_nx;
            S_acc8  <= S_frame_start ? 13'd0 : S_acc8_nx;
            S_acc9  <= S_frame_start ? 13'd0 : S_acc9_nx;
            S_acc10 <= S_frame_start ? 13'd0 : S_acc10_nx;
            S_acc11 <= S_frame_start ? 13'd0 : S_acc11_nx;
            S_acc12 <= S_frame_start ? 13'd0 : S_acc12_nx;
            S_acc13 <= S_frame_start ? 13'd0 : S_acc13_nx;
            S_acc14 <= S_frame_start ? 13'd0 : S_acc14_nx;
            S_acc15 <= S_frame_start ? 13'd0 : S_acc15_nx;

            // 每个块判定完成时把该列对应的掩码位更新
            if (S_blk_hit) begin
                case (S_bxn)
                    5'd0:  S_now[{S_byn, 4'd0 }] <= S_hit_vec[0 ];
                    5'd1:  S_now[{S_byn, 4'd1 }] <= S_hit_vec[1 ];
                    5'd2:  S_now[{S_byn, 4'd2 }] <= S_hit_vec[2 ];
                    5'd3:  S_now[{S_byn, 4'd3 }] <= S_hit_vec[3 ];
                    5'd4:  S_now[{S_byn, 4'd4 }] <= S_hit_vec[4 ];
                    5'd5:  S_now[{S_byn, 4'd5 }] <= S_hit_vec[5 ];
                    5'd6:  S_now[{S_byn, 4'd6 }] <= S_hit_vec[6 ];
                    5'd7:  S_now[{S_byn, 4'd7 }] <= S_hit_vec[7 ];
                    5'd8:  S_now[{S_byn, 4'd8 }] <= S_hit_vec[8 ];
                    5'd9:  S_now[{S_byn, 4'd9 }] <= S_hit_vec[9 ];
                    5'd10: S_now[{S_byn, 4'd10}] <= S_hit_vec[10];
                    5'd11: S_now[{S_byn, 4'd11}] <= S_hit_vec[11];
                    5'd12: S_now[{S_byn, 4'd12}] <= S_hit_vec[12];
                    5'd13: S_now[{S_byn, 4'd13}] <= S_hit_vec[13];
                    5'd14: S_now[{S_byn, 4'd14}] <= S_hit_vec[14];
                    default: S_now[{S_byn, 4'd15}] <= S_hit_vec[15];
                endcase
            end

            // bypass：清空（SW 一拨下就立刻没框，不是冻结）
            if (I_bypass) begin
                O_blk_mask <= 144'd0;
                S_now      <= 144'd0;
                S_prev     <= 144'd0;
                S_hold     <= 144'd0;
                S_holdc    <= 6'd0;
                O_blk_cnt  <= 8'd0;
                O_obj_any  <= 1'b0;
                O_hit_sum  <= 16'd0;
            end

            // 帧起始：清计数；块行结束时统计该行的命中块数
            if (S_frame_start) begin
                O_blk_cnt <= 8'd0;
                O_hit_sum <= 16'd0;
            end
            if (S_add)
                O_hit_sum <= (O_hit_sum > 16'hFFF0) ? 16'hFFFF : (O_hit_sum + {13'd0, hit4});

            // 每块判决完成就累加块计数
            // ★ [HDR-2026-10-17-fix2] 必须限定在「块行最后一行」才计数 ★
            //   因为 S_bxc 每 20 beat 归零一次，一帧里同一列会被判 80 次/块行，
            //   不限定就会重复计 80 倍（TB 实测 saturate 到 255，期望 72）。
            if (S_blk_hit && S_hit_vec[S_bxn])   // [fix8] S_blk_hit 已含块内最后一行
                O_blk_cnt <= (O_blk_cnt == 8'd255) ? 8'd255 : (O_blk_cnt + 8'd1);

            // 帧末更新 obj_any
            // ★ [HDR-2026-10-17-fix3] 改成「由掩码直接组合产生」，不再依赖块计数 ★
            //   块计数的精确统计依赖 S_lyc 与 S_bxc 的相位对齐，TB 里验证到掩码正确
            //   但计数会退化；obj_any 是 OSD/上层的唯一用途，直接用掩码最可靠。
            // ★ [fix8] 帧末合成：本帧 & 上一帧 ⇒ 单帧噪声被滤掉 ★
            if (S_line_end && (S_y == (V_LINES - 12'd1))) begin
                // ★ [A2] 本帧有目标 ⇒ 刷新保持；无目标 ⇒ 递减保持计数 ★
                // ★ [A2-fix9] 刷新条件从 S_clean 放宽到「本帧有任何原始命中」★
                //   原逻辑只在 S_clean(两帧 AND + 孤立块滤除) 非空时刷新窗口。
                //   目标在画面边缘/被手部分遮挡时 S_now 有零星命中但 S_clean 过不了
                //   两帧确认 ⇒ 窗口被白白消耗，等真正完全遮挡到来时计数器已经很低，
                //   框提前消失（板上实测：遮挡 0.68 s 就没了，而窗口名义上是 1.0 s）。
                //   改成 S_now 非空即刷新：目标还在就不消耗窗口，只在不命中时倒数。
                if (S_clean != 144'd0) begin
                    S_hold  <= S_clean;      // 有可靠目标 ⇒ 同时刷新保持的掩码
                    S_holdc <= A2_HOLD;
                end else if (S_now != 144'd0) begin
                    S_holdc <= A2_HOLD;      // 有原始命中但不满足两帧确认 ⇒ 只刷新窗口，不换掩码
                end else if (S_holdc != 6'd0) begin
                    S_holdc <= S_holdc - 6'd1;   // 本帧完全没有命中 ⇒ 消耗窗口
                end
                O_blk_mask <= (S_clean != 144'd0) ? S_clean :
                              ((S_holdc != 6'd0) ? S_hold : 144'd0);
                S_prev     <= S_now;
                S_now      <= 144'd0;
            end
            // obj_any 在帧末由新掩码决定（见上面的帧末块）
            if (S_line_end && (S_y == (V_LINES - 12'd1)))
                O_obj_any <= ((S_clean != 144'd0) || (S_holdc != 6'd0));   // [A2-fix9] 与 O_blk_mask 口径一致（含保持）
        end
    end

endmodule
