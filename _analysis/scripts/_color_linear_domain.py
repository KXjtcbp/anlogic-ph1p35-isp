# -*- coding: utf-8 -*-
"""把采集图反查 S 曲线回到线性域，再量 R/G、B/G。
若线性域比值≈1.000 ⇒ AWB（灰世界）在工作，画面偏色来自曲线/其它环节；
若线性域比值仍≈0.86~0.95 ⇒ AWB 实际没起作用（增益≈1.0）。
"""
import os, sys
import numpy as np
from PIL import Image
sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'E:\FPGA'
LUT = os.path.join(ROOT, r'_analysis\lut\gamma_lut_twoseg_p160_a050.hex')
OSD = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]
SHOTS = ['17-00-12', '17-00-21', '17-00-30', '17-00-42', '17-01-49']

# ---- 读 S 曲线表 ----
lut = []
for ln in open(LUT, encoding='utf-8'):
    ln = ln.strip()
    if ln:
        lut.append(int(ln, 16))
lut = np.array(lut, dtype=np.int32)
print('S-curve LUT: %d entries; lut[0]=%d lut[16]=%d lut[64]=%d lut[118]=%d lut[160]=%d lut[200]=%d lut[255]=%d'
      % (len(lut), lut[0], lut[16], lut[64], lut[118], lut[160], lut[200], lut[255]))

# ---- 反查表：对每个 8bit 输出码，找出所有能产生它的输入码，取平均 ----
inv = np.zeros((256, 2), dtype=np.float64)   # [out] = (mean_in, count)
for inx, outx in enumerate(lut):
    inv[outx, 0] += inx
    inv[outx, 1] += 1
inv_mean = np.where(inv[:, 1] > 0, inv[:, 0] / np.maximum(inv[:, 1], 1), np.nan)
print('LUT 覆盖的输出码个数 = %d / 256 (未覆盖的码说明曲线是上采样的，反查会有台阶)' % int((inv[:, 1] > 0).sum()))


def mask2d(w, h):
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in OSD:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


print()
print('%-10s | %-28s | %-28s' % ('shot', '8bit domain (as captured)', 'linear domain (S-curve inverted)'))
print('%-10s | %8s %8s %8s %6s | %8s %8s %8s %6s' % ('', 'R', 'G', 'B', 'R/G B/G', 'R', 'G', 'B', 'R/G B/G'))
print('-' * 100)

for name in SHOTS:
    p = os.path.join(ROOT, 'Screenshot 2026-10-11 %s.png' % name)
    a = np.asarray(Image.open(p).convert('RGB')).astype(np.float64)
    h, w, _ = a.shape
    m = mask2d(w, h)
    px = a[m][:, :3]
    # 8bit
    m8 = px.mean(axis=0)
    # 线性（反查）
    lin = inv_mean[px.astype(np.int32)]
    lin = lin[~np.isnan(lin).any(axis=1)]
    ml = lin.mean(axis=0) if lin.size else np.array([np.nan] * 3)
    print('%-10s | %8.2f %8.2f %8.2f %6.3f %6.3f | %8.2f %8.2f %8.2f %6.3f %6.3f'
          % (name, m8[0], m8[1], m8[2], m8[0] / m8[1], m8[2] / m8[1],
             ml[0], ml[1], ml[2], ml[0] / ml[1], ml[2] / ml[1]))

# ---- 顺带看看 raw_exports ----
print()
print('=' * 100)
d = os.path.join(ROOT, 'raw_exports')
if os.path.isdir(d):
    for f in sorted(os.listdir(d)):
        fp = os.path.join(d, f)
        print('%-24s %8d B' % (f, os.path.getsize(fp)))
        with open(fp, 'r', errors='replace') as fh:
            for i, ln in enumerate(fh):
                if i < 4:
                    print('      | ' + ln.rstrip()[:160])
                else:
                    break
else:
    print('no raw_exports')
