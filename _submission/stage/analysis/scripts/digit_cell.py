# -*- coding: utf-8 -*-
# 自动定位 "MODE n" 状态行，并取最右侧那一簇（就是数字），放大 12 倍。
# 文字色 = hdmi_mixer.v:175 COLOR_ALG_TEXT = 24'h00ff88 = (0,255,136) 亮绿。
# 判别：G 高 且 G 明显大于 B（可把绿底/青蓝底/蓝底/灰底都排除）。
import os
import numpy as np
from PIL import Image

SRC = r"E:\FPGA"
OUT = r"E:\FPGA\_analysis"
# 每张照片状态行大致所在的窗口（原生像素）
win = {
    "IMG_20261006_192101": (700, 1400, 850, 1030),
    "IMG_20261006_192107": (700, 1400, 880, 1080),
    "IMG_20261006_192127": (1400, 2100, 760, 980),
    "IMG_20261006_192131": (900, 1600, 940, 1140),
    "IMG_20261006_192138": (780, 1450, 1030, 1210),
}
for name, (X0, X1, Y0, Y1) in win.items():
    a = np.asarray(Image.open(os.path.join(SRC, name + ".jpg")).convert("RGB")).astype(np.int16)
    sub = a[Y0:Y1, X0:X1]
    R, G, B = sub[..., 0], sub[..., 1], sub[..., 2]
    m = (G > 150) & ((G - B) > 40)
    rows = m.sum(axis=1)
    if rows.max() < 5:
        print(f"{name}: 窗口内命中太少 max={rows.max()}")
        continue
    # 取行方向最大的一段连续区（状态行本体）
    r_on = rows > max(2, rows.max() // 3)
    best, cur = None, None
    for i, v in enumerate(r_on):
        if v and cur is None:
            cur = i
        elif not v and cur is not None:
            if best is None or (i - cur) > (best[1] - best[0]):
                best = (cur, i)
            cur = None
    if cur is not None and (best is None or (len(r_on) - cur) > (best[1] - best[0])):
        best = (cur, len(r_on))
    y0, y1 = best
    band = m[y0:y1, :]
    cols = band.sum(axis=0)
    runs, cur = [], None
    for i, v in enumerate(cols > 0):
        if v and cur is None:
            cur = i
        elif not v and cur is not None:
            runs.append((cur, i)); cur = None
    if cur is not None:
        runs.append((cur, len(cols)))
    # 合并间隔 < 4px 的碎片
    merged = []
    for r in runs:
        if merged and r[0] - merged[-1][1] < 4:
            merged[-1] = (merged[-1][0], r[1])
        else:
            merged.append(list(r))
    print(f"{name}: 状态行 y[{Y0+y0},{Y0+y1}] 字符簇 {[(X0+a_, X0+b_) for a_, b_ in merged]}")
    gx0, gx1 = merged[-1]
    px0, px1 = max(0, gx0 - 10), min(m.shape[1], gx1 + 10)
    py0, py1 = max(0, y0 - 8), min(m.shape[0], y1 + 8)
    cell = sub[py0:py1, px0:px1]
    Image.fromarray(cell.astype(np.uint8)).resize(
        (cell.shape[1]*12, cell.shape[0]*12), Image.LANCZOS).save(os.path.join(OUT, name + "_digitcell_rgb.png"))
    gg = np.clip((cell[..., 1] - np.maximum(cell[..., 0], cell[..., 2])) * 3, 0, 255).astype(np.uint8)
    Image.fromarray(gg).resize((gg.shape[1]*12, gg.shape[0]*12), Image.LANCZOS).save(
        os.path.join(OUT, name + "_digitcell.png"))
    print(f"    -> 数字单元 原生 {cell.shape[1]}x{cell.shape[0]}  (x{X0+px0}..{X0+px1})")
