# -*- coding: utf-8 -*-
"""判定 SW2 曲线极性（哪张图是「曲线开」）并量化曲线前域的通道差。

做法：从 isp_gamma.v 解析 mem_b00 的 256 项 LUT，然后对两张同场景图做
  1) 点对点预测：mean(LUT(a)) 是否等于 mean(b)、逐像素 |LUT(a)-b|；
  2) 经验传递函数 e(v)=mean(b | a==v)，与 LUT 和恒等各比一次残差。
哪个方向残差小，就说明「被 LUT 作用的是那张图」（即它的 SW2=0=曲线启用）。

用法: python _gamma_polarity_check.py <图A> <图B> [图C ...]
遮罩与统计口径与 stat_imgs.py 完全一致（3 块 OSD）。
"""
import os
import re
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
GAMMA_V = os.path.join(
    REPO, "proj", "baseline", "lab3", "user_source", "hdl_source", "isp", "isp_gamma.v"
)

BOXES = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]


def load_lut(path=GAMMA_V):
    """解析 mem_b00[<n>] = 8'hXX，返回 256 项数组（只认带数字下标的赋值）。"""
    pat = re.compile(r"mem_b00\[\s*(\d+)\s*\]\s*=\s*8'h([0-9a-fA-F]{2})")
    d = {}
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            for m in pat.finditer(line):
                d[int(m.group(1))] = int(m.group(2), 16)
    if len(d) != 256:
        raise SystemExit("LUT 解析不完整: %d/256 项 (%s)" % (len(d), path))
    return np.array([d[i] for i in range(256)], dtype=np.int32)


def osd_mask(w, h):
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in BOXES:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def load(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
    h, w = a.shape[:2]
    return a, osd_mask(w, h)


def basic(name, a, m):
    px = a[m]
    R, G, B = px[:, 0], px[:, 1], px[:, 2]
    Y = (77 * R + 150 * G + 29 * B) >> 8
    print("%-46s %dx%d n=%d Ymean=%7.3f | R=%6.2f G=%6.2f B=%6.2f "
          "R-G=%+6.3f B-G=%+6.3f R/G=%.4f B/G=%.4f"
          % (name, a.shape[1], a.shape[0], Y.size, Y.mean(),
             R.mean(), G.mean(), B.mean(),
             R.mean() - G.mean(), B.mean() - G.mean(),
             R.mean() / max(G.mean(), 1e-9), B.mean() / max(G.mean(), 1e-9)))
    return px


def emp_map(x, y):
    """e[v] = mean(y | x == v)，cnt[v] = 样本数。x/y 为展平后的 int 数组。"""
    cnt = np.bincount(x, minlength=256).astype(np.float64)
    s = np.bincount(x, weights=y.astype(np.float64), minlength=256)
    e = np.where(cnt > 0, s / np.maximum(cnt, 1.0), np.nan)
    return e, cnt


def compare(tag, A, B, lut, mincnt=200):
    """把 A 当作「曲线前」，检查 B 是否等于 LUT(A)。"""
    a = A.ravel()
    b = B.ravel()
    lb = lut[a]  # LUT(A) 的逐像素预测
    dcnt = b - lb
    dd = b - a
    e, cnt = emp_map(a, b)
    v = (cnt >= mincnt) & np.isfinite(e)
    print("  [%s] 点对点: mean(LUT(A))=%7.3f  vs  mean(B)=%7.3f  (差 %+7.3f)"
          % (tag, lb.mean(), b.mean(), b.mean() - lb.mean()))
    print("             mean|LUT(A)-B|=%6.3f   mean|A-B|=%6.3f   corr(A,B)=%.6f"
          % (np.abs(dcnt).mean(), np.abs(dd).mean(),
             np.corrcoef(a, b)[0, 1]))
    print("             经验映射 e(v)=mean(B|A=v)（v 样本>=%d 的 %d 个 bin）:"
          "  mean|e-LUT|=%6.3f   mean|e-恒等|=%6.3f"
          % (mincnt, v.sum(),
             np.abs(e[v] - lut[np.arange(256)[v]]).mean(),
             np.abs(e[v] - np.arange(256)[v]).mean()))
    return e, cnt, v


def main():
    lut = load_lut()
    print("LUT(mem_b00) 抽样: " + " ".join("%d->%d" % (i, lut[i])
          for i in (0, 1, 2, 8, 16, 32, 43, 58, 64, 69, 80, 96, 128, 160, 192, 224, 255)))
    sl = np.diff(lut)
    print("LUT 斜率: 最小 %d @x=%d, 最大 %d @x=%d；暗部 x=8..64 斜率均值 %.3f"
          % (sl.min(), int(np.argmin(sl)), sl.max(), int(np.argmax(sl)),
             sl[8:64].mean()))
    print("LUT 定点: " + " ".join("%d->%d" % (i, lut[i]) for i in (43, 58, 69)))
    print()

    imgs = []
    for p in sys.argv[1:]:
        a, m = load(p)
        px = basic(os.path.basename(p), a, m)
        imgs.append((os.path.basename(p), px))

    print()
    for i in range(len(imgs)):
        for j in range(len(imgs)):
            if i >= j:
                continue
            na, A = imgs[i]
            nb, B = imgs[j]
            print("=== 假设 %s 是曲线前（SW2=0 启用），%s 是曲线后（SW2=1 直通）===" % (na, nb))
            compare("A->B", A, B, lut)
            print("=== 反向假设：%s 是曲线前，%s 是曲线后 ===" % (nb, na))
            compare("B->A", B, A, lut)
            print()

    # ---- 通道差在「曲线前 / 曲线后」两个域的换算 ----
    inv = np.clip(np.searchsorted(lut, np.arange(256), side="left"), 0, 255)
    print("=== 通道差换算（每张图分别按两种假设换算一次）===")
    for name, px in imgs:
        R, G, B = px[:, 0], px[:, 1], px[:, 2]
        g_pre = (inv[R].mean() - inv[G].mean(), inv[B].mean() - inv[G].mean())
        g_post = (lut[R].mean() - lut[G].mean(), lut[B].mean() - lut[G].mean())
        print("%-30s 实测 R-G=%+7.3f B-G=%+7.3f | 当作曲线后→拉回曲线前 R-G=%+7.3f B-G=%+7.3f"
              " | 当作曲线前→推到曲线后 R-G=%+7.3f B-G=%+7.3f"
              % (name[:30], R.mean() - G.mean(), B.mean() - G.mean(),
                 g_pre[0], g_pre[1], g_post[0], g_post[1]))


if __name__ == "__main__":
    main()
