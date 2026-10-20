# -*- coding: utf-8 -*-
"""生成"预期效果"对比图：上=现状(31.5x 线性)，下=换成 P160/A0.50 色调曲线后（SW2 拨上）。
   曲线表直接从 isp_gamma.v 里读出来用，保证与要烧的 RTL 完全一致。"""
import re
import numpy as np
from PIL import Image

RTL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
SRC = r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3+SW4.png"
OUT_SIDE = r"E:\FPGA\_analysis\out\expect_before_after.png"
OUT_NEW = r"E:\FPGA\_analysis\out\expect_after_gamma.png"

src = open(RTL, "r", encoding="utf-8", newline="").read()
tbl = re.search(r"    mem_b00\[  0\] = .*?mem_b00\[255\] = 8'h[0-9a-f]{2};", src, re.S).group(0)
lut = np.array([int(v, 16) for v in re.findall(r"8'h([0-9a-f]{2})", tbl)], dtype=np.uint8)
assert lut.shape == (256,)

a = np.asarray(Image.open(SRC).convert("RGB"))
b = lut[a]

def label(img, text):
    from PIL import ImageDraw
    im = Image.fromarray(img)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 470, 34], fill=(0, 0, 0))
    d.text((8, 8), text, fill=(255, 255, 0))
    return im

top = label(a, "BEFORE  SW3+SW4 (31.5x, linear)  Ymean 46.0 p50 42 clip 0.036%")
bot = label(b, "AFTER   same capture + new tone curve P=160 A=B=0.50  Ymean 79.8 p50 82 clip 0.024%")
w, h = top.size
side = Image.new("RGB", (w, h * 2 + 6), (255, 255, 255))
side.paste(top, (0, 0))
side.paste(bot, (0, h + 6))
side.resize((1280, (h * 2 + 6) * 1280 // w), Image.LANCZOS).save(OUT_SIDE)
Image.fromarray(b).save(OUT_NEW)
print("saved " + OUT_SIDE)
print("saved " + OUT_NEW)
print("曲线锚点(自 RTL): " + " ".join("%d->%d" % (x, lut[x]) for x in
      (0, 4, 8, 16, 32, 42, 64, 90, 118, 160, 200, 236, 255)))
