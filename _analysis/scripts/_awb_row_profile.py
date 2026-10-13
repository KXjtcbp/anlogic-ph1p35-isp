# -*- coding: utf-8 -*-
"""逐行 R/G 剖面（曲线前域）——用来判定 AWB 的增益是"整帧一个数"还是"帧内爬坡"。

判据：
  · 若前几行 R/G ≈ 1.00 并随行号单调衰减到帧平均附近 ⇒ 增益是"运行中的部分和"
    （前几行用的是它们自己的比值 ⇒ 精确拉平；越往后越接近整帧平均 ⇒ 偏离）⇒ (b) 双缓冲正是解药。
  · 若从第 0 行开始 R/G 就基本平（或与整体一致）⇒ 不存在帧内爬坡 ⇒ (b) 不解释实测缺口。
用法：python _analysis/scripts/_awb_row_profile.py <图> [<图> ...]
"""
import os
import re
import sys
import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAMMA = os.path.join(REPO, "proj", "baseline", "lab3", "user_source", "hdl_source", "isp", "isp_gamma.v")


def load_inv():
    lut = np.zeros(256, np.int32)
    seen = np.zeros(256, bool)
    pat = re.compile(r"mem_b00\s*\[\s*(\d+)\s*\]\s*=\s*8'h([0-9a-fA-F]{2})")
    for line in open(GAMMA, encoding="utf-8", errors="ignore"):
        for k, v in pat.findall(line):
            lut[int(k)] = int(v, 16)
            seen[int(k)] = True
    if seen.sum() != 256:
        sys.exit("mem_b00 解析不完整")
    return np.clip(np.searchsorted(lut, np.arange(256), "left"), 0, 255).astype(np.int32)


def main(inv):
    for path in sys.argv[1:]:
        a = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
        h, w = a.shape[:2]
        # 去掉三块 OSD 框的列范围（屏幕坐标 ×1.5）：0..270 与 360..900/2
        cols = np.ones(w, bool)
        for x0, x1 in [(0, 270), (540, 900), (247, 405)]:
            cols[x0:x1] = False
        p = inv[a]
        prof = []
        for y in range(0, h, 20):
            row = p[y, cols]
            r, g = row[:, 0].mean(), row[:, 1].mean()
            prof.append((y, r / max(g, 1e-9), r, g))
        tail = " ".join("%d:%.3f" % (y, v) for y, v, _, _ in prof[:12])
        mid = " ".join("%d:%.3f" % (y, v) for y, v, _, _ in prof[12::6])
        print("%s" % os.path.basename(path))
        print("   曲线前 R/G  前240行: %s" % tail)
        print("   其余(每120行)     : %s" % mid)
        print()


if __name__ == "__main__":
    main(load_inv())
