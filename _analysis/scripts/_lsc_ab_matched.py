# -*- coding: utf-8 -*-
"""同场 A/B：AWB舍入版（无 LSC） vs LSC双线性版（LSC 开），间隔 37 秒。"""
import os
import re
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
INB = os.path.join(WS, "inbox")
A = os.path.join(INB, "AWB舍入版.png")        # 无 LSC
B = os.path.join(INB, "LSC双线性版.png")      # LSC 开


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


def colprof(a, y0=300, y1=800, x0=96, x1=1824, ch=(0, 1)):
    h, w, _ = a.shape
    m = osd_mask(h, w)
    band = np.zeros_like(m); band[y0:y1, :] = True
    sel = m & band
    out = []
    for x in range(x0, x1):
        s = sel[:, x]
        if s.sum() < 50:
            out.append(np.nan); continue
        g = a[:, x, 1][s].mean()
        out.append(a[:, x, ch[0]][s].mean() / g if g > 1e-6 else np.nan)
    return np.array(out)


def rowprof(a, y0=8, y1=1072, x0=150, x1=1750, ch=(0, 1)):
    h, w, _ = a.shape
    m = osd_mask(h, w)
    m[:, :x0] = False; m[:, x1:] = False
    out = []
    for y in range(y0, y1):
        s = m[y, :]
        if s.sum() < 50:
            out.append(np.nan); continue
        g = a[y, :, 1][s].mean()
        out.append(a[y, :, ch[0]][s].mean() / g if g > 1e-6 else np.nan)
    return np.array(out)


def summary(tag, p):
    a = load(p)
    h, w, _ = a.shape
    m = osd_mask(h, w)
    R, G, Bc = a[..., 0][m], a[..., 1][m], a[..., 2][m]
    Y = (77 * a[..., 0] + 150 * a[..., 1] + 29 * a[..., 2]) / 256.0
    y = Y[m]
    print("=== %s ===" % tag)
    print("  Ymean=%.3f Ystd=%.3f p1=%d p50=%d p99=%d max=%d" %
          (y.mean(), y.std(), np.percentile(y, 1), np.percentile(y, 50), np.percentile(y, 99), y.max()))
    print("  R=%.2f G=%.2f B=%.2f | R/G=%.4f B/G=%.4f | R-G=%+.2f B-G=%+.2f" %
          (R.mean(), G.mean(), Bc.mean(), R.mean() / G.mean(), Bc.mean() / G.mean(),
           R.mean() - G.mean(), Bc.mean() - G.mean()))
    pr = colprof(a); pb = colprof(a, ch=(2, 1))
    rr = rowprof(a); rb = rowprof(a, ch=(2, 1))
    print("  逐列 R/G 原始极差=%.4f 平滑=%.4f | 逐列 B/G 原始=%.4f 平滑=%.4f" %
          (np.nanmax(pr) - np.nanmin(pr), np.nanmax(smooth(pr)) - np.nanmin(smooth(pr)),
           np.nanmax(pb) - np.nanmin(pb), np.nanmax(smooth(pb)) - np.nanmin(smooth(pb))))
    print("  逐行 R/G 原始极差=%.4f 平滑=%.4f | 逐行 B/G 原始=%.4f 平滑=%.4f" %
          (np.nanmax(rr) - np.nanmin(rr), np.nanmax(smooth(rr)) - np.nanmin(smooth(rr)),
           np.nanmax(rb) - np.nanmin(rb), np.nanmax(smooth(rb)) - np.nanmin(smooth(rb))))
    # G 亮度暗角
    gy = np.array([a[:, x, 1][m[:, x]].mean() for x in range(96, 1824)])
    print("  G 逐列亮度 %.2f..%.2f  (%.1f%%)" % (gy.min(), gy.max(), 100 * (gy.max() / gy.min() - 1)))
    return a, pr, pb, rr, rb


aA, prA, pbA, rrA, rbA = summary("A  AWB舍入版（无 LSC）", A)
print()
aB, prB, pbB, rrB, rbB = summary("B  LSC双线性版（LSC 开）", B)

