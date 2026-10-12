# -*- coding: utf-8 -*-
"""把 inbox 的 21 张 AE 首版上板验证图归档进 captures/。"""
import os, shutil, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"E:\FPGA"
SRC = os.path.join(WS, "inbox")
DST = os.path.join(WS, "captures", "2026-10-12_AE首版上板验证")
os.makedirs(DST, exist_ok=True)

names = ([f"A{i}.png" for i in range(1, 5)] + [f"B{i}.png" for i in range(1, 4)] +
         [f"C{i}.png" for i in range(1, 5)] + [f"D{i}.png" for i in range(1, 6)] +
         [f"E{i}.png" for i in range(1, 6)])
moved = 0
for n in names:
    s, d = os.path.join(SRC, n), os.path.join(DST, n)
    if os.path.exists(s):
        shutil.move(s, d)
        moved += 1
    else:
        print("MISSING", n)
print("moved %d files -> captures\\2026-10-12_AE首版上板验证\\" % moved)

left = sorted(f for f in os.listdir(SRC) if f.lower().endswith(".png"))
print("inbox 里还剩 png:", left if left else "(无)")
