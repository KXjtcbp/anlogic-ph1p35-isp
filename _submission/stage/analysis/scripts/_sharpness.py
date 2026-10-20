# -*- coding: utf-8 -*-
"""1:1 裁切 + 锐度/噪声指标：判断"糊成一团"是偏色、低对比，还是真的糊。"""
import os, sys
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'E:\FPGA'
TAG = 'Screenshot 2026-10-11 %s.png'


def laplacian_var(g):
    k = np.array([[0, 1, 0], [1, -4, 1], [0, 1, 0]], float)
    from numpy.lib.stride_tricks import sliding_window_view
    w = sliding_window_view(g, (3, 3))
    return float((w * k).sum(axis=(-1, -2)).var())


for name, box in [('17-00-21', (560, 380, 1160, 780)), ('17-00-42', (560, 380, 1160, 780)),
                  ('17-00-12', (560, 380, 1160, 780))]:
    p = os.path.join(ROOT, TAG % name)
    im = Image.open(p).convert('RGB')
    a = np.asarray(im).astype(np.float64)
    Y = (77 * a[:, :, 0] + 150 * a[:, :, 1] + 29 * a[:, :, 2]) / 256.0
    x0, y0, x1, y1 = box
    crop = a[y0:y1, x0:x1]
    g = Y[y0:y1, x0:x1]
    # 平坦块（取最平坦的 64x64）算噪声
    best = None
    for yy in range(0, g.shape[0] - 64, 32):
        for xx in range(0, g.shape[1] - 64, 32):
            s = g[yy:yy + 64, xx:xx + 64].std()
            if best is None or s < best[0]:
                best = (s, xx, yy)
    print('%-10s crop Ymean=%6.2f  Ystd=%6.2f  LapVar=%8.2f  flattest64_std=%5.3f@%s  max=%d'
          % (name, g.mean(), g.std(), laplacian_var(g), best[0], (best[1], best[2]), int(g.max())))
    Image.fromarray(crop.astype(np.uint8)).save(os.path.join(ROOT, r'_analysis\out\crop_%s.png' % name.replace('-', '')))
    print('           saved _analysis/out/crop_%s.png' % name.replace('-', ''))

# 三张 best-exposed 的 1:1 拼版（左上角 400x260 各一块）
ims = []
for name in ['17-00-21', '17-00-42', '17-00-12']:
    a = np.asarray(Image.open(os.path.join(ROOT, TAG % name)).convert('RGB'))
    ims.append(a[380:640, 560:960])
out = np.concatenate(ims, axis=0)
Image.fromarray(out).save(os.path.join(ROOT, r'_analysis\out\crop_stack_1to1.png'))
print('saved _analysis/out/crop_stack_1to1.png', out.shape)
