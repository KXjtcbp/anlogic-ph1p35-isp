# -*- coding: utf-8 -*-
"""色彩修复（改动 A 黑位 / 改动 B AWB 增益）上板验证。
用法: python _verify_fix_2011.py [曲线旁路图] [曲线启用图]
默认取 captures\\2026-10-11_色彩修复验证\\ 下的 20_ / 21_。
"""
import os
import re
import sys
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"E:\FPGA"
DIR = os.path.join(ROOT, "captures", "2026-10-11_色彩修复验证")
D_A = os.path.join(DIR, "20_SW1上SW2下SW3上SW4上.png")   # SW2 down = curve bypass = linear
D_B = os.path.join(DIR, "21_SW1上SW2上SW3上SW4上.png")   # SW2 up   = curve enabled
GAMMA_V = os.path.join(ROOT, "proj", "baseline", "lab3", "user_source",
                       "hdl_source", "isp", "isp_gamma.v")

if len(sys.argv) > 2:
    D_A, D_B = sys.argv[1], sys.argv[2]

OSD_BOXES = [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]


def osd_mask(w, h):
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in OSD_BOXES:
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    return m


def load_lut():
    """Parse the 256 mem_b00 assignments out of isp_gamma.v."""
    txt = open(GAMMA_V, "rb").read().decode("utf-8", "replace")
    hits = re.findall(r"mem_b00\[\s*(\d+)\]\s*=\s*8'h([0-9a-fA-F]{1,2})\s*;", txt)
    assert len(hits) == 256, "expected 256 mem_b00 entries, found %d" % len(hits)
    t = [0] * 256
    for idx, val in hits:
        t[int(idx)] = int(val, 16)
    return np.array(t, np.int32)


def stat(path):
    im = Image.open(path).convert("RGB")
    w, h = im.size
    a = np.asarray(im)
    m = osd_mask(w, h)
    px = a[m]
    R = px[:, 0].astype(np.int32)
    G = px[:, 1].astype(np.int32)
    B = px[:, 2].astype(np.int32)
    Y = (77 * R + 150 * G + 29 * B) >> 8
    return dict(im=im, a=a, w=w, h=h, m=m, R=R, G=G, B=B, Y=Y)


def pct(v, q):
    return int(np.percentile(v, q))


