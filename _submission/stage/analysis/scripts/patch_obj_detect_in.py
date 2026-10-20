# -*- coding: utf-8 -*-
"""把 obj_detect.v 接进 isp_top / design_top_wrapper / hdmi_mixer，并登记到 .prj 与 .al
   [HDR-2026-10-17] 新增「颜色目标检测」第 7 层 OSD（绿色块描边）"""
import io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"E:\FPGA"
HS = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")
RUN = os.path.join(WS, "proj", "baseline", "lab3", "td_project",
                   "camera_to_dsi_display_Runs")
AL = os.path.join(WS, "proj", "baseline", "lab3", "td_project",
                  "camera_to_dsi_display.al")


def rw(path, fn):
    s = io.open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
    n = fn(s)
    io.open(path, "w", encoding="utf-8", newline="\n").write(n)
    return len(s.encode()), len(n.encode())


def rep1(s, old, new, tag):
    c = s.count(old)
    assert c == 1, "[%s] 锚点命中 %d 次" % (tag, c)
    return s.replace(old, new)


# ────────────────────────── 1. hdmi_mixer.v ──────────────────────────
MIX = os.path.join(HS, "hdmi_mixer.v")

OBJ_HEAD = u"""        // ---- [HDR-2026-10-17] 第 7 层：颜色目标检测块描边（绿色，优先级低于运动框）----
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
        S_obj_on   = I_obj_mask[{1'b0, S_obj_by, S_obj_bx[3:0]}] &&
                     ( (S_obj_xoff < 12'd3) || (S_obj_xoff > 12'd76) ||
                       (S_obj_yoff < 12'd3) || (S_obj_yoff > 12'd76) );
        if(S_obj_on) begin
            S_osd_hit   = 1'b1;
            S_osd_color = COLOR_OBJ_TEXT;
        end
"""

ANCHOR_MOT_END = u"""        if(S_mot_on) begin
            S_osd_hit   = 1'b1;
            S_osd_color = COLOR_MOT_TEXT;
        end
"""


def patch_mixer(s):
    s = rep1(s, u"    input wire         I_mot_en,   // 0 = \u6574\u5c42\u4e0d\u663e\u793a\uff08SW3 \u5173\uff09\n",
             u"    input wire         I_mot_en,   // 0 = \u6574\u5c42\u4e0d\u663e\u793a\uff08SW3 \u5173\uff09\n"
             u"    input wire [143:0] I_obj_mask, // [HDR-2026-10-17] \u989c\u8272\u76ee\u6807\u68c0\u6d4b\u5757\u63a9\u7801\n"
             u"    input wire [7:0]   I_obj_cnt,  // [HDR-2026-10-17] \u547d\u4e2d\u5757\u6570\n",
             "port")
    s = rep1(s, u"localparam COLOR_MOT_TEXT = 24'hff2020; // \u8fd0\u52a8\u5757\u63cf\u8fb9\u7ea2\n",
             u"localparam COLOR_MOT_TEXT = 24'hff2020; // \u8fd0\u52a8\u5757\u63cf\u8fb9\u7ea2\n"
             u"localparam COLOR_OBJ_TEXT = 24'h00ff40; // [HDR-2026-10-17] \u76ee\u6807\u68c0\u6d4b\u6846\u7eff\n",
             "color")
    s = rep1(s, u"    reg         S_mot_on;\n",
             u"    reg         S_mot_on;\n"
             u"    reg  [4:0]  S_obj_bx;   // [HDR-2026-10-17] \u7b2c 7 \u5c42\uff1a\u76ee\u6807\u68c0\u6d4b\u6846\n"
             u"    reg  [3:0]  S_obj_by;\n"
             u"    reg  [11:0] S_obj_xoff;\n"
             u"    reg  [11:0] S_obj_yoff;\n"
             u"    reg         S_obj_on;\n",
             "regs")
    s = rep1(s, ANCHOR_MOT_END, ANCHOR_MOT_END + OBJ_HEAD, "layer")
    return s


# ────────────────────────── 2. isp_top.v ──────────────────────────
ISP = os.path.join(HS, "isp", "isp_top.v")
OBJ_INST = u"""
    // ======================================================================
    // [HDR-2026-10-17] 颜色目标检测（流式分块，纯观察者，不改像素通路）
    // ======================================================================
    wire [143:0] obj_mask;
    wire [7:0]   obj_cnt;
    wire         obj_any;
    wire [15:0]  obj_hit_sum;

    obj_detect #(
        .H_BEATS       (9'd320  ),
        .V_LINES       (12'd720 ),
        .BEATS_PER_BLK (5'd20   ),
        .LINES_PER_BLK (7'd80   ),
        .LUM_MIN       (8'd80   ),
        .CHR_MIN       (8'd35   ),
        .HIT_MIN       (13'd40  )
    ) u_obj_detect (
        .I_clk      (axi4s_video_aclk ),
        .I_rst_n    (I_rst_n          ),
        .I_bypass   (I_obj_bypass     ),
        .I_tdata    (m_axis_tdata_96  ),
        .I_tvalid   (m_axis_tvalid    ),
        .I_tuser    (m_axis_tuser     ),
        .I_tlast    (m_axis_tlast     ),
        .O_blk_mask (obj_mask         ),
        .O_blk_cnt  (obj_cnt          ),
        .O_obj_any  (obj_any          ),
        .O_hit_sum  (obj_hit_sum      )
    );
    assign O_obj_mask = obj_mask;
    assign O_obj_cnt  = obj_cnt;
"""


