# -*- coding: utf-8 -*-
"""用法: python dump_region.py <file> <start_line> <end_line>"""
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

p = sys.argv[1]
a = int(sys.argv[2])
b = int(sys.argv[3])
raw = open(p, "rb").read()
t = None
enc = None
for e in ("utf-8", "gbk", "latin-1"):
    try:
        t = raw.decode(e)
        enc = e
        break
    except Exception:
        pass
lines = t.split("\n")
print("### %s  bytes=%d enc=%s lines=%d  (show %d..%d)" % (p, len(raw), enc, len(lines), a, b))
for i in range(max(0, a - 1), min(len(lines), b)):
    print("%4d| %s" % (i + 1, lines[i].rstrip()))
