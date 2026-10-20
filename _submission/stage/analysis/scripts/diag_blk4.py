# -*- coding: utf-8 -*-
"""四档盖镜头图定量：黑底电平、底噪、分通道底座、OSD CNT 拼图。
用法: python diag_blk4.py
"""
import os
import numpy as np
from PIL import Image

CAP = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis\out"
FILES = [("4.000x ", "sw3 4都向下.png"),
         ("8.000x ", "SW3上SW4下.png"),
         ("15.750x", "SW3下SW4上.png"),
         ("31.500x", "两个都向上.png")]


def osd_mask(w, h):
    s = w / 1280.0
    boxes = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in boxes:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def y_of(px):
    return ((77 * px[:, :, 0].astype(np.int32) + 150 * px[:, :, 1].astype(np.int32)
             + 29 * px[:, :, 2].astype(np.int32)) >> 8)


print("%-9s %-6s %-7s %-7s %-7s %-7s %-7s %-7s %-8s %-7s %-7s %-7s" %
      ("档位", "尺寸", "Y均值", "Y标准差", "p10", "p50", "p90", "Ymax", "Y==0%", "R", "G", "B"))
rows = []
for tag, fn in FILES:
    p = os.path.join(CAP, fn)
    if not os.path.exists(p):
        print("缺失:", p); continue
    im = Image.open(p).convert("RGB")
    w, h = im.size
    a = np.asarray(im)
    m = osd_mask(w, h)
    px = a[m]
    Y = y_of(a)[m]
    R, G, B = px[:, 0].astype(np.float64), px[:, 1].astype(np.float64), px[:, 2].astype(np.float64)
    rows.append((tag, fn, Y, R, G, B, w, h))
    print("%-9s %-6s %-7.2f %-7.2f %-7d %-7d %-7d %-7d %-8.3f %-7.2f %-7.2f %-7.2f" %
          (tag, "%dx%d" % (w, h), Y.mean(), Y.std(), np.percentile(Y, 10),
           np.percentile(Y, 50), np.percentile(Y, 90), Y.max(),
           100.0 * (Y == 0).mean(), R.mean(), G.mean(), B.mean()))

print()
print("==== 分通道比值与低端直方图（0..15 码计数占比%）====")
for tag, fn, Y, R, G, B, w, h in rows:
    print("[%s] %s" % (tag, fn))
    print("   R/G=%.4f  B/G=%.4f   R-G=%+.2f  B-G=%+.2f" %
          (R.mean() / G.mean(), B.mean() / G.mean(), R.mean() - G.mean(), B.mean() - G.mean()))
    for nm, ch in (("R", R), ("G", G), ("B", B)):
        hh = [int((ch == v).sum()) for v in range(16)]
        print("   %s 0..15: %s" % (nm, " ".join("%d" % x for x in hh)))

print()
print("==== 中央 400x400 区域 ====")
for tag, fn, Y, R, G, B, w, h in rows:
    im = Image.open(os.path.join(CAP, fn)).convert("RGB")
    a = np.asarray(im)
    cx, cy = w // 2, h // 2
    c = a[cy - 200:cy + 200, cx - 200:cx + 200].reshape(-1, 3).astype(np.float64)
    yy = y_of(a[cy - 200:cy + 200, cx - 200:cx + 200].reshape(1, -1, 3))[0]
    print("[%s] Ymean=%.2f Ystd=%.2f  R/G/B=%.2f/%.2f/%.2f (R/G=%.4f B/G=%.4f)" %
          (tag, yy.mean(), yy.std(), c[:, 0].mean(), c[:, 1].mean(), c[:, 2].mean(),
           c[:, 0].mean() / c[:, 1].mean(), c[:, 2].mean() / c[:, 1].mean()))

# OSD CNT 拼图
tiles = []
for tag, fn, *_ in rows:
    im = Image.open(os.path.join(CAP, fn)).convert("RGB")
    w, h = im.size
    s = w / 1280.0
    c = im.crop((int(360 * s), int(105 * s), int(620 * s), int(142 * s))).resize((880, 126), Image.NEAREST)
    tiles.append((tag, c))
if tiles:
    sheet = Image.new("RGB", (880, 126 * len(tiles) + 4 * (len(tiles) - 1)), (255, 255, 255))
    for i, (t, c) in enumerate(tiles):
        sheet.paste(c, (0, i * 130))
    sheet.save(os.path.join(OUT, "blk4_cnt.png"))
    print("\nsaved", os.path.join(OUT, "blk4_cnt.png"))
