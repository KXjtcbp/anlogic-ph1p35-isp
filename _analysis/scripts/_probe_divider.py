# -*- coding: utf-8 -*-
import sys, os, re
sys.stdout.reconfigure(encoding='utf-8')
p = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\awb\divider\divider_gate.v"
print(p, os.path.getsize(p))
s = open(p, "rb").read()
try:
    s = s.decode("utf-8")
except Exception:
    s = s.decode("gbk", "replace")
lines = s.splitlines()
print("total lines", len(lines))
for i, t in enumerate(lines[:120], 1):
    print("%5d| %s" % (i, t[:180]))
