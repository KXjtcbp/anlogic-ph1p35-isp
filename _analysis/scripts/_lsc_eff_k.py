# -*- coding: utf-8 -*-
"""从同场 A/B 反推 FPGA 实际施加的等效 kR/kB，并与 lsc.v 表逐节点对比。"""
import os
import re
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
INB = os.path.join(WS, "inbox")
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")

src = open(os.path.join(HDL, "isp", "lsc.v"), "rb").read().decode("utf-8", errors="replace")
kR = np.zeros((12, 20), np.int32); kB = np.zeros((12, 20), np.int32)
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", src):
    kR[int(m.group(3)), int(m.group(4))] = int(m.group(5))
    kB[int(m.group(3)), int(m.group(4))] = int(m.group(6))


def osd_mask(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


A = np.asarray(Image.open(os.path.join(INB, "AWB舍入版.png")).convert("RGB")).astype(np.float64)
B = np.asarray(Image.open(os.path.join(INB, "LSC双线性版.png")).convert("RGB")).astype(np.float64)
h, w, _ = A.shape
m = osd_mask(h, w)
band = np.zeros_like(m); band[300:800, :] = True
sel = m & band

print("节点级：把 A(无LSC) 与 B(板上LSC) 的逐列 R/G 按 96 px 节点分箱求均值")
print("  eff_k = 1024 * ( (R/G)_B / (R/G)_A - 1 )   ← FPGA 实际施加的等效 k")
print()
print("  y行  x节点 | 表 kR  表 kB | 实测 eff_kR  eff_kB | 比值 kR  kB")
rows = {}
for iy in range(12):
    yc = iy * 64 + 32                      # 内部行中心 -> 屏幕行
    ys = yc * 1080 // 720
    y0, y1 = max(300, ys - 40), min(800, ys + 40)
    if y1 - y0 < 20:
        continue
    rr = []
    for ix in range(20):
        x0, x1 = ix * 96, (ix + 1) * 96
        if x1 > 1824: x1 = 1824
        s = sel[y0:y1, x0:x1]
        if s.sum() < 200: rr.append(None); continue
        ra = A[..., 0][y0:y1, x0:x1][s].mean() / A[..., 1][y0:y1, x0:x1][s].mean()
        ba = A[..., 2][y0:y1, x0:x1][s].mean() / A[..., 1][y0:y1, x0:x1][s].mean()
        rb = B[..., 0][y0:y1, x0:x1][s].mean() / B[..., 1][y0:y1, x0:x1][s].mean()
        bb = B[..., 2][y0:y1, x0:x1][s].mean() / B[..., 1][y0:y1, x0:x1][s].mean()
        rr.append((1024 * (rb / ra - 1), 1024 * (bb / ba - 1)))
    for ix in range(0, 20, 2):
        if rr[ix] is None: continue
        ekr, ekb = rr[ix]
        tr, tb = kR[iy, ix], kB[iy, ix]
        sr = ekr / tr if tr else float("nan")
        sb = ekb / tb if tb else float("nan")
        print("  y%02d  x%02d  | %5d  %5d | %9.1f  %9.1f | %5.2f  %5.2f" % (iy, ix, tr, tb, ekr, ekb, sr, sb))

# 全局：所有节点合并
allr = []; allb = []
for iy in range(12):
    for ix in range(20):
        if kR[iy, ix] < 20: continue
        yc = iy * 64 + 32; ys = yc * 1080 // 720
        y0, y1 = max(300, ys - 40), min(800, ys + 40)
        if y1 - y0 < 20: continue
        x0, x1 = ix * 96, (ix + 1) * 96
        if x1 > 1824: x1 = 1824
        s = sel[y0:y1, x0:x1]
        if s.sum() < 200: continue
        ra = A[..., 0][y0:y1, x0:x1][s].mean() / A[..., 1][y0:y1, x0:x1][s].mean()
        ba = A[..., 2][y0:y1, x0:x1][s].mean() / A[..., 1][y0:y1, x0:x1][s].mean()
        rb = B[..., 0][y0:y1, x0:x1][s].mean() / B[..., 1][y0:y1, x0:x1][s].mean()
        bb = B[..., 2][y0:y1, x0:x1][s].mean() / B[..., 1][y0:y1, x0:x1][s].mean()
        allr.append((kR[iy, ix], 1024 * (rb / ra - 1)))
        allb.append((kB[iy, ix], 1024 * (bb / ba - 1)))
allr = np.array(allr); allb = np.array(allb)
sr = allr[allr[:, 0] > 20][:, 1] / allr[allr[:, 0] > 20][:, 0]
sb = allb[allb[:, 0] > 20][:, 1] / allb[allb[:, 0] > 20][:, 0]
print()
print("=== 全局比值（实测等效 k / 表 k）===")
print("  R 通道  n=%d  中位数 %.3f  均值 %.3f  四分位 [%.3f, %.3f]" %
      (len(sr), np.median(sr), sr.mean(), np.percentile(sr, 25), np.percentile(sr, 75)))
print("  B 通道  n=%d  中位数 %.3f  均值 %.3f  四分位 [%.3f, %.3f]" %
      (len(sb), np.median(sb), sb.mean(), np.percentile(sb, 25), np.percentile(sb, 75)))
print()
print("  若两通道中位数都≈1.00 -> RTL 正确，之前的分歧来自别的环节")
print("  若都≈0.50 -> 增益被整体减半（移位位宽错）")
print("  若≈0.00 且离散度大 -> 表没被正确索引")

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 2, figsize=(13, 5.5))
for a, nm, c in ((allr, "R", "tab:red"), (allb, "B", "tab:blue")):
    ax[0].scatter(a[:, 0], a[:, 1], s=14, alpha=0.7, color=c, label=nm)
lim = [0, 140]
ax[0].plot(lim, lim, "k--", lw=1, label="ideal (eff = table)")
ax[0].plot(lim, [0.5 * v for v in lim], "g:", lw=1, label="half")
ax[0].plot(lim, [0 for v in lim], "r:", lw=1, label="zero")
ax[0].set_xlabel("table k"); ax[0].set_ylabel("measured effective k")
ax[0].set_title("Node-by-node: FPGA effective k vs table k")
ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3); ax[0].set_xlim(lim); ax[0].set_ylim(lim)

ax[1].hist(sr, bins=24, alpha=0.65, color="tab:red", label="R: eff/table")
ax[1].hist(sb, bins=24, alpha=0.65, color="tab:blue", label="B: eff/table")
ax[1].axvline(1.0, c="k", ls="--"); ax[1].axvline(0.5, c="g", ls=":"); ax[1].axvline(0.0, c="r", ls=":")
ax[1].set_xlabel("measured effective k / table k"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
plt.tight_layout()
out = os.path.join(WS, "_analysis", "out", "lsc_eff_k_vs_table.png")
plt.savefig(out, dpi=110)
print("saved", out)
