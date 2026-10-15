//============================================================================
//  motion_detect.v  —  块级帧差运动检测（赛题「高阶挑战项 4：硬件运动目标检测」）
//============================================================================
//  设计要点
//  ---------------------------------------------------------------------------
//  1) 纯流水、零帧存：把画面划成 16x9 = 144 个块（1280x720 下每块 80x80 像素），
//     **只存上一帧每块的亮度均值**（144 个 8bit），当前帧边扫边累加同一块的亮度和，
//     扫到块行末再与上帧均值比较。存储从 921600 B（整帧）降到 144 B。
//  2) 只用移位加法与比较，**无乘法器、无除法器、无 ERAM**。
//  3) 输出给 OSD 的运动位图 + 运动块计数。
//
//  坐标系
//  ---------------------------------------------------------------------------
//  输入为 ISP 域 96bit/4 像素：{R3,G3,B3, R2,G2,B2, R1,G1,B1, R0,G0,B0}
//  每行 320 beat、每 beat 4 像素、每帧 720 行。
//  块列 = beat / 20（每块列 20 beat = 80 像素）；块行 = 行 / 80。
//  一个块 = 20 beat x 80 行 x 4 像素 = 6400 像素，亮度和最大 6400*255 = 1.63e6 < 2^21。
//  块均值（8bit 域）= 和 >> 13（等价于真实均值 x 0.781，阈值取同域即可）。
//
//  O_blk_mask 位序 idx = by*16 + bx（by 0..8，bx 0..15），OSD 用 (x/80, y/80) 取位。
//============================================================================

