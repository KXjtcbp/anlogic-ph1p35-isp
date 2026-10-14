# -*- coding: utf-8 -*-
"""判定：现场抓图里剩下的逐列 R/G 碗，是 LSC 没做好，还是"亮度暗角 × 非线性 S 曲线"造成的？

做法：拿无 LSC 对照图 N1，按顺序做
   (0) 原样
   (1) 软件施加 lsc.v 里的真表
   (2) 在 (1) 之上再施加 isp_gamma.v 里的真表（模拟 SW2 曲线 ON）
再和现场抓图 12:40 的逐列 R/G 极差对比。
"""
import os
import re
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")


def osd_mask(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


# ---- LSC 表 ----
src = open(os.path.join(HDL, "isp", "lsc.v"), "rb").read().decode("utf-8", errors="replace")
kR = np.zeros((12, 20), np.int32); kB = np.zeros((12, 20), np.int32)
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", src):
    kR[int(m.group(3)), int(m.group(4))] = int(m.group(5))
    kB[int(m.group(3)), int(m.group(4))] = int(m.group(6))

# ---- isp_gamma 表 ----
gsrc = open(os.path.join(HDL, "isp", "isp_gamma.v"), "rb").read().decode("utf-8", errors="replace")
gt = {}
for m in re.finditer(r"mem_b00\[\s*(\d+)\s*\]\s*=\s*8'h([0-9a-fA-F]{1,2})", gsrc):
    gt[int(m.group(1))] = int(m.group(2), 16)
GAMMA = np.array([gt[i] for i in range(256)], np.int32)
print("isp_gamma 表项 %d 个，LUT[0]=%d LUT[64]=%d LUT[128]=%d LUT[255]=%d"
      % (len(gt), GAMMA[0], GAMMA[64], GAMMA[128], GAMMA[255]))


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
        if s.sum() < 50:
            out.append(np.nan); continue
        g = a[:, x, 1][s].mean()
        out.append(a[:, x, 0][s].mean() / g if g > 1e-6 else np.nan)
    return np.array(out)


def smooth(v, win=21):
    k = np.ones(win) / win
    return np.convolve(np.pad(v, (win // 2, win // 2), mode="edge"), k, mode="valid")


def rng(v):
    return np.nanmax(v) - np.nanmin(v)


def yprofile(a, y0=300, y1=800, x0=96, x1=1824):
    h, w, _ = a.shape
    m = osd_mask(h, w)
    band = np.zeros_like(m); band[y0:y1, :] = True
    sel = m & band
    out = []
    for x in range(x0, x1):
        s = sel[:, x]
        out.append(a[:, x, 1][s].mean() if s.sum() >= 50 else np.nan)
    return np.array(out)


n1 = np.asarray(Image.open(os.path.join(WS, "captures/2026-10-13_白纸靶面_无LSC对照/N1_232908.png")).convert("RGB")).astype(np.float64)
live = np.asarray(Image.open(os.path.join(WS, "inbox/Screenshot 2026-10-14 12-40-45.png")).convert("RGB")).astype(np.float64)

n1_lsc = apply_lsc(n1)
n1_lsc_g = n1_lsc.copy()
for c in range(3):
    n1_lsc_g[..., c] = GAMMA[np.clip(n1_lsc[..., c].astype(np.int32), 0, 255)]

print()
print("=== 逐列 R/G 极差（原始 / 平滑）与 逐列 G 亮度极差 ===")
for tag, img in (("N1 无LSC", n1), ("N1 +软件LSC", n1_lsc), ("N1 +软件LSC +S曲线", n1_lsc_g), ("现场 12:40", live)):
    p = profile(img); s = smooth(p)
    gy = yprofile(img)
    print("  %-20s 逐列R/G 原始=%.4f 平滑=%.4f | G均值范围 %.2f..%.2f (%.1f%%)"
          % (tag, rng(p), rng(s), np.nanmin(gy), np.nanmax(gy),
             100 * (np.nanmax(gy) / np.nanmin(gy) - 1)))
