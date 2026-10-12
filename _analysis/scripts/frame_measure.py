# -*- coding: utf-8 -*-
"""
把 7 张现场照片对齐到同一个"OSD 坐标系"后比较。

锚点：OSD 上两行固定位置、固定字号的文字
  A = 黄色 "安路 CNT:xxxxxx"   (COLOR_DYN_TEXT = 24'hfff200)
  B = 亮绿 "MODE n"            (COLOR_ALG_TEXT = 24'h00ff88)
两行在 OSD 坐标里位置固定 ⇒ 由 A/B 的 bbox 中心可以解出
  平移 + 旋转 + 缩放（相似变换），把每张照片映射到参考照片的坐标系。
单位取 "OSD 文字高度 u"，于是所有照片都落在同一套无量纲坐标里。
"""
import os, json, math
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"
IMG = os.path.join(OUT, "rect")
os.makedirs(IMG, exist_ok=True)

PHOTOS = [
    "mode0室内常光.jpg",
    "mode3室内常光.jpg",
    "mode0盖住镜头.jpg",
    "IMG_20261006_192101.jpg",
    "IMG_20261006_192107.jpg",
    "IMG_20261006_192127.jpg",
    "IMG_20261006_192131.jpg",
]

# 输出画布（OSD 单位）：x ∈ [X0, X1]，y ∈ [Y0, Y1]，原点=黄字中心，x 轴沿 OSD 行方向
X0, X1 = -3.30, 3.30
Y0, Y1 = -0.30, 6.10
OUT_W = 1188


def bbox_of(mask):
    """返回 mask 的主连通带 bbox（用行/列投影，避免纯 python 连通域太慢）。"""
    if mask.sum() < 50:
        return None
    rows = mask.sum(axis=1)
    thr_r = max(rows.max() * 0.35, 3)
    ridx = np.where(rows >= thr_r)[0]
    if len(ridx) == 0:
        return None
    # 取最密的一段连续行
    best = cur = [ridx[0], ridx[0]]
    for r in ridx[1:]:
        if r == cur[1] + 1:
            cur[1] = r
        else:
            if sum(rows[cur[0]:cur[1] + 1]) > sum(rows[best[0]:best[1] + 1]):
                best = cur
            cur = [r, r]
    if sum(rows[cur[0]:cur[1] + 1]) > sum(rows[best[0]:best[1] + 1]):
        best = cur
    y0, y1 = best
    sub = mask[y0:y1 + 1]
    cols = sub.sum(axis=0)
    cidx = np.where(cols > 0)[0]
    if len(cidx) == 0:
        return None
    x0, x1 = cidx[0], cidx[-1]
    return int(x0), int(y0), int(x1), int(y1)


def anchors(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.int16)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    yellow = (R > 170) & (G > 150) & (B < 130) & ((R - B) > 70) & (np.abs(R - G) < 70)
    green = (G > 170) & ((G - R) > 60) & ((G - B) > 40)
    yb = bbox_of(yellow)
    gb = bbox_of(green)
    return a, yb, gb


records = []
for i, name in enumerate(PHOTOS):
    p = os.path.join(SRC, name)
    if not os.path.exists(p):
        print("MISSING", name)
        continue
    a, yb, gb = anchors(p)
    if yb is None or gb is None:
        print("ANCHOR-FAIL", name, "yellow=", yb, "green=", gb)
        continue
    ycx, ycy = (yb[0] + yb[2]) / 2.0, (yb[1] + yb[3]) / 2.0
    gcx, gcy = (gb[0] + gb[2]) / 2.0, (gb[1] + gb[3]) / 2.0
    h_y = yb[3] - yb[1] + 1                      # 黄字高度 = 单位 u
    h_g = gb[3] - gb[1] + 1
    u = (h_y + h_g) / 2.0
    dx, dy = gcx - ycx, gcy - ycy
    theta = math.atan2(dy, dx)                   # OSD 行方向相对照片 x 轴的夹角
    records.append(dict(idx=i, name=name, yc=(ycx, ycy), gc=(gcx, gcy),
                        u=u, h_y=int(h_y), h_g=int(h_g), theta=theta,
                        sep=math.hypot(dx, dy), size=(a.shape[1], a.shape[0])))

    # ---- 相似变换：OSD -> 照片 ----
    scale = OUT_W / (X1 - X0)
    ct, st = math.cos(theta), math.sin(theta)
    a_ = u * ct / scale
    b_ = -u * st / scale
    c_ = ycx + u * (ct * X0 - st * Y0)
    d_ = u * st / scale
    e_ = u * ct / scale
    f_ = ycy + u * (st * X0 + ct * Y0)
    OUT_H = int(round((Y1 - Y0) * scale))
    img = Image.open(p).convert("RGB")
    w = img.transform((OUT_W, OUT_H), Image.AFFINE, (a_, b_, c_, d_, e_, f_), resample=Image.BICUBIC)
    w.save(os.path.join(IMG, "%d_%s.png" % (i, os.path.splitext(name)[0])))
    records[-1]["out"] = (OUT_W, OUT_H)

