# -*- coding: utf-8 -*-
"""决定性对照：把 lsc.v 的真表在软件里施加到「无 LSC 那张（A）」上，
   再和 FPGA 实际产生的「LSC 那张（B）」逐列对比。
   A/B 同场景、同光照、间隔 37 s ⇒ 这是对 RTL 与模型一致性的干净检验。"""
import os
import re
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
INB = os.path.join(WS, "inbox")
PA = os.path.join(INB, "AWB舍入版.png")        # 无 LSC
PB = os.path.join(INB, "LSC双线性版.png")      # FPGA 的 LSC
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


def apply_lsc(a):
    h, w, _ = a.shape
    yy = np.clip((np.arange(h) * 720 // 1080) // 64, 0, 11)
    xx = np.clip(np.arange(w) // 96, 0, 19)
    tR = kR[yy][:, xx]; tB = kB[yy][:, xx]
    b = a.astype(np.int32).copy()
    b[..., 0] = np.minimum(255, a[..., 0] + ((a[..., 0].astype(np.int32) * tR) >> 10))
    b[..., 2] = np.minimum(255, a[..., 2] + ((a[..., 2].astype(np.int32) * tB) >> 10))
    return b.astype(np.float64)


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


A = np.asarray(Image.open(PA).convert("RGB")).astype(np.float64)
B = np.asarray(Image.open(PB).convert("RGB")).astype(np.float64)
Asw = apply_lsc(A)

print("=== 三个剖面的逐列 R/G 平滑极差 ===")
res = {}
for tag, img in (("A 无LSC（板上）", A), ("A + 软件施加真表", Asw), ("B 板上 LSC", B)):
    p = colprof(img, 0); s = smooth(p)
    res[tag] = (p, s)
    print("   %-18s 原始=%.4f  平滑=%.4f" % (tag, np.nanmax(p) - np.nanmin(p), np.nanmax(s) - np.nanmin(s)))

print("\n=== 三个剖面的逐列 B/G 平滑极差 ===")
resb = {}
for tag, img in (("A 无LSC（板上）", A), ("A + 软件施加真表", Asw), ("B 板上 LSC", B)):
    p = colprof(img, 2); s = smooth(p)
    resb[tag] = (p, s)
    print("   %-18s 原始=%.4f  平滑=%.4f" % (tag, np.nanmax(p) - np.nanmin(p), np.nanmax(s) - np.nanmin(s)))

# 软件模型 vs 板上：两条剖面之差
sA = res["A + 软件施加真表"][1]
sB = res["B 板上 LSC"][1]
dev = np.abs(sA - sB)
print("\n=== 模型 vs 板上（逐列平滑 R/G）===")
print("  两曲线之差：max=%.4f  mean=%.4f  相关=%.4f" % (dev.max(), dev.mean(), np.corrcoef(sA, sB)[0, 1]))
print("  段均值对比（每 8 个节点一组，共 2 组 x 20 节点）:")
for n in range(0, 20, 4):
    lo = n * 96 - 96; hi = (n + 4) * 96 - 96
    print("     x=%4d..%4d  模型 %.4f   板上 %.4f   差 %+.4f" %
          (max(96, n * 96), min(1824, (n + 4) * 96) - 1,
           np.nanmean(sA[lo:hi]), np.nanmean(sB[lo:hi]), np.nanmean(sB[lo:hi]) - np.nanmean(sA[lo:hi])))

# 画图
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
x = np.arange(96, 1824)
fig, ax = plt.subplots(1, 3, figsize=(18, 5))
for tag, c in (("A 无LSC（板上）", "0.45"), ("A + 软件施加真表", "tab:orange"), ("B 板上 LSC", "tab:red")):
    ax[0].plot(x, res[tag][0], lw=0.4, color=c, alpha=0.3)
    ax[0].plot(x, res[tag][1], lw=2.2, color=c, label=tag)
ax[0].axhline(1.0, ls="--", c="k", lw=0.8)
ax[0].set_title("Column R/G  (A/B same scene, 37 s apart)")
ax[0].set_xlabel("x"); ax[0].set_ylabel("R/G"); ax[0].legend(fontsize=8); ax[0].grid(alpha=0.3)

for tag, c in (("A 无LSC（板上）", "0.45"), ("A + 软件施加真表", "tab:orange"), ("B 板上 LSC", "tab:red")):
    ax[1].plot(x, resb[tag][1], lw=2.2, color=c, label=tag)
ax[1].axhline(1.0, ls="--", c="k", lw=0.8)
ax[1].set_title("Column B/G"); ax[1].set_xlabel("x"); ax[1].legend(fontsize=8); ax[1].grid(alpha=0.3)

labels = ["col R/G", "col B/G"]
vA = [np.nanmax(res["A 无LSC（板上）"][1]) - np.nanmin(res["A 无LSC（板上）"][1]),
      np.nanmax(resb["A 无LSC（板上）"][1]) - np.nanmin(resb["A 无LSC（板上）"][1])]
vM = [np.nanmax(res["A + 软件施加真表"][1]) - np.nanmin(res["A + 软件施加真表"][1]),
      np.nanmax(resb["A + 软件施加真表"][1]) - np.nanmin(resb["A + 软件施加真表"][1])]
vB = [np.nanmax(res["B 板上 LSC"][1]) - np.nanmin(res["B 板上 LSC"][1]),
      np.nanmax(resb["B 板上 LSC"][1]) - np.nanmin(resb["B 板上 LSC"][1])]
xx = np.arange(2)
ax[2].bar(xx - 0.26, vA, 0.25, label="no LSC", color="0.55")
ax[2].bar(xx, vM, 0.25, label="software table", color="tab:orange")
ax[2].bar(xx + 0.26, vB, 0.25, label="FPGA LSC", color="tab:red")
for i in range(2):
    for off, v in ((-0.26, vA[i]), (0, vM[i]), (0.26, vB[i])):
        ax[2].text(i + off, v + 0.002, "%.4f" % v, ha="center", fontsize=8)
ax[2].axhline(0.02, ls="--", c="r", lw=1.2)
ax[2].set_xticks(xx); ax[2].set_xticklabels(labels)
ax[2].set_title("smoothed column peak-to-peak"); ax[2].legend(fontsize=8); ax[2].grid(alpha=0.3, axis="y")
plt.tight_layout()
out = os.path.join(WS, "_analysis", "out", "lsc_model_vs_fpga.png")
plt.savefig(out, dpi=110)
print("\nsaved", out)