def patch_isp(s):
    s = rep1(s, u"    output [19:0]        O_wb_gain_b\n",
             u"    output [19:0]        O_wb_gain_b,\n"
             u"    // [HDR-2026-10-17] \u989c\u8272\u76ee\u6807\u68c0\u6d4b\u7ed3\u679c\n"
             u"    output [143:0]       O_obj_mask,\n"
             u"    output [7:0]         O_obj_cnt,\n"
             u"    input                I_obj_bypass\n",
             "isp-port")
    # 插到 awb 例化之后（用 \");\" + 紧接的注释不好定位，改用 ae_stat 例化的结尾）
    anchor = u"    .O_hi_cnt   (S_ae_hi_cnt)\n"
    if anchor in s:
        i = s.index(anchor)
        j = s.index(u"    );\n", i) + len(u"    );\n")
        s = s[:j] + OBJ_INST + s[j:]
    else:
        raise AssertionError("isp_top: 找不到 ae_stat 例化结尾")
    return s


# ────────────────────────── 3. design_top_wrapper.v ──────────────────────────
DTW = os.path.join(HS, "design_top_wrapper.v")


def patch_dtw(s):
    s = rep1(s, u"wire [7:0]           S_mot_cnt;\n",
             u"wire [7:0]           S_mot_cnt;\n"
             u"// [HDR-2026-10-17] \u989c\u8272\u76ee\u6807\u68c0\u6d4b\n"
             u"wire [143:0]         S_obj_mask;\n"
             u"wire [7:0]           S_obj_cnt;\n",
             "dtw-wire")
    s = rep1(s, u"    .O_mot_cnt      (S_mot_cnt      ),\n",
             u"    .O_mot_cnt      (S_mot_cnt      ),\n"
             u"    .O_obj_mask     (S_obj_mask     ),\n"
             u"    .O_obj_cnt      (S_obj_cnt      ),\n",
             "dtw-isp-conn")
    s = rep1(s, u"        .I_mot_cnt      ( S_mot_cnt             ),\n",
             u"        .I_mot_cnt      ( S_mot_cnt             ),\n"
             u"        .I_obj_mask     ( S_obj_mask            ),\n"
             u"        .I_obj_cnt      ( S_obj_cnt             ),\n",
             "dtw-mix-conn")
    return s


# ────────────────────────── 4. .prj / .al ──────────────────────────
def patch_prj(s):
    if "obj_detect.v" in s:
        return s
    anchor = u"<File>"
    m = re.search(r"<File>\s*<Path>([^<]*motion_detect\.v)</Path>", s)
    assert m, "prj: 找不到 motion_detect.v 条目"
    line = u"<File><Path>../../../user_source/hdl_source/isp/obj_detect.v</Path><Order>60</Order></File>\n"
    i = s.index(u"</File>", m.start()) + len(u"</File>") + 1
    return s[:i] + line + s[i:]


def patch_al(s):
    if "obj_detect.v" in s:
        return s
    m = re.search(r"[ \t]*<File>[\s\S]{0,200}?motion_detect\.v[\s\S]{0,100}?</File>\n", s)
    assert m, "al: 找不到 motion_detect.v 条目"
    blk = m.group(0)
    new = blk.replace("motion_detect.v", "obj_detect.v")
    return s[:m.end()] + new + s[m.end():]


def main():
    for path, fn, tag in ((MIX, patch_mixer, "hdmi_mixer"), (ISP, patch_isp, "isp_top"),
                          (DTW, patch_dtw, "design_top_wrapper")):
        a, b = rw(path, fn)
        print("  %-24s %6d -> %6d B" % (tag, a, b))
    for run in ("syn_1", "phy_1"):
        p = os.path.join(RUN, run, "camera_to_dsi_display.prj")
        a, b = rw(p, patch_prj)
        print("  %-24s %6d -> %6d B" % (run + "/.prj", a, b))
    a, b = rw(AL, patch_al)
    print("  %-24s %6d -> %6d B" % (".al", a, b))


main()
