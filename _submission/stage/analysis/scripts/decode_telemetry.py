# -*- coding: utf-8 -*-
"""遥测两行解码器（模板匹配版）。

- 字形库直接从 hdmi_mixer.v 的 F_dbg_glyph 解析，不手抄。
- 内部 1280x720 坐标 -> 屏幕 1920x1080 坐标：x1.5。
  第 1 行内部 y=152..161（字形行 k 在 y=152+k），第 2 行内部 y=164..173。
  19 个字符格，格 i 的字形第 j 列在内部 x = 376 + 16*i + j。
- 对 dx,dy 做 ±3 的偏移搜索，取最匹配的一组。
"""
import os, re, sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
# 仓库根：本文件在 <REPO>/_analysis/scripts/ 下 ⇒ 上溯两级。
# 原版写死 E:\FPGA\，别人的克隆不在那里就跑不了（同 compile_check.py 2026-10-12 的可移植性改动）。
# 需要时可用环境变量 FPGA_WS 覆盖。
_HERE = os.path.dirname(os.path.abspath(__file__))
WS = os.environ.get("FPGA_WS") or os.path.dirname(os.path.dirname(_HERE))
MIX = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "hdmi_mixer.v")

# ---------- 1. 解析字形库 ----------
src = open(MIX, encoding="utf-8", errors="replace").read()
glyphs = {}
for m in re.finditer(r"5'd(\d+)\s*:\s*F_dbg_glyph\s*=\s*35'b([01_]+);\s*//\s*(\S+)", src):
    idx = int(m.group(1))
    rows = m.group(2).split("_")
    assert len(rows) == 7 and all(len(r) == 5 for r in rows), rows
    glyphs[idx] = np.array([[int(c) for c in r] for r in rows], dtype=np.int8)
CH = {**{i: "0123456789ABCDEF"[i] for i in range(16)},
      16: "M", 17: "S", 18: "W", 19: "T", 20: "N", 21: "U"}
BLANK = np.zeros((7, 5), dtype=np.int8)
CODES = sorted(glyphs)


def on_mask(a):
    """橙字判据：R 明显高于 B、且够亮。"""
    R, G, B = a[..., 0].astype(np.int32), a[..., 1].astype(np.int32), a[..., 2].astype(np.int32)
    return (R - B > 70) & (R > 130) & (G > 60) & (G < 210)


def sample(mask, y_in, x0_in, dx, dy):
    """取出 19 格 x 7 行 x 5 列 的采样位图。"""
    out = np.zeros((19, 7, 5), dtype=np.int8)
    for i in range(19):
        for k in range(7):
            for j in range(5):
                sx = int(round((x0_in + 16 * i + j) * 1.5)) + dx
                sy = int(round((y_in + k) * 1.5)) + dy
                if 0 <= sy < mask.shape[0] and 0 <= sx < mask.shape[1]:
                    out[i, k, j] = 1 if mask[sy, sx] else 0
    return out


def decode_line(mask, y_in, x0_in=376):
    best = None
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            s = sample(mask, y_in, x0_in, dx, dy)
            txt, tot = [], 0
            for i in range(19):
                cell = s[i]
                if cell.sum() == 0:
                    txt.append(" "); continue
                scores = sorted(((np.abs(glyphs[c] - cell).sum(), c) for c in CODES))
                tot += scores[0][0]
                txt.append(CH[scores[0][1]])
            if best is None or tot < best[0]:
                best = (tot, dx, dy, "".join(txt))
    return best


def stats(a, m):
    px = a[m]
    R, G, B = px[:, 0].astype(np.int64), px[:, 1].astype(np.int64), px[:, 2].astype(np.int64)
    Y = (77 * R + 150 * G + 29 * B) >> 8
    return dict(Ym=Y.mean(), Ys=Y.std(), R=R.mean(), G=G.mean(), B=B.mean(),
                RG=R.mean() / max(G.mean(), 1e-9), BG=B.mean() / max(G.mean(), 1e-9))


def osmask(w, h):
    m = np.ones((h, w), bool)
    s = w / 1280.0
    for x0, y0, x1, y1 in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def run(path, label):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im)
    h, w, _ = a.shape
    mask = on_mask(a)
    l1 = decode_line(mask, 152)
    l2 = decode_line(mask, 164)
    st = stats(a.astype(np.int32), osmask(w, h))
    print("%-24s L1=[%s] r=%d (%+d,%+d)   L2=[%s] r=%d (%+d,%+d)" %
          (label, l1[3], l1[0], l1[1], l1[2], l2[3], l2[0], l2[1], l2[2]))
    print("%-24s   Ymean=%6.2f R/G=%.4f B/G=%.4f  R-G=%+.2f B-G=%+.2f" %
          ("", st["Ym"], st["RG"], st["BG"], st["R"] - st["G"], st["B"] - st["G"]))
    return l1[3], l2[3], st


if __name__ == "__main__":
    d = os.path.join(WS, "inbox")
    files = sorted([f for f in os.listdir(d) if f.lower().endswith(".png")],
                   key=lambda x: os.path.getmtime(os.path.join(d, x)))
    for f in files:
        run(os.path.join(d, f), f)
