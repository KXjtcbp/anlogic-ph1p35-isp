# -*- coding: utf-8 -*-
"""逐像素传递函数：两图同一场景同一位置，G 通道应满足 G_开 = 表[G_关]。
   - 用 IQR 判断两图是否逐像素对齐（对齐则同一输入值的输出很集中）
   - 与所有候选表比对，反推"烧进去的到底是哪张表"
"""
import re
import numpy as np
from PIL import Image

RTL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
DARK = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-36.png"
BRIGHT = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png"

def load(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    h, w = a.shape[:2]
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for (x0, y0, x1, y1) in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0*s):min(int(y1*s), h), int(x0*s):min(int(x1*s), w)] = False
    return a, m

aD, mD = load(DARK)
aB, mB = load(BRIGHT)
M = mD & mB
gd, gb = aD[:, :, 1][M], aB[:, :, 1][M]

print("== 逐像素传递函数（G 通道，输入=不开曲线图，输出=开曲线图）==")
print("%5s %8s %8s %8s %8s" % ("输入", "像素数", "输出中位", "输出均值", "IQR"))
meas = {}
for v in range(0, 256):
    sel = gd == v
    n = int(sel.sum())
    if n < 200:
        continue
    o = gb[sel]
    med = float(np.median(o)); q1, q3 = np.percentile(o, [25, 75])
    meas[v] = med
    if v % 8 == 0 or v < 12:
        print("%5d %8d %8.1f %8.1f %8.1f" % (v, n, med, o.mean(), q3 - q1))
print("可测输入档位 %d 个（每档 >=200 像素）" % len(meas))

# ---- 候选表 ----
def twoseg(P, A):
    x = np.arange(256, dtype=np.float64)
    y = np.where(x <= P, P*np.power(np.maximum(x, 0)/P, A),
                 P + (255-P)*(1 - np.power((255-x)/(255-P), A)))
    y[0] = 0; y[255] = 255
    return np.rint(y)

def logk(k):
    x = np.arange(256, dtype=np.float64)
    y = 255.0*np.log1p(k*x/255.0)/np.log1p(k)
    y[0] = 0; y[255] = 255
    return np.rint(y)

cands = {
    "旧S P118 A=B=1.25": twoseg(118, 1.25),
    "反S P118 A=B=0.50": twoseg(118, 0.50),
    "反S P118 A=B=0.55": twoseg(118, 0.55),
    "对数 k=10": logk(10),
    "对数 k=30": logk(30),
    "对数 k=60": logk(60),
    "两段 P160 A=B=0.50": twoseg(160, 0.50),
    "两段 P200 A=0.40": twoseg(200, 0.40),
}
# RTL 当前表
src = open(RTL, "r", encoding="utf-8", newline="").read()
tbl = re.search(r"    mem_b00\[  0\] = .*?mem_b00\[255\] = 8'h[0-9a-f]{2};", src, re.S).group(0)
cands["RTL 当前(P160 A0.50)"] = np.array([int(v, 16) for v in re.findall(r"8'h([0-9a-f]{2})", tbl)], dtype=np.float64)

vs = np.array(sorted(meas.keys()))
obs = np.array([meas[v] for v in vs])
print("\n== 与候选表比对（在可测档位上取平均绝对偏差）==")
for nm, C in sorted(cands.items(), key=lambda kv: np.abs(kv[1][vs]-obs).mean()):
    e = np.abs(C[vs] - obs)
    print("  %-22s 平均偏差 %6.2f 码   最大 %6.2f 码" % (nm, e.mean(), e.max()))

print("\n== 观测到的实际曲线锚点 ==")
for v in (0, 3, 7, 16, 32, 57, 105, 148, 181):
    if v in meas:
        print("   %3d -> %3.0f" % (v, meas[v]))
