# -*- coding: utf-8 -*-
"""把两行遥测按「单元格」逐个裁出来，最近邻放大 + 标注位置序号，便于逐字读数。
   cell 宽 16 内部像素，起点内部 x=376；第1行内部 y=152，第2行内部 y=164。
   屏幕 = 内部 x 1.5（采集图 1920x1080）。"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
FILES = ["SW4\u4e0b.png", "SW4\u4e0a1.png", "SW4\u4e0a2.png"]
X0_IN, CELLW = 376, 16
L1_Y, L2_Y = 152, 164
GLYPH_W, GLYPH_H = 5, 7          # 每个字只画前 5 列 x 7 行
Z = 8                            # 放大倍数


def cell_box(row_y_in, i):
    x_in = X0_IN + CELLW * i
    return (int((x_in) * 1.5) - 1, int(row_y_in * 1.5) - 1,
            int((x_in + GLYPH_W) * 1.5) + 2, int((row_y_in + GLYPH_H) * 1.5) + 2)


rows = []
for fn in FILES:
    im = Image.open(os.path.join(WS, "inbox", fn)).convert("RGB")
    for tag, y in (("L1", L1_Y), ("L2", L2_Y)):
        strips = []
        for i in range(19):
            c = im.crop(cell_box(y, i))
            c = c.resize((c.width * Z, c.height * Z), Image.NEAREST)
            strips.append(c)
        gw = max(c.width for c in strips) + 6
        gh = max(c.height for c in strips)
        strip = Image.new("RGB", (gw * 19, gh + 16), (25, 25, 25))
        d = ImageDraw.Draw(strip)
        for i, c in enumerate(strips):
            strip.paste(c, (i * gw + 3, 16))
            d.text((i * gw + 3, 2), str(i), fill=(0, 255, 255))
        rows.append(("%s %s" % (fn.replace(".png", ""), tag), strip))

W = max(s.width for _, s in rows) + 150
H = sum(s.height + 6 for _, s in rows) + 6
sheet = Image.new("RGB", (W, H), (20, 20, 20))
d = ImageDraw.Draw(sheet)
y = 3
for nm, s in rows:
    d.text((3, y + s.height // 2 - 6), nm, fill=(255, 255, 0))
    sheet.paste(s, (145, y))
    y += s.height + 6
out = os.path.join(WS, r"_analysis\out\p_cells.png")
sheet.save(out)
print("saved", out, sheet.size)
