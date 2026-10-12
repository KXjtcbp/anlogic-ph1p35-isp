# -*- coding: utf-8 -*-
"""通用采集图统计：python stat_imgs.py <图1> [图2 ...]
输出（遮掉 3 块 OSD）：Y 均值/标准差/分位/max、过曝、暗部、通道均值与比值、纯黑占比。
"""
import os
import sys
import numpy as np
from PIL import Image


def osd_mask(w, h):
    s = w / 1280.0
    boxes = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in boxes:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def stat(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    a = np.asarray(im)
    m = osd_mask(w, h)
    px = a[m]
    R, G, B = (px[:, 0].astype(np.int32), px[:, 1].astype(np.int32), px[:, 2].astype(np.int32))
    Y = (77 * R + 150 * G + 29 * B) >> 8
    return dict(w=w, h=h, n=Y.size, Y=Y, R=R, G=G, B=B)


def show(path):
    if not os.path.exists(path):
        print("MISSING", path); return
    d = stat(path)
    Y, R, G, B = d["Y"], d["R"], d["G"], d["B"]
    print("%-34s %dx%d Ymean=%7.3f std=%6.3f p1=%3d p10=%3d p50=%3d p90=%3d p99=%3d max=%3d "
          ">=250=%.3f%% <=8=%5.2f%% ==0=%6.2f%% | R/G/B=%6.2f/%6.2f/%6.2f R/G=%.4f B/G=%.4f" %
          (os.path.basename(path), d["w"], d["h"], Y.mean(), Y.std(),
           np.percentile(Y, 1), np.percentile(Y, 10), np.percentile(Y, 50),
           np.percentile(Y, 90), np.percentile(Y, 99), Y.max(),
           100.0 * (Y >= 250).mean(), 100.0 * (Y <= 8).mean(), 100.0 * (Y == 0).mean(),
           R.mean(), G.mean(), B.mean(), R.mean() / max(G.mean(), 1e-9),
           B.mean() / max(G.mean(), 1e-9)))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        show(p)
