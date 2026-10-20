# -*- coding: utf-8 -*-
"""LSC 验收对照图（含 S 曲线这一层）。"""
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
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")


def osd_mask(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


src = open(os.path.join(HDL, "isp", "lsc.v"), "rb").read().decode("utf-8", errors="replace")
kR = np.zeros((12, 20), np.int32); kB = np.zeros((12, 20), np.int32)
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", src):
    kR[int(m.group(3)), int(m.group(4))] = int(m.group(5))
    kB[int(m.group(3)), int(m.group(4))] = int(m.group(6))

gsrc = open(os.path.join(HDL, "isp", "isp_gamma.v"), "rb").read().decode("utf-8", errors="replace")
gt = {int(m.group(1)): int(m.group(2), 16) for m in re.finditer(r"mem_b00\[\s*(\d+)\s*\]\s*=\s*8'h([0-9a-fA-F]{1,2})", gsrc)}
GAMMA = np.array([gt[i] for i in range(256)], np.int32)


def apply_lsc(a):
    h, w, _ = a.shape
    yy = np.clip((np.arange(h) * 720 // 1080) // 64, 0, 11)
    xx = np.clip(np.arange(w) // 96, 0, 19)
    tR = kR[yy][:, xx]; tB = kB[yy][:, xx]
    b = a.astype(np.int32).copy()
    b[..., 0] = np.minimum(255, a[..., 0] + ((a[..., 0].astype(np.int32) * tR) >> 10))
    b[..., 2] = np.minimum(255, a[..., 2] + ((a[..., 2].astype(np.int32) * tB) >> 10))
    return b.astype(np.float64)


def profile(a, y0=300, y1=800, x0=96, x1=1824):
    h, w, _ = a.shape
    m = osd_mask(h, w)
    band = np.zeros_like(m); band[y0:y1, :] = True
    sel = m & band
    out = []
    for x in range(x0, x1):
        s = sel[:, x]
        g = a[:, x, 1][s].mean() if s.sum() >= 50 else 0.0
        out.append(a[:, x, 0][s].mean() / g if g > 1e-6 else np.nan)
    return np.array(out)


def smooth(v, win=21):
    k = np.ones(win) / win
    return np.convolve(np.pad(v, (win // 2, win // 2), mode="edge"), k, mode="valid")


n1 = np.asarray(Image.open(os.path.join(WS, "captures/2026-10-13_白纸靶面_无LSC对照/N1_232908.png")).convert("RGB")).astype(np.float64)
live = np.asarray(Image.open(os.path.join(WS, "inbox/Screenshot 2026-10-14 12-40-45.png")).convert("RGB")).astype(np.float64)
n1l = apply_lsc(n1)
n1lg = n1l.copy()
for c in range(3):
    n1lg[..., c] = GAMMA[np.clip(n1l[..., c].astype(np.int32), 0, 255)]

cases = [("no-LSC\n(reference N1)", profile(n1)),
         ("+ software LSC\n(table from lsc.v)", profile(n1l)),
         ("+ software LSC\n+ real S-curve", profile(n1lg)),
         ("live 12:40\n(FPGA LSC on)", profile(live))]

x = np.arange(96, 1824)
fig, ax = plt.subplots(1, 2, figsize=(15, 5))
for (lbl, p), c in zip(cases, ["0.45", "tab:orange", "tab:red", "tab:green"]):
    ax[0].plot(x, smooth(p), lw=2.0, color=c, label=lbl.replace("\n", " "))
    ax[0].plot(x, p, lw=0.4, color=c, alpha=0.35)
ax[0].axhline(1.0, ls="--", c="k", lw=0.8)
ax[0].set_title("Column R/G profile (y=300..800), thick = smoothed")
ax[0].set_xlabel("screen x"); ax[0].set_ylabel("R/G")
ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)

raw = [np.nanmax(p) - np.nanmin(p) for _, p in cases]
smo = [np.nanmax(smooth(p)) - np.nanmin(smooth(p)) for _, p in cases]
xx = np.arange(4)
ax[1].bar(xx - 0.2, raw, 0.38, label="raw")
ax[1].bar(xx + 0.2, smo, 0.38, label="smoothed")
for i in range(4):
    ax[1].text(i - 0.2, raw[i] + 0.002, "%.4f" % raw[i], ha="center", fontsize=8)
    ax[1].text(i + 0.2, smo[i] + 0.002, "%.4f" % smo[i], ha="center", fontsize=8)
ax[1].axhline(0.02, ls="--", c="r", lw=1.2)
ax[1].text(3.3, 0.021, "0.02", color="r", fontsize=9)
ax[1].set_xticks(xx); ax[1].set_xticklabels([c[0] for c in cases], fontsize=7.5)
ax[1].set_ylabel("column R/G peak-to-peak"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3, axis="y")
plt.tight_layout()
out = os.path.join(WS, "_analysis", "out", "lsc_accept2.png")
plt.savefig(out, dpi=110)
print("saved", out)
for (lbl, _), r, s in zip(cases, raw, smo):
    print("  %-34s raw=%.4f smooth=%.4f" % (lbl.replace("\n", " "), r, s))