json.dump(records, open(os.path.join(OUT, "rect_anchors.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)

# ---- 统计表 ----
lines = []
lines.append("idx  文件                          黄字高 绿字高 单位u  行角(度) 锚距px  中心亮度min/mean/max  饱和度")
stats = []
for r in records:
    p = os.path.join(IMG, "%d_%s.png" % (r["idx"], os.path.splitext(r["name"])[0]))
    w = np.asarray(Image.open(p).convert("RGB")).astype(np.float32)
    H, W, _ = w.shape
    # 去掉最上面 22%（那里含 OSD 文字与 logo）和左右各 6%，只留纯画面
    core = w[int(H * 0.22):int(H * 0.97), int(W * 0.06):int(W * 0.94)]
    lum = core @ np.array([0.299, 0.587, 0.114], dtype=np.float32)
    mx = core.max(axis=2); mn = core.min(axis=2)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1), 0)
    stats.append((r, core, lum, sat))
    lines.append("%-4d %-28s %6d %6d %6.1f %8.2f %7.1f  %6.1f/%6.1f/%6.1f  %6.1f" % (
        r["idx"], r["name"], r["h_y"], r["h_g"], r["u"], math.degrees(r["theta"]),
        r["sep"], lum.min(), lum.mean(), lum.max(), sat.mean() * 100))

# ---- 两两相关（同一内容判据）----
lines.append("")
lines.append("两两相关系数（对齐后 luma，去均值归一化）:")
lines.append("      " + "".join("%7d" % r["idx"] for r in records))
for s1 in stats:
    row = "%4d  " % s1[0]["idx"]
    for s2 in stats:
        x = s1[2].ravel() - s1[2].mean()
        y = s2[2].ravel() - s2[2].mean()
        c = float((x @ y) / (np.linalg.norm(x) * np.linalg.norm(y) + 1e-9))
        row += "%7.3f" % c
    lines.append(row)

# ---- 每张的亮度直方图（16 桶）----
lines.append("")
lines.append("亮度直方图（0-255 分 16 桶，% 占比）:")
for s1 in stats:
    h, _ = np.histogram(s1[2], bins=16, range=(0, 256))
    h = h / max(h.sum(), 1) * 100
    lines.append("%4d %-26s %s" % (s1[0]["idx"], s1[0]["name"],
                                   " ".join("%4.1f" % v for v in h)))

open(os.path.join(OUT, "rect_stats.txt"), "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines))

# ---- 拼成一张联络表（每张缩到宽 380）----
tw = 380
tiles = []
for r in records:
    p = os.path.join(IMG, "%d_%s.png" % (r["idx"], os.path.splitext(r["name"])[0]))
    im = Image.open(p).convert("RGB")
    th = int(im.height * tw / im.width)
    tiles.append((r["idx"], im.resize((tw, th), Image.LANCZOS)))
cols = 4
rows = (len(tiles) + cols - 1) // cols
th = max(t[1].height for t in tiles)
sheet = Image.new("RGB", (cols * tw + (cols + 1) * 6, rows * th + (rows + 1) * 6), (255, 255, 255))
for k, (idx, im) in enumerate(tiles):
    cx = 6 + (k % cols) * (tw + 6)
    cy = 6 + (k // cols) * (th + 6)
    sheet.paste(im, (cx, cy))
sheet.save(os.path.join(OUT, "contact_sheet.png"))
print("\nwrote contact_sheet.png", sheet.size)
