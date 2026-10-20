# -*- coding: utf-8 -*-
"""判定两张图是否"同构图"：位移搜索 + 梯度相关 + 多尺度搜索。
若同一画面只是过了曲线，则零位移处的（梯度）相关应接近 1。
"""
import numpy as np
from PIL import Image

DARK = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-36.png"
BRIGHT = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png"

def y_of(p, scale=4):
    im = Image.open(p).convert("RGB")
    w, h = im.size
    im = im.resize((w // scale, h // scale), Image.BOX)
    a = np.asarray(im).astype(np.float64)
    return (77 * a[:, :, 0] + 150 * a[:, :, 1] + 29 * a[:, :, 2]) / 256.0

d = y_of(DARK)
b = y_of(BRIGHT)
print("downscaled shape", d.shape)

def ncc(x, y):
    x = x - x.mean(); y = y - y.mean()
    dx = np.sqrt((x * x).sum()); dy = np.sqrt((y * y).sum())
    return float((x * y).sum() / (dx * dy + 1e-9))

H, W = d.shape
def shift_corr(a, b, maxs=25):
    best = (-2, 0, 0)
    h, w = H - 2 * maxs, W - 2 * maxs
    ref = b[maxs:maxs + h, maxs:maxs + w]
    for dy in range(-maxs, maxs + 1):
        for dx in range(-maxs, maxs + 1):
            cand = a[maxs + dy:maxs + dy + h, maxs + dx:maxs + dx + w]
            c = ncc(ref, cand)
            if c > best[0]:
                best = (c, dx, dy)
    return best

# 1) 原始 Y 的零位移相关与位移搜索
print("Y   raw   zero-shift NCC = %.4f" % ncc(d[25:-25, 25:-25], b[25:-25, 25:-25]))
print("Y   raw   best shift     = %.4f at dx=%d dy=%d" % shift_corr(d, b))

# 2) 高通（去 DC/雾）后再比：减去 9x9 均值
def hp(a, k=9):
    from PIL import ImageFilter
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    return a - np.asarray(im.filter(ImageFilter.BoxBlur(k))).astype(np.float64)

dh, bh = hp(d), hp(b)
print("HP  zero-shift NCC = %.4f" % ncc(dh[25:-25, 25:-25], bh[25:-25, 25:-25]))
print("HP  best shift     = %.4f at dx=%d dy=%d" % shift_corr(dh, bh))

# 3) 梯度方向相关（边缘图）
gd = np.abs(np.gradient(d)[0]) + np.abs(np.gradient(d)[1])
gb = np.abs(np.gradient(b)[0]) + np.abs(np.gradient(b)[1])
print("GRAD zero-shift NCC = %.4f" % ncc(gd[25:-25, 25:-25], gb[25:-25, 25:-25]))
print("GRAD best shift     = %.4f at dx=%d dy=%d" % shift_corr(gd, gb))

# 4) 多尺度：把亮图按比例缩放后再相关（看是否只是"缩放/裁剪"关系）
im_b = Image.open(BRIGHT).convert("L")
for s in (0.7, 0.8, 0.9, 1.0, 1.1, 1.25, 1.4):
    w, h = im_b.size
    im2 = im_b.resize((int(w * s / 4), int(h * s / 4)), Image.BOX)
    a2 = np.asarray(im2).astype(np.float64)
    hh = min(d.shape[0], a2.shape[0]) - 50
    ww = min(d.shape[1], a2.shape[1]) - 50
    c = ncc(d[25:25 + hh, 25:25 + ww], a2[25:25 + hh, 25:25 + ww])
    print("scale %.2f  NCC = %+.4f" % (s, c))

# 5) 局部对比度（标准差）对照：整幅 + 同样大小的中心块
for nm, a in (("DARK", d), ("BRIGHT", b)):
    c = a[100:170, 100:250]
    print("%s: Y mean %.2f  std %.2f | 中心块 mean %.2f std %.2f" %
          (nm, a.mean(), a.std(), c.mean(), c.std()))
