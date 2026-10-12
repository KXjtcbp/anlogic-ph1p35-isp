# -*- coding: utf-8 -*-
# 算法状态行是 "MODE n" 共 6 个字符（hdmi_mixer.v:1009 第5位是空格，:1010 第6位是数字）。
# 这里把每张照片那行的"最后两个字符位（空格+数字）"抠出来放大 8 倍，用于目视读数字。
import os
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"
# name: 该行 6 个字符的 bbox (x0, x1, y0, y1)，原生像素
bbox = {
    "IMG_20261006_192101": (861, 1198, 913, 952),    # 实测掩膜 bbox
    "IMG_20261006_192138": (934, 1263, 1105, 1141),  # 实测掩膜 bbox
    "IMG_20261006_192107": (861, 1165, 955, 1005),   # 估
    "IMG_20261006_192127": (1625, 1896, 835, 885),   # 估
    "IMG_20261006_192131": (1043, 1409, 1020, 1075), # 估
}
for name, (x0, x1, y0, y1) in bbox.items():
    a = np.asarray(Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")).astype(np.int16)
    w = x1 - x0
    # 最后 2 个字符位 = 右边 2/6
    cx0 = x0 + int(w * 4.0 / 6.0) - 8
    sub = a[y0:y1, cx0:x1]
    rgb = Image.fromarray(sub.astype(np.uint8))
    rgb.resize((rgb.width*8, rgb.height*8), Image.LANCZOS).save(os.path.join(OUT, name + "_digit_rgb.png"))
    # 绿色文字强度图：G - (R+B)/2
    R, G, B = sub[..., 0], sub[..., 1], sub[..., 2]
    d = G - (R + B) / 2.0
    d = np.clip((d - d.min()) / max(1.0, d.max() - d.min()) * 255, 0, 255).astype(np.uint8)
    im2 = Image.fromarray(d)
    im2.resize((im2.width*8, im2.height*8), Image.LANCZOS).save(os.path.join(OUT, name + "_digit_g.png"))
    print(f"{name}: 源裁剪 x[{cx0},{x1}] y[{y0},{y1}] = {sub.shape[1]}x{sub.shape[0]}  绿强度 max={d.max()} mean={d.mean():.0f}")
