#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""[HDR-2026-10-10] 判定列向梯度是否为合成斜坡（线性度 + 每像素步长）。
"""
import numpy as np
from PIL import Image

P = r'E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 21-16-07.png'
Q = r'E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 20-55-54.png'


def ramp_fit(path, tag):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float64)
    # 取中段（避开 OSD 与上下边框）的行平均，得到列剖面
    prof = a[300:900, :, :].mean(axis=(0, 2))
    x = np.arange(1920)
    for (lo, hi) in ((0, 1024), (128, 900), (0, 1920)):
        s = slice(lo, hi)
        c = np.polyfit(x[s], prof[s], 1)
        pred = np.polyval(c, x[s])
        ss_res = ((prof[s] - pred) ** 2).sum()
        ss_tot = ((prof[s] - prof[s].mean()) ** 2).sum()
        r2 = 1 - ss_res / ss_tot
        print('%s  区间[%4d,%4d) 斜率=%+.4f 码/列 (numpy R^2=%.5f) 截距=%+.1f' %
              (tag, lo, hi, c[0], r2, c[1]))
    # 相邻列差的分布（看量化台阶宽度）
    d = np.diff(prof[128:900])
    print('   相邻列差: 均值=%+.4f  零差比例=%.3f  |差|>0.5 的比例=%.3f' %
          (d.mean(), (np.abs(d) < 1e-9).mean(), (np.abs(d) > 0.5).mean()))


ramp_fit(P, '新图 21:16')
ramp_fit(Q, '基准 20:55')
