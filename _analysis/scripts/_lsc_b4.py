# -*- coding: utf-8 -*-
"""第三批 SW1 对照（2026-10-14 22:27:36~22:28:00）。含线性域模型预测。"""
import os, re, sys
import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"; INB = os.path.join(WS, "inbox"); OUT = os.path.join(WS, "_analysis", "out")
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")
FILES = sorted([f for f in os.listdir(INB) if f.startswith("Screenshot 2026-10-14 22-3")])
print("本批文件 (%d):" % len(FILES))
for f in FILES: print("   ", f)

g = open(os.path.join(HDL, "isp", "isp_gamma.v"), "rb").read().decode("utf-8", "replace")
LUT = np.zeros(256, np.int32)
for m in re.finditer(r"mem_b00\[\s*(\d+)\s*\]\s*=\s*8'h([0-9a-fA-F]{1,2})", g):
    LUT[int(m.group(1))] = int(m.group(2), 16)
INV = np.zeros(256, np.int32)
for i in range(1, 256): INV[i] = INV[i-1] if LUT[i] == LUT[i-1] else i

kR = np.zeros((12, 20), np.int32); kB = np.zeros((12, 20), np.int32)
s = open(os.path.join(HDL, "isp", "lsc.v"), "rb").read().decode("utf-8", "replace")
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", s):
    kR[int(m.group(3)), int(m.group(4))] = int(m.group(5)); kB[int(m.group(3)), int(m.group(4))] = int(m.group(6))


def mask(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


def smooth(v, win=21):
    k = np.ones(win)/win
    return np.convolve(np.pad(v, (win//2, win//2), mode="edge"), k, mode="valid")


def colprof(a, ch, y0=300, y1=800, x0=96, x1=1824):
    h, w, _ = a.shape; m = mask(h, w)
    band = np.zeros_like(m); band[y0:y1, :] = True; sel = m & band
    o = []
    for x in range(x0, x1):
        ss = sel[:, x]; gg = a[:, x, 1][ss].mean() if ss.sum() >= 50 else 0.0
        o.append(a[:, x, ch][ss].mean()/gg if gg > 1e-6 else np.nan)
    return np.array(o)


def gainmap(h, w):
    bx = (np.arange(w)//4).astype(np.int32); y2 = (np.arange(h)*720//1080).astype(np.int32)
    hidx = np.clip(bx//16, 0, 19); fx = bx % 16; vidx = np.clip(y2//64, 0, 11); fy = (y2 % 64)//4
    h1 = np.minimum(hidx+1, 19); v1 = np.minimum(vidx+1, 11)
    res = {}
    for ch, tab in ((0, kR), (2, kB)):
        a00 = tab[vidx[:, None], hidx[None, :]].astype(np.int32); a10 = tab[vidx[:, None], h1[None, :]].astype(np.int32)
        a01 = tab[v1[:, None], hidx[None, :]].astype(np.int32);  a11 = tab[v1[:, None], h1[None, :]].astype(np.int32)
        FY = fy[:, None]; FX = fx[None, :]
        rv0 = a00 + (((a10-a00)*FY) >> 4); rv1 = a01 + (((a11-a01)*FY) >> 4)
        res[ch] = rv0 + (((rv1-rv0)*FX) >> 4)
    return res


imgs = {}
print("\n=== 场景与整帧统计 ===")
for f in FILES:
    a = np.asarray(Image.open(os.path.join(INB, f)).convert("RGB")).astype(np.int32)
    imgs[f] = a; h, w, _ = a.shape; m = mask(h, w)
    Y = (77*a[...,0]+150*a[...,1]+29*a[...,2])/256.0
    R, G, B = a[...,0][m], a[...,1][m], a[...,2][m]
    pr = smooth(colprof(a, 0)); pb = smooth(colprof(a, 2))
    xr = [Y[300:800, x][m[300:800, x]].mean() for x in range(96, 1824, 288)]
    print("  %s  Y=%.2f std=%.2f | R/G=%.4f B/G=%.4f R-G=%+.2f | 逐列R/G极差=%.4f 逐列B/G极差=%.4f | x向Y %s"
          % (f[-9:-4], Y[m].mean(), Y[m].std(), R.mean()/G.mean(), B.mean()/G.mean(), R.mean()-G.mean(),
             np.nanmax(pr)-np.nanmin(pr), np.nanmax(pb)-np.nanmin(pb), " ".join("%.0f" % v for v in xr)))

tele = []; cnt = []
for f in FILES:
    im = Image.open(os.path.join(INB, f)).convert("RGB")
    tele.append(im.crop((540, 215, 1030, 265)).resize((1470, 150), Image.LANCZOS))
    cnt.append(im.crop((540, 155, 920, 215)).resize((1520, 240), Image.NEAREST))
for arr, nm, hh in ((tele, "b4_4tele.png", 168), (cnt, "b4_4cnt.png", 258)):
    sh = Image.new("RGB", (arr[0].width, len(arr)*hh), (20, 20, 20)); d = ImageDraw.Draw(sh)
    for i, c in enumerate(arr):
        sh.paste(c, (0, i*hh+18)); d.text((4, i*hh+4), FILES[i][-9:-4], fill=(255, 255, 0))
    sh.save(os.path.join(OUT, nm))
sh = Image.new("RGB", (1280, 740), (25, 25, 25)); d = ImageDraw.Draw(sh)
for i, f in enumerate(FILES):
    im = Image.open(os.path.join(INB, f)).convert("RGB").resize((640, 360), Image.LANCZOS)
    x = (i % 2)*640; y = (i//2)*370
    sh.paste(im, (x, y+20)); d.text((x+6, y+4), FILES[i][-9:-4], fill=(255, 255, 0))
sh.save(os.path.join(OUT, "b4_4up.png"))
print("saved b3_4tele.png / b3_4cnt.png / b3_4up.png")

# 配对（按时间 1-2 / 3-4），W 值需人工从图里读；这里只用剖面做线性域模型比对
for pi, (ia, ib) in enumerate(((0, 1), (2, 3))):
    A = imgs[FILES[ia]].astype(np.int32); B = imgs[FILES[ib]].astype(np.int32)
    h, w, _ = A.shape; GM = gainmap(h, w)
    Lin = INV[A]; L2 = Lin.copy()
    for ch in (0, 2):
        v = Lin[..., ch]; K = GM[ch]; L2[..., ch] = np.clip(v + ((v*K) >> 10), 0, 255)
    Sm = LUT[L2]
    pA = smooth(colprof(A, 0)); pB = smooth(colprof(B, 0)); pS = smooth(colprof(Sm, 0))
    print("\n=== 候选配对 %d:  %s(关?) vs %s(开?) ===" % (pi+1, FILES[ia][-9:-4], FILES[ib][-9:-4]))
    for nm, p in (("A", pA), ("B", pB), ("线性域模型(A+表)", pS)):
        print("   %-16s 极差=%.4f 均值=%.4f" % (nm, np.nanmax(p)-np.nanmin(p), np.nanmean(p)))
    print("   形状相关 B vs 模型 = %.4f | B vs A = %.4f | 极差比 B/模型 = %.3f" %
          (np.corrcoef(pB-pB.mean(), pS-pS.mean())[0,1], np.corrcoef(pB-pB.mean(), pA-pA.mean())[0,1],
           (np.nanmax(pB)-np.nanmin(pB))/(np.nanmax(pS)-np.nanmin(pS))))
