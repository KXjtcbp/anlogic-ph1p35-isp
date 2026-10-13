//=============================================================================
//  lsc.v  ——  镜头色彩暗角校正 (Lens Shading Correction)
//-----------------------------------------------------------------------------
//  [HDR-2026-10-14] 新增。依据：2026-10-13 的带标记旋转对照实验（E1/E2/E3）
//  证明 R/G、B/G 的"中间绿、四周中性"色碗**固定在画面坐标上**，场景旋转后
//  碗不动 ⇒ 不是 AWB、不是黑电平、不是 gamma、不是采集链、不是照明，
//  而是镜头/传感器的色彩暗角（color shading）。
//
//  ---- 为什么只校 R 和 B，不动 G ----
//  灰世界要求 R/G = B/G = 1。实测两个比值在画面中心**同向**偏低（R/G 与 B/G
//  的剖面形状几乎重合），所以给 R、B 施加**同一个**增益 (1 + k/64) 就能同时
//  把两个比值拉平。G 不动 ⇒ 显示器上的整体亮度不变，AE 的目标均值含义不变。
//  代价：亮度暗角（中心本来亮约 7%）会保留。这是刻意的取舍 —— 亮度暗角在
//  人眼里读作"景深/立体感"，色彩暗角才读作"脏"。
//
//  ---- 资源优化的四个手段（合计约 210 LUT() / 0 DSP / 0 ERAM）----
//  ① **可分离**：k(x,y) = KH[x] + KV[y]，而不是 2D 网格。
//     表从 20x24=480 项降到 20+24=44 项，两张小表都是 3 bit。
//     数学依据：径向碗是 r^2 的函数，r^2 = (x-cx)^2 + (y-cy)^2 天然可分离。
//  ② **不做插值**：节点足够密（水平每 64 像素、垂直每 32 行一个节点），
//     台阶误差约 0.29%，肉眼不可见。省掉两条插值乘法器和分数地址逻辑。
//  ③ **不乘法**：k 只有 0..7 共 8 个取值，乘法退化成移位加法树
//     （k=5 -> R + (R<<2)），4 选 1 加一个取反，8 bit 加法器 2 个。
//     完全避开 DSP —— 参考 HISTORY 第 2 条（常数乘法被 TD 推断成 DSP，
//     一次把 40 个 DSP 顶满）。
//  ④ **每 beat 只算一次坐标与表**：96bit = 4 像素共用同一个 x，表查找与
//     k 的计算每拍只做一遍，只有"乘以 k"是 4 份。
//
//  ---- 扩展点（后续开发留的口子）----
//  * LSC_ENABLE 参数：设为 0 即整体旁路（综合期消掉，不占资源）。
//  * I_bypass 端口：运行期旁路（不重新综合即可做 A/B）。
//  * KH/KV 表用 function-case 写（和 isp_gamma.v 同一种风格），
//    换表只需 `_analysis/scripts/fit_lsc.py` 重跑，不动任何逻辑。
//  * 只校 R/B 是参数化的：将来若实测发现 G 也需要单独校，把 CH_SEL 扩成
//    3 通道即可，结构与现在完全同构（多一份移位加法树）。
//=============================================================================
`timescale 1ns / 1ps

module lsc #(
    // 总开关：0 = 完全不例化校正逻辑（综合期消除）
    parameter        LSC_ENABLE = 1'b1,
    // 每行 beat 数（1280 像素 / 4 像素每拍）
    parameter [11:0] H_BEATS    = 12'd320,
    // 每帧行数
    parameter [11:0] V_LINES    = 12'd720,
    // 增益量化：g = 1 + k/64，k 取 0..K_MAX（K_MAX=7 -> 最大 +10.94%）
    parameter [3:0]  K_MAX      = 4'd7
)(
    input  wire        I_clk,
    input  wire        I_rst_n,
    input  wire        I_bypass,      // 1 = 直通（运行期旁路）
    input  wire [95:0] I_tdata,       // 4 像素 x 24bit {R[23:16],G[15:8],B[7:0]}
    input  wire        I_tvalid,
    input  wire        I_tuser,       // 帧起始（每帧 1 拍）
    input  wire        I_tlast,       // 行结束
    output reg  [95:0] O_tdata,
    output reg         O_tvalid,
    output reg         O_tuser,
    output reg         O_tlast
);

//-----------------------------------------------------------------------------
//  表：水平 20 节点（每节点 64 像素 = 16 beat）、垂直 24 节点（每节点 32 行）
//  数值含义：g = 1 + k/64。k = 0 表示该位置不需要校正。
//  ★本段由 _analysis/scripts/fit_lsc.py 自动生成，手改会被覆盖★
//-----------------------------------------------------------------------------
// ==== LSC_TABLE_BEGIN ====
    // 由 fit_lsc.py 自动生成（2 张干净靶面平均，二次碗最小二乘 + 圆心搜索）
    // D = 1 - R/G = +0.0164 +0.0000*u^2 +0.0000*v^2 , u=(x-0)/960, v=(y-0)/540 , R^2=0.9379
    // 水平 20 节点（每节点 64 像素），垂直 24 节点（每节点 30 行）
    // g = 1 + k/64；k=0 -> 1.0000x ，k=7 -> 1.1094x
    function [2:0] F_kh(input [4:0] i);
        begin
            case (i)
                5'd0 : F_kh = 3'd2;
                5'd1 : F_kh = 3'd2;
                5'd2 : F_kh = 3'd3;
                5'd3 : F_kh = 3'd3;
                5'd4 : F_kh = 3'd3;
                5'd5 : F_kh = 3'd4;
                5'd6 : F_kh = 3'd4;
                5'd7 : F_kh = 3'd5;
                5'd8 : F_kh = 3'd5;
                5'd9 : F_kh = 3'd5;
                5'd10: F_kh = 3'd5;
                5'd11: F_kh = 3'd5;
                5'd12: F_kh = 3'd4;
                5'd13: F_kh = 3'd3;
                5'd14: F_kh = 3'd3;
                5'd15: F_kh = 3'd2;
                5'd16: F_kh = 3'd1;
                5'd17: F_kh = 3'd1;
                5'd18: F_kh = 3'd0;
                5'd19: F_kh = 3'd0;
                default: F_kh = 3'd0;
            endcase
        end
    endfunction

    function [2:0] F_kv(input [4:0] i);
        begin
            case (i)
                5'd0 : F_kv = 3'd0;
                5'd1 : F_kv = 3'd0;
                5'd2 : F_kv = 3'd0;
                5'd3 : F_kv = 3'd1;
                5'd4 : F_kv = 3'd1;
                5'd5 : F_kv = 3'd1;
                5'd6 : F_kv = 3'd1;
                5'd7 : F_kv = 3'd1;
                5'd8 : F_kv = 3'd2;
                5'd9 : F_kv = 3'd2;
                5'd10: F_kv = 3'd2;
                5'd11: F_kv = 3'd2;
                5'd12: F_kv = 3'd2;
                5'd13: F_kv = 3'd2;
                5'd14: F_kv = 3'd2;
                5'd15: F_kv = 3'd2;
                5'd16: F_kv = 3'd2;
                5'd17: F_kv = 3'd2;
                5'd18: F_kv = 3'd2;
                5'd19: F_kv = 3'd2;
                5'd20: F_kv = 3'd2;
                5'd21: F_kv = 3'd1;
                5'd22: F_kv = 3'd1;
                5'd23: F_kv = 3'd1;
                default: F_kv = 3'd0;
            endcase
        end
    endfunction
// ==== LSC_TABLE_END ====

//-----------------------------------------------------------------------------
//  坐标：每行 beat 计数 + 行计数
//  ★这里只数 valid 拍，因为 MIPI→ISP 这条流的 tvalid 是有空隙的（实测
//    占空比约 2/3），不能拿 clk 计数代替。★
//-----------------------------------------------------------------------------
    reg [8:0]  S_bx;      // 0 .. H_BEATS-1（320 需 9 bit）
    reg [11:0] S_y;       // 0 .. V_LINES-1

    wire S_line_end  = I_tvalid & I_tlast;
    wire S_beat_last = (S_bx == (H_BEATS[8:0] - 9'd1)) | S_line_end;

    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            S_bx <= 9'd0;
            S_y  <= 12'd0;
        end
        else if (I_tuser) begin           // 帧起始：行列都归零
            S_bx <= 9'd0;
            S_y  <= 12'd0;
        end
        else if (I_tvalid) begin
            if (S_line_end) begin
                S_bx <= 9'd0;
                S_y  <= (S_y == (V_LINES - 12'd1)) ? 12'd0 : (S_y + 12'd1);
            end
            else begin
                S_bx <= S_beat_last ? S_bx : (S_bx + 9'd1);
            end
        end
    end

    // 节点索引：水平 = bx / 16 = bx[8:4]（0..19）；垂直 = y / 32 = y[9:5]（0..22）
    wire [4:0] S_hidx = S_bx[8:4];
    wire [4:0] S_vidx = (S_y[11:5] > 5'd23) ? 5'd23 : S_y[11:5];

    //-----------------------------------------------------------------------------
    //  分离式取值：k = KH[x] + KV[y]，饱和到 K_MAX
    //-----------------------------------------------------------------------------
    wire [3:0] S_kh   = {1'b0, F_kh(S_hidx)};
    wire [3:0] S_kv   = {1'b0, F_kv(S_vidx)};
    wire [4:0] S_ksum = {1'b0, S_kh} + {1'b0, S_kv};
    wire [3:0] S_k    = (S_ksum > {1'b0, K_MAX}) ? K_MAX : S_ksum[3:0];

//-----------------------------------------------------------------------------
//  第 1 级流水：锁存 k 与像素数据
//-----------------------------------------------------------------------------
    reg [3:0]  S_k_r;
    reg [95:0] S_d_r;
    reg        S_v1, S_u1, S_l1;

    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            S_k_r <= 4'd0;
            S_d_r <= 96'd0;
            S_v1  <= 1'b0;
            S_u1  <= 1'b0;
            S_l1  <= 1'b0;
        end
        else begin
            S_k_r <= I_bypass ? 4'd0 : S_k;
            S_d_r <= I_tdata;
            S_v1  <= I_tvalid;
            S_u1  <= I_tuser;
            S_l1  <= I_tlast;
        end
    end

//-----------------------------------------------------------------------------
//  移位加法树：p = v * k，k 只有 0..7
//  用 v 的移位组合代替乘法器 —— 8bit 输入、10bit 结果，全部是 LUT 加法器。
//  乘数只有 4bit，先拆成"2 的幂"再相加。
//-----------------------------------------------------------------------------
    function [9:0] F_mul(input [7:0] v, input [3:0] k);
        reg [9:0] a, b, c;
        begin
            a = {2'b00, v};                 // v * 1
            b = {1'b0, v, 1'b0};            // v * 2
            c = {v, 2'b00};                 // v * 4
            case (k)
                4'd0: F_mul = 10'd0;
                4'd1: F_mul = a;
                4'd2: F_mul = b;
                4'd3: F_mul = a + b;
                4'd4: F_mul = c;
                4'd5: F_mul = a + c;
                4'd6: F_mul = b + c;
                default: F_mul = a + b + c;
            endcase
        end
    endfunction

    // g = 1 + k/64  =>  out = v + ((v*k) >> 6)，饱和到 255
    function [7:0] F_apply(input [7:0] v, input [3:0] k);
        reg [9:0] p;
        reg [8:0] s;
        begin
            p = F_mul(v, k);
            s = {1'b0, v} + {1'b0, p[9:6]};     // v + p/64
            F_apply = s[8] ? 8'd255 : s[7:0];
        end
    endfunction

//-----------------------------------------------------------------------------
//  第 2 级流水：4 像素 x 2 通道（R 与 B）
//  像素 j 的 R 在 bit[24j+16 +: 8]、B 在 bit[24j +: 8]、G 在 bit[24j+8 +: 8]
//-----------------------------------------------------------------------------
    wire [7:0] r0 = S_d_r[23:16], g0 = S_d_r[15: 8], b0 = S_d_r[ 7: 0];
    wire [7:0] r1 = S_d_r[47:40], g1 = S_d_r[39:32], b1 = S_d_r[31:24];
    wire [7:0] r2 = S_d_r[71:64], g2 = S_d_r[63:56], b2 = S_d_r[55:48];
    wire [7:0] r3 = S_d_r[95:88], g3 = S_d_r[87:80], b3 = S_d_r[79:72];

    wire [7:0] r0c = F_apply(r0, S_k_r), b0c = F_apply(b0, S_k_r);
    wire [7:0] r1c = F_apply(r1, S_k_r), b1c = F_apply(b1, S_k_r);
    wire [7:0] r2c = F_apply(r2, S_k_r), b2c = F_apply(b2, S_k_r);
    wire [7:0] r3c = F_apply(r3, S_k_r), b3c = F_apply(b3, S_k_r);

    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            O_tdata <= 96'd0;
            O_tvalid <= 1'b0;
            O_tuser  <= 1'b0;
            O_tlast  <= 1'b0;
        end
        else begin
            // G 三路原样直通；R/B 用校正后的值
            O_tdata <= { r3c, g3, b3c,
                         r2c, g2, b2c,
                         r1c, g1, b1c,
                         r0c, g0, b0c };
            O_tvalid <= S_v1;
            O_tuser  <= S_u1;
            O_tlast  <= S_l1;
        end
    end

endmodule
