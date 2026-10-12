# -*- coding: utf-8 -*-
"""修 patch_osd_2line.py 留下的一个顺序问题：
   S_dbg2_1d / S_dbg2_2d 的 reg 声明被插到了用它的 always 块之后
   ⇒ (vlog-2730) Undefined variable。
   把这两条声明上移到 reg [48:0] S_dbg_2d; 之后。"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
MIX = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\hdmi_mixer.v"
raw = open(MIX, "rb").read()
crlf = b"\r\n" in raw
t = raw.decode("utf-8").replace("\r\n", "\n")

oldreg = "    reg [33:0] S_dbg2_1d;\n    reg [33:0] S_dbg2_2d;\n"
assert t.count(oldreg) == 1, "找不到待删的两行声明: %d" % t.count(oldreg)
t = t.replace(oldreg, "")

anchor = "reg [48:0] S_dbg_2d;"
assert t.count(anchor) == 1, "anchor 不唯一: %d" % t.count(anchor)
t = t.replace(anchor, anchor +
              "\n    reg [33:0] S_dbg2_1d;             // [HDR-2026-10-12m] 第二行遥测同步链"
              "\n    reg [33:0] S_dbg2_2d;")

open(MIX, "wb").write(t.replace("\n", "\r\n" if crlf else "\n").encode("utf-8"))
print("hdmi_mixer.v 修好，%d B" % os.path.getsize(MIX))
