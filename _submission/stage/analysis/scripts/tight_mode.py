# -*- coding: utf-8 -*-
# 三张彩色画面照片的模式文字：按目视估的坐标做紧裁剪，输出 (a) 原色放大 (b) 判别式掩膜放大
import os
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"

# name: (x0, x1, y0, y1) 原生像素坐标
regions = {
    "IMG_20261006_192107": (800, 1280, 900, 1060),
    "IMG_20261006_192127": (1520, 2000, 780, 940),
    "IMG_20261006_192131": (960, 1500, 960, 1130),
}
for name, (x0, x1, y0, y1) in regions.items():
    im = Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")
    a = np.asarray(im).astype(np.int16)
    sub = a[y0:y1, x0:x1]
    # (a) 原色
    rgb = Image.fromarray(sub.astype(np.uint8))
    rgb.resize((rgb.width*3, rgb.height*3), Image.LANCZOS).save(os.path.join(OUT, name + "_rgb.png"))
    # (b) 掩膜：min(G,B)-R
    d = np.minimum(sub[..., 1], sub[..., 2]) - sub[..., 0]
    for thr in (100, 140):
        m = (d > thr).astype(np.uint8)
        img = Image.fromarray(255 - m*255)
        img.resize((img.width*3, img.height*3), Image.LANCZOS).save(
            os.path.join(OUT, f"{name}_mask{thr}.png"))
    print(f"{name}: 裁剪 {x1-x0}x{y1-y0}  min(G,B)-R 统计 min={d.min()} max={d.max()} mean={d.mean():.0f}")
