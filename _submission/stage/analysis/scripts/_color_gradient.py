# -*- coding: utf-8 -*-
"""色彩偏色空间分布诊断：per-row / per-column 的 R/G、B/G 剖面。
用来判断 AWB 增益是"每行重置后逐拍爬升"（⇒ 左右渐变）
还是"每帧重置后逐行爬升"（⇒ 上下渐变）。
"""
import os, sys
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'E:\FPGA'
SHOTS = ['17-00-12', '17-00-21', '17-00-30', '17-00-42', '17-01-49']

# OSD 三块（按 1280 宽设计，实际 1920 → 缩放 1.5）
OSD = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]


def load(name):
    p = os.path.join(ROOT, 'Screenshot 2026-10-11 %s.png' % name)
    im = Image.open(p).convert('RGB')
    return np.asarray(im).astype(np.float64)


def mask2d(w, h):
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in OSD:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def profile(a, axis, lo, hi):
    """axis=0 → 按行剖面（对列区间 [lo:hi] 平均）；axis=1 → 按列剖面（对行区间平均）"""
    sub = a[:, lo:hi, :] if axis == 0 else a[lo:hi, :, :]
    R = sub[:, :, 0].mean(axis=1 if axis == 0 else 0)
    G = sub[:, :, 1].mean(axis=1 if axis == 0 else 0)
    B = sub[:, :, 2].mean(axis=1 if axis == 0 else 0)
    return R, G, B


for name in SHOTS:
    a = load(name)
    h, w, _ = a.shape
    print('=' * 104)
    print('### %s   %dx%d' % (name, w, h))

    # ---- 按行（上下）剖面：列取 450..1500，避开 OSD 与画面左右边缘 ----
    R, G, B = profile(a, 0, 450, 1500)
    print('-- per-ROW profile (x in 450..1500), sampling 12 rows --')
    print('   y   :  ' + ' '.join('%7d' % y for y in np.linspace(0, h - 1, 12).astype(int)))
    print('   R/G :  ' + ' '.join('%7.3f' % v for v in R[np.linspace(0, h - 1, 12).astype(int)] / G[np.linspace(0, h - 1, 12).astype(int)]))
    print('   B/G :  ' + ' '.join('%7.3f' % v for v in B[np.linspace(0, h - 1, 12).astype(int)] / G[np.linspace(0, h - 1, 12).astype(int)]))
    print('   G   :  ' + ' '.join('%7.2f' % v for v in G[np.linspace(0, h - 1, 12).astype(int)]))

    # ---- 按列（左右）剖面：行取 400..1000 ----
    R, G, B = profile(a, 1, 400, 1000)
    print('-- per-COL profile (y in 400..1000), sampling 12 cols --')
    print('   x   :  ' + ' '.join('%7d' % x for x in np.linspace(0, w - 1, 12).astype(int)))
    print('   R/G :  ' + ' '.join('%7.3f' % v for v in R[np.linspace(0, w - 1, 12).astype(int)] / G[np.linspace(0, w - 1, 12).astype(int)]))
    print('   B/G :  ' + ' '.join('%7.3f' % v for v in B[np.linspace(0, w - 1, 12).astype(int)] / G[np.linspace(0, w - 1, 12).astype(int)]))
    print('   G   :  ' + ' '.join('%7.2f' % v for v in G[np.linspace(0, w - 1, 12).astype(int)]))

    # ---- 3x3 分块 R/G ----
    print('-- 3x3 block R/G (and B/G) --')
    for by in range(3):
        rowtxt = []
        for bx in range(3):
            blk = a[by * h // 3:(by + 1) * h // 3, bx * w // 3:(bx + 1) * w // 3, :]
            m = mask2d(w, h)[by * h // 3:(by + 1) * h // 3, bx * w // 3:(bx + 1) * w // 3]
            px = blk[m]
            if px.size == 0:
                rowtxt.append('   ---/---   ')
                continue
            r, g, b = px[:, 0].mean(), px[:, 1].mean(), px[:, 2].mean()
            g = max(g, 1e-9)
            rowtxt.append('%6.3f/%5.3f' % (r / g, b / g))
        print('     ' + '  '.join(rowtxt))
