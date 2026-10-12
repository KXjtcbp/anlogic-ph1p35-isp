# -*- coding: utf-8 -*-
import os
import numpy as np
from PIL import Image
SRC, OUT = r"E:\FPGA", r"E:\FPGA\_analysis"
for nm in ["mode0室内常光","mode3室内常光","mode0盖住镜头"]:
    a = np.asarray(Image.open(os.path.join(SRC, nm+".jpg")).convert("RGB")).astype(np.int16)
    H, W, _ = a.shape
    R, G, B = a[...,0], a[...,1], a[...,2]
    m = (G > R+20) & (G > B+20) & (G > 60)
    m[:, int(W*0.30):] = False
    m[int(H*0.5):, :] = False
    ys, xs = np.where(m)
    if len(ys) < 30:
        print(nm, "绿字太少", len(ys)); continue
    y0,y1 = max(0,ys.min()-10), min(H,ys.max()+10)
    x0,x1 = max(0,xs.min()-10), min(W,xs.max()+10)
    print(f"{nm}: {len(ys)}px bbox x[{xs.min()},{xs.max()}] y[{ys.min()},{ys.max()}] crop {x1-x0}x{y1-y0}")
    c = np.asarray(Image.open(os.path.join(SRC, nm+".jpg")).convert("RGB"))[y0:y1, x0:x1]
    im = Image.fromarray(c)
    im.resize((im.width*8, im.height*8), Image.LANCZOS).save(os.path.join(OUT, nm+"_moderow2.png"))
