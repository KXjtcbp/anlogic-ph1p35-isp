# -*- coding: utf-8 -*-
"""inbox 批次分析：统计 + logo identity + OSD 裁图拼版。
输出：
  _analysis/out/inbox_stats.txt
  _analysis/out/inbox_cnt_sheet.png    （每张图的 CNT 文字区，x2 放大后纵拼）
  _analysis/out/inbox_mode_sheet.png   （每张图的 MODE 文字区，x4 放大后纵拼）
  _analysis/out/inbox_contact.png      （全部图 5 列缩略图）
"""
import os, sys, collections
import numpy as np
from PIL import Image, ImageDraw

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
INBOX = os.path.join(WS, "inbox")
OUT = os.path.join(WS, "_analysis", "out")
os.makedirs(OUT, exist_ok=True)

# 已经由前面多轮验证过的 OSD 位置（1920x1080 空间）
CNT_BOX = (540, 168, 900, 222)     # 黄字“安路 CNT:xxxxxx”
MODE_BOX = (240, 250, 660, 292)    # 绿字“MODE n”
# 统计时要遮掉的 3 块（1280 空间，按 w/1280 缩放）
MASKS = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]


def mask_of(w, h):
    m = np.ones((h, w), bool)
    s = w / 1280.0
    for x0, y0, x1, y1 in MASKS:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def analyse(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    a = np.asarray(im).astype(np.int32)
    m = mask_of(w, h)
    Y = (77 * a[..., 0] + 150 * a[..., 1] + 29 * a[..., 2]) >> 8
    ym = Y[m]
    R, G, B = a[..., 0][m], a[..., 1][m], a[..., 2][m]
    r = dict(w=w, h=h, size=os.path.getsize(path),
             ymean=float(ym.mean()), ystd=float(ym.std()),
             p1=int(np.percentile(ym, 1)), p10=int(np.percentile(ym, 10)),
             p50=int(np.percentile(ym, 50)), p90=int(np.percentile(ym, 90)),
             p99=int(np.percentile(ym, 99)), mx=int(ym.max()),
             ov=100.0 * float((ym >= 250).mean()),
             dk=100.0 * float((ym <= 8).mean()),
             z=100.0 * float((ym == 0).mean()),
             Rm=float(R.mean()), Gm=float(G.mean()), Bm=float(B.mean()))
    r["rg"] = r["Rm"] / max(r["Gm"], 1e-9)
    r["bg"] = r["Bm"] / max(r["Gm"], 1e-9)
    # 排除近黑后的通道比（暗场更可信）
    sel = Y[m] > 16
    if sel.sum() > 500:
        r["rg16"] = float(R[sel].mean()) / max(float(G[sel].mean()), 1e-9)
        r["bg16"] = float(B[sel].mean()) / max(float(G[sel].mean()), 1e-9)
        r["n16"] = int(sel.sum())
    else:
        r["rg16"] = r["bg16"] = float("nan"); r["n16"] = 0
    r["sat"] = float((np.maximum(np.maximum(R, G), B) - np.minimum(np.minimum(R, G), B)).mean())
    # logo identity：左上角区域出现次数最多的两种颜色
    reg = a[:250, :250].reshape(-1, 3)
    cnt = collections.Counter(map(tuple, reg))
    r["top"] = cnt.most_common(4)
    return im, r


def sheet(imgs, box, zoom, path, label_w=64):
    x0, y0, x1, y1 = box
    w = (x1 - x0) * zoom
    h = (y1 - y0) * zoom
    canvas = Image.new("RGB", (w + label_w, (h + 6) * len(imgs)), (20, 20, 20))
    d = ImageDraw.Draw(canvas)
    for i, (name, im) in enumerate(imgs):
        c = im.crop(box).resize((w, h), Image.LANCZOS)
        y = i * (h + 6)
        canvas.paste(c, (label_w, y))
        d.text((4, y + h // 3), name, fill=(255, 220, 0))
    canvas.save(path)
    print("saved %s  %s" % (path, canvas.size))


def contact(imgs, path, cols=5, cw=384):
    ch = int(cw * 1080 / 1920)
    rows = (len(imgs) + cols - 1) // cols
    canvas = Image.new("RGB", (cols * (cw + 4), rows * (ch + 20)), (20, 20, 20))
    d = ImageDraw.Draw(canvas)
    for i, (name, im) in enumerate(imgs):
        cx = (i % cols) * (cw + 4)
        cy = (i // cols) * (ch + 20)
        canvas.paste(im.resize((cw, ch), Image.LANCZOS), (cx, cy + 16))
        d.text((cx + 3, cy + 3), name, fill=(255, 220, 0))
    canvas.save(path)
    print("saved %s  %s" % (path, canvas.size))


names = sorted([f for f in os.listdir(INBOX) if f.lower().endswith(".png")],
               key=lambda f: (f[0], f))
print("共 %d 张\n" % len(names))

hdr = ("%-8s %5s %8s %7s %4s %4s %4s %4s %4s %4s | %7s %7s %7s | %6s %6s | %6s %6s %6s | logo top1 / top2"
       % ("file", "kB", "Ymean", "Ystd", "p1", "p10", "p50", "p90", "p99", "max",
          "ov250%", "dk<=8%", "z==0%", "R", "G", "R/G", "B/G", "sat"))
lines = [hdr]
imgs = []
for n in names:
    im, r = analyse(os.path.join(INBOX, n))
    imgs.append((n.replace(".png", ""), im))
    lines.append("%-8s %5d %8.2f %7.2f %4d %4d %4d %4d %4d %4d | %7.3f %7.2f %7.2f | %6.2f %6.2f | %6.4f %6.4f %6.2f | %s"
                 % (n.replace(".png", ""), r["size"] // 1024, r["ymean"], r["ystd"],
                    r["p1"], r["p10"], r["p50"], r["p90"], r["p99"], r["mx"],
                    r["ov"], r["dk"], r["z"], r["Rm"], r["Gm"], r["rg"], r["bg"], r["sat"],
                    " ".join(str(c) for c, _ in r["top"][:2])))
txt = "\n".join(lines)
print(txt)
open(os.path.join(OUT, "inbox_stats.txt"), "w", encoding="utf-8").write(txt + "\n")

sheet(imgs, CNT_BOX, 2, os.path.join(OUT, "inbox_cnt_sheet.png"))
sheet(imgs, MODE_BOX, 4, os.path.join(OUT, "inbox_mode_sheet.png"))
contact(imgs, os.path.join(OUT, "inbox_contact.png"))
