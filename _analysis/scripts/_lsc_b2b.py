# -*- coding: utf-8 -*-
"""逐节点：表 k  vs  实测等效 k  vs  AWB 全局增益模型预测。"""
import os, re, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"; INB = os.path.join(WS, "inbox")
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")

src = open(os.path.join(HDL, "isp", "lsc.v"), "rb").read().decode("utf-8", errors="replace")
kRh = np.zeros((12, 20), np.int32); kRc = np.zeros((12, 20), np.int32)
seen = set()
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", src):
    iy, ix = int(m.group(3)), int(m.group(4)); seen.add((iy, ix))
    kRh[iy, ix] = (int(m.group(2), 16) >> 10) & 0x3FF
    kRc[iy, ix] = int(m.group(5))
d = np.abs(kRh - kRc)[np.array(sorted(seen))[:, 0], np.array(sorted(seen))[:, 1]]
print("表项数=%d  注释 kR 与 20bit 高 10 位的最大差 = %d  （0 表示两者一致）" % (len(seen), d.max()))
print("表 kR: min=%d max=%d mean=%.1f" % (kRc.min(), kRc.max(), kRc.mean()))

PAIRS = [(os.path.join(INB, "Screenshot 2026-10-14 20-32-50.png"),
          os.path.join(INB, "Screenshot 2026-10-14 20-33-00.png"), 1.1660, 1.1304),
         (os.path.join(INB, "Screenshot 2026-10-14 20-33-06.png"),
          os.path.join(INB, "Screenshot 2026-10-14 20-33-15.png"), 1.1814, 1.0784)]


def msk(h, w):
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(530, 170, 1030, 305), (250, 255, 400, 290),
                           (0, 35, 215, 175), (575, 35, 810, 100)]:
        m[y0:y1, x0:x1] = False
    return m


for A_f, B_f, Wo, Wn in PAIRS:
    A = np.asarray(Image.open(A_f).convert("RGB")).astype(np.float64)
    B = np.asarray(Image.open(B_f).convert("RGB")).astype(np.float64)
    h, w, _ = A.shape
    m = msk(h, w); band = np.zeros_like(m); band[300:800, :] = True; sel = m & band
    rho = Wn / Wo
    print("\n=== %s(OFF) vs %s(ON)   rho=gR_on/gR_off=%.4f ===" %
          (os.path.basename(A_f)[-9:-4], os.path.basename(B_f)[-9:-4], rho))
    print("   AWB 模型预测 eff_k = %.4f*k %+.1f" % (rho, 1024*(rho-1)))
    print("   k(表)  eff_k(实测)  模型   差")
    rows = []
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
            eff = 1024*(rb/ra - 1)
            mod = rho*kRc[iy, ix] + 1024*(rho-1)
            rows.append((kRc[iy, ix], eff, mod, eff-mod))
    rows.sort()
    for r in rows[::14]:
        print("   %4d   %+8.1f  %+8.1f  %+8.1f" % r)
    a = np.array(rows)
    af, bf = np.polyfit(a[:,0], a[:,1], 1)
    print("   线性拟合: eff_k = %.4f*k %+.1f   (R^2=%.3f)" % (af, bf, np.corrcoef(a[:,0], a[:,1])[0,1]**2))
    print("   残差(实测-模型): 均值 %+.1f 标准差 %.1f" % (a[:,3].mean(), a[:,3].std()))
