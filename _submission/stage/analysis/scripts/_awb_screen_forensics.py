# -*- coding: utf-8 -*-
"""AWB 屏上偏色的离线取证（只看 PNG，不碰 RTL）。

三个量：
  1) as-displayed     : 采集图上直接量到的 R/G、B/G（A 报的就是这个数）。
  2) pre-gamma(反表)  : 用 isp_gamma.v 的 mem_b00 反表把画面搬回曲线前（AWB 输出域）。
  3) perfect-AWB 模拟 : ★关键★ 把曲线前的 R 通道整体乘 mean(G)/mean(R)（= 一个"数学上
     完全正确的均匀增益"，正是 AWB 该做的事），再看屏上会显示成什么比值。
        · 若结果 ≈1.00 ⇒ 正确的 AWB 在屏上就该显示 1.00 ⇒ 现在显示 0.88 是**真实的曲线前缺陷**
        · 若结果 ≈0.88 ⇒ 屏上这个 R/G 指标本身被"曲线 + 分布形状"带偏了 ⇒ AWB 可能是好的
用法：python _analysis/scripts/_awb_screen_forensics.py <图1> [图2 ...]
"""
import os
import re
import sys
import numpy as np
from PIL import Image

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GAMMA = os.path.join(REPO, "proj", "baseline", "lab3", "user_source", "hdl_source", "isp", "isp_gamma.v")


def load_lut():
    lut = np.zeros(256, np.int32)
    seen = np.zeros(256, bool)
    pat = re.compile(r"mem_b00\s*\[\s*(\d+)\s*\]\s*=\s*8'h([0-9a-fA-F]{2})")
    for line in open(GAMMA, encoding="utf-8", errors="ignore"):
        for k, v in pat.findall(line):      # 一行 4 个赋值，必须 findall
            lut[int(k)] = int(v, 16)
            seen[int(k)] = True
    if seen.sum() != 256:
        sys.exit("mem_b00 解析不完整: %d/256" % seen.sum())
    inv = np.clip(np.searchsorted(lut, np.arange(256), "left"), 0, 255).astype(np.int32)
    return lut, inv


def mask(w, h):
    """stat_imgs.py 的 3 个 OSD 框（屏幕坐标）+ 砍掉顶部 300 行。
    原因：2026-10-12 两行遥测版在内部 y=152/164（屏幕 y≈228/246）又加了两行橙字，
    旧框没覆盖到；橙字 R−G≈+100 会把 R/G 抬上去。"""
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    m[:300, :] = False
    return m


def ratio(r, g):
    return r.mean() / max(g.mean(), 1e-9)


def show(path, lut, inv):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    a = np.asarray(im).astype(np.int32)
    m = mask(w, h)
    d = a[m]
    dR, dG, dB = d[:, 0], d[:, 1], d[:, 2]
    S = dR + dG + dB
    p = inv[d]                       # 反表：搬回曲线前（AWB 输出域）
    pR, pG, pB = p[:, 0], p[:, 1], p[:, 2]
    # perfect-AWB：曲线前把 R/B 各乘一个常数，使曲线前均值相等
    cR = pG.mean() / max(pR.mean(), 1e-9)
    cB = pG.mean() / max(pB.mean(), 1e-9)
    qR = np.clip(np.round(pR * cR), 0, 255).astype(np.int32)
    qB = np.clip(np.round(pB * cB), 0, 255).astype(np.int32)

    print("== %s   (%d px)" % (os.path.basename(path), dR.size))
    print("   720 门限排掉: %6.3f%%  通道和均值 %.1f" % (100.0 * (S >= 720).mean(), S.mean()))
    print("   ① as-displayed : R/G=%.4f B/G=%.4f  R-G=%+.2f B-G=%+.2f  Ymean=%.2f" %
          (ratio(dR, dG), ratio(dB, dG), dR.mean() - dG.mean(), dB.mean() - dG.mean(),
           ((77 * dR + 150 * dG + 29 * dB) >> 8).mean()))
    print("   ② 反表回曲线前 : R/G=%.4f B/G=%.4f  R-G=%+.2f B-G=%+.2f  mean=%.2f/%.2f/%.2f" %
          (ratio(pR, pG), ratio(pB, pG), pR.mean() - pG.mean(), pB.mean() - pG.mean(),
           pR.mean(), pG.mean(), pB.mean()))
    print("   ③ perfect-AWB  : 曲线前 R/G=%.4f  过表后屏上 R/G=%.4f  屏上 B/G=%.4f  (需乘 %.4f / %.4f)" %
          (ratio(qR, pG), ratio(lut[qR], lut[pG]), ratio(lut[qB], lut[pG]), cR, cB))
    bands = []
    for name, y0, y1 in [("上", 300, int(h * 0.45)), ("中", int(h * 0.45), int(h * 0.7)), ("下", int(h * 0.7), h)]:
        sub, sm = a[y0:y1], m[y0:y1]
        pp = inv[sub[sm]]
        bands.append("%s R/G=%.4f" % (name, ratio(pp[:, 0], pp[:, 1])))
    print("   曲线前分带: " + "  ".join(bands))
    print()


if __name__ == "__main__":
    L, I = load_lut()
    for f in sys.argv[1:]:
        show(f, L, I) if os.path.exists(f) else print("MISSING", f)
