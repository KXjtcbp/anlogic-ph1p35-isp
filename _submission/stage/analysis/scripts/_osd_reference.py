# -*- coding: utf-8 -*-
"""Independent check on the capture chain: read back the two OSD text constants
that hdmi_mixer.v writes verbatim, plus the scene statistics of the newest shot.

    COLOR_DYN_TEXT = 24'hfff200 -> (255,242,0)   CNT line
    COLOR_ALG_TEXT = 24'h00ff88 -> (  0,255,136) MODE line
    logo main blue (ROM)        -> ( 28, 45,78)
    logo red triangle (ROM)     -> (237, 28,36)

Usage: python _osd_reference.py [screenshot ...]   (default: newest under E:\\FPGA)
"""
import glob
import os
import sys
import time
from collections import Counter

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def newest():
    c = glob.glob(r"E:\FPGA\Screenshot*.png")
    if not c:
        sys.exit("no Screenshot*.png under E:\\FPGA")
    return max(c, key=os.path.getmtime)


paths = sys.argv[1:] or [newest()]

for path in paths:
    print("=" * 94)
    print("%s   mtime %s" % (os.path.basename(path),
                             time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(path)))))
    a = np.asarray(Image.open(path).convert("RGB"))
    H, W = a.shape[:2]
    R, G, B = a[:, :, 0].astype(int), a[:, :, 1].astype(int), a[:, :, 2].astype(int)

    m = (R > 200) & (G > 200) & (B < 90)
    v = a[m]
    if len(v):
        c = Counter(map(tuple, v.tolist()))
        print("  CNT yellow text   : %5d px   top %s" % (m.sum(), c.most_common(3)))
        print("                      exact (255,242,0) hits = %d"
              % sum(n for t, n in c.items() if t == (255, 242, 0)))

    m = (G > 150) & (R < 140) & (B > 60) & (B < 220) & (R < B)
    v = a[m]
    if len(v):
        c = Counter(map(tuple, v.tolist()))
        print("  MODE green text   : %5d px   top %s" % (m.sum(), c.most_common(3)))
        print("                      exact (0,255,136) hits = %d"
              % sum(n for t, n in c.items() if t == (0, 255, 136)))

    # logo main blue field: sample the centre of the 160x160 window
    sx = W / 1280.0
    reg = a[int(60 * sx):int(100 * sx), int(40 * sx):int(120 * sx)].reshape(-1, 3)
    c = Counter(map(tuple, reg.tolist()))
    print("  logo blue field   : top %s   (ROM value is (28,45,78))" % (c.most_common(3),))

    # scene statistics with the three OSD boxes masked out
    m = np.ones((H, W), bool)
    for x0, y0, x1, y1 in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0 * sx):int(y1 * sx), int(x0 * sx):int(x1 * sx)] = False
    px = a[m]
    Rm, Gm, Bm = px[:, 0].mean(), px[:, 1].mean(), px[:, 2].mean()
    Y = (77 * px[:, 0].astype(int) + 150 * px[:, 1].astype(int) + 29 * px[:, 2].astype(int)) >> 8
    print("  scene (OSD masked): Y mean=%6.2f std=%6.2f p50=%3d   R/G=%.4f B/G=%.4f   >=250=%.3f%%"
          % (Y.mean(), Y.std(), int(np.percentile(Y, 50)), Rm / Gm, Bm / Gm, 100.0 * (Y >= 250).mean()))
