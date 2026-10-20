# -*- coding: utf-8 -*-
"""用用户自己的"不开曲线"采集图(00-07-23)预测换成新曲线(P160 A=B=0.50)后的效果。"""
import numpy as np
from PIL import Image, ImageDraw

SRC = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png"
HEX = r"E:\FPGA\_analysis\lut\gamma_lut_twoseg_p160_a050.hex"
OUT = r"E:\FPGA\_analysis\out\expect_from_0007_23.png"

lut = np.array([int(l.strip(), 16) for l in open(HEX) if l.strip()], dtype=np.uint8)
a = np.asarray(Image.open(SRC).convert("RGB"))
after = lut[a]

def stat(x, tag):
    x = x.astype(np.int32)
    Y = (77 * x[:, :, 0] + 150 * x[:, :, 1] + 29 * x[:, :, 2]) >> 8
    print("%-24s Ymean %6.2f  p10 %3d p50 %3d p90 %3d p99 %3d max %3d | 暗部<=8 %5.2f%%  过曝>=250 %5.3f%% | R/G %.4f B/G %.4f"
          % (tag, Y.mean(), np.percentile(Y, 10), np.percentile(Y, 50), np.percentile(Y, 90),
             np.percentile(Y, 99), Y.max(),
             (Y <= 8).mean() * 100, (Y >= 250).mean() * 100,
             x[:, :, 0].mean() / x[:, :, 1].mean(), x[:, :, 2].mean() / x[:, :, 1].mean()))

stat(a, "现状(曲线关/旧S关)")
stat(after, "换新表预测")

h2 = a.shape[0] // 2
w2 = a.shape[1] // 2
canvas = Image.new("RGB", (w2, h2 * 2 + 10), (30, 30, 30))
for k, (img, lab) in enumerate(((a, "BEFORE (当前烧录 / SW2 关)"), (after, "AFTER 预测 (新表 P=160 A=0.50)"))):
    im = Image.fromarray(img).resize((w2, h2), Image.BOX)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 430, 26], fill=(0, 0, 0))
    d.text((6, 8), lab, fill=(255, 255, 0))
    canvas.paste(im, (0, k * (h2 + 10)))
canvas.save(OUT)
print("saved " + OUT)
