#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""[HDR-2026-10-10] 采集图定量对比：相机区（全帧去 OSD）通道均值/分位/过曝/中性/彩度。

用法: python diag_new.py 图1 图2 ...
"""
import sys
import numpy as np
from PIL import Image

# OSD 框（1920x1080 采集坐标，来自 hdmi_mixer.v 三层窗口 x1.5）
OSD_BOXES = [(0, 0, 250, 250), (555, 170, 870, 225), (258, 258, 398, 285)]


def load_cam(path):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.int16)
    if a.shape[0] != 1080 or a.shape[1] != 1920:
        # 非 1920x1080：整幅当相机区，仅裁掉明显的 OSD 行
        pass
    m = np.ones(a.shape[:2], bool)
    for (x0, y0, x1, y1) in OSD_BOXES:
        if x1 <= a.shape[1] and y1 <= a.shape[0]:
            m[y0:y1, x0:x1] = False
    return a, m


def report(path):
    a, m = load_cam(path)
    px = a[m]
    R, G, B = px[:, 0], px[:, 1], px[:, 2]
    luma = (77 * R + 150 * G + 29 * B) >> 8
    sat = px.max(axis=1) - px.min(axis=1)
    neutral = (R == G) & (G == B)
    over = (R >= 255) & (G >= 255) & (B >= 255)
    print('=' * 96)
    print('%s  (%dx%d)' % (path, a.shape[1], a.shape[0]))
    print('  R/G/B 均值  : %.2f / %.2f / %.2f      R-G %+.2f   B-G %+.2f' %
          (R.mean(), G.mean(), B.mean(), R.mean() - G.mean(), B.mean() - G.mean()))
    print('  luma 均值   : %.2f   p50=%.0f p90=%.0f p99=%.0f p99.9=%.0f max=%d' %
          (luma.mean(), np.percentile(luma, 50), np.percentile(luma, 90),
           np.percentile(luma, 99), np.percentile(luma, 99.9), luma.max()))
    print('  通道 max    : R=%d G=%d B=%d' % (R.max(), G.max(), B.max()))
    print('  过曝(255)   : %.4f%%   几乎全黑(<=1): %.2f%%   严格中性: %.2f%%' %
          (100.0 * over.mean(), 100.0 * (luma <= 1).mean(), 100.0 * neutral.mean()))
    print('  彩度max-min : 均值 %.2f  p50=%.0f p99=%.0f max=%d   >=3 占 %.2f%%' %
          (sat.mean(), np.percentile(sat, 50), np.percentile(sat, 99), sat.max(),
           100.0 * (sat >= 3).mean()))
    print('  不同码值数  : R=%d G=%d B=%d    奇数值占比 %.1f%%' %
          (len(np.unique(R)), len(np.unique(G)), len(np.unique(B)),
           100.0 * (R % 2 == 1).mean()))


if __name__ == '__main__':
    for p in sys.argv[1:]:
        report(p)
