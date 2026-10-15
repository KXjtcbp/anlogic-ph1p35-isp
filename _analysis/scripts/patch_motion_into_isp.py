# -*- coding: utf-8 -*-
"""把 motion_detect.v 接进 isp_top.v，并把两个输出端口透传到 design_top_wrapper.v。

这一步【只做数据通路与端口】，不动 hdmi_mixer 的 OSD —— 目的是先确认
「新模块能进综合、资源与时序不退化」，再加显示层。
"""
import os, sys, shutil
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

LAB3 = r"E:\FPGA\proj\baseline\lab3"
ISP  = os.path.join(LAB3, "user_source", "hdl_source", "isp", "isp_top.v")
DTW  = os.path.join(LAB3, "user_source", "hdl_source", "design_top_wrapper.v")

def rd(p):  return open(p, "rb").read().decode("utf-8")
def wr(p, s):
    shutil.copy2(p, p + ".bak_motion")
    open(p, "wb").write(s.encode("utf-8"))

# ============================ isp_top.v ============================
s = rd(ISP); n = 0

old = "output [19:0]   O_wb_gain_b\n"
new = ("output [19:0]   O_wb_gain_b     ,\n"
       "// [HDR-2026-10-15b] ★运动目标检测（帧差法）输出★\n"
       "//   144 个运动块位图（16 列 x 9 行，每块 80x80 像素，bit 序号 = row*16+col）\n"
       "//   + 本帧运动块计数。由 hdmi_mixer 的 OSD 层读走画框。\n"
       "//   O_blk_mask 是跨帧保持的，OSD 整帧任意时刻读到的都是本帧结果。\n"
       "output [143:0]  O_mot_mask      ,\n"
       "output [7:0]    O_mot_cnt       ,\n"
       "output          O_mot_any       \n")
if old in s: s = s.replace(old, new, 1); n += 1
else: print("!! isp_top 端口锚点未命中")

anchor = "data_96bit_to_128bit u_data_96bit_to_128bit("
inst = """// [HDR-2026-10-15b] ★运动目标检测（帧差法）★
//   插在 my_algo 之后、data_96bit_to_128bit 之前，只旁路监听 96bit 像素流，
//   不改动主通路（无握手端口，纯观察者）。
//   原理：把画面划成 16x9 = 144 个 80x80 的块，逐帧算块均值；
//         与上一帧的块均值做绝对差，超阈值且块亮度高于下限则判为运动块；
//         STRICT2=1 时要求连续两帧都动，抑制噪声与单帧闪烁。
motion_detect #(
    .H_BEATS       (12'd320),
    .V_LINES       (12'd720),
    .BEATS_PER_BLK (5'd20),
    .LINES_PER_BLK (7'd80),
    .DIFF_TH       (8'd10),
    .FLOOR_TH      (8'd6),
    .STRICT2       (1'b1)
) u_motion_detect (
    .I_clk      (axi4s_video_aclk),
    .I_rst_n    (I_rst_n),
    .I_bypass   (1'b0),
    .I_tdata    (algo_O_tdata),
    .I_tvalid   (algo_O_tvalid),
    .I_tuser    (algo_O_tuser),
    .I_tlast    (algo_O_tlast),
    .O_blk_mask (O_mot_mask),
    .O_blk_cnt  (O_mot_cnt),
    .O_motion_any(O_mot_any),
    .O_dbg_cur  (),
    .O_dbg_prev ()
);

"""
if "u_motion_detect" not in s:
    i = s.find(anchor)
    if i < 0: print("!! isp_top 例化锚点未命中")
    else: s = s[:i] + inst + s[i:]; n += 1

if n: wr(ISP, s); print("isp_top.v 改动 %d 处" % n)

# ====================== design_top_wrapper.v ======================
t = rd(DTW); m = 0

old2 = ".O_wb_gain_b     (S_wb_gain_b   )\n"
new2 = (".O_wb_gain_b     (S_wb_gain_b   ),\n"
        "// [HDR-2026-10-15b] 运动检测结果：透传给 hdmi_mixer 的 OSD 层\n"
        "    .O_mot_mask      (S_mot_mask    ),\n"
        "    .O_mot_cnt       (S_mot_cnt     ),\n"
        "    .O_mot_any       (S_mot_any     )\n")
if old2 in t: t = t.replace(old2, new2, 1); m += 1
else: print("!! dtw 连接锚点未命中")

decl = ("// [HDR-2026-10-15b] 运动检测结果（144 块位图 + 计数）\n"
        "wire [143:0] S_mot_mask;\n"
        "wire [7:0]   S_mot_cnt;\n"
        "wire         S_mot_any;\n\n")
a2 = "isp_top u_isp_top ("
if "S_mot_mask" not in t.split(a2)[0]:
    i = t.find(a2)
    if i < 0: print("!! dtw 例化锚点未命中")
    else: t = t[:i] + decl + t[i:]; m += 1

if m: wr(DTW, t); print("design_top_wrapper.v 改动 %d 处" % m)

# ============ 把 motion_detect.v 加进 .prj / .al ============
import re
PRJ_REL = "../../../user_source/hdl_source/isp/motion_detect.v"
BLOCK = ('                                    <File Path="%s">\n'
         '                                        <FileInfo>\n'
         '                                            <Attr Name="UsedInSyn" Val="true"/>\n'
         '                                            <Attr Name="UsedInP&R" Val="true"/>\n'
         '                                            <Attr Name="BelongTo" Val="design_1"/>\n'
         '                                            <Attr Name="CompileOrder" Val="59"/>\n'
         '                                        </FileInfo>\n'
         '                                    </File>\n') % PRJ_REL
for p in (os.path.join(LAB3,"td_project","camera_to_dsi_display_Runs","syn_1","camera_to_dsi_display.prj"),
          os.path.join(LAB3,"td_project","camera_to_dsi_display_Runs","phy_1","camera_to_dsi_display.prj"),
          os.path.join(LAB3,"td_project","camera_to_dsi_display.al")):
    txt = rd(p)
    if "motion_detect.v" in txt: print("SKIP %s" % os.path.basename(p)); continue
    mm = re.search(r'<File Path="[^"]*wb_recip\.v">.*?</File>\s*', txt, re.S)
    if not mm: print("!! %s 里找不到 wb_recip 块" % os.path.basename(p)); continue
    txt = txt[:mm.end()] + BLOCK + txt[mm.end():]
    open(p, "wb").write(txt.encode("utf-8"))
    print("OK  %-34s -> %d B" % (os.path.basename(p), len(txt)))