def main():
    lut = load_lut()
    reach = set(int(x) for x in np.unique(lut))

    print("=" * 108)
    print("LUT in RTL now : %s" % GAMMA_V)
    print("  anchors 0/1/2/3/4/8/13/16/34/64/96/128/160/200/255 = %s"
          % [int(lut[i]) for i in (0, 1, 2, 3, 4, 8, 13, 16, 34, 64, 96, 128, 160, 200, 255)])
    print("  distinct output codes = %d / 256" % len(reach))

    st = {}
    for tag, p in (("20 (SW2 down = BYPASS)", D_A), ("21 (SW2 up   = CURVE )", D_B)):
        if not os.path.exists(p):
            print("MISSING", p)
            return
        d = stat(p)
        st[tag] = d
        Y, R, G, B = d["Y"], d["R"], d["G"], d["B"]
        print("=" * 108)
        print("%s   %s" % (tag, os.path.basename(p)))
        print("  %dx%d  mtime=%s" % (d["w"], d["h"],
              __import__("time").strftime("%H:%M:%S", __import__("time").localtime(os.path.getmtime(p)))))
        print("  Ymean=%7.3f std=%6.3f p1=%3d p5=%3d p10=%3d p25=%3d p50=%3d p75=%3d p90=%3d p95=%3d p99=%3d max=%3d"
              % (Y.mean(), Y.std(), pct(Y, 1), pct(Y, 5), pct(Y, 10), pct(Y, 25), pct(Y, 50),
                 pct(Y, 75), pct(Y, 90), pct(Y, 95), pct(Y, 99), Y.max()))
        print("  R=%7.2f G=%7.2f B=%7.2f   R/G=%.4f B/G=%.4f   sat=%.2f"
              % (R.mean(), G.mean(), B.mean(), R.mean() / G.mean(), B.mean() / G.mean(),
                 (np.maximum(np.maximum(R, G), B) - np.minimum(np.minimum(R, G), B)).mean()))
        print("  >=250=%.4f%%  <=8=%6.3f%%  <=16=%6.3f%%  ==0=%6.3f%%"
              % (100.0 * (Y >= 250).mean(), 100.0 * (Y <= 8).mean(),
                 100.0 * (Y <= 16).mean(), 100.0 * (Y == 0).mean()))
        # reachable-code occupancy (per channel, and Y)
        badY = 100.0 * (~np.isin(Y, list(reach))).mean()
        badG = 100.0 * (~np.isin(G, list(reach))).mean()
        print("  pixels on UNREACHABLE codes:  Y %.3f%%   G channel %.3f%%" % (badY, badG))
        print("  G histogram codes 0..24 = %s"
              % [int((G == c).sum()) for c in range(25)])
        # per-band uniformity (change B check): horizontal thirds
        bands = []
        for k in range(3):
            sub = np.zeros_like(d["m"])
            sub[k * d["h"] // 3:(k + 1) * d["h"] // 3, :] = d["m"][k * d["h"] // 3:(k + 1) * d["h"] // 3, :]
            r, g, b = d["R"][sub[d["m"]]], d["G"][sub[d["m"]]], d["B"][sub[d["m"]]]
            bands.append((r.mean() / max(g.mean(), 1e-9), b.mean() / max(g.mean(), 1e-9), g.mean()))
        print("  band R/G (top/mid/bot) = %.4f / %.4f / %.4f   (spread %.4f)"
              % (bands[0][0], bands[1][0], bands[2][0],
                 max(b[0] for b in bands) - min(b[0] for b in bands)))
        print("  band B/G (top/mid/bot) = %.4f / %.4f / %.4f   (spread %.4f)"
              % (bands[0][1], bands[1][1], bands[2][1],
                 max(b[1] for b in bands) - min(b[1] for b in bands)))

    # ---- LUT prediction: apply RTL table to shot 20, compare with shot 21 ----
    A = st["20 (SW2 down = BYPASS)"]
    Bt = st["21 (SW2 up   = CURVE )"]
    print("=" * 108)
    print("CHANGE A CHECK -- apply the RTL table to every shot-20 Y pixel, compare to shot-21")
    pred = lut[A["Y"]]
    print("  predicted Ymean=%7.3f std=%6.3f | measured Ymean=%7.3f std=%6.3f"
          % (pred.mean(), pred.std(), Bt["Y"].mean(), Bt["Y"].std()))
    print("  %-6s %-9s %-9s %-9s %s" % ("pct", "#20 byp", "LUT pred", "#21 meas", "diff"))
    for q in (1, 5, 10, 25, 50, 75, 90, 95, 99):
        v20 = pct(A["Y"], q)
        print("  p%-5d %-9d %-9d %-9d %+d" % (q, v20, int(lut[v20]), pct(Bt["Y"], q),
                                              pct(Bt["Y"], q) - int(lut[v20])))
    print("  pixel-exact match rate = %.3f%%" % (100.0 * (pred == Bt["Y"]).mean()))
    print("  mean |pred - meas| = %.3f codes" % np.abs(pred - Bt["Y"]).mean())

    # ---- expected black-point effect ----
    print("=" * 108)
    print("CHANGE A  expected:  <=8 fraction must come back from 0.082%% toward 1-4%%")
    print("  20 (bypass) <=8 = %6.3f%%     21 (curve) <=8 = %6.3f%%" %
          (100.0 * (A["Y"] <= 8).mean(), 100.0 * (Bt["Y"] <= 8).mean()))
    print("  20 (bypass) ==0 = %6.3f%%     21 (curve) ==0 = %6.3f%%" %
          (100.0 * (A["Y"] == 0).mean(), 100.0 * (Bt["Y"] == 0).mean()))

    # ---- save side-by-side + OSD crops ----
    out = os.path.join(ROOT, "_analysis", "out")
    sa = A["im"].resize((760, 428), Image.LANCZOS)
    sb = Bt["im"].resize((760, 428), Image.LANCZOS)
    sh = Image.new("RGB", (760, 864), (30, 30, 30))
    sh.paste(sa, (0, 0))
    sh.paste(sb, (0, 436))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sh)
    d.text((8, 8), "20  SW2 DOWN = curve BYPASS", fill=(255, 255, 0))
    d.text((8, 444), "21  SW2 UP  = curve ENABLED", fill=(255, 255, 0))
    sh.save(os.path.join(out, "fix2011_scene.png"))

    s = A["w"] / 1280.0
    boxes = {"cnt": (540, 150, 900, 228), "mode": (240, 240, 645, 300)}
    tiles = []
    for tag, d_ in (("20", A), ("21", Bt)):
        im = d_["im"]
        for k in ("cnt", "mode"):
            x0, y0, x1, y1 = [int(v * s) for v in boxes[k]]
            tiles.append(im.crop((x0, y0, x1, y1)).resize(((x1 - x0) * 3, (y1 - y0) * 3), Image.LANCZOS))
    W = max(t.width for t in tiles)
    H = sum(t.height for t in tiles) + 6 * len(tiles)
    osh = Image.new("RGB", (W, H), (20, 20, 20))
    y = 0
    for t in tiles:
        osh.paste(t, (0, y))
        y += t.height + 6
    osh.save(os.path.join(out, "osd_fix2011.png"))
    print("=" * 108)
    print("saved %s" % os.path.join(out, "fix2011_scene.png"))
    print("saved %s" % os.path.join(out, "osd_fix2011.png"))


if __name__ == "__main__":
    main()
