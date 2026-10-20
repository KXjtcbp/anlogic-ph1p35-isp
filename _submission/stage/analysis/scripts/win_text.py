# -*- coding: utf-8 -*-
# 彩色画面上那三张：按"屏幕上的相对位置"开窗（文字总在同一屏幕位置，只是手持角度略移）
import os
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"
regions = {
    "IMG_20261006_192107": (800, 1240, 900, 1060),
    "IMG_20261006_192127": (1560, 1990, 780, 940),
    "IMG_20261006_192131": (980, 1470, 960, 1130),
}
for name, (x0, x1, y0, y1) in regions.items():
    a = np.asarray(Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")).astype(np.int16)
    sub = a[y0:y1, x0:x1]
    R, G, B = sub[..., 0], sub[..., 1], sub[..., 2]
    rgb = Image.fromarray(sub.astype(np.uint8))
    rgb.resize((rgb.width*4, rgb.height*4), Image.LANCZOS).save(os.path.join(OUT, name + "_win_rgb.png"))
    for tag, m in (
        ("t1", (R < 100) & (G > 190) & (B < 210)),          # 宽松：绿文字
        ("t2", (G.astype(np.int32) - B.astype(np.int32)) > 60),  # 绿多于蓝
        ("t3", (G.astype(np.int32) - R.astype(np.int32)) > 120) & (B > 60),
    ):
        img = Image.fromarray(255 - m.astype(np.uint8)*255)
        img.resize((img.width*4, img.height*4), Image.LANCZOS).save(os.path.join(OUT, f"{name}_win_{tag}.png"))
        print(f"{name} {tag}: 命中 {int(m.sum())}px")
    print(f"{name}: 窗口 {x1-x0}x{y1-y0}  底色均值 R{sub[...,0].mean():.0f} G{sub[...,1].mean():.0f} B{sub[...,2].mean():.0f}")
