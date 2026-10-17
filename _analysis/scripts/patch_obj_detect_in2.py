# -*- coding: utf-8 -*-
"""obj_detect 接线 step-2：isp_top.v + design_top_wrapper.v + .prj/.al
   （hdmi_mixer.v 已在 step-1 打好，本脚本会跳过）"""
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
    if "u_obj_detect" in s:
        return s
    s = rep1(s, u"    output [19:0]   O_wb_gain_b     ,\n",
             u"    output [19:0]   O_wb_gain_b     ,\n"
             u"    //----------------------------------------------------------------------\n"
             u"    // [HDR-2026-10-17] \u989c\u8272\u76ee\u6807\u68c0\u6d4b\uff08\u57fa\u7840\u6269\u5c55\u9879 2\uff09\n"
             u"    //----------------------------------------------------------------------\n"
             u"    output [143:0]  O_obj_mask      ,\n"
             u"    output [7:0]    O_obj_cnt       ,\n"
             u"    input           I_obj_bypass    ,\n",
             "isp-port")
    # 插到 ae_stat 例化之后：先定位 .O_frame_tgl，再找它后面第一个 ");"
    i = s.index(u".O_frame_tgl")
    j = s.index(u");", i) + 2
    if s[j] == u"\n":
        j += 1
    return s[:j] + OBJ_INST + s[j:]


def patch_dtw(s):
    if "S_obj_mask" in s:
        return s

    def ins_after_line(src, key, text):
        i = src.index(key)
        j = src.index(u"\n", i) + 1
        return src[:j] + text + src[j:]

    s = ins_after_line(s, u"wire [7:0]   S_mot_cnt;",
                       u"// [HDR-2026-10-17] \u989c\u8272\u76ee\u6807\u68c0\u6d4b\n"
                       u"wire [143:0] S_obj_mask;\n"
                       u"wire [7:0]   S_obj_cnt;\n")
    s = ins_after_line(s, u".O_mot_cnt",
                       u"        .O_obj_mask      (S_obj_mask    ),\n"
                       u"        .O_obj_cnt       (S_obj_cnt     ),\n")
    s = ins_after_line(s, u".I_mot_cnt",
                       u"        .I_obj_mask      ( S_obj_mask           ),\n"
                       u"        .I_obj_cnt       ( S_obj_cnt            ),\n")
    s = ins_after_line(s, u".I_mot_en",
                       u"        .I_obj_bypass    ( ~S_mot_en            ),  // [HDR-2026-10-17] SW3 \u5173\u5219\u76ee\u6807\u68c0\u6d4b\u4e5f\u6e05\u7a7a\n")
    return s


def patch_prj(s):
    if "obj_detect.v" in s:
        return s
    m = re.search(r"[ \t]*<File>[\s\S]{0,240}?motion_detect\.v[\s\S]{0,120}?</File>\n", s)
    assert m, "prj: 找不到 motion_detect.v 条目"
    blk = m.group(0)
    new = blk.replace("motion_detect.v", "obj_detect.v")
    return s[:m.end()] + new + s[m.end():]


def main():
    for path, fn, tag in ((os.path.join(HS, "isp", "isp_top.v"), patch_isp, "isp_top"),
                          (os.path.join(HS, "design_top_wrapper.v"), patch_dtw, "design_top_wrapper")):
        a, b = rw(path, fn)
        print("  %-22s %6d -> %6d B" % (tag, a, b))
    for run in ("syn_1", "phy_1"):
        p = os.path.join(RUN, run, "camera_to_dsi_display.prj")
        a, b = rw(p, patch_prj)
        print("  %-22s %6d -> %6d B" % (run + "/.prj", a, b))
    a, b = rw(AL, patch_prj)
    print("  %-22s %6d -> %6d B" % (".al", a, b))


main()