print()
print("=== 同场 A/B 结论 ===")
for nm, pA, pB in (("逐列 R/G", prA, prB), ("逐列 B/G", pbA, pbB)):
    rA = np.nanmax(smooth(pA)) - np.nanmin(smooth(pA))
    rB = np.nanmax(smooth(pB)) - np.nanmin(smooth(pB))
    print("  %s 平滑极差：无LSC %.4f → LSC %.4f  降幅 %.1f%%" % (nm, rA, rB, 100 * (1 - rB / rA)))
for nm, pA, pB in (("逐行 R/G", rrA, rrB), ("逐行 B/G", rbA, rbB)):
    rA = np.nanmax(smooth(pA)) - np.nanmin(smooth(pA))
    rB = np.nanmax(smooth(pB)) - np.nanmin(smooth(pB))
    print("  %s 平滑极差：无LSC %.4f → LSC %.4f  降幅 %.1f%%" % (nm, rA, rB, 100 * (1 - rB / rA)))

# 画图
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
x = np.arange(96, 1824)
fig, ax = plt.subplots(1, 3, figsize=(18, 5))
ax[0].plot(x, prA, lw=0.4, color="tab:blue", alpha=0.35)
ax[0].plot(x, smooth(prA), lw=2.2, color="tab:blue", label="no-LSC  (raw 0.1215-ish)")
ax[0].plot(x, prB, lw=0.4, color="tab:red", alpha=0.35)
ax[0].plot(x, smooth(prB), lw=2.2, color="tab:red", label="LSC bilinear")
ax[0].axhline(1.0, ls="--", c="k", lw=0.8)
ax[0].set_title("Column R/G profile"); ax[0].set_xlabel("x"); ax[0].set_ylabel("R/G")
ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)

ax[1].plot(x, pbA, lw=0.4, color="tab:blue", alpha=0.35)
ax[1].plot(x, smooth(pbA), lw=2.2, color="tab:blue", label="no-LSC")
ax[1].plot(x, pbB, lw=0.4, color="tab:red", alpha=0.35)
ax[1].plot(x, smooth(pbB), lw=2.2, color="tab:red", label="LSC bilinear")
ax[1].axhline(1.0, ls="--", c="k", lw=0.8)
ax[1].set_title("Column B/G profile"); ax[1].set_xlabel("x")
ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)

labels = ["col R/G", "col B/G", "row R/G", "row B/G"]
vA = [np.nanmax(smooth(p)) - np.nanmin(smooth(p)) for p in (prA, pbA, rrA, rbA)]
vB = [np.nanmax(smooth(p)) - np.nanmin(smooth(p)) for p in (prB, pbB, rrB, rbB)]
xx = np.arange(4)
ax[2].bar(xx - 0.2, vA, 0.38, label="no-LSC (AWB rounding ver.)", color="tab:blue")
ax[2].bar(xx + 0.2, vB, 0.38, label="LSC bilinear", color="tab:red")
for i in range(4):
    ax[2].text(i - 0.2, vA[i] + 0.001, "%.4f" % vA[i], ha="center", fontsize=8)
    ax[2].text(i + 0.2, vB[i] + 0.001, "%.4f" % vB[i], ha="center", fontsize=8)
    ax[2].text(i, max(vA[i], vB[i]) + 0.006, "-%.0f%%" % (100 * (1 - vB[i] / vA[i])), ha="center", fontsize=9, color="green")
ax[2].axhline(0.02, ls="--", c="r", lw=1.2)
ax[2].set_xticks(xx); ax[2].set_xticklabels(labels)
ax[2].set_title("smoothed peak-to-peak"); ax[2].legend(fontsize=8); ax[2].grid(alpha=0.3, axis="y")
plt.tight_layout()
out = os.path.join(WS, "_analysis", "out", "lsc_ab_matched.png")
plt.savefig(out, dpi=110)
print("\nsaved", out)

# 遥测与 CNT 裁剪
for tag, p in (("A", A), ("B", B)):
    im = Image.open(p).convert("RGB")
    im.crop((540, 215, 1030, 265)).resize((1960, 200), Image.LANCZOS).save(
        os.path.join(WS, "_analysis", "out", "ab_tele_%s.png" % tag))
    im.crop((540, 155, 920, 215)).resize((1520, 240), Image.NEAREST).save(
        os.path.join(WS, "_analysis", "out", "ab_cnt_%s.png" % tag))
print("saved ab_tele_A/B.png, ab_cnt_A/B.png")
