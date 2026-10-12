# -*- coding: utf-8 -*-
"""B 的 P0-2 / P1-4 / P4-9 补充：releases 全景、K=45 归档、6 张基准图的 MODE 与开关。"""
import os, sys, glob, shutil, hashlib, datetime
import numpy as np
from PIL import Image, ImageDraw
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
line = "=" * 78


def sec(t):
    print("\n" + line + "\n" + t + "\n" + line)


# ------------------------------------------------------------------ A
sec("A  proj\\releases 全景（归档约定目录）")
r = os.path.join(WS, "proj", "releases")
for root, dirs, files in os.walk(r):
    for f in sorted(files):
        p = os.path.join(root, f)
        print("   %-62s %9d B  %s" % (
            os.path.relpath(p, r), os.path.getsize(p),
            datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%Y-%m-%d %H:%M")))

sec("A2  把 K=45 基线 (f4f9ce5e...) 也归档进 proj\\releases")
src = os.path.join(WS, r"_backup\20261012_bit_K45_0149\camera_to_dsi_display.bit")
dst_dir = os.path.join(r, "2026-10-12_K45基线")
os.makedirs(dst_dir, exist_ok=True)
if os.path.exists(src):
    shutil.copy2(src, os.path.join(dst_dir, "camera_to_dsi_display.bit"))
    p = os.path.join(dst_dir, "camera_to_dsi_display.bit")
    print("   写入 %s" % os.path.relpath(p, WS))
    print("   md5 = %s" % hashlib.md5(open(p, "rb").read()).hexdigest())

sec("A3  _backup 里其他历史 bit")
for p in sorted(glob.glob(os.path.join(WS, "_backup", "**", "*.bit"), recursive=True)):
    print("   %-70s %9d B  md5=%s" % (
        os.path.relpath(p, WS), os.path.getsize(p),
        hashlib.md5(open(p, "rb").read()).hexdigest()))

# ------------------------------------------------------------------ B
sec("B  P1-4  两批基准图里 OSD 显示的 MODE（裁 (240,250,660,292)，1920 空间）")
imgs = []
for d in (r"captures\2026-10-12_AWB诊断基准面",
          r"captures\2026-10-12_照亮后三图"):
    for f in sorted(os.listdir(os.path.join(WS, d))):
        if f.lower().endswith(".png"):
            imgs.append(os.path.join(WS, d, f))
TILES = []
for p in imgs:
    im = Image.open(p).convert("RGB")
    w, h = im.size
    s = w / 1280.0
    box = (int(240 * s), int(250 * s), int(660 * s), int(292 * s))
    c = im.crop(box).resize((840, 84), Image.LANCZOS)
    TILES.append((os.path.relpath(p, WS), c))
    a = np.asarray(im.crop(box)).astype(np.int32)
    # MODE 绿字 bbox
    g = np.all((a >= [0, 150, 40]) & (a <= [110, 255, 190]), axis=2)
    ys, xs = np.where(g)
    bb = "x[%d..%d] y[%d..%d] n=%d" % (xs.min(), xs.max(), ys.min(), ys.max(), len(ys)) if len(ys) else "未找到"
    print("   %-58s  %s" % (os.path.basename(p), bb))
sheet = Image.new("RGB", (900, len(TILES) * 100 + 10), (25, 25, 25))
d = ImageDraw.Draw(sheet)
for i, (nm, c) in enumerate(TILES):
    sheet.paste(c, (55, i * 100 + 6))
    d.text((4, i * 100 + 40), nm.split("\\")[-1][:12], fill=(255, 255, 0))
sheet.save(os.path.join(WS, r"_analysis\out\bench_mode_sheet.png"))
print("   拼图 -> _analysis\\out\\bench_mode_sheet.png (%s)" % (sheet.size,))
