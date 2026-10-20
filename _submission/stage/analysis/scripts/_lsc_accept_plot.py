# -*- coding: utf-8 -*-
"""画 LSC 验收对照图：无LSC原始 / 无LSC+软件模拟校正 / 现场抓图（已过FPGA的LSC）。"""
import os
import re
import sys
import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"


def osd_mask(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


def profile(a, y0, y1, x0=96, x1=1824):
    h, w, _ = a.shape
    m = osd_mask(h, w)
    band = np.zeros_like(m)
    band[y0:y1, :] = True
    sel = m & band
    out = []
    for x in range(x0, x1):
        s = sel[:, x]
        if s.sum() < 50:
            out.append(np.nan); continue
        g = a[:, x, 1][s].mean()
        out.append(a[:, x, 0][s].mean() / g if g > 1e-6 else np.nan)
    return np.array(out)


def load(rel):
    return np.asarray(Image.open(os.path.join(WS, rel)).convert("RGB")).astype(np.float64)


# 解析表
src = open(os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "isp", "lsc.v"),
           "rb").read().decode("utf-8", errors="replace")
kR = np.zeros((12, 20), np.int32); kB = np.zeros((12, 20), np.int32)
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", src):
    kR[int(m.group(3)), int(m.group(4))] = int(m.group(5))
    kB[int(m.group(3)), int(m.group(4))] = int(m.group(6))


def apply_lsc(a):
    h, w, _ = a.shape
    yy = np.clip((np.arange(h) * 720 // 1080) // 64, 0, 11)
    xx = np.clip(np.arange(w) // 96, 0, 19)
    tR = kR[yy][:, xx]; tB = kB[yy][:, xx]
    b = a.astype(np.int32).copy()
    b[..., 0] = np.minimum(255, a[..., 0] + ((a[..., 0].astype(np.int32) * tR) >> 10))
    b[..., 2] = np.minimum(255, a[..., 2] + ((a[..., 2].astype(np.int32) * tB) >> 10))
    return b.astype(np.uint8).astype(np.float64)


n1 = load("captures/2026-10-13_白纸靶面_无LSC对照/N1_232908.png")
live = load("inbox/Screenshot 2026-10-14 12-40-45.png")
n1c = apply_lsc(n1)

p_raw = profile(n1, 300, 800)
p_sim = profile(n1c, 300, 800)
p_live = profile(live, 300, 800)


def smooth(v, win=21):
    k = np.ones(win) / win
    return np.convolve(np.pad(v, (win // 2, win // 2), mode="edge"), k, mode="valid")


x = np.arange(96, 1824)
fig, ax = plt.subplots(1, 2, figsize=(15, 5))
ax[0].set_title("Column R/G profile  (y=300..800, raw)")
ax[0].plot(x, p_raw, lw=0.6, color="0.7", label="no-LSC  N1 raw")
ax[0].plot(x, p_sim, lw=0.6, color="0.85", label="no-LSC  N1 + software LSC")
ax[0].plot(x, p_live, lw=0.6, color="0.9", label="live 12:40 (FPGA LSC)")
ax[0].plot(x, smooth(p_raw), lw=2.0, color="tab:blue", label="no-LSC  smoothed")
ax[0].plot(x, smooth(p_sim), lw=2.0, color="tab:orange", label="+SW LSC smoothed")
ax[0].plot(x, smooth(p_live), lw=2.0, color="tab:green", label="live smoothed")
ax[0].axhline(1.0, ls="--", c="k", lw=0.8)
ax[0].set_xlabel("screen x (1920 space)"); ax[0].set_ylabel("R/G")
ax[0].legend(fontsize=7); ax[0].grid(alpha=0.3)

labels = ["no-LSC\nN1", "N1 +\nsoftware LSC", "live 12:40\nFPGA LSC"]
raw = [np.nanmax(p_raw) - np.nanmin(p_raw), np.nanmax(p_sim) - np.nanmin(p_sim), np.nanmax(p_live) - np.nanmin(p_live)]
smo = [np.nanmax(smooth(p_raw)) - np.nanmin(smooth(p_raw)),
       np.nanmax(smooth(p_sim)) - np.nanmin(smooth(p_sim)),
       np.nanmax(smooth(p_live)) - np.nanmin(smooth(p_live))]
xx = np.arange(3)
ax[1].bar(xx - 0.2, raw, 0.38, label="raw column range")
ax[1].bar(xx + 0.2, smo, 0.38, label="smoothed column range")
for i, (r, s) in enumerate(zip(raw, smo)):
    ax[1].text(i - 0.2, r + 0.001, "%.4f" % r, ha="center", fontsize=8)
    ax[1].text(i + 0.2, s + 0.001, "%.4f" % s, ha="center", fontsize=8)
ax[1].axhline(0.02, ls="--", c="r", lw=1.2)
ax[1].text(2.35, 0.0205, "0.02 criterion", color="r", fontsize=8)
ax[1].set_xticks(xx); ax[1].set_xticklabels(labels, fontsize=8)
ax[1].set_ylabel("column R/G peak-to-peak"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3, axis="y")
plt.tight_layout()
out = os.path.join(WS, "_analysis", "out", "lsc_accept.png")
plt.savefig(out, dpi=110)
print("saved", out)
print("raw  : no-LSC %.4f | +SW LSC %.4f | live %.4f" % tuple(raw))
print("smooth: no-LSC %.4f | +SW LSC %.4f | live %.4f" % tuple(smo))
print("reduction raw : %.1f%% / %.1f%%" % (100 * (1 - raw[1] / raw[0]), 100 * (1 - raw[2] / raw[0])))
print("reduction smooth: %.1f%% / %.1f%%" % (100 * (1 - smo[1] / smo[0]), 100 * (1 - smo[2] / smo[0])))
