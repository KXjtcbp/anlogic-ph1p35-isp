#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""[HDR-2026-10-10] 结构分析：判断新采图是"真实场景"还是"传感器测试图/纯梯度"。

用法: python diag_struct.py 图1 [图2 ...]
"""
import sys
import numpy as np
from PIL import Image

OSD_BOXES = [(0, 0, 250, 250), (555, 170, 870, 225), (258, 258, 398, 285)]


def load(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.int32)
    m = np.ones(a.shape[:2], bool)
    for (x0, y0, x1, y1) in OSD_BOXES:
        if x1 <= a.shape[1] and y1 <= a.shape[0]:
            m[y0:y1, x0:x1] = False
    luma = (77 * a[:, :, 0] + 150 * a[:, :, 1] + 29 * a[:, :, 2]) >> 8
    return a, m, luma


def report(path):
    a, m, luma = load(path)
    lm = luma.astype(np.float64)
    lm[~m] = np.nan
    v = luma[m]
    print('=' * 100)
    print('%s   (%dx%d)' % (path, a.shape[1], a.shape[0]))
    print('  luma: mean=%.2f  p10=%.0f p50=%.0f p90=%.0f p99=%.0f max=%d  唯一值=%d' %
          (v.mean(), *[np.percentile(v, q) for q in (10, 50, 90, 99)], v.max(),
           len(np.unique(v))))

    # 行内/列内是否恒定（测试图/合成渐变的特征）
    row_const = np.mean([len(np.unique(lm[y][~np.isnan(lm[y])])) <= 2 for y in range(0, 1080, 8)])
    col_const = np.mean([len(np.unique(lm[:, x][~np.isnan(lm[:, x])])) <= 2 for x in range(0, 1920, 8)])
    print('  行内近似恒定比例=%.2f   列内近似恒定比例=%.2f  (测试图/合成梯度会接近 1.0)' %
          (row_const, col_const))

    # 纹理：拉普拉斯绝对值均值
    c = luma[200:1000, 300:1800].astype(np.float64)
    lap = np.abs(4 * c[1:-1, 1:-1] - c[:-2, 1:-1] - c[2:, 1:-1] - c[1:-1, :-2] - c[1:-1, 2:])
    print('  拉普拉斯|·|均值=%.3f   相邻像素差|·|均值=%.3f' %
          (lap.mean(), np.abs(np.diff(c, axis=1)).mean()))

    # 列剖面（每 128 列取列均值）与行剖面
    colp = np.nanmean(lm[:, :], axis=0)
    rowp = np.nanmean(lm[:, :], axis=1)
    print('  列均值剖面(每128列): ' + ' '.join('%.0f' % colp[i] for i in range(0, 1920, 128)))
    print('  行均值剖面(每108行): ' + ' '.join('%.0f' % rowp[i] for i in range(0, 1080, 108)))

    # 12x12 分块均值网格
    gh, gw = 1080 // 12, 1920 // 12
    grid = np.nanmean(lm[:gh * 12, :gw * 12].reshape(12, gh, 12, gw), axis=(1, 3))
    print('  12x12 分块均值网格:')
    for r in grid:
        print('    ' + ' '.join('%4.0f' % x for x in r))


if __name__ == '__main__':
    for p in sys.argv[1:]:
        report(p)
