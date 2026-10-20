# -*- coding: utf-8 -*-
"""判定方向与表：用候选表在"亮图->暗图"和"暗图->亮图"两个方向拟合，比 RMS。
   若某方向某表 RMS 明显最小，则说明该表就是实际烧录的表、且方向确定。
"""
import numpy as np
from PIL import Image

A_IMG = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png"   # 亮（Ymean 63.4）
B_IMG = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-36.png"   # 暗（Ymean 25.1）
TABLES = {
    "identity           ": None,
    "old S  P118 A1.25  ": r"E:\FPGA\_analysis\lut\gamma_lut_p118_k125.hex",
    "log    k10         ": r"E:\FPGA\_analysis\lut\gamma_lut_log_k10.hex",
    "twoseg P160 A0.50  ": r"E:\FPGA\_analysis\lut\gamma_lut_twoseg_p160_a050.hex",
}

def g_of(p, step=3):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    return a[::step, ::step, 1].ravel()

gA = g_of(A_IMG); gB = g_of(B_IMG)
print("图A(23,亮) G均值 %.2f   图B(36,暗) G均值 %.2f\n" % (gA.mean(), gB.mean()))

def rms(pred, ref):
    return float(np.sqrt(((pred.astype(np.float64) - ref) ** 2).mean()))

print("%-22s | %-24s | %-24s" % ("候选表", "A->B (亮图当输入)", "B->A (暗图当输入)"))
print("-" * 78)
for nm, path in TABLES.items():
    if path is None:
        r_ab, r_ba = rms(gA, gB), rms(gB, gA)
    else:
        lut = np.array([int(l.strip(), 16) for l in open(path) if l.strip()], dtype=np.int32)
        r_ab, r_ba = rms(lut[gA], gB), rms(lut[gB], gA)
    print("%-22s | %8.2f (%s->%s)   | %8.2f (%s->%s)" %
          (nm, r_ab, "亮", "暗", r_ba, "暗", "亮"))

print("\n== 若表=old S P118 A1.25，则 23->36 的分位预测 vs 实测 ==")
lut = np.array([int(l.strip(), 16) for l in open(TABLES["old S  P118 A1.25  "]) if l.strip()], dtype=np.int32)
for q in (1, 5, 10, 30, 50, 70, 90, 99, 100):
    v = np.percentile(gA, q)
    print("   %5.1f%% : A=%3.0f -> 预测 %3d   实测B分位 %3.0f" %
          (q, v, lut[int(round(v))], np.percentile(gB, q)))

print("\n== 若表=twoseg P160 A0.50，则 36->23 的分位预测 vs 实测 ==")
lut2 = np.array([int(l.strip(), 16) for l in open(TABLES["twoseg P160 A0.50  "]) if l.strip()], dtype=np.int32)
for q in (1, 5, 10, 30, 50, 70, 90, 99, 100):
    v = np.percentile(gB, q)
    print("   %5.1f%% : B=%3.0f -> 预测 %3d   实测A分位 %3.0f" %
          (q, v, lut2[int(round(v))], np.percentile(gA, q)))
