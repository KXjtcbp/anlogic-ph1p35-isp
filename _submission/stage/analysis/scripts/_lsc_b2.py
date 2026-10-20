# -*- coding: utf-8 -*-
"""第二批 SW1 对照（2026-10-14 20:32:50~20:33:15，4 张）。
   用 AWB 的 W 增益指纹 + 逐列 R/G 形状，判定每张的 LSC 状态并做关/开比值。"""
import os
import re
import sys
import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"; INB = os.path.join(WS, "inbox"); OUT = os.path.join(WS, "_analysis", "out")
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")

FILES = sorted([f for f in os.listdir(INB) if f.startswith("Screenshot 2026-10-14 20-3")])

src = open(os.path.join(HDL, "isp", "lsc.v"), "rb").read().decode("utf-8", errors="replace")
kR = np.zeros((12, 20), np.int32); kB = np.zeros((12, 20), np.int32)
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", src):
    kR[int(m.group(3)), int(m.group(4))] = int(m.group(5))
    kB[int(m.group(3)), int(m.group(4))] = int(m.group(6))


def mask(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


def smooth(v, win=21):
    k = np.ones(win) / win
    return np.convolve(np.pad(v, (win // 2, win // 2), mode="edge"), k, mode="valid")


def colprof(a, ch, y0=300, y1=800, x0=96, x1=1824):
    h, w, _ = a.shape
    m = mask(h, w)
    band = np.zeros_like(m); band[y0:y1, :] = True
    sel = m & band
    out = []
    for x in range(x0, x1):
        s = sel[:, x]
        g = a[:, x, 1][s].mean() if s.sum() >= 50 else 0.0
        out.append(a[:, x, ch][s].mean() / g if g > 1e-6 else np.nan)
    return np.array(out)


imgs = {}
print("=== 场景与整帧统计 ===")
for f in FILES:
    a = np.asarray(Image.open(os.path.join(INB, f)).convert("RGB")).astype(np.float64)
    imgs[f] = a
    h, w, _ = a.shape
    m = mask(h, w)
    Y = (77*a[...,0] + 150*a[...,1] + 29*a[...,2]) / 256.0
    R, G, B = a[...,0][m], a[...,1][m], a[...,2][m]
    pr = colprof(a, 0); pb = colprof(a, 2)
    xramp = [Y[300:800, x][m[300:800, x]].mean() for x in range(96, 1824, 288)]
    print("  %s" % f)
    print("     Y=%.2f std=%.2f p1=%d p50=%d p99=%d | x向Y %s" %
          (Y[m].mean(), Y[m].std(), np.percentile(Y[m],1), np.percentile(Y[m],50), np.percentile(Y[m],99),
           " ".join("%.0f" % v for v in xramp)))
    print("     R/G=%.4f B/G=%.4f R-G=%+.2f | 逐列R/G极差=%.4f 逐列B/G极差=%.4f" %
          (R.mean()/G.mean(), B.mean()/G.mean(), R.mean()-G.mean(),
           np.nanmax(smooth(pr))-np.nanmin(smooth(pr)), np.nanmax(smooth(pb))-np.nanmin(smooth(pb))))

# 遥测 + CNT 拼图
tele = []; cnt = []
for f in FILES:
    im = Image.open(os.path.join(INB, f)).convert("RGB")
    tele.append(im.crop((540, 215, 1030, 265)).resize((1470, 150), Image.LANCZOS))
    cnt.append(im.crop((540, 155, 920, 215)).resize((1520, 240), Image.NEAREST))
for arr, nm, hh in ((tele, "b2_4tele.png", 168), (cnt, "b2_4cnt.png", 258)):
    sh = Image.new("RGB", (arr[0].width, len(arr)*hh), (20, 20, 20))
    d = ImageDraw.Draw(sh)
    for i, c in enumerate(arr):
        sh.paste(c, (0, i*hh + 18)); d.text((4, i*hh + 4), FILES[i][-9:-4], fill=(255, 255, 0))
    sh.save(os.path.join(OUT, nm)); print("saved", nm)

sh = Image.new("RGB", (1280, 740), (25, 25, 25)); d = ImageDraw.Draw(sh)
for i, f in enumerate(FILES):
    im = Image.open(os.path.join(INB, f)).convert("RGB").resize((640, 360), Image.LANCZOS)
    x = (i % 2)*640; y = (i//2)*370
    sh.paste(im, (x, y+20)); d.text((x+6, y+4), FILES[i][-9:-4], fill=(255, 255, 0))
sh.save(os.path.join(OUT, "b2_4up.png")); print("saved b2_4up.png")

# 关/开比值：按时间序两两配 (1,2) 与 (3,4)
h, w, _ = imgs[FILES[0]].shape
m = mask(h, w); band = np.zeros_like(m); band[300:800, :] = True; sel = m & band
for pi, (ia, ib) in enumerate(((0, 1), (2, 3))):
    A = imgs[FILES[ia]]; B = imgs[FILES[ib]]
    ra_g = A[...,0].mean()/A[...,1].mean(); rb_g = B[...,0].mean()/B[...,1].mean()
    print("\n=== 候选配对 %d:  %s (A) vs %s (B) ===" % (pi+1, FILES[ia][-9:-4], FILES[ib][-9:-4]))
    print("   整帧 R/G: A=%.4f B=%.4f  (B/A=%.4f)" % (ra_g, rb_g, rb_g/ra_g))
    ks = []
    for iy in range(12):
        ys = (iy*64 + 32)*1080//720
        y0, y1 = max(300, ys-40), min(800, ys+40)
        if y1-y0 < 20: continue
        for ix in range(20):
            x0, x1 = ix*96, min((ix+1)*96, 1824)
            s = sel[y0:y1, x0:x1]
            if s.sum() < 200: continue
            ra = A[...,0][y0:y1,x0:x1][s].mean()/A[...,1][y0:y1,x0:x1][s].mean()
            rb = B[...,0][y0:y1,x0:x1][s].mean()/B[...,1][y0:y1,x0:x1][s].mean()
            if kR[iy, ix] >= 20: ks.append((kR[iy,ix], 1024*(rb/ra - 1)))
    ks = np.array(ks)
    q = ks[:,1]/ks[:,0]
    print("   节点数 %d，实测等效k/表k：中位数 %.3f 四分位 [%.3f, %.3f]" %
          (len(ks), np.median(q), np.percentile(q,25), np.percentile(q,75)))
    print("   拟合 eff_k = a*k + b : ", end="")
    a1, b1 = np.polyfit(ks[:,0], ks[:,1], 1)
    print("a=%.3f  b=%+.1f" % (a1, b1))
