# -*- coding: utf-8 -*-
"""差值到底是"处处均匀的偏移"还是"随位置变化的场景性变化"：6x6 网格统计 + 差值图。"""
import numpy as np
from PIL import Image

DARK = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-36.png"
BRIGHT = r"E:\FPGA\captures\2026-10-11_AB曲线作废\Screenshot 2026-10-11 00-07-23.png"
OUT = r"E:\FPGA\_analysis\out\ab_diffmap.png"

def y_of(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    return (77 * a[:, :, 0] + 150 * a[:, :, 1] + 29 * a[:, :, 2]) >> 8

d = y_of(DARK); b = y_of(BRIGHT)
H, W = d.shape
print("整体 Y: 暗 %.2f  亮 %.2f  差均值 %+.2f" % (d.mean(), b.mean(), (b - d).mean()))
print("\n6x6 网格： 暗均值 -> 亮均值 (差)")
for i in range(6):
    row = []
    for j in range(6):
        sl = (slice(i * H // 6, (i + 1) * H // 6), slice(j * W // 6, (j + 1) * W // 6))
        md, mb = d[sl].mean(), b[sl].mean()
        row.append("%5.1f>%5.1f(%+5.1f)" % (md, mb, mb - md))
    print("  " + " ".join(row))

# 差值图：把 (b-d) 映射到伪彩
diff = np.clip(b - d, -80, 80)
r = np.clip(diff, 0, 80) / 80 * 255
bl = np.clip(-diff, 0, 80) / 80 * 255
g = (1 - np.abs(diff) / 80) * 120
rgbd = np.dstack([r, g, bl]).astype(np.uint8)
# 暗图/亮图 的可视化（按 4x 分箱平均后线性拉伸到 0-255）
def vis(a):
    a = a.astype(np.float64)
    lo, hi = np.percentile(a, 1), np.percentile(a, 99)
    return np.clip((a - lo) / max(hi - lo, 1) * 255, 0, 255).astype(np.uint8)
panels = [vis(d), vis(b), rgbd]
h2 = H // 2; w2 = W // 2
canvas = Image.new("RGB", (w2, h2 * 3 + 16), (30, 30, 30))
for k, p in enumerate(panels):
    im = Image.fromarray(p).resize((w2, h2), Image.BOX)
    canvas.paste(im, (0, k * (h2 + 8)))
canvas.save(OUT)
print("\n差值图(红=变亮, 蓝=变暗) saved " + OUT)
