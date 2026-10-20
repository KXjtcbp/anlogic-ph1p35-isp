# -*- coding: utf-8 -*-
"""Use the Anlogic logo ROM as a colour chart for the capture chain.

anlogic_logo_rom.v stores, for every covered pixel, a literal
    15'd<addr> : O_pixel = 25'h<valid><RRGGBB>;
so hdmi_mixer.v paints that EXACT RGB value (no blending, :1239-1242).
The logo therefore contains a fixed set of known colours that travel through
HDMI -> capture card -> OBS -> PNG.  Comparing the known palette with the
measured pixels characterises the capture chain.

Outputs
  - the ROM palette (colour -> number of pixels in the logo)
  - the measured histogram of the logo window
  - candidate (known -> measured) pairs via nearest-neighbour matching
  - per-channel fit of the capture transfer curve
"""
import re
import sys
from collections import Counter

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROM = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\anlogic_logo_rom.v"
SHOTS = [r"E:\FPGA\Screenshot 2026-10-11 17-00-21.png",
         r"E:\FPGA\Screenshot 2026-10-11 17-00-42.png"]

# ---------------------------------------------------------------- ROM palette
txt = open(ROM, "rb").read().decode("utf-8", errors="replace")
pat = re.compile(r"15'd(\d+):\s*O_pixel\s*=\s*25'h([0-9a-fA-F]+);")
pal = Counter()
opaque = 0
for m in pat.finditer(txt):
    v = int(m.group(2), 16)
    if (v >> 24) & 1:
        opaque += 1
        pal[((v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)] += 1
print("ROM entries parsed   : %d" % len(pat.findall(txt)))
print("opaque (bit24=1) px  : %d" % opaque)
print("distinct opaque RGB  : %d" % len(pal))
print("top-8 ROM colours (known RGB -> count in logo):")
for c, n in pal.most_common(8):
    print("    %-18s %5d" % (str(c), n))
KNOWN = [c for c, _ in pal.most_common(8)]

# ------------------------------------------------------- measured logo window
for path in SHOTS:
    a = np.asarray(Image.open(path).convert("RGB"))
    H, W = a.shape[:2]
    # logo window is 160x160 at (0,0) in the 1280x720 output -> x1.5 at 1920x1080
    sx = W / 1280.0
    x1, y1 = int(160 * sx), int(160 * sx)
    logo = a[0:y1, 0:x1].reshape(-1, 3)
    print("=" * 92)
    print("%s  logo window %dx%d = %d px" % (path.split("\\")[-1], x1, y1, len(logo)))
    hist = Counter(map(tuple, logo.tolist()))
    print("  top-8 measured colours:")
    for c, n in hist.most_common(8):
        print("    %-18s %5d   (%.2f%%)" % (str(c), n, 100.0 * n / len(logo)))

    # nearest measured colour for each known ROM colour
    meas = np.array([c for c, _ in hist.most_common(60)], dtype=float)
    cnts = np.array([n for _, n in hist.most_common(60)], dtype=float)
    print("  known -> nearest measured (weighted by pixel count):")
    print("     %-18s %-18s %s" % ("known RGB", "measured", "count"))
    for k in KNOWN:
        d = np.abs(meas - np.array(k, dtype=float)).sum(axis=1)
        j = int(np.argmin(d))
        print("     %-18s %-18s %5d   L1=%d" % (str(k), str(tuple(meas[j].astype(int))), int(cnts[j]), int(d[j])))
