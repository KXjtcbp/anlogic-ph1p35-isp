# -*- coding: utf-8 -*-
"""清晰度指标：判断两张 A/B 图是否存在"离焦/雾化"（而非色调曲线）。
指标：HF = mean(|Y - blur5(Y)|)；相对清晰度 = HF / std(Y)（消除对比度差异）；
      绝对高频能量 = HF / mean(Y)。
若某张的 HF/std 明显更低 => 该张被低通（离焦/雾化/遮挡）。
"""
import numpy as np
from PIL import Image, ImageFilter

FILES = [
    (r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png", "00-07-23 曲线ON"),
    (r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-36.png", "00-07-36 曲线OFF"),
    (r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3+SW4.png", "SW3+SW4 31.5x"),
    (r"E:\FPGA\captures\2026-10-10_增益梯SW34\两个全关.png", "两个全关 4.0x"),
    (r"E:\FPGA\captures\2026-10-10_基线\00.png", "00.png 厂商11.25x"),
]

def luma(a):
    a = a.astype(np.int32)
    return (77 * a[:, :, 0] + 150 * a[:, :, 1] + 29 * a[:, :, 2]) >> 8

# OSD 遮罩（1920x1080 下的固定盒，按宽等比）
def mask(w, h):
    m = np.ones((h, w), bool)
    s = w / 1280.0
    for (x0, y0, x1, y1) in [(0, 0, 180, 180), (360, 105, 620, 145), (165, 165, 280, 200)]:
        m[int(y0*s):int(y1*s), int(x0*s):int(x1*s)] = False
    return m

print("file                     Ymean  Ystd   HF    HF/std  HF/mean")
for p, name in FILES:
    im = Image.open(p).convert("RGB")
    a = np.asarray(im)
    h, w = a.shape[:2]
    y = luma(a).astype(np.float64)
    m = mask(w, h)
    # 用 PIL 高斯模糊（半径 1.5）近似低通
    blur = np.asarray(im.filter(ImageFilter.GaussianBlur(1.5))).astype(np.int32)
    yb = luma(blur).astype(np.float64)
    hf = np.abs(y - yb)[m]
    yy = y[m]
    print("%-24s %6.2f %6.2f %6.2f %7.4f %7.4f" % (
        name, yy.mean(), yy.std(), hf.mean(), hf.mean()/max(yy.std(), 1e-9),
        hf.mean()/max(yy.mean(), 1e-9)))
