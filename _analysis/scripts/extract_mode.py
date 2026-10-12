# -*- coding: utf-8 -*-
import os, glob
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"

# 青色 OSD 文字的判别式：min(G,B) - R。
# 蓝底(2,62,254)->60, 青蓝底(0,150,245)->150, 绿底(13,254,76)->63, 灰底(208,217,235)->9
# 青色文字(约 0,255,255) -> 255。用 120 做门限可把文字从任何底色里抠出来。
for f in sorted(glob.glob(os.path.join(SRC, "IMG_20261006_*.jpg"))):
    name = os.path.splitext(os.path.basename(f))[0]
    im = Image.open(f).convert("RGB")
    W, H = im.size
    a = np.asarray(im).astype(np.int16)
    y0, y1, x0, x1 = int(0.15*H), int(0.50*H), int(0.10*W), int(0.60*W)
    sub = a[y0:y1, x0:x1]
    d = np.minimum(sub[..., 1], sub[..., 2]) - sub[..., 0]
    m = (d > 120).astype(np.uint8)
    ys, xs = np.nonzero(m)
    if len(xs) == 0:
        print(f"{name}: 无命中")
        continue
    print(f"{name}: 命中{len(xs)}px  bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}]  (裁剪原点 {x0},{y0})")
    px0, px1 = max(0, xs.min()-40), min(m.shape[1], xs.max()+40)
    py0, py1 = max(0, ys.min()-25), min(m.shape[0], ys.max()+25)
    crop = m[py0:py1, px0:px1]
    img = Image.fromarray(255 - crop*255)
    img = img.resize((img.width*3, img.height*3), Image.LANCZOS)
    img.save(os.path.join(OUT, name + "_mode_zoom.png"))
    print(f"    -> {name}_mode_zoom.png  {img.width}x{img.height}  源裁剪 {crop.shape[1]}x{crop.shape[0]}")
