# -*- coding: utf-8 -*-
"""把 RTL 同一套算式（4 角查表 + 双线性 + F_apply）施加到本批 LSC 关的那张上，
   预测 LSC 开的剖面，与实测对照。"""
import os, re, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"; INB = os.path.join(WS, "inbox")
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")

kR = np.zeros((12, 20), np.int32); kB = np.zeros((12, 20), np.int32)
src = open(os.path.join(HDL, "isp", "lsc.v"), "rb").read().decode("utf-8", errors="replace")
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", src):
    kR[int(m.group(3)), int(m.group(4))] = int(m.group(5))
    kB[int(m.group(3)), int(m.group(4))] = int(m.group(6))


def lerp(k0, k1, f):
    d = np.int32(k1) - np.int32(k0)
    acc = np.zeros_like(d) if isinstance(d, np.ndarray) else np.int32(0)
    r = np.int32(k0) + ((d * np.int32(f)) >> 4)
    return np.clip(r, 0, 1023)


def apply_lsc(a):
    h, w, _ = a.shape
    out = a.copy()
    bx = (np.arange(w) // 4).astype(np.int32)          # beat 计数（1280 内部坐标）
    y2 = (np.arange(h) * 720 // 1080).astype(np.int32)  # 屏幕 -> 内部行
    hidx = np.clip(bx // 16, 0, 19); fx = bx % 16
    vidx = np.clip(y2 // 64, 0, 11); fy = (y2 % 64) // 4
    h1 = np.minimum(hidx + 1, 19); v1 = np.minimum(vidx + 1, 11)
    for ch, tab in ((0, kR), (2, kB)):
        n00 = tab[vidx][:, None][:, 0:1] * 0  # placeholder
        # 逐像素（向量化）
        a00 = tab[vidx[:, None], hidx[None, :]]
        a10 = tab[vidx[:, None], h1[None, :]]
        a01 = tab[v1[:, None], hidx[None, :]]
        a11 = tab[v1[:, None], h1[None, :]]
        FY = fy[:, None]; FX = fx[None, :]
        rv0 = np.where(a10 >= a00, a00 + (((a10 - a00) * FY) >> 4), a00 - (((a00 - a10) * FY) >> 4))
        rv1 = np.where(a11 >= a01, a01 + (((a11 - a01) * FY) >> 4), a01 - (((a01 - a11) * FY) >> 4))
        K = np.where(rv1 >= rv0, rv0 + (((rv1 - rv0) * FX) >> 4), rv0 - (((rv0 - rv1) * FX) >> 4)).astype(np.int32)
        v = out[..., ch].astype(np.int32)
        out[..., ch] = np.clip(v + ((v * K) >> 10), 0, 255)
    return out


def mask(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


def smooth(v, win=21):
    k = np.ones(win) / win
    return np.convolve(np.pad(v, (win // 2, win // 2), mode="edge"), k, mode="valid")


def colprof(a, ch, y0=300, y1=800, x0=96, x1=1824):
    h, w, _ = a.shape
    m = mask(h, w)
    band = np.zeros_like(m); band[y0:y1, :] = True
    sel = m & band
    out = []
    for x in range(x0, x1):
        s = sel[:, x]
        g = a[:, x, 1][s].mean() if s.sum() >= 50 else 0.0
        out.append(a[:, x, ch][s].mean() / g if g > 1e-6 else np.nan)
    return np.array(out)


for off, on, tag in (("Screenshot 2026-10-14 20-32-50.png", "Screenshot 2026-10-14 20-33-00.png", "配对1"),
                     ("Screenshot 2026-10-14 20-33-06.png", "Screenshot 2026-10-14 20-33-15.png", "配对2")):
    A = np.asarray(Image.open(os.path.join(INB, off)).convert("RGB")).astype(np.float64)
    B = np.asarray(Image.open(os.path.join(INB, on)).convert("RGB")).astype(np.float64)
    Sw = apply_lsc(A)
    # 软件模型只做空间校正，不含 AWB；对每条剖面减去自身均值后再比形状
    pA = colprof(A, 0); pB = colprof(B, 0); pS = colprof(Sw, 0)
    for nm, p in (("LSC关(实测)", pA), ("LSC开(实测)", pB), ("LSC开(软件模型)", pS)):
        s = smooth(p)
        print("%s %-16s 平滑极差=%.4f  均值=%.4f" % (tag, nm, np.nanmax(s)-np.nanmin(s), np.nanmean(s)))
    # 形状比较：各自减均值
    fA = smooth(pA); fB = smooth(pB); fS = smooth(pS)
    fA = fA - np.nanmean(fA); fB = fB - np.nanmean(fB); fS = fS - np.nanmean(fS)
    print("     形状相关: 实测开 vs 软件模型 = %.4f   实测开 vs 实测关 = %.4f" %
          (np.corrcoef(fB, fS)[0, 1], np.corrcoef(fB, fA)[0, 1]))
    print("     形状极差: 关 %.4f  开(实测) %.4f  开(软件模型) %.4f" %
          (np.nanmax(fA)-np.nanmin(fA), np.nanmax(fB)-np.nanmin(fB), np.nanmax(fS)-np.nanmin(fS)))
