# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
T = os.environ.get("TEMP", r"C:\Users\KX\AppData\Local\Temp")
p = os.path.join(T, "_L2.py")
L = open(p, encoding="utf-8-sig").read().splitlines()
print("=== _L2.py 共 %d 行；打印含 isp_top.v 的上下文 ===" % len(L))
for i, s in enumerate(L):
    if "isp_top.v" in s:
        a = max(0, i - 4); b = min(len(L), i + 12)
        print("\n---- 第 %d~%d 行 ----" % (a + 1, b))
        for k in range(a, b):
            print("%4d| %s" % (k + 1, L[k]))
