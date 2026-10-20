# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FILES = [
    r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\uics500_cfg\uics500regAE.v",
    r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\uics500_cfg\uicfgcs500_720p.v",
]

for p in FILES:
    raw = open(p, "rb").read()
    t = None
    enc = None
    for e in ("gbk", "utf-8", "latin-1"):
        try:
            t = raw.decode(e)
            enc = e
            break
        except Exception:
            pass
    print("#" * 100)
    print("### %s   bytes=%d  enc=%s  LF=%d" % (p.split("\\")[-1], len(raw), enc, t.count("\n")))
    for i, l in enumerate(t.split("\n")):
        print("%3d| %s" % (i + 1, l.rstrip()))
