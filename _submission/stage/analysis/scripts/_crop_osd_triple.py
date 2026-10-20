# -*- coding: utf-8 -*-
"""裁出三张根目录截图的 OSD 文本区并放大，便于目视/OCR 读取 CNT 与开关状态行。"""
import os
from PIL import Image

ROOT = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis\out"
IMGS = [
    "Screenshot 2026-10-11 12-49-49.png",
    "Screenshot 2026-10-11 12-49-53.png",
    "Screenshot 2026-10-11 12-50-24.png",
]

# 1280 空间下的三块 OSD，按 w/1280 缩放；这里只取 CNT 行 + MODE 行
BOXES_1280 = [(355, 112, 605, 148), (160, 168, 275, 192)]

tiles = []
for name in IMGS:
    p = os.path.join(ROOT, name)
    im = Image.open(p).convert("RGB")
    s = im.size[0] / 1280.0
    rows = []
    for (x0, y0, x1, y1) in BOXES_1280:
        c = im.crop((int(x0 * s), int(y0 * s), int(x1 * s), int(y1 * s)))
        rows.append(c)
    W = max(r.size[0] for r in rows)
    H = sum(r.size[1] for r in rows) + 6
    strip = Image.new("RGB", (W, H), (0, 0, 0))
    y = 0
    for r in rows:
        strip.paste(r, (0, y)); y += r.size[1] + 6
    strip = strip.resize((strip.size[0] * 3, strip.size[1] * 3), Image.LANCZOS)
    tiles.append((name, strip))
    print("%-40s crop=%s -> %s" % (name, (W, H), strip.size))

# 纵向拼成一张总图
W = max(t.size[0] for _, t in tiles)
H = sum(t.size[1] for _, t in tiles) + 12 * (len(tiles) - 1)
sheet = Image.new("RGB", (W, H), (32, 32, 32))
y = 0
for _, t in tiles:
    sheet.paste(t, (0, y)); y += t.size[1] + 12
sheet.save(os.path.join(OUT, "osd_1211_triple.png"))
print("saved", os.path.join(OUT, "osd_1211_triple.png"), sheet.size)
