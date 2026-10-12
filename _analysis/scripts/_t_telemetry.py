# -*- coding: utf-8 -*-
"""遥测版上板：读 T1/T2/T3 的橙色遥测行 + 常规统计。
遥测层常量（hdmi_mixer.v）：
  COLOR_DBG_TEXT = 24'hff8000（橙）
  DBG_OSD_X=376 DBG_OSD_Y=152 DBG_OSD_W=304(19 字符 x 16 字距) DBG_OSD_H=10
  位打包：S_dbg_2d[48:42]=AE 增益索引7b  [41:40]=AE 状态2b  [39:32]=实测均值8b
          [31:16]=AWB R 增益[19:4]  [15:0]=AWB B 增益[19:4]
"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
INBOX = os.path.join(WS, "inbox")
FILES = ["T1.png", "T2.png", "T3.png"]
LINE = "=" * 76

# OSD 遮罩（1280 空间，按 w/1280 缩放）
MASK = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195),
        (290, 145, 545, 168)]   # 第 4 块 = 橙色遥测行(1920 空间 376..679 x 152..161 -> /1.5)

for fn in FILES:
    p = os.path.join(INBOX, fn)
    if not os.path.exists(p):
        print("MISSING", p); continue
    im = Image.open(p).convert("RGB")
    w, h = im.size
    a = np.asarray(im).astype(np.int32)
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in MASK:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    R, G, B = a[..., 0][m], a[..., 1][m], a[..., 2][m]
    Y = (77 * a[..., 0] + 150 * a[..., 1] + 29 * a[..., 2]) >> 8
    Ym = Y[m]
    # 橙色遥测行检测（1920 空间 x376..679 y152..161）
    sub = a[150:164, 370:686]
    om = (sub[..., 0] > 190) & (sub[..., 1] > 80) & (sub[..., 1] < 190) & (sub[..., 2] < 70)
    ys, xs = np.where(om)
    obb = ("x[%d..%d] y[%d..%d] n=%d" % (xs.min() + 370, xs.max() + 370,
                                         ys.min() + 150, ys.max() + 150, len(ys))) if len(ys) else "未找到"
    print("%s  %dx%d" % (fn, w, h))
    print("   Ymean %7.3f  Ystd %6.3f  p1 %3d p10 %3d p50 %3d p90 %3d p99 %3d max %3d"
          % (Ym.mean(), Ym.std(), np.percentile(Ym, 1), np.percentile(Ym, 10),
             np.percentile(Ym, 50), np.percentile(Ym, 90), np.percentile(Ym, 99), Ym.max()))
    print("   ==0 %6.3f%%  <=8 %6.3f%%  >=250 %6.3f%%   R %6.2f G %6.2f B %6.2f  R-G %+6.3f B-G %+6.3f  R/G %.4f B/G %.4f"
          % (100 * (Ym == 0).mean(), 100 * (Ym <= 8).mean(), 100 * (Ym >= 250).mean(),
             R.mean(), G.mean(), B.mean(), R.mean() - G.mean(), B.mean() - G.mean(),
             R.mean() / max(G.mean(), 1e-9), B.mean() / max(G.mean(), 1e-9)))
    print("   橙色行 bbox: %s" % obb)
    # logo identity
    reg = a[:250, :250].reshape(-1, 3)
    import collections
    top = collections.Counter(map(tuple, reg)).most_common(3)
    print("   logo top3: " + "  ".join("(%d,%d,%d)x%d" % (c[0], c[1], c[2], n) for c, n in top))
    print()

# 裁橙色行，放大 4 倍纵拼
tiles = []
for fn in FILES:
    p = os.path.join(INBOX, fn)
    if not os.path.exists(p): continue
    im = Image.open(p).convert("RGB")
    c = im.crop((370, 148, 690, 166))
    c = c.resize((c.width * 3, c.height * 6), Image.LANCZOS)   # 横向 3x 纵向 6x，字形拉高好认
    tiles.append((fn, c))
W = max(c.width for _, c in tiles) + 90
H = sum(c.height + 14 for _, c in tiles) + 10
sh = Image.new("RGB", (W, H), (20, 20, 20)); dr = ImageDraw.Draw(sh)
y = 5
for nm, c in tiles:
    dr.text((4, y + c.height // 2 - 6), nm + "  x6", fill=(255, 255, 0))
    sh.paste(c, (86, y)); y += c.height + 14
out = os.path.join(WS, r"_analysis\out\t_telemetry_sheet.png")
sh.save(out)
print("遥测行拼图 -> %s  %s" % (out, sh.size))
