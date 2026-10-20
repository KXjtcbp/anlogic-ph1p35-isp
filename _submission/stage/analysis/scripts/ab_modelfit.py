# -*- coding: utf-8 -*-
"""用四种模型拟合 亮图 = f(暗图)（G 通道，同坐标），看哪种模型能解释这对 A/B。
   模型1 纯加法偏移    bright = dark + C
   模型2 纯查表(RTL新曲线) bright = lut[dark]
   模型3 线性 bright = a*dark + C
   模型4 先线性再查表 bright = lut[a*dark + C]  (a,C 网格搜索)
残差(RMS, 码)越小说明该模型越能解释两图差异。
"""
import numpy as np
from PIL import Image

DARK = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-36.png"
BRIGHT = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png"
LUTP = r"E:\FPGA\_analysis\lut\gamma_lut_twoseg_p160_a050.hex"

def g_of(p, step=3):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    return a[::step, ::step, 1].ravel()

d = g_of(DARK); b = g_of(BRIGHT)
lut = np.array([int(l.strip(), 16) for l in open(LUTP) if l.strip()], dtype=np.int32)
assert lut.size == 256, lut.size
print("样本数 %d，暗图 G 均值 %.2f，亮图 G 均值 %.2f" % (d.size, d.mean(), b.mean()))

def rms(pred):
    return float(np.sqrt(((pred - b) ** 2).mean()))

print("\n== 模型残差 (RMS 码) ==")
print("  1 纯加法  bright=d+C            : C=%+6.1f  RMS=%6.2f" % (b.mean() - d.mean(), rms(d + (b.mean() - d.mean()))))
print("  2 纯查表  bright=lut[d]         :            RMS=%6.2f" % rms(lut[d]))
A = np.vstack([d, np.ones_like(d)]).T
coef, *_ = np.linalg.lstsq(A.astype(np.float64), b.astype(np.float64), rcond=None)
print("  3 线性    bright=a*d+C          : a=%.3f C=%+6.1f RMS=%6.2f" % (coef[0], coef[1], rms(coef[0] * d + coef[1])))
best = None
for a in np.arange(0.4, 3.01, 0.05):
    for C in np.arange(-20, 121, 2.0):
        pred = lut[np.clip(a * d + C, 0, 255).astype(np.int32)]
        r = rms(pred)
        if best is None or r < best[0]:
            best = (r, a, C)
print("  4 线性+查表 bright=lut[a*d+C]   : a=%.2f C=%+5.1f RMS=%6.2f" % (best[1], best[2], best[0]))

print("\n== 参考：把新曲线套在暗图上（不做任何线性前置）的预测 ==")
for v in (1, 4, 7, 11, 16, 24, 32, 42, 57, 80, 105, 148, 181):
    print("   暗图 %3d -> 曲线 %3d" % (v, lut[v]))
print("\n== 实测分位对齐表（暗图分位 -> 亮图分位）==")
for q in (1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99):
    print("   %2d%% : %3.0f -> %3.0f" % (q, np.percentile(d, q), np.percentile(b, q)))
