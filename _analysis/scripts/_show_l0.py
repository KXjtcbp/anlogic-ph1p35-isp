# -*- coding: utf-8 -*-
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
T = os.environ.get("TEMP", r"C:\Users\KX\AppData\Local\Temp")
p = os.path.join(T, "_L0.py")
s = open(p, encoding="utf-8-sig").read()
print("=== _L0.py 全文（%d chars）===" % len(s))
print(s)
