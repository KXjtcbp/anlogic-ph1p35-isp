# -*- coding: utf-8 -*-
"""裁出 14 张 17:00 采集图的 OSD 文本（CNT 行 + MODE 行），放大拼版。"""
import os, sys, glob
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')
ROOT = r'E:\FPGA'
OUT = os.path.join(ROOT, '_analysis', 'out')
files = sorted(glob.glob(os.path.join(ROOT, 'Screenshot 2026-10-11 17-0*.png')))

# 1920x1080 采集图：OSD 相对 1280x720 设计坐标缩放 1.5x
S = 1.5
# CNT 窗口 @(375,120) 200x24 ; MODE 窗口 @(176,176) 84x10
cnt_box = (int(360 * S), int(100 * S), int(600 * S), int(152 * S))
mode_box = (int(160 * S), int(160 * S), int(430 * S), int(200 * S))

Z = 3
try:
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 16)
except Exception:
    font = ImageFont.load_default()

rows = []
for p in files:
    im = Image.open(p).convert('RGB')
    c = im.crop(cnt_box).resize(((cnt_box[2] - cnt_box[0]) * Z, (cnt_box[3] - cnt_box[1]) * Z), Image.LANCZOS)
    m = im.crop(mode_box).resize(((mode_box[2] - mode_box[0]) * Z, (mode_box[3] - mode_box[1]) * Z), Image.LANCZOS)
    rows.append((os.path.basename(p)[-12:-4], c, m))

w1 = max(r[1].size[0] for r in rows)
w2 = max(r[2].size[0] for r in rows)
lab = 150
W = lab + w1 + 20 + w2
H = sum(max(r[1].size[1], r[2].size[1]) + 6 for r in rows)
sheet = Image.new('RGB', (W, H), (18, 18, 18))
d = ImageDraw.Draw(sheet)
y = 0
for name, c, m in rows:
    rh = max(c.size[1], m.size[1])
    d.text((6, y + rh // 2 - 8), name, font=font, fill=(255, 230, 60))
    sheet.paste(c, (lab, y))
    sheet.paste(m, (lab + w1 + 20, y))
    y += rh + 6
sp = os.path.join(OUT, 'osd_1700.png')
sheet.save(sp)
print('saved', sp, sheet.size)
print('CNT box', cnt_box, ' MODE box', mode_box)
