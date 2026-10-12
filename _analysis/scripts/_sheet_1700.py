# -*- coding: utf-8 -*-
"""对 2026-10-11 17:00-17:02 的 14 张采集图做统计 + 拼版。"""
import os, sys, glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.stdout.reconfigure(encoding='utf-8')

ROOT = r'E:\FPGA'
OUT = os.path.join(ROOT, '_analysis', 'out')
files = sorted(glob.glob(os.path.join(ROOT, 'Screenshot 2026-10-11 17-0*.png')))
print('found %d files' % len(files))


def osd_mask(w, h):
    s = w / 1280.0
    boxes = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in boxes:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def stat(path):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    a = np.asarray(im).astype(np.int32)
    m = osd_mask(w, h)
    px = a[m]
    R, G, B = px[:, 0], px[:, 1], px[:, 2]
    Y = (77 * R + 150 * G + 29 * B) >> 8
    return dict(w=w, h=h, Y=Y, R=R, G=G, B=B)


rows = []
for p in files:
    d = stat(p)
    Y, R, G, B = d['Y'], d['R'], d['G'], d['B']
    r = dict(
        name=os.path.basename(p)[-12:-4],
        w=d['w'], h=d['h'],
        ymean=Y.mean(), ystd=Y.std(),
        p1=np.percentile(Y, 1), p10=np.percentile(Y, 10), p50=np.percentile(Y, 50),
        p90=np.percentile(Y, 90), p99=np.percentile(Y, 99), ymax=Y.max(),
        ov=100.0 * (Y >= 250).mean(), dk=100.0 * (Y <= 8).mean(), z=100.0 * (Y == 0).mean(),
        Rm=R.mean(), Gm=G.mean(), Bm=B.mean(),
        rg=R.mean() / max(G.mean(), 1e-9), bg=B.mean() / max(G.mean(), 1e-9),
    )
    # 额外：色偏诊断（排除近黑像素后的通道均值）
    lum = Y
    sel = lum > 16
    if sel.sum() > 100:
        r['Rl'] = R[sel].mean(); r['Gl'] = G[sel].mean(); r['Bl'] = B[sel].mean()
        r['rgl'] = r['Rl'] / max(r['Gl'], 1e-9); r['bgl'] = r['Bl'] / max(r['Gl'], 1e-9)
        # 饱和度：max-min 通道差
        mx = np.maximum(np.maximum(R, G), B)[sel]
        mn = np.minimum(np.minimum(R, G), B)[sel]
        r['sat'] = (mx - mn).mean()
    else:
        r['Rl'] = r['Gl'] = r['Bl'] = 0; r['rgl'] = r['bgl'] = 0; r['sat'] = 0
    rows.append(r)

hdr = ('%-9s %5s %4s | %7s %6s %4s %4s %4s %4s %4s %4s | %7s %6s %6s | %7s %7s %7s %6s %6s | %6s'
       % ('name', 'w', 'h', 'Ymean', 'Ystd', 'p1', 'p10', 'p50', 'p90', 'p99', 'max',
          'ov%', 'dk%', 'z%', 'R', 'G', 'B', 'R/G', 'B/G', 'sat'))
print(hdr)
print('-' * len(hdr))
for r in rows:
    print('%-9s %5d %4d | %7.2f %6.2f %4d %4d %4d %4d %4d %4d | %7.3f %6.2f %6.2f | %7.2f %7.2f %7.2f %6.3f %6.3f | %6.2f'
          % (r['name'], r['w'], r['h'], r['ymean'], r['ystd'], r['p1'], r['p10'], r['p50'],
             r['p90'], r['p99'], r['ymax'], r['ov'], r['dk'], r['z'],
             r['Rm'], r['Gm'], r['Bm'], r['rg'], r['bg'], r['sat']))
print()
print('--- 排除近黑(Y<=16)后的通道比 ---')
for r in rows:
    print('%-9s R=%7.2f G=%7.2f B=%7.2f  R/G=%.4f B/G=%.4f' %
          (r['name'], r['Rl'], r['Gl'], r['Bl'], r['rgl'], r['bgl']))

# ---- 拼版：4 列 x 4 行 ----
TH_W = 320
cols, rowsn = 4, 4
tiles = []
try:
    font = ImageFont.truetype('C:/Windows/Fonts/consola.ttf', 13)
except Exception:
    font = ImageFont.load_default()

for i, p in enumerate(files):
    im = Image.open(p).convert('RGB')
    w, h = im.size
    th = int(h * TH_W / w)
    tiles.append((i + 1, im.resize((TH_W, th), Image.LANCZOS)))

tile_h = max(t[1].size[1] for t in tiles)
sheet = Image.new('RGB', (cols * TH_W, rowsn * (tile_h + 18)), (24, 24, 24))
d = ImageDraw.Draw(sheet)
for k, (idx, tim) in enumerate(tiles):
    cx = (k % cols) * TH_W
    cy = (k // cols) * (tile_h + 18)
    d.text((cx + 4, cy + 2), '#%02d  %s' % (idx, os.path.basename(files[k])[-12:-4]), font=font, fill=(255, 230, 60))
    sheet.paste(tim, (cx, cy + 18))
sp = os.path.join(OUT, 'sheet_1700.png')
sheet.save(sp)
print('\nsaved', sp, sheet.size)
