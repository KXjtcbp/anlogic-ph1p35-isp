# -*- coding: utf-8 -*-
"""把关键单元格的「采样位图」与「匹配到的字形位图」并排打成 ASCII，肉眼可判。"""
import os, re, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
MIX = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "hdmi_mixer.v")
src = open(MIX, "rb").read().decode("utf-8", errors="replace")
glyph = {}
for m in re.finditer(r"5'd(\d+)\s*:\s*F_dbg_glyph\s*=\s*35'b([01_]+)", src):
    bits = m.group(2).replace("_", "")
    idx = int(m.group(1))
    glyph[idx] = [[int(bits[r * 5 + c]) for c in range(5)] for r in range(7)]
name = {0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
        10: 'A', 11: 'B', 12: 'C', 13: 'D', 14: 'E', 15: 'F', 16: 'M', 17: 'S', 18: 'W',
        19: 'T', 20: 'N', 21: 'U'}


def sample(img, row_y_in, i, dx, dy):
    a = np.asarray(img).astype(np.int32)
    X0 = 376 + 16 * i
    score = a[..., 0].astype(float) - a[..., 2].astype(float)
    v = np.zeros((7, 5))
    for ly in range(7):
        for lx in range(5):
            v[ly, lx] = score[int(round((row_y_in + ly) * 1.5 + 0.75)) + dy,
                              int(round((X0 + lx) * 1.5 + 0.75)) + dx]
    return (v > (v.max() + v.min()) / 2.0).astype(int)


def rank(pat):
    out = []
    for idx, g in glyph.items():
        out.append((int(np.sum(np.abs(np.array(g) - pat))), idx))
    out.sort()
    return out[:4]


def art(m):
    return ["".join("#" if x else "." for x in row) for row in m]


CASES = [("SW4\u4e0b.png", 152, -1, 0), ("SW4\u4e0a1.png", 152, -1, -1),
         ("SW4\u4e0a1.png", 164, -1, 0)]
CELLS = [2, 3, 5, 7]
for fn, y, dx, dy in CASES:
    img = Image.open(os.path.join(WS, "inbox", fn)).convert("RGB")
    print("=" * 70)
    print("%s  row_y_in=%d  dx=%d dy=%d" % (fn, y, dx, dy))
    for i in CELLS:
        pat = sample(img, y, i, dx, dy)
        top = rank(pat)
        print("  cell %2d : 采样                      候选(top4 残差->字)" % i)
        for a_, b_ in zip(art(pat), art(glyph[top[0][1]])):
            print("           %s     %s" % (a_, b_))
        print("           候选 = %s" % "  ".join("%d->'%s'" % (d, name[k]) for d, k in top))
