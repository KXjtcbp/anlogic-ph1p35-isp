# -*- coding: utf-8 -*-
"""用采集图离线仿真"色调曲线 + 增益"的组合，挑出能同时解决【偏暗】与【光源过亮】的参数。
口径与 diag_sw34.py 一致（去 3 个 OSD 区域后统计）。"""
import os, numpy as np
from PIL import Image

OUT = r"E:\FPGA\_analysis"
SRC_1575 = r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW4.png"        # 模拟 15.750x（数字增益 1x）
SRC_3150 = r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3+SW4.png"    # 模拟 31.500x（数字增益 2x）

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
    return dict(mean=Y.mean(), p10=np.percentile(Y, 10), p50=np.percentile(Y, 50),
                p90=np.percentile(Y, 90), p99=np.percentile(Y, 99), mx=int(Y.max()),
                clip250=(Y >= 250).mean()*100, dark8=(Y <= 8).mean()*100,
                RG=R.mean()/G.mean(), BG=B.mean()/G.mean())

def curve(x, P=118.0, A=1.25, B=1.25):
    x = np.asarray(x, dtype=np.float64)
    y = np.where(x <= P, P*np.power(x/P, A),
                 P + (255-P)*(1.0 - np.power(np.clip((255-x)/(255-P), 0, 1), B)))
    return np.clip(np.rint(y), 0, 255).astype(np.int32)

def apply_lut(a, P=118.0, A=1.0, B=1.0):
    lut = curve(np.arange(256), P, A, B)
    return lut[a]

a1575, m = load(SRC_1575)
a3150, _ = load(SRC_3150)

print("=" * 124)
print("候选方案对照（同一张 31.500x 采集 / 15.750x 采集，去 OSD 后统计；Y 为 BT.601 8bit）")
print("=" * 124)
cases = [
    ("现状 31.5x 线性（SW3+SW4 全开）",      a3150, None),
    ("现状 15.75x 线性（仅 SW4）",           a1575, None),
    ("31.5x + 现表S曲线 P118 A=B=1.25",      a3150, (118, 1.25, 1.25)),
    ("31.5x + 反S P118 A=B=0.70",            a3150, (118, 0.70, 0.70)),
    ("31.5x + 反S P118 A=B=0.55",            a3150, (118, 0.55, 0.55)),
    ("31.5x + 反S P118 A=B=0.45",            a3150, (118, 0.45, 0.45)),
    ("15.75x x2(数字增益4x) 线性",           np.clip(a1575*2, 0, 255), None),
    ("15.75x x2 + 反S P118 A=B=0.55",        np.clip(a1575*2, 0, 255), (118, 0.55, 0.55)),
    ("15.75x x4(数字增益8x) + 反S A=B=0.55", np.clip(a1575*4, 0, 255), (118, 0.55, 0.55)),
]
print("%-38s %6s %4s %4s %4s %4s %4s %8s %7s %6s %6s" %
      ("方案", "Ymean", "p10", "p50", "p90", "p99", "max", ">=250%", "<=8%", "R/G", "B/G"))
for name, a, g in cases:
    b = a if g is None else apply_lut(a, *g)
    s = ystats(b, m)
    print("%-38s %6.1f %4.0f %4.0f %4.0f %4.0f %4d %8.3f %7.2f %6.4f %6.4f" %
          (name, s["mean"], s["p10"], s["p50"], s["p90"], s["p99"], s["mx"],
           s["clip250"], s["dark8"], s["RG"], s["BG"]))

print("\n" + "=" * 124)
print("反 S 曲线锚点表（P=118，A=B 取不同值）—— 用于挑表")
print("=" * 124)
xs = [0, 4, 8, 16, 21, 32, 42, 64, 90, 118, 140, 160, 200, 236, 255]
print("   x   :" + "".join("%6d" % x for x in xs))
for AB in (1.25, 1.0, 0.70, 0.55, 0.45):
    lut = curve(np.arange(256), 118.0, AB, AB)
    print("A=B=%.2f:" % AB + "".join("%6d" % lut[x] for x in xs))

# 存预览图，供目视
for tag, arr in [("pre_3150_linear", a3150),
                 ("pre_3150_invS055", apply_lut(a3150, 118, 0.55, 0.55)),
                 ("pre_1575_invS055", apply_lut(a1575, 118, 0.55, 0.55)),
                 ("pre_1575x2_invS055", apply_lut(np.clip(a1575*2, 0, 255), 118, 0.55, 0.55))]:
    im = Image.fromarray(arr.astype(np.uint8)).resize((960, 540), Image.BILINEAR)
    p = os.path.join(OUT, tag + ".png")
    im.save(p)
    print("预览: " + p)
