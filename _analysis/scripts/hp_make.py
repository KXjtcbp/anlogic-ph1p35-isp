#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""[HDR-2026-10-10] 高通增强：看新图里有没有被平滑梯度掩盖的真实场景结构。
"""
import numpy as np
import cv2
from PIL import Image

P = r'E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 21-16-07.png'
Q = r'E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 20-55-54.png'

for tag, path, crop, gain in (('new', P, (0, 250, 1100, 900), 30), ('old', Q, (0, 250, 1100, 900), 8)):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float32)
    x0, y0, x1, y1 = crop
    c = a[y0:y1, x0:x1]
    blur = cv2.GaussianBlur(c, (0, 0), 25)
    hp = (c - blur) * gain + 128
    out = np.clip(hp, 0, 255).astype(np.uint8)
    cv2.imwrite(r'E:\FPGA\_analysis\hp_%s.png' % tag, cv2.cvtColor(out, cv2.COLOR_RGB2BGR))
    print('hp_%s.png 保存，高通增益 x%d，区域 %s' % (tag, gain, crop))
