# -*- coding: utf-8 -*-
# 抠出 OSD 的绿色 "MODE n" 文字行并放大，用于确认模式号
import os
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"
names = ["mode0室内常光", "mode3室内常光", "mode0盖住镜头"]
for nm in names:
    a = np.asarray(Image.open(os.path.join(SRC, nm + ".jpg")).convert("RGB")).astype(np.int16)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    m = (G > R + 20) & (G > B + 20) & (G > 60)
    m[int(a.shape[0]*0.5):, :] = False      # 只看上半屏
    if m.sum() < 50:
        print(f"{nm}: 绿色文字像素只有 {int(m.sum())} 个，放弃")
        continue
    ys, xs = np.where(m)
    y0, y1 = max(0, ys.min()-14), min(a.shape[0], ys.max()+14)
    x0, x1 = max(0, xs.min()-14), min(a.shape[1], xs.max()+14)
    print(f"{nm}: 绿字 {int(m.sum())} px, bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}] -> 裁 x[{x0},{x1}] y[{y0},{y1}] ({x1-x0}x{y1-y0})")
    c = np.asarray(Image.open(os.path.join(SRC, nm + ".jpg")).convert("RGB"))[y0:y1, x0:x1]
    im = Image.fromarray(c)
    im.resize((im.width*8, im.height*8), Image.LANCZOS).save(os.path.join(OUT, f"{nm}_mode_tight.png"))
    g = (255 - m[y0:y1, x0:x1].astype(np.uint8)*255)
    Image.fromarray(g).resize((im.width*8, im.height*8), Image.NEAREST).save(os.path.join(OUT, f"{nm}_mode_mask.png"))
