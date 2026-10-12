# -*- coding: utf-8 -*-
"""对同一机位的三个时间点做「隐藏细节」检查：
   17:00-42 (清晰室内)  vs  19:35-53 (S曲线A/B)  vs  23:37-04 (本次)
做法：高通（原图 − 大核高斯）+ 强增益，看镜头里到底还有没有细节。"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R = r"E:\FPGA"
OUT = os.path.join(R, "_analysis", "out")

SRC = [
    ("17:00:42  CNT010296  (室内常光, 清晰)", os.path.join(R, "captures", "2026-10-11_采集链未校准", "04_MODE0_室内常光_CNT010296.png")),
    ("19:35:53  CNT574558  (S曲线A/B 旁路)", os.path.join(R, "captures", "2026-10-11_S曲线AB验证", "10_SW1上_SW2下_曲线旁路_CNT574558.png")),
    ("23:37:04  CNT002227  (本次验证 旁路)", os.path.join(R, "captures", "2026-10-11_色彩修复验证", "20_SW1上_SW2下_曲线渐变态_CNT002227.png")),
    ("23:37:06  CNT002335  (本次验证 曲线)", os.path.join(R, "captures", "2026-10-11_色彩修复验证", "21_SW1上_SW2上_曲线启用_灰度渐变测试面_CNT002335.png")),
]
# fix names that may differ
for i, (lab, p) in enumerate(SRC):
    if not os.path.exists(p):
        d = os.path.dirname(p)
        base = lab.split()[-2] if False else None
        # fall back: search for CNT substring in the dir
        key = lab.split("CNT")[1][:6]
        for f in os.listdir(d):
            if key in f:
                SRC[i] = (lab, os.path.join(d, f))
                break

tiles = []
print("%-42s %-12s %-10s %-10s %-10s" % ("file", "size", "Ymean", "Ystd", "LapVar*"))
for lab, p in SRC:
    if not os.path.exists(p):
        print("MISSING  %s   (%s)" % (lab, p)); continue
    im = Image.open(p).convert("L")
    w, h = im.size
    g = np.asarray(im, np.float32)
    # large-kernel blur -> high-pass
    blur = np.asarray(im.filter(ImageFilter.GaussianBlur(6)), np.float32)
    hp = g - blur
    gain = 8.0
    vis = np.clip(128 + hp * gain, 0, 255).astype(np.uint8)
    print("%-42s %-12s %10.2f %10.2f %10.3f   hp_std=%.3f  hp_p99=%.1f"
          % (lab, "%dx%d" % (w, h), g.mean(), g.std(), np.var(hp), hp.std(), np.percentile(np.abs(hp), 99)))
    tiles.append((lab, Image.fromarray(vis).resize((640, 360), Image.LANCZOS)))

if tiles:
    sh = Image.new("RGB", (640, (360 + 18) * len(tiles)), (20, 20, 20))
    d = ImageDraw.Draw(sh)
    y = 0
    for lab, t in tiles:
        sh.paste(t.convert("RGB"), (0, y + 18))
        d.text((4, y + 3), lab + "   high-pass x%d" % 8, fill=(255, 255, 0))
        y += 360 + 18
    sh.save(os.path.join(OUT, "focus_compare.png"))
    print("saved %s  %s" % (os.path.join(OUT, "focus_compare.png"), sh.size))
