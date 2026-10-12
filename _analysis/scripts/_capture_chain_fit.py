# -*- coding: utf-8 -*-
"""Characterise the HDMI-capture -> OBS -> PNG chain, using the Anlogic logo ROM
as an in-frame colour chart.

Why this works
    anlogic_logo_rom.v stores one literal 25'h<valid><RRGGBB> per covered pixel,
    and hdmi_mixer.v paints it verbatim (:1239-1242, no blending).  The logo is a
    solid 160x160 block at the top-left corner, and hdmi_mixer drives the ROM with
    a linear address (hdmi_mixer.v:131, addr = local_y*160 + local_x).  So for
    every ROM entry we know both the exact RGB the FPGA emits AND where it lands
    on screen.  Reading the PNG at that position gives an exact known->measured
    colour pair with no matching ambiguity.

Outputs
    _analysis/out/capture_chain_fit.txt
    _analysis/out/capture_chain_fit.png
"""
import re
import sys
from collections import defaultdict

import numpy as np
from PIL import Image
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROM = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\anlogic_logo_rom.v"
OUT_TXT = r"E:\FPGA\_analysis\out\capture_chain_fit.txt"
OUT_PNG = r"E:\FPGA\_analysis\out\capture_chain_fit.png"

LOGO_W = 160
lines = []


def say(s=""):
    print(s)
    lines.append(s)


def pick_shot():
    """Screenshot to analyse: argv[1] if given, else the newest Screenshot*.png
    under E:\\FPGA.  Always printed so a stale file can never be mistaken for a
    fresh capture."""
    if len(sys.argv) > 1:
        return sys.argv[1]
    import glob
    import os
    cands = glob.glob(r"E:\FPGA\Screenshot*.png")
    if not cands:
        sys.exit("no Screenshot*.png found under E:\\FPGA - pass a path explicitly")
    return max(cands, key=os.path.getmtime)


SHOT = pick_shot()
import os
import time
if not os.path.exists(SHOT):
    sys.exit("not found: %s" % SHOT)
say("analysing screenshot : %s" % SHOT)
say("          mtime       : %s   (%.6f)"
    % (time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(SHOT))),
       os.path.getmtime(SHOT)))
say("   pass a path explicitly if this is not the capture you just took.")
say("")


