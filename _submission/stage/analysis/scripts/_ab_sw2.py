# -*- coding: utf-8 -*-
"""SW2 A/B 分析：曲线旁路 vs 曲线启用。

用 isp_gamma.v 内联的 mem_b00 真值构造可达码集合，
落在"不可达码"上的像素比例 = 曲线是否真的进通路的决定性判据。
"""
import os
import re
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GAMMA = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
LOGO = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\anlogic_logo_rom.v"


def load_lut():
    txt = open(GAMMA, encoding="utf-8", errors="replace").read()
    tab = {}
    for m in re.finditer(r"mem_b00\[\s*(\d+)\]\s*=\s*8'h([0-9a-fA-F]{1,2})", txt):
        tab[int(m.group(1))] = int(m.group(2), 16)
    assert len(tab) == 256, "only parsed %d of 256 entries" % len(tab)
    return [tab[i] for i in range(256)]


def load_logo():
    """{(r,g,b): count} for opaque logo pixels."""
    from collections import Counter
    c = Counter()
    for m in re.finditer(r"O_pixel\s*=\s*25'h([0-9a-fA-F]{7})", open(LOGO, encoding="utf-8", errors="replace").read()):
        w = int(m.group(1), 16)
        if (w >> 24) & 1:
            c[((w >> 16) & 255, (w >> 8) & 255, w & 255)] += 1
    return c


def osd_mask(w, h):
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def unreach_frac(a, unreach):
    """a: HxWx3 uint8 -> (overall, per-channel, dark<=60)."""
    u = np.zeros(256, bool)
    u[unreach] = True
    out = {}
    out["all"] = float(u[np.asarray(a).ravel()].mean() * 100)
    for i, ch in enumerate("RGB"):
        flat = a[:, :, i].ravel()
        out[ch] = float(u[flat].mean() * 100)
        d = flat[flat <= 60]
        out[ch + "_dark"] = float(u[d].mean() * 100) if d.size else float("nan")
    lum = (77 * a[:, :, 0].astype(np.int32) + 150 * a[:, :, 1].astype(np.int32) + 29 * a[:, :, 2].astype(np.int32)) >> 8
    out["Y"] = float(u[lum.ravel()].mean() * 100)
    dd = lum.ravel(); dd = dd[dd <= 60]
    out["Y_dark"] = float(u[dd].mean() * 100) if dd.size else float("nan")
    return out


def hist_gaps(a, ch, hi=40):
    """print counts for codes 0..hi on channel ch."""
    h = np.bincount(a[:, :, ch].ravel(), minlength=256)
    return h[:hi + 1]


def top_colors(patch):
    from collections import Counter
    c = Counter(map(tuple, patch.reshape(-1, 3)))
    return c.most_common(6)


def report(path, lut, unreach, logo):
    im = Image.open(path).convert("RGB")
    a = np.asarray(im).astype(np.uint8)
    h, w, _ = a.shape
    print("=" * 100)
    print("FILE   %s" % path)
    print("SIZE   %dx%d" % (w, h))
    m = osd_mask(w, h)
    px = a[m]
    R, G, B = px[:, 0].astype(np.int32), px[:, 1].astype(np.int32), px[:, 2].astype(np.int32)
    Y = (77 * R + 150 * G + 29 * B) >> 8
    print("SCENE  Y mean=%.3f std=%.3f p1=%d p10=%d p50=%d p90=%d p99=%d max=%d  >=250=%.3f%%  <=8=%.2f%%" % (
        Y.mean(), Y.std(), np.percentile(Y, 1), np.percentile(Y, 10), np.percentile(Y, 50),
        np.percentile(Y, 90), np.percentile(Y, 99), Y.max(),
        100.0 * (Y >= 250).mean(), 100.0 * (Y <= 8).mean()))
    print("       R=%.2f G=%.2f B=%.2f   R/G=%.4f B/G=%.4f" % (
        R.mean(), G.mean(), B.mean(), R.mean() / max(G.mean(), 1e-9), B.mean() / max(G.mean(), 1e-9)))
    f = unreach_frac(a, unreach)
    print("UNREACH  all=%.3f%%  Y=%.3f%%  R=%.3f%% G=%.3f%% B=%.3f%%   |  dark<=60: Y=%.2f%% R=%.2f%% G=%.2f%% B=%.2f%%" % (
        f["all"], f["Y"], f["R"], f["G"], f["B"], f["Y_dark"], f["R_dark"], f["G_dark"], f["B_dark"]))
    # logo identity
    s = w / 1280.0
    lp = a[0:int(170 * s), 0:int(170 * s)]
    print("LOGO   top6 = %s" % (top_colors(lp),))
    for col, cnt in logo.most_common(3):
        print("       ROM %-14s x%-5d -> want exact" % (str(col), cnt))
    # dark histogram
    hg = hist_gaps(a, 1, 20)
    print("G hist codes 0..20 = %s" % (list(map(int, hg)),))
    hr = hist_gaps(a, 0, 20)
    print("R hist codes 0..20 = %s" % (list(map(int, hr)),))
    return a, f


def main():
    lut = load_lut()
    reach = sorted(set(lut))
    unreach = sorted(set(range(256)) - set(reach))
    print("isp_gamma.v mem_b00 -> %d distinct output codes, %d unreachable" % (len(reach), len(unreach)))
    print("reachable prefix : %s" % reach[:40])
    print("unreachable      : %s" % unreach)
    logo = load_logo()
    files = sys.argv[1:] or [
        r"E:\FPGA\captures\2026-10-11_S曲线AB验证\10_SW1上_SW2下_曲线旁路_CNT574558.png",
        r"E:\FPGA\captures\2026-10-11_S曲线AB验证\11_SW1上_SW2上_曲线启用_CNT574725.png",
    ]
    res = {}
    for p in files:
        if not os.path.exists(p):
            print("MISSING", p); continue
        res[p] = report(p, lut, unreach, logo)
    print("=" * 100)
    print("VERDICT")
    for p, (a, f) in res.items():
        print("  %-46s unreach(all)=%6.3f%%  unreach(Y<=60)=%6.2f%%" % (
            os.path.basename(p), f["all"], f["Y_dark"]))


if __name__ == "__main__":
    main()
