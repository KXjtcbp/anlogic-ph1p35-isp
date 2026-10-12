# -*- coding: utf-8 -*-
"""第三轮：在「两段幂函数」族里扫描 (P, A=B)，目标同时满足
   ①中位数抬到 ~80-100（解决偏暗）②>=250 过曝面积不升反降（解决光源过亮）
   ③x=236 的输出不高于 230（把光源本身压下去，而不只是"相对没那么亮"）
   ④低端斜率别太猛（y(4)/4 越小，暗部噪声/灰雾越轻）"""
import numpy as np
from PIL import Image

SRC = r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3+SW4.png"      # 31.5x 现状（最高档）

def load(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    h, w = a.shape[:2]
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for (x0, y0, x1, y1) in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0*s):min(int(y1*s), h), int(x0*s):min(int(x1*s), w)] = False
    return a, m

def lut_2seg(P, A):
    x = np.arange(256, dtype=np.float64)
    y = np.where(x <= P, P*np.power(x/P, A), P + (255-P)*(1 - np.power((255-x)/(255-P), A)))
    return np.clip(np.rint(y), 0, 255).astype(np.int32)

a, m = load(SRC)
px = a[m]
R, G, B = px[:, 0], px[:, 1], px[:, 2]
Y0 = (77*R + 150*G + 29*B) >> 8

def score(lut):
    b = lut[a]
    Y = (77*b[:, :, 0] + 150*b[:, :, 1] + 29*b[:, :, 2]) >> 8
    Yv = Y[m]
    return dict(mean=Yv.mean(), p50=np.percentile(Yv, 50), p90=np.percentile(Yv, 90),
                clip=(Yv >= 250).mean()*100, dark=(Yv <= 8).mean()*100,
                h236=int(lut[236]), h200=int(lut[200]), toe=float(lut[4])/4.0,
                mx=int(Yv.max()), mn=int(Yv.min()))

print("=" * 128)
print("原始（不做曲线）: mean %.1f  p50 %.0f  clip %.3f%%  dark %.2f%%" %
      (Y0.mean(), np.percentile(Y0, 50), (Y0 >= 250).mean()*100, (Y0 <= 8).mean()*100))
print("=" * 128)
print("%-16s %6s %5s %5s %8s %7s %6s %6s %5s %5s %5s" %
      ("(P, A=B)", "mean", "p50", "p90", "clip%", "dark%", "y236", "y200", "toe", "min", "max"))
best = None
for P in (118, 140, 160, 180, 200):
    for A in (0.40, 0.45, 0.50, 0.55, 0.60, 0.70):
        lut = lut_2seg(P, A)
        s = score(lut)
        ok = (0.02 <= s["clip"] <= 0.035) and (s["h236"] <= 232) and (70 <= s["p50"] <= 115)
        tag = " <==" if ok else ""
        print("P=%-4d A=%.2f %6.1f %5.0f %5.0f %8.3f %7.2f %6d %6d %5.1f %5d %5d%s" %
              (P, A, s["mean"], s["p50"], s["p90"], s["clip"], s["dark"],
               s["h236"], s["h200"], s["toe"], s["mn"], s["mx"], tag))
        if ok:
            sc = s["p50"] - 60 * s["clip"] - 2 * s["toe"]
            if best is None or sc > best[0]:
                best = (sc, P, A, s)
print("\n最优候选: P=%d A=%.2f -> %s" % (best[1], best[2], best[3]) if best else "\n没有满足约束的候选")

for P, A in [(160, 0.50), (160, 0.55), (180, 0.50), (140, 0.50)]:
    lut = lut_2seg(P, A)
    print("锚点 P=%-4d A=%.2f: " % (P, A) + " ".join("%d->%d" % (x, lut[x])
          for x in (0, 4, 8, 16, 32, 42, 64, 90, 118, 160, 200, 236, 255)))
