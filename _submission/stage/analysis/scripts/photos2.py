# -*- coding: utf-8 -*-
# 第 1 轮三张照片的量化：以 OSD 亮黄文字为"已知码值 255 的参考电平"，
# 反推画面在显示器+手机链路下的等效码值；并对 MODE3 做色相分类（5 档亮度区间）。
import os
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"
os.makedirs(OUT, exist_ok=True)
names = ["mode0室内常光", "mode3室内常光", "mode0盖住镜头"]

for nm in names:
    p = os.path.join(SRC, nm + ".jpg")
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    H, W, _ = a.shape
    Ra, Ga, Ba = a[..., 0], a[..., 1], a[..., 2]

    # 屏幕区：避开顶部墙面/木柜，避开 OSD 行（OSD 在 y≈0.30~0.35）
    y0, y1, x0, x1 = int(H*0.40), int(H*0.95), int(W*0.02), int(W*0.98)
    sub = a[y0:y1, x0:x1]
    R, G, B = sub[..., 0], sub[..., 1], sub[..., 2]
    luma = 0.299*R + 0.587*G + 0.114*B

    m_ref = (Ra > 140) & (Ga > 140) & (Ba < 110)
    if m_ref.sum() > 200:
        ref = float(np.mean(0.299*Ra[m_ref] + 0.587*Ga[m_ref] + 0.114*Ba[m_ref]))
    else:
        ref = float("nan")

    print(f"--- {nm}  ({os.path.getsize(p)} B) ---")
    print(f"  屏幕区 {sub.shape[1]}x{sub.shape[0]}px  RGB均值=({R.mean():.1f},{G.mean():.1f},{B.mean():.1f})")
    print(f"  luma 均值={luma.mean():.1f}  p5/p25/p50/p75/p95={np.percentile(luma,[5,25,50,75,95]).round(1)}")
    print(f"  OSD 亮黄参考 {int(m_ref.sum())} px, 参考 luma={ref:.1f}（板端名义 255）")
    if ref == ref:
        for lbl, v in (("均值", luma.mean()), ("p50", np.percentile(luma, 50)), ("p95", np.percentile(luma, 95))):
            print(f"    按 gamma=2.2 反推：画面{lbl} ≈ {255*(v/ref)**(1/2.2):.1f}/255   (线性模型 {255*v/ref:.1f})")

    tot = sub.shape[0]*sub.shape[1]
    mx, mn = sub.max(2), sub.min(2)
    dark = mx < 90
    nd = ~dark
    blue = nd & (B >= R) & (B >= G)
    green = nd & (G > R) & (G >= B)
    yellow = nd & (R > B) & (G > B) & (np.abs(R - G) < 80)
    red = nd & (R > G) & (R > B) & ~yellow
    print(f"  色相粗分(%)：暗 {100*dark.sum()/tot:.1f} | 蓝 {100*blue.sum()/tot:.1f} | 绿 {100*green.sum()/tot:.1f} | 黄 {100*yellow.sum()/tot:.1f} | 红 {100*red.sum()/tot:.1f}   色度均值={(mx-mn).mean():.1f}")

    # 抠 OSD 两行文字放大（MODE 行 + CNT 行）
    for tag, (yy0, yy1) in (("moderow", (int(H*0.28), int(H*0.37))), ("cntrow", (int(H*0.19), int(H*0.28)))):
        c = a[yy0:yy1, int(W*0.02):int(W*0.60)].astype(np.uint8)
        im = Image.fromarray(c)
        im.resize((im.width*3, im.height*3), Image.LANCZOS).save(os.path.join(OUT, f"{nm}_{tag}.png"))
print("done")
