# -*- coding: utf-8 -*-
"""把两张图同一区域 1:1 裁出来并排，判断"是否同一画面/结构是否一致"。"""
import numpy as np
from PIL import Image, ImageDraw

DARK = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-36.png"
BRIGHT = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png"
OUT = r"E:\FPGA\_analysis\out\ab_crop.png"

def load(p):
    return np.asarray(Image.open(p).convert("RGB"))

d = load(DARK); b = load(BRIGHT)
# 同一区域：书架+窗帘（两图都有的结构）
boxes = {"shelf(600,250)-(1150,700)": (600, 250, 1150, 700),
         "leftwhite(0,700)-(500,1080)": (0, 700, 500, 1080)}
tiles = []
for nm, (x0, y0, x1, y1) in boxes.items():
    for tag, img in (("DARK(no curve)", d), ("BRIGHT(curve)", b)):
        t = Image.fromarray(img[y0:y1, x0:x1]).copy()
        dr = ImageDraw.Draw(t)
        dr.rectangle([0, 0, 260, 26], fill=(0, 0, 0))
        dr.text((6, 6), "%s %s" % (nm.split('(')[0], tag), fill=(255, 255, 0))
        tiles.append(t)

W = max(t.size[0] for t in tiles) * 2 + 12
H = sum(max(tiles[i].size[1], tiles[i+1].size[1]) + 12 for i in range(0, len(tiles), 2))
canvas = Image.new("RGB", (W, H), (40, 40, 40))
y = 0
for i in range(0, len(tiles), 2):
    canvas.paste(tiles[i], (0, y))
    canvas.paste(tiles[i+1], (tiles[i].size[0] + 12, y))
    y += max(tiles[i].size[1], tiles[i+1].size[1]) + 12
canvas.save(OUT)

# 亮度差图（同一位置相减，看差值是不是空间上均匀的常数）
diff = b.astype(np.int32) - d.astype(np.int32)
Yd = (77*d[:, :, 0].astype(np.int32) + 150*d[:, :, 1] + 29*d[:, :, 2]) >> 8
Yb = (77*b[:, :, 0].astype(np.int32) + 150*b[:, :, 1] + 29*b[:, :, 2]) >> 8
print("diff(Y亮 - Y暗) 统计：均值 %.1f  中位 %.1f  p10 %.1f  p90 %.1f" %
      (diff.mean(), np.median(diff), np.percentile(diff, 10), np.percentile(diff, 90)))
for lo, hi in ((0, 8), (8, 24), (24, 48), (48, 96), (96, 200)):
    sel = (Yd >= lo) & (Yd < hi)
    if sel.sum() > 1000:
        print("  暗图 Y 在 [%3d,%3d) 的像素: %7d 个，正差中位 %+6.1f，亮图对应值中位 %6.1f" %
              (lo, hi, sel.sum(), np.median(Yb[sel]-Yd[sel]), np.median(Yb[sel])))
print("saved " + OUT)
