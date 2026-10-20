# -*- coding: utf-8 -*-
"""本轮三张标定图（盖住镜头 / 直看光源 / 直看白纸）定量：
- OSD 遮罩后全画面与中央区统计（Y 分位、过曝、暗部、通道均值与比值、中性比、纯黑比）
- 每通道低端直方图（0..12 计数）用于黑电平反推
- 保存 3 张的 OSD CNT 行拼图（判同一上电/是否重启）
用法: python diag_cal3.py
"""
import numpy as np
from PIL import Image

FILES = [
    (r"E:\FPGA\captures\2026-10-11_标定\盖住镜头.png", "盖住镜头"),
    (r"E:\FPGA\captures\2026-10-11_标定\直看光源.png", "直看光源"),
    (r"E:\FPGA\captures\2026-10-11_标定\直看白纸.png", "直看白纸"),
]

def omask(w, h):
    m = np.ones((h, w), bool)
    s = w / 1280.0
    for (x0, y0, x1, y1) in [(0, 0, 180, 180), (360, 105, 620, 150), (165, 165, 280, 200)]:
        m[int(y0*s):int(y1*s), int(x0*s):int(x1*s)] = False
    return m

def luma(a):
    a = a.astype(np.int32)
    return ((77 * a[..., 0] + 150 * a[..., 1] + 29 * a[..., 2]) >> 8)

def stats(y, m, tag):
    v = y[m].astype(np.float64)
    q = np.percentile(v, [1, 10, 50, 90, 99, 99.9])
    print("  %-10s n=%9d  Ymean %6.2f  std %6.2f  p1 %.0f p10 %.0f p50 %.0f p90 %.0f p99 %.0f p99.9 %.0f max %.0f"
          % (tag, v.size, v.mean(), v.std(), q[0], q[1], q[2], q[3], q[4], q[5], v.max()))
    print("            过曝>=250 %.4f%%   >=254 %.4f%%   暗部<=8 %.2f%%   Y==0 %.2f%%"
          % (100.0*np.mean(v >= 250), 100.0*np.mean(v >= 254), 100.0*np.mean(v <= 8), 100.0*np.mean(v == 0)))

def chan(a, m, tag):
    out = []
    for i, nm in enumerate("RGB"):
        c = a[..., i][m].astype(np.float64)
        out.append(c.mean())
        print("  %-10s %s mean %6.2f  median %5.0f  p99 %5.0f  max %3.0f  ==0 %6.3f%%"
              % (tag, nm, c.mean(), np.median(c), np.percentile(c, 99), c.max(), 100.0*np.mean(c == 0)))
    r, g, b = out
    print("  %-10s R/G %.4f   B/G %.4f   R-G %+.2f  B-G %+.2f" % (tag, r/g, b/g, r-g, b-g))

crops = []
for p, name in FILES:
    im = Image.open(p).convert("RGB")
    a = np.asarray(im)
    h, w = a.shape[:2]
    y = luma(a)
    m = omask(w, h)
    print("=" * 96)
    print("%s   %dx%d   %d B" % (name, w, h, __import__("os").path.getsize(p)))
    stats(y, m, "全画面")
    chan(a, m, "全画面")
    # 中央区（目标物）
    cy = np.zeros_like(m); cy[int(0.20*h):int(0.80*h), int(0.20*w):int(0.80*w)] = True
    cm = m & cy
    stats(y, cm, "中央区")
    chan(a, cm, "中央区")
    # 低端直方图
    for i, nm in enumerate("RGB"):
        c = a[..., i]
        cnt = [int(np.sum(c == k)) for k in range(0, 13)]
        print("  低端直方图 %s: %s" % (nm, " ".join(str(x) for x in cnt)))
    # OSD 行裁剪
    s = w / 1280.0
    crops.append(im.crop((int(360*s), int(105*s), int(620*s), int(142*s))).resize((880, 126), Image.NEAREST))

sheet = Image.new("RGB", (880, 126*3+8), (255, 255, 255))
for i, c in enumerate(crops):
    sheet.paste(c, (0, i*(126+4)))
sheet.save(r"E:\FPGA\_analysis\out\cal3_cnt.png")
print("saved E:\\FPGA\\_analysis\\out\\cal3_cnt.png")
