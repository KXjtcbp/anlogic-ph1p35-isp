# -*- coding: utf-8 -*-
"""Analyse the newest capture batch: OSD decode + scene stats + capture-chain identity check."""
import glob
import os
import sys
import time
from collections import Counter

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BATCH = sorted(glob.glob(r"E:\FPGA\Screenshot 2026-10-11 19-1*.png"), key=os.path.getmtime)
if not BATCH:
    sys.exit("no 19:1x screenshots")

OSD = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]


def mask(w, h):
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in OSD:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


print("=" * 108)
print("BATCH = %d files, all under E:\\FPGA, mtime 19:14:05 .. 19:14:29" % len(BATCH))
print("=" * 108)

for p in BATCH:
    a = np.asarray(Image.open(p).convert("RGB"))
    H, W = a.shape[:2]
    s = W / 1280.0
    print()
    print("-" * 108)
    print("%s   mtime %s   %dx%d"
          % (os.path.basename(p), time.strftime("%H:%M:%S", time.localtime(os.path.getmtime(p))), W, H))

    # --- OSD colour ground truth -------------------------------------------
    R, G, B = a[:, :, 0].astype(int), a[:, :, 1].astype(int), a[:, :, 2].astype(int)
    m = (R > 200) & (G > 200) & (B < 90)
    if m.sum():
        c = Counter(map(tuple, a[m].tolist()))
        t, n = c.most_common(1)[0]
        print("  OSD yellow  : top %-16s x%-5d  diff vs (255,242,0) = %s"
              % (str(t), n, tuple(t[i] - (255, 242, 0)[i] for i in range(3))))
    m = (R < 110) & (G > 180) & (B > 60) & (B < 220)
    if m.sum():
        c = Counter(map(tuple, a[m].tolist()))
        t, n = c.most_common(1)[0]
        print("  OSD green   : top %-16s x%-5d  diff vs (0,255,136)  = %s"
              % (str(t), n, tuple(t[i] - (0, 255, 136)[i] for i in range(3))))

    # --- logo solid areas (the colour chart) --------------------------------
    reg = a[int(20 * s):int(120 * s), int(10 * s):int(140 * s)].reshape(-1, 3)
    c = Counter(map(tuple, reg.tolist()))
    print("  logo top5   : %s" % ", ".join("%s x%d" % (str(k), v) for k, v in c.most_common(5)))

    # --- scene statistics ---------------------------------------------------
    px = a[mask(W, H)]
    Rm, Gm, Bm = px[:, 0].mean(), px[:, 1].mean(), px[:, 2].mean()
    Y = (77 * px[:, 0].astype(int) + 150 * px[:, 1].astype(int) + 29 * px[:, 2].astype(int)) >> 8
    print("  scene       : Y mean=%6.2f std=%6.2f p1=%3d p10=%3d p50=%3d p90=%3d p99=%3d max=%3d"
          % (Y.mean(), Y.std(), np.percentile(Y, 1), np.percentile(Y, 10), np.percentile(Y, 50),
             np.percentile(Y, 90), np.percentile(Y, 99), Y.max()))
    print("              : R=%6.2f G=%6.2f B=%6.2f   R/G=%.4f B/G=%.4f   >=250=%.3f%% <=8=%.2f%% ==0=%.2f%%"
          % (Rm, Gm, Bm, Rm / Gm, Bm / Gm, 100.0 * (Y >= 250).mean(), 100.0 * (Y <= 8).mean(),
             100.0 * (Y == 0).mean()))
    # centre crop = the actual target, avoids the dark surround
    cy0, cy1 = int(H * 0.35), int(H * 0.75)
    cx0, cx1 = int(W * 0.25), int(W * 0.80)
    cp = a[cy0:cy1, cx0:cx1].reshape(-1, 3).astype(float)
    cR, cG, cB = cp[:, 0].mean(), cp[:, 1].mean(), cp[:, 2].mean()
    cY = (77 * cp[:, 0] + 150 * cp[:, 1] + 29 * cp[:, 2]) / 256.0
    print("  centre crop : R=%6.2f G=%6.2f B=%6.2f   R/G=%.4f B/G=%.4f   Ymean=%.2f Ystd=%.2f"
          % (cR, cG, cB, cR / cG, cB / cG, cY.mean(), cY.std()))
