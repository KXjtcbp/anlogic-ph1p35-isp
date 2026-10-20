# -*- coding: utf-8 -*-
"""对最新采集图做定量判定：真实场景 vs 传感器灰度递增测试图。

判据：
  ramp_R2  = 中间带（x 100..900, y 200..900）列均值剖面的线性拟合 R²
             ≥0.98 ⇒ 合成斜坡（测试图）；<0.6 ⇒ 真实场景
  slope    = 每列 8bit 码值变化量（合成斜坡约 -0.19）
  zero%    = 三通道同时为 0 的像素占比（测试图右侧大片为 0）
另给出常规统计：通道均值/分位/过曝/中性/彩度（luma 用 int32，避免 int16 溢出）。
"""
import sys, numpy as np, cv2

NEW = sys.argv[1] if len(sys.argv) > 1 else r"E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 21-46-50.png"
REF = r"E:\FPGA\captures\2026-10-10_基线\00.png"
OUT = r"E:\FPGA\_analysis\out\latest_preview.png"


def stats(p):
    im = cv2.imread(p)
    if im is None:
        print("读不到:", p); sys.exit(1)
    b, g, r = [im[..., i].astype(np.int32) for i in range(3)]
    luma = (77 * r + 150 * g + 29 * b) >> 8          # BT.601, int32 不会溢出
    chroma = np.maximum(np.maximum(r, g), b) - np.minimum(np.minimum(r, g), b)
    # 中间带列剖面
    band = luma[200:900, 100:900]
    prof = band.mean(axis=0)
    x = np.arange(prof.size, dtype=np.float64)
    A = np.polyfit(x, prof, 1)
    fit = np.polyval(A, x)
    ss_res = float(((prof - fit) ** 2).sum())
    ss_tot = float(((prof - prof.mean()) ** 2).sum())
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    d = dict(
        name=p.split("\\")[-1], shape=im.shape[:2],
        R=r.mean(), G=g.mean(), B=b.mean(),
        RmG=r.mean() - g.mean(), BmG=b.mean() - g.mean(),
        RG=r.mean() / g.mean(), BG=b.mean() / g.mean(),
        lmean=luma.mean(), p50=np.percentile(luma, 50), p90=np.percentile(luma, 90),
        p99=np.percentile(luma, 99), p999=np.percentile(luma, 99.9), lmax=luma.max(),
        over=float((luma >= 250).mean() * 100),
        neu=float((chroma == 0).mean() * 100),
        c50=np.percentile(chroma, 50), c99=np.percentile(chroma, 99), cmax=chroma.max(),
        zero=float(((r == 0) & (g == 0) & (b == 0)).mean() * 100),
        rmax=r.max(), gmax=g.max(), bmax=b.max(),
        r2=r2, slope=A[0], prof0=prof[0], profN=prof[-1],
    )
    return im, d


def show(d):
    print("== %s  %dx%d ==" % (d["name"], d["shape"][1], d["shape"][0]))
    print("  通道均值 R/G/B = %.2f / %.2f / %.2f    R-G %+.2f  B-G %+.2f   R/G %.4f  B/G %.4f"
          % (d["R"], d["G"], d["B"], d["RmG"], d["BmG"], d["RG"], d["BG"]))
    print("  luma 均值 %.2f  p50 %.1f  p90 %.1f  p99 %.1f  p99.9 %.1f  max %d   过曝(>=250) %.3f%%"
          % (d["lmean"], d["p50"], d["p90"], d["p99"], d["p999"], d["lmax"], d["over"]))
    print("  通道 max  R%d G%d B%d    彩度 p50 %.1f  p99 %d  max %d   严格中性 %.2f%%   纯黑(000) %.2f%%"
          % (d["rmax"], d["gmax"], d["bmax"], d["c50"], d["c99"], d["cmax"], d["neu"], d["zero"]))
    print("  ★列剖面（x100-900,y200-900）斜率 %+.4f 码/列   R² %.5f   起点 %.1f → 终点 %.1f"
          % (d["slope"], d["r2"], d["prof0"], d["profN"]))
    ramp = d["r2"] >= 0.98
    print("  ★判定：%s" % ("【合成斜坡 = 传感器测试图】" if ramp
                          else ("【真实场景】" if d["r2"] < 0.6 else "【不确定，需看图】")))
    return ramp


for p in (REF, NEW):
    im, d = stats(p)
    show(d)
    print()
    if p == NEW:
        h, w = im.shape[:2]
        cv2.imwrite(OUT, cv2.resize(im, (w // 2, h // 2), interpolation=cv2.INTER_AREA))
        print("预览已写:", OUT)
