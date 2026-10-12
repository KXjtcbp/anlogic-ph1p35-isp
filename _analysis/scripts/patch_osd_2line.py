# -*- coding: utf-8 -*-
"""把橙色遥测从 1 行扩到 2 行。

第 1 行（不变）: AExxSxMxxWxxxxBxxxx   —— AE 增益索引/状态/实测均值 + AWB R/B 增益
第 2 行（新增）: FcbnamTssNnnDnnUnn   —— AE 决策链内部量
    F + 5 位标志: c=can_act  b=frame_ok  n=req_pend  a=ae_cfg_done  m=cam_cfg_done
    T ss : S_settle（正常应 = 3C = 60）
    N nn : S_gi_next（本帧算出来的目标档）
    D nn : S_gi_dec （要减的档）
    U nn : S_gi_inc （要加的档）
纯观测，不改任何功能逻辑；定案后整块可删。

只改三个文件，全部走精确字符串匹配 + 断言。
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"E:\FPGA"
AE  = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "isp", "ae_ctrl.v")
TOP = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "design_top_wrapper.v")
MIX = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "hdmi_mixer.v")

def load(p):
    raw = open(p, "rb").read()
    assert not raw.startswith(b"\xef\xbb\xbf"), "有 BOM: " + p
    return raw.decode("utf-8"), raw.decode("utf-8").replace("\r\n", "\n").count("\n")

def save(p, txt, crlf):
    nl = "\r\n" if crlf else "\n"
    data = txt.replace("\n", nl).encode("utf-8")
    open(p, "wb").write(data)
    print("   写入 %-24s %d -> %d B" % (os.path.basename(p), os.path.getsize(p), len(data)))

def sub(txt, old, new, tag, count=1):
    if new in txt:
        print("   [%s] 已是目标状态，跳过" % tag)
        return txt
    n = txt.count(old)
    assert n == count, "[%s] 精确匹配到 %d 处（应为 %d）:\n---\n%s\n---" % (tag, n, count, old[:200])
    return txt.replace(old, new)

# ============================================================ ae_ctrl.v
print("[1/3] ae_ctrl.v")
t, _ = load(AE)
crlf = b"\r\n" in open(AE, "rb").read()
t = sub(t, """    output reg  [1:0]  O_state            // 0=等配置 1=稳定中 2=闭环中 3=冻结
);""",
"""    output reg  [1:0]  O_state,           // 0=等配置 1=稳定中 2=闭环中 3=冻结

    // ---- [HDR-2026-10-12m] 第二行遥测：AE 决策链内部量（纯只读观测）----
    output wire [33:0] O_dbg2
);""", "ae-port")

t = sub(t, """    end

endmodule""",
"""    end

    //=========================================================================
    // 5. [HDR-2026-10-12m] 第二行遥测总线（纯观测，不参与任何逻辑）
    //    [33:27] S_gi_inc   [26:20] S_gi_dec   [19:13] S_gi_next
    //    [12:5]  S_settle   [4] S_can_act  [3] S_frame_ok  [2] S_req_pend
    //    [1] I_ae_cfg_done  [0] I_cam_cfg_done
    //    目的：AE"闭环但增益不动"到底卡在哪个与条件上，看一眼就知道。
    //=========================================================================
    assign O_dbg2 = { S_gi_inc, S_gi_dec, S_gi_next, S_settle,
                      S_can_act, S_frame_ok, S_req_pend, I_ae_cfg_done, I_cam_cfg_done };

