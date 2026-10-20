# -*- coding: utf-8 -*-
"""判断 LSC 逐列 R/G 极差的物理下限：区分真实 shading 结构 与 逐列测量噪声。"""
import os
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"


def osd_mask(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


def col_profile(path, y0, y1, x0=96, x1=1824):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    h, w, _ = a.shape
    m = osd_mask(h, w)
    band = np.zeros_like(m)
    band[y0:y1, :] = True
    sel = m & band
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    rg, bg = [], []
    for x in range(x0, x1):
        s = sel[:, x]
        if s.sum() < 50:
            rg.append(np.nan); bg.append(np.nan); continue
        g = G[:, x][s].mean()
        rg.append(R[:, x][s].mean() / g if g > 1e-6 else np.nan)
        bg.append(B[:, x][s].mean() / g if g > 1e-6 else np.nan)
    return np.array(rg), np.array(bg)


def smooth(v, win=21):
    k = np.ones(win) / win
    return np.convolve(np.pad(v, (win // 2, win // 2), mode="edge"), k, mode="valid")


def ideal_resid(v, nodes):
    """理想节点级校正（把每个节点均值归一到 1）后，剩余剖面极差。"""
    step = 1920.0 / nodes
    out = v.copy()
    per = []
    for n in range(nodes):
        lo = max(96, int(round(n * step)))
        hi = min(1824, int(round((n + 1) * step)))
        if hi <= lo:
            continue
        s = slice(lo - 96, hi - 96)
        seg = out[s]
        out[s] = seg / np.nanmean(seg)
        per.append(np.nanmax(out[s]) - np.nanmin(out[s]))
    return (np.nanmax(out) - np.nanmin(out)), float(np.mean(per))


CASES = [("N1 nocorr", "captures/2026-10-13_白纸靶面_无LSC对照/N1_232908.png"),
         ("N2 nocorr", "captures/2026-10-13_白纸靶面_无LSC对照/N2_232918.png"),
         ("N3 nocorr", "captures/2026-10-13_白纸靶面_无LSC对照/N3_232923.png"),
         ("12:40 live", "inbox/Screenshot 2026-10-14 12-40-45.png")]

print("=== 逐列 R/G 结构：原始极差 vs 平滑后极差 vs 理想 20 节点残差 ===")
for tag, rel in CASES:
    p = os.path.join(WS, rel)
    if not os.path.exists(p):
        print("  MISSING", rel); continue
    rg, bg = col_profile(p, 300, 800)
    s = smooth(rg, 21)
    t_raw, _ = ideal_resid(rg, 20)
    t_smo, wi = ideal_resid(s, 20)
    print("  %-11s 原始极差=%.4f | 平滑(21)极差=%.4f | 理想20节点(原始)=%.4f | 理想20节点(平滑)=%.4f"
          % (tag, np.nanmax(rg) - np.nanmin(rg), np.nanmax(s) - np.nanmin(s), t_raw, t_smo))

print()
print("=== 平滑剖面的节点均值（N1，20 节点）===")
rg, _ = col_profile(os.path.join(WS, CASES[0][1]), 300, 800)
s = smooth(rg, 21)
for n in range(20):
    lo = max(96, int(round(n * 96)))
    hi = min(1824, int(round((n + 1) * 96)))
    if hi <= lo:
        continue
    print("   节点%2d x=%4d..%4d  R/G=%.4f" % (n, lo, hi - 1, np.nanmean(s[lo - 96:hi - 96])))
