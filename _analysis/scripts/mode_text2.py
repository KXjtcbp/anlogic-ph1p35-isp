# -*- coding: utf-8 -*-
# OSD 算法状态行的文字颜色是 hdmi_mixer.v:175 的 localparam COLOR_ALG_TEXT = 24'h00ff88
#   = (R=0, G=255, B=136) 亮绿。用 R<80 & G>200 & 90<B<200 可把它从下列所有底色里分离：
#   灰底(208,217,235) R 太高 / 绿底(13,254,76) B 太低 / 青蓝底(0,150,245) G 太低 / 蓝底(2,62,254) G 太低
import os, glob
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"

for f in sorted(glob.glob(os.path.join(SRC, "IMG_20261006_*.jpg"))):
    name = os.path.splitext(os.path.basename(f))[0]
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.int16)
    H, W = a.shape[:2]
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    m = (R < 80) & (G > 200) & (B > 90) & (B < 200)
    ys, xs = np.nonzero(m)
    if len(xs) < 50:
        print(f"{name}: 命中{len(xs)}px —— 太少，跳过")
        continue
    # 只保留最大的一簇（按 x 直方图找连续主簇）
    print(f"{name}: 命中{len(xs)}px  x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}] 密集中位x={int(np.median(xs))} y={int(np.median(ys))}")
    x0, x1 = max(0, xs.min()-30), min(W, xs.max()+30)
    y0, y1 = max(0, ys.min()-20), min(H, ys.max()+20)
    mask = m[y0:y1, x0:x1]
    img = Image.fromarray(255 - mask.astype(np.uint8)*255)
    img = img.resize((img.width*4, img.height*4), Image.LANCZOS)
    img.save(os.path.join(OUT, name + "_MODEn.png"))
    rgb = Image.fromarray(a[y0:y1, x0:x1].astype(np.uint8))
    rgb.resize((rgb.width*4, rgb.height*4), Image.LANCZOS).save(os.path.join(OUT, name + "_MODEn_rgb.png"))
    print(f"    -> {name}_MODEn.png {img.width}x{img.height}  (原生裁剪 {x1-x0}x{y1-y0})")
