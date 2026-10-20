# -*- coding: utf-8 -*-
"""分析最新截图 + 检查是否有新的 ChipWatcher 导出。"""
import os, sys, re, time, glob, collections
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R_ = r"E:\FPGA"

print("=== ChipWatcher export dirs ===")
for d in ("raw_exports", os.path.join("proj", "baseline", "lab3", "td_project", "camera_to_dsi_display_Runs", "phy_1", "cw")):
    p = os.path.join(R_, d)
    if not os.path.isdir(p):
        print("  (none) %s" % d); continue
    fs = [(os.path.getmtime(os.path.join(p, f)), f, os.path.getsize(os.path.join(p, f)))
          for f in os.listdir(p) if os.path.isfile(os.path.join(p, f))]
    fs.sort(reverse=True)
    print("  %s  (%d files)" % (d, len(fs)))
    for t, f, s in fs[:8]:
        print("     %s %9d  %s" % (time.strftime("%m-%d %H:%M:%S", time.localtime(t)), s, f))

# newest screenshot
cands = [p for p in glob.glob(os.path.join(R_, "Screenshot*.png"))]
cands.sort(key=os.path.getmtime, reverse=True)
if not cands:
    print("\nno Screenshot*.png in root"); sys.exit(0)
p = cands[0]
print("\n=== analysing %s ===" % os.path.basename(p))
a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
h, w, _ = a.shape
m = np.ones((h, w), bool)
for x0, y0, x1, y1 in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
    s = w / 1280.0
    m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
Y = (77 * a[..., 0] + 150 * a[..., 1] + 29 * a[..., 2]) >> 8
ys = Y[m]
R = a[..., 0][m].astype(float); G = a[..., 1][m].astype(float); B = a[..., 2][m].astype(float)
print("  size=%dx%d  Ymean=%.3f Ystd=%.3f p1=%d p10=%d p50=%d p90=%d p99=%d max=%d" %
      (w, h, ys.mean(), ys.std(), np.percentile(ys, 1), np.percentile(ys, 10),
       np.percentile(ys, 50), np.percentile(ys, 90), np.percentile(ys, 99), ys.max()))
print("  >=250=%.3f%%  <=8=%.3f%%  ==0=%.3f%%" % (100 * (ys >= 250).mean(), 100 * (ys <= 8).mean(), 100 * (ys == 0).mean()))
print("  R=%.3f G=%.3f B=%.3f | R-G=%+.3f B-G=%+.3f | R/G=%.4f B/G=%.4f" %
      (R.mean(), G.mean(), B.mean(), R.mean() - G.mean(), B.mean() - G.mean(), R.mean() / G.mean(), B.mean() / G.mean()))
print("\n  OSD yellow bbox / green bbox:")
for nm, lo, hi in (("yellow", (200, 180, 0), (255, 255, 60)), ("green", (0, 180, 60), (80, 255, 180))):
    mm = np.all((a >= np.array(lo)) & (a <= np.array(hi)), axis=2)
    yy, xx = np.where(mm)
    print("    %-7s n=%5d  x[%d..%d] y[%d..%d]" % (nm, len(yy), xx.min(), xx.max(), yy.min(), yy.max()) if len(yy) else "    %s none" % nm)
print("\n  logo region top colours (identity check; ROM (28,45,78)x3003 / (237,28,36)x785):")
reg = a[:250, :250].reshape(-1, 3)
c = collections.Counter(map(tuple, reg))
for t, n in c.most_common(4):
    print("    (%3d,%3d,%3d) x%d" % (t[0], t[1], t[2], n))
print("\n  per-band R/G:")
for nm, sl in (("top", slice(0, h // 3)), ("mid", slice(h // 3, 2 * h // 3)), ("bot", slice(2 * h // 3, h))):
    s = m[sl]
    print("    %-3s R/G=%.4f B/G=%.4f" % (nm, a[..., 0][sl][s].mean() / max(a[..., 1][sl][s].mean(), 1e-9),
                                          a[..., 2][sl][s].mean() / max(a[..., 1][sl][s].mean(), 1e-9)))
# downscaled view
Image.open(p).convert("RGB").resize((900, 506), Image.LANCZOS).save(os.path.join(R_, "_analysis", "out", "view_newest.png"))
print("\n  saved _analysis/out/view_newest.png")
