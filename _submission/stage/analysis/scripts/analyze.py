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
    print("=" * 74)
    print(f"{name}   {W}x{H}")

    # ---- 1) OSD 青色 MODE 文字：青色掩膜（蓝、绿都明显高于红）----
    y0, y1, x0, x1 = int(0.18*H), int(0.46*H), int(0.10*W), int(0.62*W)
    sub = a[y0:y1, x0:x1]
    v = np.minimum(sub[..., 2] - sub[..., 0], sub[..., 1] - sub[..., 0])
    m = (v > 25).astype(np.uint8) * 255
    Image.fromarray(255 - m).resize((m.shape[1]*2, m.shape[0]*2), Image.NEAREST).save(
        os.path.join(OUT, name + "_cyantext.png"))

    # ---- 2) OSD 黄色 CNT 文字：黄掩膜（红、绿都高，蓝低）----
    y0, y1, x0, x1 = int(0.13*H), int(0.40*H), int(0.28*W), int(0.85*W)
    sub = a[y0:y1, x0:x1]
    v = np.minimum(sub[..., 0], sub[..., 1]) - sub[..., 2]
    m = (v > 40).astype(np.uint8) * 255
    Image.fromarray(255 - m).resize((m.shape[1]*2, m.shape[0]*2), Image.NEAREST).save(
        os.path.join(OUT, name + "_cnttext.png"))

    # ---- 3) 逐列色彩剖面（屏幕中部一条横带，避开 OSD 文字行）----
    yy0, yy1 = int(0.46*H), int(0.66*H)
    print("  列%        R      G      B     | 判定")
    for i in range(4, 100, 4):
        x = int(i / 100.0 * W)
        blk = a[yy0:yy1, max(0, x-8):x+9].reshape(-1, 3).mean(axis=0)
        r, g, b = blk
        mx, mn = max(r, g, b), min(r, g, b)
        sat = 0 if mx < 1 else (mx - mn) / mx
        if sat < 0.15:
            tag = "灰/白" if mx > 128 else "黑/暗灰"
        else:
            if r > g and r > b:      tag = "红" if g < r*0.75 else "黄"
            elif g > r and g > b:    tag = "绿" if r < g*0.75 else "黄绿"
            else:                    tag = "蓝" if g < b*0.75 else "青"
        print(f"  {i:3d}%  {r:6.0f} {g:6.0f} {b:6.0f}     | 亮{int(mx):3d} 饱和{sat:4.2f} {tag}")
