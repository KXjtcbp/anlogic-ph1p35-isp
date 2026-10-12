# -*- coding: utf-8 -*-
"""把 10 号（曲线旁路）的 percentile 过一遍 p160_a050 真值表，
看能不能预测出 11 号（曲线启用）的 percentile —— 决定性验证。"""
import re, sys, os
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GAMMA = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
A = r"E:\FPGA\captures\2026-10-11_S曲线AB验证\10_SW1上_SW2下_曲线旁路_CNT574558.png"
B = r"E:\FPGA\captures\2026-10-11_S曲线AB验证\11_SW1上_SW2上_曲线启用_CNT574725.png"


def load_lut():
    txt = open(GAMMA, encoding="utf-8", errors="replace").read()
    t = {int(m.group(1)): int(m.group(2), 16)
         for m in re.finditer(r"mem_b00\[\s*(\d+)\]\s*=\s*8'h([0-9a-fA-F]{1,2})", txt)}
    assert len(t) == 256
    return np.array([t[i] for i in range(256)], np.int32)


def osd_mask(w, h):
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def lum(a):
    return (77 * a[:, :, 0].astype(np.int32) + 150 * a[:, :, 1].astype(np.int32)
            + 29 * a[:, :, 2].astype(np.int32)) >> 8


lut = load_lut()
ia = np.asarray(Image.open(A).convert("RGB"))
ib = np.asarray(Image.open(B).convert("RGB"))
m = osd_mask(*ia.shape[1::-1])
Ya, Yb = lum(ia)[m], lum(ib)[m]

print("LUT p160_a050 truth table (isp_gamma.v mem_b00):")
print("   x  -> y :", ", ".join("%d->%d" % (x, lut[x]) for x in [0, 1, 2, 3, 4, 8, 16, 32, 64, 96, 128, 160, 200, 255]))
print()
pcts = [0.1, 1, 5, 10, 25, 50, 75, 90, 95, 99, 99.9]
print("percentile | #10 bypass | LUT(#10) | #11 curve ON | delta")
print("-" * 66)
for p in pcts:
    xa = int(round(np.percentile(Ya, p)))
    pred = int(lut[xa])
    xb = int(round(np.percentile(Yb, p)))
    print("   p%-6s |    %4d    |   %4d   |     %4d     | %+d" % (p, xa, pred, xb, xb - pred))
print()
print("mean       |  %7.2f   |  %7.2f  |   %7.2f    | %+.2f" % (
    Ya.mean(), lut[np.clip(Ya, 0, 255)].mean(), Yb.mean(),
    Yb.mean() - lut[np.clip(Ya, 0, 255)].mean()))
print("std        |  %7.2f   |  %7.2f  |   %7.2f    | %+.2f" % (
    Ya.std(), lut[np.clip(Ya, 0, 255)].std(), Yb.std(),
    Yb.std() - lut[np.clip(Ya, 0, 255)].std()))
print()
print("=== per-channel frame means (post-AWB) ===")
for nm, arr in (("10 bypass", ia), ("11 curve", ib)):
    px = arr[m]
    R, G, Bc = px[:, 0].mean(), px[:, 1].mean(), px[:, 2].mean()
    print("  %-10s R=%6.2f G=%6.2f B=%6.2f  R/G=%.4f B/G=%.4f" % (nm, R, G, Bc, R / G, Bc / G))
print()
print("=== histogram occupancy (luminance) ===")
for nm, Y in (("10 bypass", Ya), ("11 curve ", Yb)):
    h = np.bincount(Y.ravel(), minlength=256)
    nz = np.nonzero(h)[0]
    print("  %s codes used %d/256, range %d..%d, %%==0 -> %.3f%%, %%<=8 -> %.3f%%, %%>=250 -> %.3f%%" % (
        nm, len(nz), nz[0], nz[-1], 100.0 * h[0] / h.sum(),
        100.0 * h[:9].sum() / h.sum(), 100.0 * h[250:].sum() / h.sum()))
print()
print("=== scene crop (x 560..1160, y 380..780) ===")
for nm, arr in (("10 bypass", ia), ("11 curve ", ib)):
    c = arr[380:780, 560:1160]
    Y = lum(c)
    print("  %s Ymean=%7.3f Ystd=%6.3f" % (nm, Y.mean(), Y.std()))

# OSD crop
print()
os.makedirs(r"E:\FPGA\_analysis\out", exist_ok=True)
tiles = []
for f in (A, B):
    im = Image.open(f).convert("RGB")
    t = im.crop((540, 150, 900, 228)).resize((1080, 234), Image.NEAREST)
    tiles.append(t)
    t2 = im.crop((240, 240, 645, 300)).resize((1215, 180), Image.NEAREST)
    tiles.append(t2)
W = max(t.width for t in tiles)
H = sum(t.height for t in tiles)
sheet = Image.new("RGB", (W, H), (20, 20, 20))
y = 0
for t in tiles:
    sheet.paste(t, (0, y)); y += t.height
sheet.save(r"E:\FPGA\_analysis\out\osd_ab_sw2.png")
print("saved E:\\FPGA\\_analysis\\out\\osd_ab_sw2.png (%dx%d)" % sheet.size)
