#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""[HDR-2026-10-10] 判定新图是否为"逐行重复的合成梯度/测试图"。
"""
import numpy as np
from PIL import Image

P = r'E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 21-16-07.png'
a = np.asarray(Image.open(P).convert('RGB')).astype(np.int32)

# 1) 行间是否完全相同
r = a[:, :, 1]
same_next = np.mean([np.array_equal(r[y], r[y + 1]) for y in range(300, 900)])
same_500_700 = np.array_equal(r[500], r[700])
print('相邻行完全相同比例(300..900)=%.3f   第500行==第700行: %s' % (same_next, same_500_700))

# 2) 一行内的取样值（看是否 1 LSB 递增/递减的斜坡）
row = r[540]
print('第540行 每8列取样 (x=200..1000):')
print('   ' + ' '.join('%d' % row[x] for x in range(200, 1000, 8)))
d = np.diff(row[200:1000])
print('该段相邻列差: 唯一值=%s' % np.unique(d)[:12])
print('该段中 >0 差的比例=%.3f  <0 差的比例=%.3f  ==0 的比例=%.3f' %
      ((d > 0).mean(), (d < 0).mean(), (d == 0).mean()))

# 3) 三个通道是否相同（测试图通常三通道一致）
print('R==G==B 的像素比例: %.3f' % np.mean((a[:, :, 0] == a[:, :, 1]) & (a[:, :, 1] == a[:, :, 2])))
d_rg = np.abs(a[:, :, 0] - a[:, :, 1])
print('|R-G| 唯一值: %s' % np.unique(d_rg)[:10])

# 4) 列方向结构：每列的唯一值个数（列内恒定 => 1）
colu = np.array([len(np.unique(r[:, x])) for x in range(0, 1920, 64)])
print('每64列一采样 的"列内唯一值个数": %s' % colu)

# 5) 与 20-55 基准行比较（同一场景下是否结构一致）
Q = r'E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 20-55-54.png'
b = np.asarray(Image.open(Q).convert('RGB')).astype(np.int32)[:, :, 1]
print('第540行 新图 vs 基准图 前 20 个采样点:')
print('  new:', ' '.join('%3d' % row[x] for x in range(200, 1000, 40)))
print('  old:', ' '.join('%3d' % b[540][x] for x in range(200, 1000, 40)))
