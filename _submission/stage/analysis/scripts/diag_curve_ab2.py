# -*- coding: utf-8 -*-
"""第二级判定：把两张图看成同一场景的"输入/输出"，
   用分位数映射（经验传递函数 ETF）反推实际生效的曲线，
   并与 RTL 里的表逐点对照 —— 用来回答"曲线是否真的按设计生效"。
   另外做 OSD 文字像素对照（OSD 在 hdmi_mixer 里叠加，位于 gamma 之后，
   其像素值应两张图完全一致 ⇒ 作为"屏幕/采集链路未变"的对照）。"""
import re
import numpy as np
from PIL import Image

RTL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
DARK = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-36.png"   # 判定为"不开曲线"
BRIGHT = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png"  # 判定为"开曲线"
OUT = r"E:\FPGA\_analysis"

src = open(RTL, "r", encoding="utf-8", newline="").read()
tbl = re.search(r"    mem_b00\[  0\] = .*?mem_b00\[255\] = 8'h[0-9a-f]{2};", src, re.S).group(0)
lut = np.array([int(v, 16) for v in re.findall(r"8'h([0-9a-f]{2})", tbl)], dtype=np.float64)

def load(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    h, w = a.shape[:2]
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for (x0, y0, x1, y1) in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0*s):min(int(y1*s), h), int(x0*s):min(int(x1*s), w)] = False
    Y = (77*a[:, :, 0] + 150*a[:, :, 1] + 29*a[:, :, 2]) >> 8
    return a, m, Y

aD, mD, YD = load(DARK)
aB, mB, YB = load(BRIGHT)
# 两张图同一场景 ⇒ 用同一套 OSD 遮罩（取交集之外的公共有效区）
M = mD & mB
yd, yb = YD[M], YB[M]

print("公共有效像素 %d（%.2f%%）" % (M.sum(), 100.0*M.sum()/M.size))
print("\n== 经验传递函数 ETF：按分位数对齐两张图 ==")
print("%6s %8s %8s %10s %8s" % ("分位", "不开曲线", "开曲线", "实际增益", "RTL表预测"))
qs = [0.1, 1, 5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 99, 99.9]
etf = []
for q in qs:
    vd = np.percentile(yd, q); vb = np.percentile(yb, q)
    print("%5.1f%% %8.1f %8.1f %10s %8.1f" % (q, vd, vb,
          ("%.3f" % (vb/vd)) if vd > 0 else "  -", lut[int(round(vd))]))
# 全量 ETF（逐分位），用于拟合
p = np.linspace(0, 100, 2001)
vd_all = np.percentile(yd, p); vb_all = np.percentile(yb, p)

best = None
for g in np.arange(0.70, 1.45, 0.005):
    pred = np.interp(np.clip(g*vd_all, 0, 255), np.arange(256), lut)
    e = np.abs(pred - vb_all).mean()
    if best is None or e < best[0]:
        best = (e, g)
print("\n最优拟合：不开曲线 x 数字增益 %.3f 再查 RTL 表  ==> 与开曲线图的平均偏差 %.2f 码" % (best[1], best[0]))
e1 = np.abs(np.interp(vd_all, np.arange(256), lut) - vb_all).mean()
print("           不加数字增益（纯查表）        ==> 平均偏差 %.2f 码" % e1)

print("\n== OSD 文字像素对照（应完全一致）==")
for nm, a in (("不开曲线", aD), ("开曲线", aB)):
    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    sel = (R > 140) & (G > 140) & (B < 130) & (np.arange(a.shape[0])[:, None] < 300)
    print("  %-6s 黄色文字像素 %6d  均值 RGB = %6.2f / %6.2f / %6.2f" %
          (nm, sel.sum(), R[sel].mean(), G[sel].mean(), B[sel].mean()))

print("\n== 暗场噪声（同一暗区 y[600:700] x[300:500]）==")
for nm, a in (("不开曲线", aD), ("开曲线", aB)):
    pat = a[600:700, 300:500, 1].astype(np.float64)
    print("  %-6s G 均值 %6.2f 标准差 %5.2f 极差 %3d" % (nm, pat.mean(), pat.std(), pat.max()-pat.min()))
