# -*- coding: utf-8 -*-
"""读 inbox 里最新一批的 OSD 两行遥测 + 全帧统计。
橙色遥测层 COLOR_DBG_TEXT = 24'hff8000。
内部坐标 1280x720 -> 屏幕 = x1.5（采集图 1920x1080）。
  第 1 行 内部 (376,152) 尺寸 304x10  -> 屏幕 x[564..1019] y[228..242]
  第 2 行 内部 (376,164) 尺寸 304x10  -> 屏幕 x[564..1019] y[246..261]
"""
import os, sys, collections
import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
FILES = ["SW4\u4e0b.png", "SW4\u4e0a1.png", "SW4\u4e0a2.png"]
BAND1 = (560, 226, 1024, 244)
BAND2 = (560, 244, 1024, 262)
ORANGE = np.array([255, 128, 0])


def osd_mask(w, h):
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195),
                           (376, 146, 680, 178)]:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


rows = []
for fn in FILES:
    p = os.path.join(WS, "inbox", fn)
    im = Image.open(p).convert("RGB")
    a = np.asarray(im).astype(np.int32)
    h, w, _ = a.shape
    m = osd_mask(w, h)
    px = a[m]
    Y = (77 * px[:, 0] + 150 * px[:, 1] + 29 * px[:, 2]) >> 8
    R, G, B = px[:, 0].astype(float), px[:, 1].astype(float), px[:, 2].astype(float)
    print("=" * 78)
    print("%s   %dx%d   mtime=%s" % (fn, w, h,
          __import__("datetime").datetime.fromtimestamp(os.path.getmtime(p)).strftime("%H:%M:%S")))
    print("  Ymean %.2f  Ystd %.2f  p1 %d p10 %d p50 %d p90 %d p99 %d max %d"
          % (Y.mean(), Y.std(), np.percentile(Y, 1), np.percentile(Y, 10), np.percentile(Y, 50),
             np.percentile(Y, 90), np.percentile(Y, 99), Y.max()))
    print("  ov250 %.3f%%  <=8 %.3f%%  ==0 %.3f%%" % (100 * (Y >= 250).mean(),
          100 * (Y <= 8).mean(), 100 * (Y == 0).mean()))
    print("  R %.2f G %.2f B %.2f | R/G %.4f B/G %.4f | R-G %+.3f B-G %+.3f"
          % (R.mean(), G.mean(), B.mean(), R.mean() / G.mean(), B.mean() / G.mean(),
             R.mean() - G.mean(), B.mean() - G.mean()))
    for nm, band in (("L1", BAND1), ("L2", BAND2)):
        sub = a[band[1]:band[3], band[0]:band[2]]
        d = np.abs(sub - ORANGE).sum(axis=2)
        ys, xs = np.where(d <= 70)
        if len(ys):
            print("  %s orange n=%4d  x[%d..%d] y[%d..%d]" % (nm, len(ys),
                  band[0] + xs.min(), band[0] + xs.max(), band[1] + ys.min(), band[1] + ys.max()))
        else:
            print("  %s orange 无" % nm)
        c = Image.fromarray(np.asarray(im)[band[1]:band[3], band[0]:band[2]])
        c = c.resize((c.width * 4, c.height * 4), Image.LANCZOS)
        rows.append(("%s %s" % (fn, nm), c))

W = max(c.width for _, c in rows) + 260
H = sum(c.height + 8 for _, c in rows) + 10
sh = Image.new("RGB", (W, H), (20, 20, 20))
dr = ImageDraw.Draw(sh)
y = 5
for nm, c in rows:
    dr.text((5, y + c.height // 2 - 6), nm, fill=(255, 255, 0))
    sh.paste(c, (255, y))
    y += c.height + 8
out = os.path.join(WS, r"_analysis\out\p_telemetry_sheet.png")
sh.save(out)
print("\nsaved %s  %s" % (out, sh.size))
