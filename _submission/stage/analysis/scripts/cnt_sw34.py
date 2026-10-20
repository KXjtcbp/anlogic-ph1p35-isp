# -*- coding: utf-8 -*-
"""把四张 SW3/SW4 采集图的 OSD 帧计数行裁出来纵向拼接，用于读 CNT（判断有没有复位）。"""
import numpy as np
from PIL import Image

FILES = [r"E:\FPGA\captures\2026-10-10_增益梯SW34\两个全关.png", r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3.png", r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW4.png", r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3+SW4.png"]
crops = []
for p in FILES:
    im = Image.open(p).convert("RGB")
    w, h = im.size
    s = w / 1280.0
    box = (int(360*s), int(105*s), int(620*s), int(142*s))
    c = im.crop(box).resize((880, 126), Image.NEAREST)
    crops.append(np.asarray(c))

sep = np.full((8, 880, 3), 255, np.uint8)
out = []
for i, c in enumerate(crops):
    if i:
        out.append(sep)
    out.append(c)
Image.fromarray(np.vstack(out)).save(r"E:\FPGA\_analysis\out\cnt_sw34.png")
print("saved E:\\FPGA\\_analysis\\out\\cnt_sw34.png")
for p in FILES:
    print("  " + p)
