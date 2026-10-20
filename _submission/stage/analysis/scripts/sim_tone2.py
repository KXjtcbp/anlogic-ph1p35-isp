# -*- coding: utf-8 -*-
"""第二轮：把"反S"与"对数+黑点"两类曲线在真实采集图上比出最优参数。
指标里加了 p1/min —— 用来识别"暗部被整体抬起"造成的灰雾（milky black）。"""
import os, numpy as np
from PIL import Image

OUT = r"E:\FPGA\_analysis"
SRC = {1.0: r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW4.png",      # 15.750x 模拟，数字增益 1x
       2.0: r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3+SW4.png"}  # 31.500x 模拟，数字增益 2x（现状）

def load(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    h, w = a.shape[:2]
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for (x0, y0, x1, y1) in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0*s):min(int(y1*s), h), int(x0*s):min(int(x1*s), w)] = False
    return a, m

def ystats(a, m):
    px = a[m]
    R, G, B = px[:, 0], px[:, 1], px[:, 2]
    Y = (77*R + 150*G + 29*B) >> 8
    return (Y.mean(), np.percentile(Y, 1), np.percentile(Y, 50), np.percentile(Y, 90),
            np.percentile(Y, 99), int(Y.min()), int(Y.max()),
            (Y >= 250).mean()*100, (Y <= 8).mean()*100, R.mean()/G.mean(), B.mean()/G.mean())

def lut_invS(P=118.0, A=0.50):
    x = np.arange(256, dtype=np.float64)
    return np.clip(np.rint(np.where(x <= P, P*np.power(x/P, A),
                P + (255-P)*(1 - np.power((255-x)/(255-P), A)))), 0, 255).astype(np.int32)

def lut_log(BL=8.0, k=8.0):
    x = np.arange(256, dtype=np.float64)
    xx = np.clip(x - BL, 0, None)
    return np.clip(np.rint(255.0*np.log1p(k*xx/255.0)/np.log1p(k)), 0, 255).astype(np.int32)

print("=" * 140)
print("第二轮候选（Y 统计去除 OSD；min=全画面最暗像素，p1 用来判灰雾）")
print("=" * 140)
print("%-42s %6s %4s %4s %4s %4s %4s %4s %8s %7s %6s %6s" %
      ("方案", "Ymean", "p1", "p50", "p90", "p99", "min", "max", ">=250%", "<=8%", "R/G", "B/G"))

def run(name, base_key, mult, lut):
    a, m = load(SRC[base_key])
    b = a if mult == 1 else np.clip(a*mult, 0, 255)
    if lut is not None:
        b = lut[b]
    s = ystats(b, m)
    print("%-42s %6.1f %4.0f %4.0f %4.0f %4.0f %4d %4d %8.3f %7.2f %6.4f %6.4f" % ((name,) + s))
    return b

# 现状
run("【现状】31.5x 线性（SW3+SW4 全开）", 2.0, 1, None)
run("【现状】15.75x 线性（仅 SW4）", 1.0, 1, None)
# 反S
run("15.75x + 反S 0.55（SW3 关）", 1.0, 1, lut_invS(118, 0.55))
run("15.75x + 反S 0.50（SW3 关）", 1.0, 1, lut_invS(118, 0.50))
run("31.5x + 反S 0.55", 2.0, 1, lut_invS(118, 0.55))
run("31.5x + 反S 0.50", 2.0, 1, lut_invS(118, 0.50))
run("31.5x + 反S 0.45", 2.0, 1, lut_invS(118, 0.45))
# 数字增益 4x（=63x 总增益）再套曲线
run("63x(数字4x) 线性", 1.0, 4, None)
run("63x(数字4x) + 反S 0.50", 1.0, 4, lut_invS(118, 0.50))
# 对数 + 黑点
for BL in (0, 4, 8, 12):
    for k in (6, 10, 16):
        run("31.5x + log BL%d k%d" % (BL, k), 2.0, 1, lut_log(BL, k))

print("\n" + "=" * 140)
print("曲线锚点（挑表用）")
print("=" * 140)
xs = [0, 2, 4, 8, 12, 16, 21, 32, 42, 64, 90, 118, 160, 200, 236, 255]
print("      x   :" + "".join("%6d" % x for x in xs))
for tag, l in [("invS0.55", lut_invS(118, 0.55)), ("invS0.50", lut_invS(118, 0.50)),
               ("invS0.45", lut_invS(118, 0.45)), ("log BL4 k10", lut_log(4, 10)),
               ("log BL8 k10", lut_log(8, 10)), ("log BL8 k16", lut_log(8, 16))]:
    print("%10s:" % tag + "".join("%6d" % l[x] for x in xs))
