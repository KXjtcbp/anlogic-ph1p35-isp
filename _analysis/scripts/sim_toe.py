# -*- coding: utf-8 -*-
"""色调曲线选型第二轮：给"两段幂函数 S 曲线"加线性趾（压制近黑噪声被放大成灰雾）。

曲线定义（x = 曲线前 8bit 输入, y = 输出）：
    x <= t        :  y = s*x                                    线性趾（死区斜率 s）
    t < x <= P    :  y = y_t + (P - y_t) * ((x-t)/(P-t))^A      中段（提亮）
    x > P         :  y = P + (255-P) * (1 - ((255-x)/(255-P))^B) 上臂（压光源）
其中 y_t = s*t。
对照基线 = 现表 P=160 A=B=0.50（无趾，y(1)=12.6 ⇒ 1 码噪声被放大成 12.6 码灰）。
"""
import os
import numpy as np
from PIL import Image

OUT = r"E:\FPGA\_analysis\out"
IMG = r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3+SW4.png"
IMG2 = r"E:\FPGA\captures\2026-10-11_标定\直看白纸.png"


def curve(t, s, A, P, B):
    lut = np.zeros(256, np.float64)
    y_t = s * t
    for x in range(256):
        if x <= t:
            y = s * x
        elif x <= P:
            y = y_t + (P - y_t) * (((x - t) / (P - t)) ** A)
        else:
            y = P + (255 - P) * (1.0 - (((255 - x) / (255 - P)) ** B))
        lut[x] = y
    lut[0] = 0.0
    lut[255] = 255.0
    return np.clip(np.round(lut), 0, 255)


def osd_mask(w, h):
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def load(path):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im)
    m = osd_mask(*im.size)
    return a, m


def report(tag, lut, a, m):
    px = a[m].astype(np.int32)
    out = lut[px]
    R, G, Bc = out[:, 0], out[:, 1], out[:, 2]
    Y = (77 * R + 150 * G + 29 * Bc) / 256.0
    Y0 = (77 * px[:, 0] + 150 * px[:, 1] + 29 * px[:, 2]) / 256.0
    print("%-26s 前:mean=%5.1f p50=%3.0f | 后:mean=%5.1f p10=%3.0f p50=%3.0f p90=%3.0f "
          ">=250=%6.3f%% <=8=%5.2f%% | 趾 y(1)=%2.0f y(2)=%2.0f y(4)=%2.0f y(8)=%2.0f | "
          "y(42)=%3.0f y(118)=%3.0f y(236)=%3.0f" %
          (tag, Y0.mean(), np.percentile(Y0, 50), Y.mean(), np.percentile(Y, 10),
           np.percentile(Y, 50), np.percentile(Y, 90),
           100.0 * (Y >= 250).mean(), 100.0 * (Y <= 8).mean(),
           lut[1], lut[2], lut[4], lut[8], lut[42], lut[118], lut[236]))


a, m = load(IMG)
print("== 31.500x 实拍（SW3+SW4.png）==")
CANDS = [("现表 P160 A.50 无趾", None),
         ("t=8  s=1.5 A.50", (8, 1.5, 0.50, 160, 0.50)),
         ("t=12 s=1.5 A.50", (12, 1.5, 0.50, 160, 0.50)),
         ("t=16 s=1.5 A.50", (16, 1.5, 0.50, 160, 0.50)),
         ("t=16 s=2.0 A.50", (16, 2.0, 0.50, 160, 0.50)),
         ("t=24 s=1.5 A.50", (24, 1.5, 0.50, 160, 0.50)),
         ("t=16 s=1.5 A.55", (16, 1.5, 0.55, 160, 0.50)),
         ("t=16 s=1.5 A.50 P200", (16, 1.5, 0.50, 200, 0.50)),
         ("纯线性（无曲线）", None)]
for tag, prm in CANDS:
    if prm is None and tag.startswith("纯线性"):
        lut = np.arange(256, dtype=np.float64)
        report(tag, lut, a, m); continue
    if prm is None:
        lut = curve(0.0001, 160 * (0.0001 ** 0.0), 0.5, 160, 0.5)  # 占位
        # 现表：P=160 A=B=0.5，无线性趾（t→0 且 s→∞ 的极限），直接按公式算
        lut = np.array([0.0 if x == 0 else (160 * ((x / 160) ** 0.5) if x <= 160 else
                                            160 + 95 * (1 - ((255 - x) / 95) ** 0.5)) for x in range(256)])
        lut = np.clip(np.round(lut), 0, 255)
    else:
        lut = curve(*prm)
    report(tag, lut, a, m)

print()
print("== 直看白纸（平坦白场，检查上臂/削顶）==")
a2, m2 = load(IMG2)
for tag, prm in CANDS:
    if prm is None and tag.startswith("纯线性"):
        report(tag, np.arange(256, dtype=np.float64), a2, m2); continue
    if prm is None:
        lut = np.array([0.0 if x == 0 else (160 * ((x / 160) ** 0.5) if x <= 160 else
                                            160 + 95 * (1 - ((255 - x) / 95) ** 0.5)) for x in range(256)])
        lut = np.clip(np.round(lut), 0, 255)
    else:
        lut = curve(*prm)
    report(tag, lut, a2, m2)
