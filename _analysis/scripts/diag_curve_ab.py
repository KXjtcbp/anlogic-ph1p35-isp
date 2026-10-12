# -*- coding: utf-8 -*-
"""判定两张新采集图哪张是"不开曲线"、哪张是"开曲线"，并量化差异。
判据：
  H1: 23 号图 = 旁路(线性)，36 号图 = 开曲线  =>  lut[23] 应≈ 36
  H2: 36 号图 = 旁路(线性)，23 号图 = 开曲线  =>  lut[36] 应≈ 23
（lut 直接从 isp_gamma.v 读出，保证与烧进去的表一致）
"""
import re
import numpy as np
from PIL import Image

RTL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
IMG1 = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png"
IMG2 = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-36.png"
OUT = r"E:\FPGA\_analysis"

src = open(RTL, "r", encoding="utf-8", newline="").read()
tbl = re.search(r"    mem_b00\[  0\] = .*?mem_b00\[255\] = 8'h[0-9a-f]{2};", src, re.S).group(0)
lut = np.array([int(v, 16) for v in re.findall(r"8'h([0-9a-f]{2})", tbl)], dtype=np.uint8)
assert lut.shape == (256,)

def load(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    h, w = a.shape[:2]
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for (x0, y0, x1, y1) in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0*s):min(int(y1*s), h), int(x0*s):min(int(x1*s), w)] = False
    return a, m, (h, w)

def stat(a, m):
    Y = (77*a[:, :, 0] + 150*a[:, :, 1] + 29*a[:, :, 2]) >> 8
    Yv = Y[m]
    R, G, B = a[:, :, 0][m], a[:, :, 1][m], a[:, :, 2][m]
    return dict(mean=Yv.mean(), p10=np.percentile(Yv, 10), p50=np.percentile(Yv, 50),
                p90=np.percentile(Yv, 90), p99=np.percentile(Yv, 99), mx=int(Yv.max()),
                clip=(Yv >= 250).mean()*100, dark=(Yv <= 8).mean()*100,
                R=R.mean(), G=G.mean(), B=B.mean(), rg=R.mean()/max(G.mean(), 1e-9),
                bg=B.mean()/max(G.mean(), 1e-9),
                neutral=(np.abs(R.astype(np.int32)-G) + np.abs(B.astype(np.int32)-G) <= 1).mean()*100,
                black=((R == 0) & (G == 0) & (B == 0)).mean()*100)

a1, m1, shp = load(IMG1)
a2, m2, _ = load(IMG2)
s1, s2 = stat(a1, m1), stat(a2, m2)

print("=" * 96)
for nm, s in (("00-07-23", s1), ("00-07-36", s2)):
    print("%s  Ymean %6.2f p10 %3.0f p50 %3.0f p90 %3.0f p99 %3.0f max %3d | clip>=250 %.4f%% | <=8 %.2f%% | "
          "R/G %.4f B/G %.4f | R/G/B %.2f/%.2f/%.2f | 中性 %.1f%% 纯黑 %.2f%%" %
          (nm, s["mean"], s["p10"], s["p50"], s["p90"], s["p99"], s["mx"], s["clip"], s["dark"],
           s["rg"], s["bg"], s["R"], s["G"], s["B"], s["neutral"], s["black"]))
print("=" * 96)

# ---- 交叉预测：如果某张是线性的，另一个张应该等于 lut[它] ----
for name, lin, other, m in (("H1: 23=线性 -> lut[23] 应≈36", a1, a2, m1 & m2),
                            ("H2: 36=线性 -> lut[36] 应≈23", a2, a1, m1 & m2)):
    pred = lut[lin]
    d = np.abs(pred - other)[m]
    d0 = np.abs(lin - other)[m]
    print("%-28s 交叉残差 mean|pred-other| = %6.3f  (不使用曲线时 mean|A-B| = %6.3f)  改善 %.2fx" %
          (name, d.mean(), d0.mean(), d0.mean()/max(d.mean(), 1e-9)))

# ---- 逐像素：若 36 = lut[23]，则 36 应当完全落在 lut 的值域上（灰度直方图重合）----
h1 = np.bincount(a1[:, :, 1][m1].ravel(), minlength=256)
h2 = np.bincount(a2[:, :, 1][m2].ravel(), minlength=256)
h1p = np.bincount(lut[a1[:, :, 1][m1]].ravel(), minlength=256)
tot = h2.sum()
overlap_raw = np.minimum(h1, h2).sum()/min(h1.sum(), h2.sum())
overlap_pred = np.minimum(h1p, h2).sum()/min(h1p.sum(), h2.sum())
print("\nG 通道直方图重合度：原始 23 vs 36 = %.4f ；把 23 过表后 vs 36 = %.4f" % (overlap_raw, overlap_pred))

# ---- OSD 区域（OSD 在 hdmi_mixer 里叠加，位于 gamma 之后，不应受曲线影响）----
y0, y1, x0, x1 = 155, 215, 540, 900
osd1 = a1[y0:y1, x0:x1].astype(np.float64)
osd2 = a2[y0:y1, x0:x1].astype(np.float64)
print("OSD 区(y155-215,x540-900) 平均绝对差 = %.2f 码 ；整幅平均绝对差 = %.2f 码" %
      (np.abs(osd1-osd2).mean(), np.abs(a1.astype(np.float64)-a2.astype(np.float64)).mean()))

# ---- 出图：并排 + CNT 裁切 ----
def tag(img, text):
    from PIL import ImageDraw
    im = Image.fromarray(img.astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 560, 30], fill=(0, 0, 0))
    d.text((8, 8), text, fill=(255, 255, 0))
    return im

h, w = shp
top = tag(a1, "00-07-23  Ymean %.1f p50 %.0f" % (s1["mean"], s1["p50"]))
bot = tag(a2, "00-07-36  Ymean %.1f p50 %.0f" % (s2["mean"], s2["p50"]))
side = Image.new("RGB", (w, h*2+6), (255, 255, 255))
side.paste(top, (0, 0)); side.paste(bot, (0, h+6))
side.resize((1100, (h*2+6)*1100//w), Image.LANCZOS).save(OUT + r"\ab_side.png")

s = w/1280.0
box = (int(360*s), int(105*s), int(620*s), int(142*s))
c1 = Image.fromarray(a1.astype(np.uint8)).crop(box).resize((880, 126), Image.NEAREST)
c2 = Image.fromarray(a2.astype(np.uint8)).crop(box).resize((880, 126), Image.NEAREST)
cnt = Image.new("RGB", (880, 126*2+8), (255, 255, 255))
cnt.paste(c1, (0, 0)); cnt.paste(c2, (0, 134))
cnt.save(OUT + r"\ab_cnt.png")
print("\nsaved " + OUT + r"\ab_side.png")
print("saved " + OUT + r"\ab_cnt.png")
