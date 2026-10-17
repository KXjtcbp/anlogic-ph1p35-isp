# -*- coding: utf-8 -*-
"""把 obj_detect.v 登记进 .al 与两个 run 的 .prj（复制 motion_detect.v 的 <File> 块）"""
import io, os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
HS = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")
RUN = os.path.join(WS, "proj", "baseline", "lab3", "td_project",
                   "camera_to_dsi_display_Runs")
AL = os.path.join(WS, "proj", "baseline", "lab3", "td_project",
                  "camera_to_dsi_display.al")

PAT = re.compile(r"<File Path=\"([^\"]*isp/)motion_detect\.v\">[\s\S]*?</File>\n")


def patch(path):
    s = io.open(path, encoding="utf-8", errors="replace").read().replace("\r\n", "\n")
    if "obj_detect.v" in s:
        print("  %-24s 已存在，跳过" % path.split("\\")[-2:])
        return
    m = PAT.search(s)
    assert m, "找不到 motion_detect.v 块: " + path
    blk = m.group(0).replace("motion_detect.v", "obj_detect.v")
    s = s[:m.end()] + blk + s[m.end():]
    io.open(path, "w", encoding="utf-8", newline="\n").write(s)
    print("  %-34s +obj_detect.v (%d B)" % ("/".join(path.split("\\")[-2:]), len(s.encode())))


patch(AL)
for run in ("syn_1", "phy_1"):
    patch(os.path.join(RUN, run, "camera_to_dsi_display.prj"))
