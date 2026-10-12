# -*- coding: utf-8 -*-
"""Measure the OSD text colours in the HDMI captures.

The OSD is drawn in hdmi_mixer.v *after* the whole ISP chain, with hard-wired
constant colours:
    COLOR_DYN_TEXT = 24'hfff200   (CNT line, yellow)
    COLOR_ALG_TEXT = 24'h00ff88   (MODE line, spring green)
    logo triangles = red / orange
So whatever RGB we read back on the captured frame is the transfer of the
DISPLAY path alone, independent of sensor / BLC / demosaic / AWB / gamma.

If the yellow reads (255,242,0) the display path is colour-neutral and any
green cast must come from the ISP.  If it reads tinted, the fault is downstream.
"""
import glob
import os
import sys
from collections import Counter

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SHOTS = sorted(glob.glob(r"E:\FPGA\Screenshot 2026-10-11 17-*.png"))

# rectangles in 1920x1080 coordinates
CNT = (540, 150, 900, 230)
MODE = (240, 240, 650, 300)


def top_colors(img, box, n=4, pred=None):
    x0, y0, x1, y1 = box
    a = np.asarray(img)[y0:y1, x0:x1].reshape(-1, 3)
    if pred is not None:
        a = a[pred(a)]
    if len(a) == 0:
        return []
    keys = (a[:, 0].astype(np.uint32) << 16) | (a[:, 1].astype(np.uint32) << 8) | a[:, 2].astype(np.uint32)
    return [(tuple(int(v) for v in ((k >> 16) & 255, (k >> 8) & 255, k & 255)), c)
            for k, c in Counter(keys.tolist()).most_common(n)]


print("Expected OSD colours:  CNT text = (255,242,  0)   MODE text = (  0,255,136)")
print()
print("%-26s | %-28s | %s" % ("file", "CNT box top colours (bright px)", "MODE box top colours"))
print("-" * 118)
for p in SHOTS:
    im = Image.open(p).convert("RGB")
    cnt = top_colors(im, CNT, 3, lambda a: a[:, 0] > 180)
    mode = top_colors(im, MODE, 3, lambda a: a[:, 1] > 150)
    print("%-26s | %-28s | %s" % (
        os.path.basename(p).replace("Screenshot 2026-10-11 ", "").replace(".png", ""),
        "  ".join("%s x%d" % (c, n) for c, n in cnt),
        "  ".join("%s x%d" % (c, n) for c, n in mode)))

print()
print("=== pooled: brightest 200 pixels of every CNT box ===")
pool = []
for p in SHOTS:
    a = np.asarray(Image.open(p).convert("RGB"))[CNT[1]:CNT[3], CNT[0]:CNT[2]].reshape(-1, 3)
    pool.append(a)
pool = np.concatenate(pool)
sel = pool[pool.sum(axis=1) > 600]
if len(sel):
    print("n=%d  mean=%s  median=%s  p90=%s" % (
        len(sel), np.round(sel.mean(axis=0), 2), np.median(sel, axis=0),
        np.percentile(sel, 90, axis=0)))
    print("  R/G = %.4f   B/G = %.4f" % (sel[:, 0].mean() / sel[:, 1].mean(),
                                         sel[:, 2].mean() / sel[:, 1].mean()))