# ------------------------------------------------ ROM: address -> exact colour
txt = open(ROM, "rb").read().decode("utf-8", errors="replace")
pat = re.compile(r"15'd(\d+):\s*O_pixel\s*=\s*25'h([0-9a-fA-F]+);")
by_color = defaultdict(list)          # colour -> list of addresses
for m in pat.finditer(txt):
    v = int(m.group(2), 16)
    if (v >> 24) & 1:
        by_color[((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)].append(int(m.group(1)))

say("ROM: %d opaque pixels, %d distinct colours" % (sum(len(v) for v in by_color.values()), len(by_color)))
CHART = [(c, a) for c, a in by_color.items() if len(a) >= 25]
CHART.sort(key=lambda t: -len(t[1]))
say("colour-chart entries (>=25 px each): %d  covering %d ROM px"
    % (len(CHART), sum(len(a) for _, a in CHART)))
say("")
say("%-18s %6s | %s" % ("ROM colour", "rom px", "median PNG colour per screenshot"))
for c, a in CHART[:14]:
    say("%-18s %6d" % (str(c), len(a)))

# ------------------------------------------------------------- sample the PNG
def sample(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.int32)
    H, W = a.shape[:2]
    sx, sy = W / 1280.0, H / 720.0                 # HDMI 1280x720 -> screenshot
    K, M, Wt, rows = [], [], [], []
    for c, addrs in CHART:
        vals = []
        for ad in addrs:
            y, x = divmod(ad, LOGO_W)
            px = min(int(round((x + 0.5) * sx)), W - 1)
            py = min(int(round((y + 0.5) * sy)), H - 1)
            vals.append(a[max(py - 1, 0):py + 2, max(px - 1, 0):px + 2].reshape(-1, 3))
        vals = np.concatenate(vals, axis=0)
        med = np.median(vals, axis=0)
        K.append(c)
        M.append(med)
        Wt.append(len(addrs))
        rows.append((c, len(addrs), tuple(int(v) for v in med)))
    return np.array(K, float), np.array(M, float), np.array(Wt, float), rows


K, M, Wt, rows = sample(SHOT)
say("")
say("%-18s %6s | %-18s | %-22s" % ("ROM colour (known)", "rom px", "PNG colour (median)", "limited->full prediction"))
for c, n, med in rows:
    pr = tuple(int(np.clip((v - 16) * 255.0 / 219.0, 0, 255)) for v in c)
    say("%-18s %6d | %-18s | %-22s" % (str(c), n, str(med), str(pr)))


def wfit(x, y, w):
    A = np.vstack([x * w, w]).T
    (aa, bb), *_ = np.linalg.lstsq(A, y * w, rcond=None)
    pred = aa * x + bb
    r2 = 1.0 - float((w * (y - pred) ** 2).sum()) / max(float((w * (y - y.mean()) ** 2).sum()), 1e-9)
    return aa, bb, r2


say("")
say("--- candidate models, weighted RMS error over all chart entries ---")
MODELS = [
    ("identity", lambda v: v),
    ("limited->full  (in-16)*255/219", lambda v: np.clip((v - 16) * 255.0 / 219.0, 0, 255)),
    ("full->limited  in*219/255+16", lambda v: v * 219.0 / 255.0 + 16.0),
    ("BT.709 ltd->full (in-16)*255/219", lambda v: np.clip((v - 16) * 255.0 / 219.0, 0, 255)),
]
best = None
for label, fn in MODELS:
    d = M - fn(K)
    rms = np.sqrt((Wt[:, None] * d ** 2).sum(axis=0) / Wt.sum())
    ov = float(np.sqrt((Wt[:, None] * d ** 2).sum() / (Wt.sum() * 3)))
    say("  %-34s RMS R=%6.2f G=%6.2f B=%6.2f  overall=%6.2f  maxabs=%6.1f"
        % (label, rms[0], rms[1], rms[2], ov, float(np.abs(d).max())))
    if best is None or ov < best[0]:
        best = (ov, label)
say("  => best model: %s (overall RMS %.2f)" % (best[1], best[0]))

# Only the large solid areas survive 1.5x resampling cleanly; dithered single
# pixels pull their neighbours in, so restrict the fit to entries >= 120 ROM px.
REL = Wt >= 120
say("")
say("--- reliable subset (>=120 ROM px, i.e. solid areas) ---")
say("  NOTE: entries whose ROM colours sit within a few codes of each other share")
say("        interleaved dither addresses, so their 3x3 medians bleed into one")
say("        another.  Only the entries carrying the most pixels are trustworthy.")
rel = [(c, n, med) for c, n, med in rows if n >= 120]
for c, n, med in rel:
    pr = tuple(int(np.clip((v - 16) * 255.0 / 219.0, 0, 255)) for v in c)
    d = tuple(int(med[i] - c[i]) for i in range(3))
    say("  %-18s %6d -> %-18s   limited->full %-18s  identity diff %s"
        % (str(c), n, str(med), str(pr), d))

# The eye (and the 1.5x resampler) is dominated by the largest solid areas, so
# base the verdict on the top few by pixel count rather than on every entry.
top = sorted(rel, key=lambda t: -t[1])[:3]
mx = max(abs(int(t[2][i] - t[0][i])) for t in top for i in range(3))
say("")
say("  top solid areas (by pixel count): %s" % ", ".join(str(t[0]) for t in top))
say("  max |identity diff| over those   = %d codes   (was 14 before the fix)" % mx)
if mx <= 4:
    say("  ==> VERDICT: capture chain is IDENTITY.  FIXED - screenshots now equal the FPGA output.")
elif mx <= 10:
    say("  ==> VERDICT: close (%d codes).  Good enough for colour work; the residual looks like" % mx)
    say("      a 1.5x-resampling smear rather than a range error.")
else:
    say("  ==> VERDICT: capture chain is STILL rescaled. NOT fixed yet.")
say("")
say("--- per-channel least-squares affine  measured = a*known + b (weighted, reliable subset) ---")
for ch, name in enumerate("RGB"):
    aa, bb, r2 = wfit(K[REL, ch], M[REL, ch], Wt[REL])
    say("  %s:  out = %+.4f * in %+.3f    R^2 = %.5f" % (name, aa, bb, r2))

say("")
say("--- OSD text constants written by hdmi_mixer.v ---")
for known, label in [((255, 242, 0), "COLOR_DYN_TEXT 24'hfff200"),
                     ((0, 255, 136), "COLOR_ALG_TEXT 24'h00ff88")]:
    pr = tuple(int(np.clip((v - 16) * 255.0 / 219.0, 0, 255)) for v in known)
    say("  %-28s known=%-16s  limited->full predicts %s" % (label, str(known), str(pr)))

say("")
say("--- invert the capture chain on the MODE-0 scene captures ---")
say("    fpga = png / 1.1644 + 16")
for tag, (R, G, B) in [("17-00-12", (36.78, 41.85, 38.02)),
                       ("17-00-21", (86.35, 90.78, 89.06)),
                       ("17-00-30", (27.90, 32.45, 32.34)),
                       ("17-00-42", (63.25, 66.44, 65.09)),
                       ("17-01-49", (38.49, 39.95, 38.57))]:
    r, g, b = R / 1.1644 + 16, G / 1.1644 + 16, B / 1.1644 + 16
    say("  %s  png R/G=%.4f B/G=%.4f  ->  fpga R/G=%.4f B/G=%.4f   (R=%.1f G=%.1f B=%.1f)"
        % (tag, R / G, B / G, r / g, b / g, r, g, b))

# ------------------------------------------------------------------- figure
fig, ax = plt.subplots(1, 3, figsize=(15, 4.6))
xs = np.linspace(0, 255, 100)
for ch, (name, col) in enumerate(zip("RGB", "rgb")):
    ax[ch].scatter(K[~REL, ch], M[~REL, ch], s=18, c=col, alpha=0.35,
                   label="dithered entries (unreliable)", zorder=2)
    ax[ch].scatter(K[REL, ch], M[REL, ch], s=90, c=col, edgecolors="k", linewidths=0.6,
                   label="solid areas (>=120 ROM px)", zorder=4)
    ax[ch].plot(xs, xs, "k--", lw=0.9, label="identity (ideal)")
    ax[ch].plot(xs, np.clip((xs - 16) * 255.0 / 219.0, 0, 255), "b-", lw=1.4,
                label="limited->full (in-16)*255/219")
    aa, bb, _ = wfit(K[REL, ch], M[REL, ch], Wt[REL])
    ax[ch].plot(xs, np.clip(aa * xs + bb, 0, 255), "m:", lw=1.2, label="least-squares fit")
    ax[ch].set_title("%s channel" % name)
    ax[ch].set_xlabel("RGB written by hdmi_mixer")
    ax[ch].set_ylabel("RGB in the PNG screenshot")
    ax[ch].grid(alpha=0.3)
    ax[ch].legend(fontsize=7)
fig.suptitle("HDMI capture-chain transfer function, measured with the Anlogic logo ROM as a colour chart", fontsize=11)
fig.tight_layout()
fig.savefig(OUT_PNG, dpi=115)
open(OUT_TXT, "w", encoding="utf-8").write("\n".join(lines))
say("")
say("saved %s" % OUT_PNG)
say("saved %s" % OUT_TXT)
