# -*- coding: utf-8 -*-
"""分析 SW3/SW4 四个增益档的采集图：亮度梯、信噪、过曝（光源过亮）分布。
口径与 diag2.py 一致：去掉 3 个 OSD 区域后统计，便于与 00.png / 21:xx 的历史数据比较。"""
import os, numpy as np
from PIL import Image

FILES = [
    ("两个全关 (SW4下/SW3下 = 4.000x)", r"E:\FPGA\captures\2026-10-10_增益梯SW34\两个全关.png"),
    ("SW3     (SW3上/SW4下 = 8.000x)",  r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3.png"),
    ("SW4     (SW4上/SW3下 = 15.750x)", r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW4.png"),
    ("SW3+SW4 (两上     = 31.500x)",    r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3+SW4.png"),
    ("00.png  (厂商基线 11.25x)",       r"E:\FPGA\captures\2026-10-10_基线\00.png"),
]

def load_masked(p):
    im = Image.open(p).convert("RGB")
    a = np.asarray(im).astype(np.int32)
    h, w = a.shape[:2]
    s = w / 1280.0
    for (x0, y0, x1, y1) in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        X0, Y0, X1, Y1 = int(x0 * s), int(y0 * s), int(x1 * s), int(y1 * s)
        a[Y0:min(Y1, h), X0:min(X1, w)] = -1          # 用 -1 标记被遮罩，避免影响统计
    return a, w, h

def stats(p):
    a, w, h = load_masked(p)
    used = a[:, :, 0] >= 0
    px = a[used]                                        # (N,3)
    R, G, B = px[:, 0], px[:, 1], px[:, 2]
    # BT.601 定点系数，int32 防溢出
    Y = (77 * R + 150 * G + 29 * B) >> 8
    out = {}
    out["mean"] = (R.mean(), G.mean(), B.mean())
    out["Ymean"] = Y.mean()
    out["pct"] = {q: np.percentile(Y, q) for q in (10, 25, 50, 75, 90, 99, 99.9)}
    out["Ymax"] = int(Y.max())
    out["clip250"] = float((Y >= 250).mean() * 100)      # 8bit 截顶
    out["clip240"] = float((Y >= 240).mean() * 100)
    out["clip200"] = float((Y >= 200).mean() * 100)
    out["dark8"] = float((Y <= 8).mean() * 100)          # 暗部压死
    out["black0"] = float((Y == 0).mean() * 100)
    out["sat"] = np.percentile(px.max(axis=1) - px.min(axis=1), 99)
    out["neutral"] = float(((R == G) & (G == B)).mean() * 100)
    out["RG"] = R.mean() / G.mean() if G.mean() else 0
    out["BG"] = B.mean() / G.mean() if G.mean() else 0
    # 暗部/亮部分别的平均，用来判"整体偏暗 + 光源过亮"这种高反差场景
    m = Y > 8
    out["Ymean_gt8"] = Y[m].mean() if m.any() else 0
    return out

print("=" * 132)
print("SW3/SW4 增益档对照（均为 E:\\FPGA 下 2026-10-10 23:33 采集，同一场景）")
print("=" * 132)
rows = []
for name, p in FILES:
    if not os.path.exists(p):
        print("缺失: " + p); continue
    s = stats(p)
    rows.append((name, s))
    print("\n### %s" % name)
    print("  尺寸/文件: %d B" % os.path.getsize(p))
    print("  通道均值 R/G/B = %.2f / %.2f / %.2f     R/G %.4f  B/G %.4f   严格中性 %.2f%%"
          % (s["mean"][0], s["mean"][1], s["mean"][2], s["RG"], s["BG"], s["neutral"]))
    print("  亮度 Y: 均值 %.2f   分位 p10 %d  p25 %d  p50 %d  p75 %d  p90 %d  p99 %d  max %d"
          % (s["Ymean"], s["pct"][10], s["pct"][25], s["pct"][50], s["pct"][75], s["pct"][90], s["pct"][99], s["Ymax"]))
    print("  过曝: >=250 %.3f%%   >=240 %.3f%%   >=200 %.3f%%      暗部: Y<=8 %.2f%%  Y==0 %.2f%%"
          % (s["clip250"], s["clip240"], s["clip200"], s["dark8"], s["black0"]))
    print("  彩度 p99 %d      Y>8 部分均值 %.2f" % (s["sat"], s["Ymean_gt8"]))

print("\n" + "=" * 132)
print("档间比值（Y 均值）——理论应为 相邻档 x2.0 / 与最低档 x1, x2, x3.94, x7.875")
print("=" * 132)
if len(rows) >= 4:
    base = rows[0][1]["Ymean"]
    for name, s in rows[:4]:
        print("  %-38s Ymean %7.2f   与最低档比 x%.3f" % (name.split()[0], s["Ymean"], s["Ymean"] / base))
    print("\n  相邻档比: 关->SW3 x%.3f   SW3->SW4 x%.3f   SW4->两开 x%.3f"
          % (rows[1][1]["Ymean"] / rows[0][1]["Ymean"],
             rows[2][1]["Ymean"] / rows[1][1]["Ymean"],
             rows[3][1]["Ymean"] / rows[2][1]["Ymean"]))
print()
