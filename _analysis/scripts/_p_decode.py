# -*- coding: utf-8 -*-
"""从 hdmi_mixer.v 解析 F_dbg_glyph 字形库，再把采集图里两行遥测的 19 个字符
   逐个采样还原成 5x7 位图做精确匹配，输出字符串（而不是靠肉眼认字）。

坐标：内部 1280x720，屏幕 = x1.5。第1行内部 y=152，第2行 y=164，起点内部 x=376，字距 16。
每个字的 5x7 位图占内部列 0..4、行 0..6。
"""
import os, re, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
MIX = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "hdmi_mixer.v")

src = open(MIX, "rb").read().decode("utf-8", errors="replace")
glyph = {}
for m in re.finditer(r"5'd(\d+)\s*:\s*F_dbg_glyph\s*=\s*35'b([01_]+)", src):
    idx = int(m.group(1))
    bits = m.group(2).replace("_", "")
    assert len(bits) == 35, (idx, len(bits))
    rows = [[int(bits[r * 5 + c]) for c in range(5)] for r in range(7)]
    glyph[idx] = rows
print("解析到 %d 个字形：" % len(glyph), sorted(glyph.keys()))
name = {0: '0', 1: '1', 2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8', 9: '9',
        10: 'A', 11: 'B', 12: 'C', 13: 'D', 14: 'E', 15: 'F', 16: 'M', 17: 'S', 18: 'W',
        19: 'T', 20: 'N', 21: 'U'}


def sample(img, row_y_in, i, dx=0, dy=0):
    """把第 i 个字的 5x7 位图从 1920x1080 采集图里采回来：1 = 橙色（亮），0 = 暗。"""
    a = np.asarray(img).astype(np.int32)
    X0 = 376 + 16 * i
    score = a[..., 0].astype(float) - a[..., 2].astype(float)   # 橙色度量：R 高、B 低
    vals = np.zeros((7, 5))
    for ly in range(7):
        for lx in range(5):
            xs = int(round((X0 + lx) * 1.5 + 0.75)) + dx
            ys = int(round((row_y_in + ly) * 1.5 + 0.75)) + dy
            vals[ly, lx] = score[ys, xs]
    thr = (vals.max() + vals.min()) / 2.0
    return (vals > thr).astype(int)


def row_string(img, row_y_in, dx, dy):
    s, res = "", 0
    for i in range(19):
        pat = sample(img, row_y_in, i, dx, dy)
        idx, d = match(pat)
        s += name.get(idx, "?")
        res += d
    return s, res


def match(pat):
    best, bestd = None, 999
    for idx, g in glyph.items():
        d = int(np.sum(np.abs(np.array(g) - pat)))
        if d < bestd:
            bestd, best = d, idx
    return best, bestd


FILES = ["SW4\u4e0b.png", "SW4\u4e0a1.png", "SW4\u4e0a2.png"]
for fn in FILES:
    p = os.path.join(WS, "inbox", fn)
    img = Image.open(p).convert("RGB")
    print("\n" + "=" * 70)
    print(fn)
    for tag, y in (("L1", 152), ("L2", 164)):
        best = None
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                s, res = row_string(img, y, dx, dy)
                if best is None or res < best[0]:
                    best = (res, s, dx, dy)
        res, s, dx, dy = best
        print("  %s = %-24s  残差合计 %3d  (dx=%+d dy=%+d)" % (tag, s, res, dx, dy))