endmodule""", "ae-assign")
save(AE, t, crlf)

# ============================================================ design_top_wrapper.v
print("[2/3] design_top_wrapper.v")
t, _ = load(TOP)
crlf = b"\r\n" in open(TOP, "rb").read()
t = sub(t, "wire [6:0]  S_ae_gi;      // 回读：当前增益索引 0..127",
        "wire [6:0]  S_ae_gi;      // 回读：当前增益索引 0..127\n"
        "wire [33:0] S_osd_dbg2;   // [HDR-2026-10-12m] 第二行遥测：AE 决策链内部量",
        "top-wire")
t = sub(t, ".O_gain_idx     (S_ae_gi       ),",
        ".O_gain_idx     (S_ae_gi       ),\n"
        "              .O_dbg2         (S_osd_dbg2    ),", "top-inst")
t = sub(t, ".I_dbg_vals      ( S_osd_dbg          ),",
        ".I_dbg_vals      ( S_osd_dbg          ),\n"
        "              .I_dbg2_vals     ( S_osd_dbg2         ),", "top-mix")
save(TOP, t, crlf)

# ============================================================ hdmi_mixer.v
print("[3/3] hdmi_mixer.v")
t, _ = load(MIX)
crlf = b"\r\n" in open(MIX, "rb").read()

t = sub(t, "input wire [48:0] I_dbg_vals,",
        "input wire [48:0] I_dbg_vals,\n"
        "    input wire [33:0] I_dbg2_vals,       // [HDR-2026-10-12m] 第二行遥测：AE 决策内部量",
        "mix-port")

t = sub(t, "wire [15:0] S_dbg_gb = S_dbg_2d[15:0];   // AWB B 增益 [19:4]",
"""wire [15:0] S_dbg_gb = S_dbg_2d[15:0];   // AWB B 增益 [19:4]

    //------------------------------------------------------------------------
    // [HDR-2026-10-12m] 第 5 层：第二行橙色遥测（AE 决策链内部量）
    //------------------------------------------------------------------------
    localparam DBG2_OSD_X     = 12'd376;
    localparam DBG2_OSD_Y     = 12'd164;   // 第一行在 152..161，MODE 在 176..185
    localparam DBG2_OSD_W     = 12'd304;   // 19 字符 x 16 字距
    localparam DBG2_OSD_H     = 12'd10;

    reg [33:0] S_dbg2_1d;
    reg [33:0] S_dbg2_2d;
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
    reg        S_dbg2_on;""", "mix-wires")

t = sub(t, "S_dbg_2d <= 49'd0;",
        "S_dbg_2d <= 49'd0;\n            S_dbg2_1d <= 34'd0;\n            S_dbg2_2d <= 34'd0;",
        "mix-rst")
t = sub(t, "S_dbg_2d <= S_dbg_1d;",
        "S_dbg_2d <= S_dbg_1d;\n            S_dbg2_1d <= I_dbg2_vals;\n            S_dbg2_2d <= S_dbg2_1d;",
        "mix-sync")

t = sub(t, "5'd18: F_dbg_glyph = 35'b10001_10001_10001_10101_10101_11011_10001; // W",
"""5'd18: F_dbg_glyph = 35'b10001_10001_10001_10101_10101_11011_10001; // W
                    5'd19: F_dbg_glyph = 35'b11111_00100_00100_00100_00100_00100_00100; // T
                    5'd20: F_dbg_glyph = 35'b10001_11001_11001_10101_10011_10001_10001; // N
                    5'd21: F_dbg_glyph = 35'b10001_10001_10001_10001_10001_10001_01110; // U""",
        "mix-glyph")

t = sub(t, "S_dbg_bits = 5'd0;",
"""S_dbg_bits = 5'd0;
            S_dbg2_x    = 12'd0;
            S_dbg2_y    = 12'd0;
            S_dbg2_idx  = 5'd0;
            S_dbg2_lx   = 4'd0;
            S_dbg2_ly   = 4'd0;
            S_dbg2_gl   = 5'd0;
            S_dbg2_bits = 5'd0;
            S_dbg2_on   = 1'b0;""", "mix-default")

t = sub(t, """                if(S_dbg_on) begin
                    S_osd_hit   = 1'b1;
                    S_osd_color = COLOR_DBG_TEXT;
                end
            end""",
"""                if(S_dbg_on) begin
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
            end""", "mix-layer")
save(MIX, t, crlf)

print("\n三个文件都改完。备份在 _backup\\20261012m_osd2line\\")
