# -*- coding: utf-8 -*-
"""深度诊断 20/21 两张图：(1) 用颜色自动定位 OSD 文字框；(2) 剔除纯黑平台后的曲线比对；
(3) 追查 shot-21 里码 1/2 的来源。"""
import os
import re
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"E:\FPGA"
DIR = os.path.join(ROOT, "captures", "2026-10-11_色彩修复验证")
PA = os.path.join(DIR, "20_SW1上SW2下SW3上SW4上.png")
PB = os.path.join(DIR, "21_SW1上SW2上SW3上SW4上.png")
GAMMA_V = os.path.join(ROOT, "proj", "baseline", "lab3", "user_source", "hdl_source", "isp", "isp_gamma.v")
OUT = os.path.join(ROOT, "_analysis", "out")


def load_lut():
    txt = open(GAMMA_V, "rb").read().decode("utf-8", "replace")
    hits = re.findall(r"mem_b00\[\s*(\d+)\]\s*=\s*8'h([0-9a-fA-F]{1,2})\s*;", txt)
    t = [0] * 256
    for i, v in hits:
        t[int(i)] = int(v, 16)
    return np.array(t, np.int32)


def find_color(a, target, tol):
    d = np.abs(a.astype(np.int32) - np.array(target, np.int32)).sum(axis=2)
    return d <= tol


lut = load_lut()
A = np.asarray(Image.open(PA).convert("RGB"))
B = np.asarray(Image.open(PB).convert("RGB"))
print("A %s  shape=%s" % (os.path.basename(PA), A.shape))
print("B %s  shape=%s" % (os.path.basename(PB), B.shape))

# ---------- 1. locate OSD by colour ----------
print("=" * 100)
for tag, a in (("20", A), ("21", B)):
    yel = find_color(a, (255, 242, 0), 90)
    grn = find_color(a, (0, 255, 136), 110)
    for nm, m in (("yellow CNT", yel), ("green MODE", grn)):
        ys, xs = np.nonzero(m)
        if len(ys) == 0:
            print("  %s %-12s none" % (tag, nm)); continue
        print("  %s %-12s n=%6d  bbox x[%4d..%4d] y[%4d..%4d]  peak=%s"
              % (tag, nm, len(ys), xs.min(), xs.max(), ys.min(), ys.max(),
                 tuple(a[ys[len(ys) // 2], xs[len(xs) // 2]])))

# crop generously around each, 3x
tiles = []
for tag, a in (("20", A), ("21", B)):
    for nm, tgt, tol in (("cnt", (255, 242, 0), 90), ("mode", (0, 255, 136), 110)):
        m = find_color(a, tgt, tol)
        ys, xs = np.nonzero(m)
        if len(ys) == 0:
            continue
        x0, x1 = max(0, xs.min() - 10), min(a.shape[1], xs.max() + 11)
        y0, y1 = max(0, ys.min() - 8), min(a.shape[0], ys.max() + 9)
        t = Image.fromarray(a[y0:y1, x0:x1]).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.LANCZOS)
        tiles.append((tag + " " + nm, t))
W = max(t.width for _, t in tiles)
H = sum(t.height + 8 for _, t in tiles)
sh = Image.new("RGB", (W, H), (20, 20, 20))
d = ImageDraw.Draw(sh)
y = 0
for lab, t in tiles:
    sh.paste(t, (0, y)); d.text((4, y + 2), lab, fill=(255, 0, 255)); y += t.height + 8
sh.save(os.path.join(OUT, "osd_fix2011_v2.png"))
print("  saved %s  %s" % (os.path.join(OUT, "osd_fix2011_v2.png"), sh.size))

# ---------- 2. curve comparison excluding the pure-black plateau ----------
print("=" * 100)
Ya = (77 * A[..., 0].astype(np.int32) + 150 * A[..., 1].astype(np.int32) + 29 * A[..., 2].astype(np.int32)) >> 8
Yb = (77 * B[..., 0].astype(np.int32) + 150 * B[..., 1].astype(np.int32) + 29 * B[..., 2].astype(np.int32)) >> 8
for lo in (0, 1, 9, 33):
    sel = Ya > lo
    pred = lut[Ya[sel]]
    meas = Yb[sel]
    d_ = meas - pred
    print("  Ya > %-3d  n=%8d (%.2f%%)  exact=%6.2f%%  |d|<=1=%6.2f%%  |d|<=2=%6.2f%%  mean|d|=%5.3f  bias=%+5.3f"
          % (lo, sel.sum(), 100.0 * sel.mean(),
             100.0 * (d_ == 0).mean(), 100.0 * (np.abs(d_) <= 1).mean(),
             100.0 * (np.abs(d_) <= 2).mean(), np.abs(d_).mean(), d_.mean()))

# ---------- 3. where do codes 1 and 2 come from in shot 21? ----------
print("=" * 100)
reach = set(int(x) for x in np.unique(lut))
unreach = sorted(set(range(256)) - reach)
print("  unreachable output codes (%d):" % len(unreach))
print("   ", unreach)
print("  in shot 21, G-channel occupancy of every unreachable code that has >0 px:")
tot = B[..., 1].size
rows = []
for c in unreach:
    n = int((B[..., 1] == c).sum())
    if n:
        # for each, what would the input have to be (i.e. what bypass value maps here)?
        src = int(np.nonzero(lut == c)[0].size)
        rows.append((n, c, src))
rows.sort(reverse=True)
for n, c, src in rows[:15]:
    print("    code %3d : %7d px (%.4f%%)  #inputs mapping here in the table = %d" % (c, n, 100.0 * n / tot, src))
print("  total on unreachable = %d px (%.3f%%)" % (sum(r[0] for r in rows), 100.0 * sum(r[0] for r in rows) / tot))

# 1 and 2 specifically
for c in (1, 2, 3):
    mask = B[..., 1] == c
    n = int(mask.sum())
    if n:
        ys, xs = np.nonzero(mask)
        # what does shot A read at those same positions?
        av = Ya[mask]
        print("    code %-2d n=%7d  shot-A Y at those px: mean=%.2f  hist(0..6)=%s"
              % (c, n, av.mean(), [int((av == k).sum()) for k in range(7)]))
    else:
        print("    code %-2d n=0" % c)

# ---------- 4. scene: is the dark side truly at black level? ----------
print("=" * 100)
print("  shot A (bypass) column-mean Y every 120 px:")
cm = Ya.mean(axis=0)
print("   ", [int(cm[x]) for x in range(0, 1920, 120)])
print("  shot B (curve)  column-mean Y every 120 px:")
cmb = Yb.mean(axis=0)
print("   ", [int(cmb[x]) for x in range(0, 1920, 120)])
print("  shot A (bypass) row-mean Y every 60 px:")
rm = Ya.mean(axis=1)
print("   ", [int(rm[y]) for y in range(0, 1080, 80)])