module motion_detect #(
    parameter [11:0] H_BEATS       = 12'd320,   // 每行 beat 数（1280/4）
    parameter [11:0] V_LINES       = 12'd720,   // 每帧行数
    parameter [4:0]  BEATS_PER_BLK = 5'd20,     // 每块列跨的 beat 数（80/4）
    parameter [6:0]  LINES_PER_BLK = 7'd80,     // 每块行跨的行数
    parameter [7:0]  DIFF_TH       = 8'd10,     // 块均值差阈值（>>13 域）
    parameter [7:0]  FLOOR_TH      = 8'd6,      // 块亮度下限，抑制纯黑噪声
    parameter        STRICT2       = 1'b1       // 1 = 连续两帧都动才算
)(
    input  wire         I_clk,
    input  wire         I_rst_n,
    input  wire         I_bypass,       // 1 = 直通（冻结位图与计数）
    input  wire [95:0]  I_tdata,
    input  wire         I_tvalid,
    input  wire         I_tuser,        // 帧起始
    input  wire         I_tlast,        // 行结束

    output reg  [143:0] O_blk_mask,     // 运动位图（持久，供 OSD 整帧读取）
    output reg  [7:0]   O_blk_cnt,      // 本帧运动块个数
    output reg          O_motion_any,
    output reg  [7:0]   O_dbg_cur,      // 调试：样本块当前均值
    output reg  [7:0]   O_dbg_prev      // 调试：样本块上帧均值
);

    //------------------------------------------------------------------------
    // 像素亮度：Y = (77R + 150G + 29B) >> 8，全移位加法
    //------------------------------------------------------------------------
    function [15:0] F_luma(input [23:0] px);
        reg [15:0] r, g, b;
        begin
            r = {8'd0, px[23:16]};
            g = {8'd0, px[15:8]};
            b = {8'd0, px[7:0]};
            F_luma = ((r<<6) + (r<<3) + (r<<2) + r
                    + (g<<7) + (g<<4) + (g<<2) + (g<<1)
                    + (b<<4) + (b<<3) + (b<<2) + b) >> 8;
        end
    endfunction

    //------------------------------------------------------------------------
    // 位置计数（单一 always 块）
    //------------------------------------------------------------------------
    reg [11:0] S_bx;                      // beat 0 .. H_BEATS-1
    reg [11:0] S_y;                       // 行   0 .. V_LINES-1
    reg [4:0]  S_bxc;                     // 块列 0 .. 15
    reg [4:0]  S_bcnt;                    // 块内 beat 0 .. 19
    reg [3:0]  S_byc;                     // 块行 0 .. 8
    reg [6:0]  S_lyc;                     // 块行内行号 0 .. 79

    wire S_line_end   = I_tvalid & I_tlast;
    wire S_beat_last  = (S_bx == (H_BEATS[11:0] - 12'd1)) | S_line_end;
    wire S_blkcol_last= (S_bcnt == (BEATS_PER_BLK - 5'd1)) | S_beat_last;
    // ★块行内行号计数器★ y mod 80 不能用位切片表达（80 = 64+16），必须自己数
    wire S_blkrow_last= (S_lyc == (LINES_PER_BLK[6:0] - 7'd1));
    wire S_update     = I_tvalid & S_blkrow_last & S_beat_last & !I_bypass;

    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            S_bx   <= 12'd0;
            S_y    <= 12'd0;
            S_bxc  <= 5'd0;
            S_bcnt <= 5'd0;
        end else if (I_tuser) begin
            S_bx   <= 12'd0;
            S_y    <= 12'd0;
            S_bxc  <= 5'd0;
            S_bcnt <= 5'd0;
            S_lyc  <= 7'd0;
        end else if (S_line_end) begin
            S_bx   <= 12'd0;
            S_bcnt <= 5'd0;
            S_bxc  <= 5'd0;
            S_lyc  <= (S_lyc == (LINES_PER_BLK[6:0] - 7'd1)) ? 7'd0 : (S_lyc + 7'd1);
            S_y    <= (S_y == (V_LINES[11:0] - 12'd1)) ? 12'd0 : (S_y + 12'd1);
        end else if (I_tvalid) begin
            S_bx <= S_beat_last ? S_bx : (S_bx + 12'd1);
            if (S_blkcol_last) begin
                S_bcnt <= 5'd0;
                S_bxc  <= (S_bxc == 5'd15) ? 5'd15 : (S_bxc + 5'd1);
            end else begin
                S_bcnt <= S_bcnt + 5'd1;
            end
        end
    end

    // [HDR-2026-10-15c] S_byc 从上面那个 always 块里拆出来单独成块。
    //   TD 对上面那种「先 if/else 链、再跟一条独立 if」的写法报
    //   HDL-8007 ERROR: if-condition does not match any sensitivity list edge
    //   （syn_1 因此拒绝执行，phy_1 拿着旧库照跑，产出的是上一版的 bit）。
    //   拆成独立块后每个 reg 只由唯一一个 always 块驱动，TD 接受。
    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n)      S_byc <= 4'd0;
        else if (I_tuser)  S_byc <= 4'd0;
        else if (S_update) S_byc <= (S_byc == 4'd8) ? 4'd0 : (S_byc + 4'd1);
    end

    //------------------------------------------------------------------------
    // 亮度与像素和
    //------------------------------------------------------------------------
    wire [15:0] S_y0 = F_luma(I_tdata[23:0]);
    wire [15:0] S_y1 = F_luma(I_tdata[47:24]);
    wire [15:0] S_y2 = F_luma(I_tdata[71:48]);
    wire [15:0] S_y3 = F_luma(I_tdata[95:72]);
    wire [17:0] S_bsum = {2'b00, S_y0} + {2'b00, S_y1} + {2'b00, S_y2} + {2'b00, S_y3};

    //------------------------------------------------------------------------
    // 累加 + 块行末比较 + 清零（全部在同一个 always 块，保证单一驱动）
    //------------------------------------------------------------------------
    reg [20:0] S_acc [0:15];             // 当前块行的 16 个块列亮度和
    reg [7:0]  S_prev [0:8][0:15];       // 上帧每块均值
    reg [143:0] S_hit1;                  // 上帧是否已命中（STRICT2）
    reg         S_first;                 // 复位后第一帧无参考

    reg [7:0]  S_cur_k [0:15];           // 组合：本块行各块均值
    reg [15:0] S_row_mask, S_row_hit;
    reg [7:0]  S_row_cnt;
    reg        S_row_any;

    integer i, k;
    always @* begin
        for (k = 0; k < 16; k = k + 1) S_cur_k[k] = S_acc[k][20:13];
    end

    always @* begin
        S_row_mask = 16'd0;
        S_row_hit  = 16'd0;
        S_row_cnt  = 8'd0;
        S_row_any  = 1'b0;
        for (k = 0; k < 16; k = k + 1) begin
            if (S_cur_k[k] > S_prev[S_byc][k])
                S_row_hit[k] = ((S_cur_k[k] - S_prev[S_byc][k]) > DIFF_TH && S_cur_k[k] > FLOOR_TH);
            else
                S_row_hit[k] = ((S_prev[S_byc][k] - S_cur_k[k]) > DIFF_TH && S_cur_k[k] > FLOOR_TH);
            if (S_row_hit[k] && (!STRICT2 || S_hit1[S_byc*16 + k])) begin
                S_row_mask[k] = 1'b1;
                S_row_cnt = S_row_cnt + 8'd1;
                S_row_any = 1'b1;
            end
        end
    end

    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            O_blk_mask   <= 144'd0;
            O_blk_cnt    <= 8'd0;
            O_motion_any <= 1'b0;
            S_hit1       <= 144'd0;
            S_first      <= 1'b1;
            O_dbg_cur    <= 8'd0;
            O_dbg_prev   <= 8'd0;
            for (i = 0; i < 16; i = i + 1) S_acc[i] <= 21'd0;
            for (i = 0; i <= 8; i = i + 1)
                for (k = 0; k < 16; k = k + 1) S_prev[i][k] <= 8'd0;
        end else begin
            // ---- 累加（默认动作）----
            if (I_tvalid) S_acc[S_bxc] <= S_acc[S_bxc] + {3'b000, S_bsum};

            // ---- 块行末：比较 + 写回 + 清累加器 ----
            if (S_update) begin
                O_blk_mask[S_byc*16 +: 16] <= S_first ? 16'd0 : S_row_mask;
                S_hit1     [S_byc*16 +: 16] <= S_row_hit;
                O_blk_cnt    <= S_first ? 8'd0 : (O_blk_cnt + S_row_cnt);
                O_motion_any <= S_first ? 1'b0 : (O_motion_any | S_row_any);
                O_dbg_cur    <= S_cur_k[0];
                O_dbg_prev   <= S_prev[S_byc][0];
                for (k = 0; k < 16; k = k + 1) begin
                    S_prev[S_byc][k] <= S_cur_k[k];
                    S_acc[k]         <= 21'd0;          // ★清零与累加同块，后者优先 ⇒ 本拍末 4 像素丢弃，占 4/6400 = 0.06%
                end
                if (S_byc == 4'd8) S_first <= 1'b0;     // 首帧走完
            end

            // ---- 帧起始：计数清零，位图保留供本帧 OSD 使用 ----
            if (I_tuser & !I_bypass) begin
                O_blk_cnt    <= 8'd0;
                O_motion_any <= 1'b0;
            end
        end
    end

endmodule
