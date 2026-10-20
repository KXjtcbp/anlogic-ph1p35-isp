# -*- coding: utf-8 -*-
import os, glob
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"
os.makedirs(OUT, exist_ok=True)

files = sorted(glob.glob(os.path.join(SRC, "IMG_20261006_*.jpg")))
for f in files:
    name = os.path.splitext(os.path.basename(f))[0]
    im = Image.open(f).convert("RGB")
    W, H = im.size
    a = np.asarray(im).astype(np.int16)

    # MODE 文字（青色）：窄裁剪、不放大，保持原生像素
    y0, y1, x0, x1 = int(0.20*H), int(0.42*H), int(0.12*W), int(0.48*W)
    sub = a[y0:y1, x0:x1]
    v = np.minimum(sub[..., 2] - sub[..., 0], sub[..., 1] - sub[..., 0])
    m = (v > 25).astype(np.uint8)
    ys, xs = np.nonzero(m)
    if len(xs):
        print(f"{name}  MODE文字: 尺寸{m.shape}  命中{len(xs)}px  x范围[{xs.min()},{xs.max()}] y范围[{ys.min()},{ys.max()}]  (裁剪原点 x={x0} y={y0})")
    else:
        print(f"{name}  MODE文字: 掩膜为空（该区无青色文字）")
    Image.fromarray(255 - m*255).save(os.path.join(OUT, name + "_mode.png"))

    # CNT 文字（黄色）
    y0, y1, x0, x1 = int(0.18*H), int(0.36*H), int(0.36*W), int(0.78*W)
    sub = a[y0:y1, x0:x1]
    v = np.minimum(sub[..., 0], sub[..., 1]) - sub[..., 2]
    m = (v > 45).astype(np.uint8)
    ys, xs = np.nonzero(m)
    if len(xs):
        print(f"{name}  CNT文字 : 尺寸{m.shape}  命中{len(xs)}px  x范围[{xs.min()},{xs.max()}] y范围[{ys.min()},{ys.max()}]")
    Image.fromarray(255 - m*255).save(os.path.join(OUT, name + "_cnt.png"))
