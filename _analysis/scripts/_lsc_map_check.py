# -*- coding: utf-8 -*-
"""解析 tb_lsc_map.v 的输出，量出 lsc.v 在 (beat,line) 上实际施加的增益。"""
import os, re, sys
import numpy as np

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
SIM = os.path.join(WS, "_analysis", "sim", "lsc")
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")
VIN = 100

kR = np.zeros((12, 20), np.int32); kB = np.zeros((12, 20), np.int32)
src = open(os.path.join(HDL, "isp", "lsc.v"), "rb").read().decode("utf-8", errors="replace")
for m in re.finditer(r"9'd(\d+)\s*:\s*F_k2d\s*=\s*20'h([0-9a-fA-F]{5});\s*//\s*y=(\d+)\s+x=(\d+)\s+kR=\s*(\d+)\s+kB=\s*(\d+)", src):
    kR[int(m.group(3)), int(m.group(4))] = int(m.group(5))
    kB[int(m.group(3)), int(m.group(4))] = int(m.group(6))
print("表 kR: min=%d max=%d mean=%.1f   kB: min=%d max=%d mean=%.1f"
      % (kR.min(), kR.max(), kR.mean(), kB.min(), kB.max(), kB.mean()))

d = np.loadtxt(os.path.join(SIM, "lsc_gain_map.txt"), dtype=np.int64)
print("采样行数 =", d.shape[0])
bx, yy, krr, kbr, ro, go, bo = (d[:, i] for i in range(7))

gain = 1024.0 * (ro.astype(np.float64) / VIN - 1.0)
print("\n=== RTL 实际施加的增益（v=%d 恒定输入）===" % VIN)
print("  输出 R 码: min=%d max=%d  唯一值 %d 个" % (ro.min(), ro.max(), len(np.unique(ro))))
print("  反推 applied_k: min=%.1f max=%.1f mean=%.1f" % (gain.min(), gain.max(), gain.mean()))
print("  DUT 内部 S_kr_r: min=%d max=%d mean=%.1f" % (krr.min(), krr.max(), krr.mean()))
bad = np.abs(gain - krr).max()
print("  |applied_k - S_kr_r| 最大 = %.3f  （应≈0，说明 F_apply 正确）" % bad)

iy = np.clip(yy // 64, 0, 11); ix = np.clip(bx // 16, 0, 19)
print("\n=== 逐节点：表 kR  vs  DUT 实测 S_kr_r（取该节点内的众数）===")
M = np.zeros((12, 20), np.int32); R = np.zeros((12, 20), np.int32)
for a in range(12):
    for b2 in range(20):
        s = (iy == a) & (ix == b2)
        if s.sum():
            M[a, b2] = int(np.bincount(krr[s]).argmax())
            R[a, b2] = int(ro[s].mean())
np.set_printoptions(linewidth=200)
print("表 kR ="); print(kR)
print("DUT S_kr_r 众数 ="); print(M)
print("差 (DUT - 表) ="); print(M - kR)
print("\n表 kR 范围 %d..%d (跨度 %d)  |  DUT 范围 %d..%d (跨度 %d)"
      % (kR.min(), kR.max(), kR.max()-kR.min(), M.min(), M.max(), M.max()-M.min()))

print("\n=== 一行的完整剖面（y=32*1080/720=48 那一行，取 S_y=48）===")
rowsel = (yy == 48)
if rowsel.sum():
    xs = bx[rowsel]; ks = krr[rowsel]
    o = np.argsort(xs)
    xs, ks = xs[o], ks[o]
    for j in range(0, len(xs), 16):
        print("   bx=%3d (屏幕 x=%4d)  S_kr_r=%4d  表 kR[%d][%d]=%4d"
              % (xs[j], int(xs[j]*1.5*4), ks[j], 48//64, min(int(xs[j])//16,19), kR[0, min(int(xs[j])//16,19)]))
print("\n=== 饱和检查 ===")
print("  输出 R 码 == 255 的比例 = %.3f%%" % (100.0*(ro == 255).mean()))
