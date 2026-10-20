# -*- coding: utf-8 -*-
"""AWB ChipWatcher 导出解析器。

用法：
    python parse_awb_csv.py <导出的.csv> [更多.csv ...]

设计目标：不管你导出时给信号起了什么名字，也不管 tdata 是二进制串还是十六进制，
都能自动识别并按帧统计出「输入帧均值 / 输出帧均值 / 商 / 应用增益」，
从而判断 AWB 是否真的把 R、B 拉平到 G。

背景（踩过的坑，已内置处理）：
  1. ChipWatcher 导出的波形数据列，tdata 是**二进制字符串**（128 个 '0'/'1'），
     不是十六进制。早期脚本用 int(x,16) 解析全部错。
  2. 列名会被加上实例层级前缀，例如
     `u_awb.sum_r[0][31:0]` 或 `S_ISP_O_tdata[127:0]`，所以用子串匹配。
  3. `I_tuser` 在 ISP 输入侧是**每帧一个**，不是每行一个。
"""
import os
import re
import sys
import csv

import numpy as np


def find_col(header, *keys):
    """返回第一个名字里同时含全部 key 的列下标（大小写不敏感）。"""
    for i, h in enumerate(header):
        hl = h.lower()
        if all(k.lower() in hl for k in keys):
            return i
    return None


def to_int(tok):
    tok = tok.strip()
    if tok == "" or tok.lower() in ("x", "z", "nan"):
        return None
    if set(tok) <= {"0", "1"} and len(tok) > 4:      # 二进制串
        return int(tok, 2)
    try:
        return int(tok, 16)
    except ValueError:
        try:
            return int(tok, 10)
        except ValueError:
            return None


def parse(path):
    print("=" * 78)
    print("FILE:", path, " (%d B)" % os.path.getsize(path))
    with open(path, "r", encoding="utf-8", errors="replace", newline="") as fh:
        rows = list(csv.reader(fh))
    if not rows:
        print("  empty"); return
    header = rows[0]
    data = rows[1:]
    print("  columns (%d): %s" % (len(header), ", ".join(header[:14])))
    if len(header) > 14:
        print("                ... %s" % ", ".join(header[14:]))
    print("  samples:", len(data))

    # 关键列
    c_valid = find_col(header, "tvalid")
    c_sumr = find_col(header, "sum_r")
    c_sumg = find_col(header, "sum_g")
    c_sumb = find_col(header, "sum_b")
    c_tgtr = find_col(header, "tgt") if find_col(header, "tgt") else find_col(header, "in_r_tgt")
    c_gainr = find_col(header, "in_r_r1")
    c_gainb = find_col(header, "in_b_r1")
    c_done = find_col(header, "done")
    c_tuser = find_col(header, "tuser")

    def col(idx):
        if idx is None:
            return None
        out = []
        for r in data:
            out.append(to_int(r[idx]) if idx < len(r) else None)
        return np.array([np.nan if v is None else v for v in out], dtype=np.float64)

    for nm, idx in (("tvalid", c_valid), ("tuser", c_tuser), ("done", c_done),
                    ("sum_r[0]", c_sumr), ("sum_g[0]", c_sumg), ("sum_b[0]", c_sumb),
                    ("in_r_tgt1", c_tgtr), ("in_r_r1", c_gainr), ("in_b_r1", c_gainb)):
        c = col(idx)
        if c is None:
            print("  %-10s : (not present)" % nm); continue
        v = c[~np.isnan(c)]
        if v.size == 0:
            print("  %-10s : all x/z" % nm); continue
        print("  %-10s : n=%4d  min=%d  max=%d  first=%d  last=%d  nonzero=%d" %
              (nm, v.size, int(v.min()), int(v.max()), int(v[0]), int(v[-1]), int((v != 0).sum())))

    # ---- 帧边界（tuser 上升沿）----
    if c_tuser is not None:
        t = col(c_tuser)
        edges = np.where((t[1:] > 0) & (t[:-1] == 0))[0] + 1
        if edges.size == 0:
            hi = np.where(t > 0)[0]
            edges = hi[:1] if hi.size else np.array([], dtype=int)
        print("\n  frame boundaries (tuser rising edges) at samples:", edges[:8].tolist(),
              "..." if edges.size > 8 else "")
    else:
        edges = np.array([], dtype=int)

    # ---- 帧内统计（用 tvalid 门控）----
    if c_sumr is not None and c_sumg is not None:
        sr, sg, sb = col(c_sumr), col(c_sumg), col(c_sumb)
        vmask = (col(c_valid) > 0) if c_valid is not None else np.ones(len(data), bool)
        print("\n  --- sum_* at the END of each frame (last valid sample before reset) ---")
        bounds = list(edges) + [len(data)]
        for k in range(min(len(bounds) - 1, 6)):
            a, b = int(bounds[k]), int(bounds[k + 1])
            seg = np.arange(a, b)
            seg = seg[vmask[seg]]
            if seg.size == 0:
                continue
            last = seg[-1]
            R, G = sr[last], sg[last]
            B = sb[last] if sb is not None else np.nan
            ratio = (G / R) if R else np.nan
            print("    frame %d: samples[%d..%d]  sum_r=%12.0f sum_g=%12.0f sum_b=%12.0f"
                  "  G/R=%.4f  B/G=%.4f  => target gain_R=%.4f" %
                  (k, a, b, R, G, B, (G / R if R else np.nan), (G / B if B else np.nan), ratio))

    # ---- 增益是否收敛 / 是否停在 1.000x ----
    for nm, idx in (("in_r_r1", c_gainr), ("in_b_r1", c_gainb), ("in_r_tgt1", c_tgtr)):
        c = col(idx)
        if c is None:
            continue
        v = c[~np.isnan(c)]
        if v.size == 0:
            continue
        uniq = np.unique(v.astype(np.int64))
        hexs = ["0x%X(%.4fx)" % (u, u / 65536.0) for u in uniq[:6]]
        print("\n  %s distinct values: %d  -> %s" % (nm, uniq.size, ", ".join(hexs)))
        if np.all(uniq == 0x10000):
            print("    !! STUCK at 1.000x -> the gain is never updated")
        elif uniq.size <= 3:
            print("    !! nearly constant -> damping may not be running")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        d = r"E:\FPGA\raw_exports"
        if os.path.isdir(d):
            print("\n(no argument given; found these CSVs in %s)" % d)
            for f in sorted(os.listdir(d)):
                if f.lower().endswith(".csv"):
                    print("   ", os.path.join(d, f))
        sys.exit(0)
    for p in sys.argv[1:]:
        if os.path.exists(p):
            parse(p)
        else:
            print("MISSING", p)
