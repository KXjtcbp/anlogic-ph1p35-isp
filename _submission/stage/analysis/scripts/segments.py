# -*- coding: utf-8 -*-
# 逐张照片做两件事：
#  (1) 客观"灰度"统计：屏幕中部采样区的平均饱和度、强饱和像素占比、亮度均值/极值
#  (2) 把水平方向分割成"颜色段"（相邻采样色差 < 门限视为同一段），输出每段的 x 区间与平均 RGB
# 注意：所有数值都是"显示器+手机相机"这个系统后的值，不能当传感器码值用。
import os, glob
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"

def cname(r, g, b):
    mx, mn = max(r, g, b), min(r, g, b)
    if mx < 8: return "黑"
    sat = (mx - mn) / mx
    if sat < 0.15: return "灰/白" if mx > 110 else "暗灰"
    if mx == r and mx == g: return "黄"
    if mx == r and mx == b: return "品红"
    if mx == g and mx == b: return "青"
    if mx == r: return "红"
    if mx == g: return "黄绿" if (g - r) < 100 else "绿"
    return "蓝"

rows = []
for f in sorted(glob.glob(os.path.join(SRC, "IMG_20261006_*.jpg"))):
    name = os.path.splitext(os.path.basename(f))[0]
    a = np.asarray(Image.open(f).convert("RGB")).astype(np.int16)
    H, W = a.shape[:2]
    # 采样区：屏幕中部横带 y 0.46~0.66，x 6%~97%（避开左边框与机身）
    yy0, yy1 = int(0.46*H), int(0.66*H)
    x0, x1 = int(0.06*W), int(0.97*W)
    band = a[yy0:yy1, x0:x1].astype(np.float64)
    mx = band.max(axis=2); mn = band.min(axis=2)
    sat = np.where(mx > 1, (mx - mn) / np.maximum(mx, 1), 0.0)
    strong = (mn > 0) & ((mx - mn) > 60) & (mx > 60)     # 明显有彩色
    print("=" * 78)
    print(f"{name}   采样区 {x1-x0}x{yy1-yy0}px")
    print(f"  亮度均值 {band.mean():6.1f}   亮度 p5 {np.percentile(band.mean(axis=2),5):5.1f}   p95 {np.percentile(band.mean(axis=2),95):5.1f}")
    print(f"  色度 (max-min) 均值 {np.mean(mx-mn):6.1f}   中位 {np.median(mx-mn):6.1f}   最大 {np.max(mx-mn):6.0f}")
    print(f"  平均饱和度 {sat.mean():5.3f}   饱和>0.6 的像素占比 {100*np.mean(sat>0.6):5.1f}%   强彩色像素占比 {100*strong.mean():5.1f}%")
    # 分段
    step = max(1, (x1 - x0) // 160)
    prof = []
    for x in range(x0, x1, step):
        blk = a[yy0:yy1, x:x+step].reshape(-1, 3).mean(axis=0)
        prof.append((x, blk))
    segs = []
    cur = [prof[0]]
    for x, c in prof[1:]:
        ref = np.mean([p[1] for p in cur], axis=0)
        if np.abs(c - ref).max() > 28 or len(cur) > 20:
            segs.append(cur); cur = [(x, c)]
        else:
            cur.append((x, c))
    segs.append(cur)
    print("  水平分段（左→右）：")
    for seg in segs:
        xs = [p[0] for p in seg]
        c = np.mean([p[1] for p in seg], axis=0)
        frac0, frac1 = 100.0*(xs[0]-x0)/(x1-x0), 100.0*(xs[-1]+step-x0)/(x1-x0)
        if frac1 - frac0 < 1.2:
            continue
        print(f"    x {frac0:5.1f}%~{frac1:5.1f}%  ({frac1-frac0:4.1f}% 宽)  RGB=({c[0]:5.0f},{c[1]:5.0f},{c[2]:5.0f})  亮度{c.max():5.0f}  {cname(c[0],c[1],c[2])}")
        rows.append((name, round(frac0,1), round(frac1,1), int(c[0]), int(c[1]), int(c[2]), cname(c[0],c[1],c[2])))

with open(os.path.join(OUT, "segments.md"), "w", encoding="utf-8") as fp:
    fp.write("| 照片 | x起% | x止% | R | G | B | 判色 |\n|---|---|---|---|---|---|---|\n")
    for r in rows:
        fp.write("| " + " | ".join(str(v) for v in r) + " |\n")
print("\n已写 E:\\FPGA\\_analysis\\docs\\segments.md")
