# -*- coding: utf-8 -*-
"""同一次上电、只拨 SW1 的 LSC 关/开对照（两组）。
   反推 FPGA 实际施加的等效 k，并与 lsc.v 表逐节点对比。"""
import os
import re
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
INB = os.path.join(WS, "inbox")
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")

PAIRS = [(os.path.join(INB, "SW1下1.png"), os.path.join(INB, "SW1上1 (2).png"), "组1"),
         (os.path.join(INB, "SW1下2.png"), os.path.join(INB, "SW1上2.png"), "组2")]

src = open(os.path.join(HDL, "isp", "lsc.v"), "rb").read().decode("utf-8", errors="replace")
kR = np.zeros((12, 20), np.int32); kB = np.zeros((12, 20), np.int32)
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", src):
    kR[int(m.group(3)), int(m.group(4))] = int(m.group(5))
    kB[int(m.group(3)), int(m.group(4))] = int(m.group(6))
print("表已解析：kR max=%d  kB max=%d" % (kR.max(), kB.max()))


def osd_mask(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.float64)


def smooth(v, win=21):
    k = np.ones(win) / win
    return np.convolve(np.pad(v, (win // 2, win // 2), mode="edge"), k, mode="valid")


def colprof(a, ch, y0=300, y1=800, x0=96, x1=1824):
    h, w, _ = a.shape
    m = osd_mask(h, w)
    band = np.zeros_like(m); band[y0:y1, :] = True
    sel = m & band
    out = []
    for x in range(x0, x1):
        s = sel[:, x]
        g = a[:, x, 1][s].mean() if s.sum() >= 50 else 0.0
        out.append(a[:, x, ch][s].mean() / g if g > 1e-6 else np.nan)
    return np.array(out)


def frame_stats(a, tag):
    h, w, _ = a.shape
    m = osd_mask(h, w)
    R, G, Bc = a[..., 0][m], a[..., 1][m], a[..., 2][m]
    print("  %-16s R/G=%.4f B/G=%.4f  R-G=%+.2f B-G=%+.2f" %
          (tag, R.mean() / G.mean(), Bc.mean() / G.mean(), R.mean() - G.mean(), Bc.mean() - G.mean()))
    return R.mean() / G.mean(), Bc.mean() / G.mean()


allr = []; allb = []
for off_p, on_p, nm in PAIRS:
    A = load(off_p); B = load(on_p)
    print("\n=== %s   LSC关=%s   LSC开=%s ===" % (nm, os.path.basename(off_p), os.path.basename(on_p)))
    frame_stats(A, "LSC 关")
    frame_stats(B, "LSC 开")
    prA, prB = colprof(A, 0), colprof(B, 0)
    pbA, pbB = colprof(A, 2), colprof(B, 2)
    print("  逐列 R/G 平滑极差: 关 %.4f -> 开 %.4f  (降 %.1f%%)" %
          (np.nanmax(smooth(prA)) - np.nanmin(smooth(prA)),
           np.nanmax(smooth(prB)) - np.nanmin(smooth(prB)),
           100 * (1 - (np.nanmax(smooth(prB)) - np.nanmin(smooth(prB))) /
                  (np.nanmax(smooth(prA)) - np.nanmin(smooth(prA))))))
    print("  逐列 B/G 平滑极差: 关 %.4f -> 开 %.4f" %
          (np.nanmax(smooth(pbA)) - np.nanmin(smooth(pbA)),
           np.nanmax(smooth(pbB)) - np.nanmin(smooth(pbB))))

    # 节点级反推
    h, w, _ = A.shape
    m = osd_mask(h, w)
    band = np.zeros_like(m); band[300:800, :] = True
    sel = m & band
    rA = A[..., 0].mean() / A[..., 1].mean()   # 整帧比例，用于去掉 AWB 全局增益差
    rowlist = []
    for iy in range(12):
        ys = (iy * 64 + 32) * 1080 // 720
        y0, y1 = max(300, ys - 40), min(800, ys + 40)
        if y1 - y0 < 20: continue
        for ix in range(20):
            x0, x1 = ix * 96, min((ix + 1) * 96, 1824)
            s = sel[y0:y1, x0:x1]
            if s.sum() < 200: continue
            ra = A[..., 0][y0:y1, x0:x1][s].mean() / A[..., 1][y0:y1, x0:x1][s].mean()
            ba = A[..., 2][y0:y1, x0:x1][s].mean() / A[..., 1][y0:y1, x0:x1][s].mean()
            rb = B[..., 0][y0:y1, x0:x1][s].mean() / B[..., 1][y0:y1, x0:x1][s].mean()
            bb = B[..., 2][y0:y1, x0:x1][s].mean() / B[..., 1][y0:y1, x0:x1][s].mean()
            if kR[iy, ix] >= 20:
                allr.append((kR[iy, ix], 1024 * (rb / ra - 1)))
                rowlist.append(("R", iy, ix, kR[iy, ix], 1024 * (rb / ra - 1)))
            if kB[iy, ix] >= 20:
                allb.append((kB[iy, ix], 1024 * (bb / ba - 1)))
    print("  -- 部分节点（表 k -> 实测等效 k）--")
    for t in rowlist[:10]:
        print("     %s y%02d x%02d  表 %3d -> 实测 %+7.1f  (比 %.2f)" %
              (t[0], t[1], t[2], t[3], t[4], t[4] / t[3]))

allr = np.array(allr); allb = np.array(allb)
for nmv, arr in (("R", allr), ("B", allb)):
    q = arr[arr[:, 0] > 0][:, 1] / arr[arr[:, 0] > 0][:, 0]
    print("\n=== 全局：%s 通道 实测等效 k / 表 k ===" % nmv)
    print("   n=%d  中位数 %.3f  均值 %.3f  四分位 [%.3f, %.3f]" %
          (len(q), np.median(q), q.mean(), np.percentile(q, 25), np.percentile(q, 75)))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
fig, ax = plt.subplots(1, 2, figsize=(13, 5.5))
for a, nmv, c in ((allr, "R", "tab:red"), (allb, "B", "tab:blue")):
    ax[0].scatter(a[:, 0], a[:, 1], s=16, alpha=0.7, color=c, label=nmv)
ax[0].plot([0, 140], [0, 140], "k--", lw=1, label="ideal")
ax[0].plot([0, 140], [0, 70], "g:", lw=1, label="half")
ax[0].set_xlabel("table k"); ax[0].set_ylabel("measured effective k")
ax[0].set_title("LSC ON/OFF within one power-up: effective k")
ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3); ax[0].set_xlim(0, 140); ax[0].set_ylim(-40, 145)
q1 = allr[allr[:, 0] > 20][:, 1] / allr[allr[:, 0] > 20][:, 0]
q2 = allb[allb[:, 0] > 20][:, 1] / allb[allb[:, 0] > 20][:, 0]
ax[1].hist(q1, bins=22, alpha=0.65, color="tab:red", label="R eff/table")
ax[1].hist(q2, bins=22, alpha=0.65, color="tab:blue", label="B eff/table")
ax[1].axvline(1.0, c="k", ls="--"); ax[1].axvline(0.5, c="g", ls=":"); ax[1].axvline(0.0, c="r", ls=":")
ax[1].set_xlabel("effective k / table k"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)
plt.tight_layout()
out = os.path.join(WS, "_analysis", "out", "lsc_eff_k_sw1.png")
plt.savefig(out, dpi=110)
print("saved", out)

for off_p, on_p, nm in PAIRS:
    for tag, p in (("off", off_p), ("on", on_p)):
        im = Image.open(p).convert("RGB")
        im.crop((540, 215, 1030, 265)).resize((1960, 200), Image.LANCZOS).save(
            os.path.join(WS, "_analysis", "out", "sw1_%s_%s_tele.png" % (nm[-1], tag)))
        im.crop((540, 155, 920, 215)).resize((1520, 240), Image.NEAREST).save(
            os.path.join(WS, "_analysis", "out", "sw1_%s_%s_cnt.png" % (nm[-1], tag)))
print("saved tele/cnt crops")
