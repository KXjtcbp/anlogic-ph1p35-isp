# -*- coding: utf-8 -*-
"""Ground-truth the capture path using known OSD pixels.

hdmi_mixer.v writes OSD pixels as exact constants with no blending
(:1239  O_hdmi_data <= S_osd_color;):
    COLOR_DYN_TEXT = 24'hfff200  (255,242,  0)
    COLOR_ALG_TEXT = 24'h00ff88  (  0,255,136)
and the logo comes from anlogic_logo_rom.
So the captured RGB for a SOLID text pixel is a direct read-out of the whole
HDMI transmit + capture-card + OBS chain.

This prints, for one screenshot:
  * image size
  * the exact histogram of the CNT text band
  * a raw scanline through the middle of the "CNT" digits
  * the logo region histogram (large solid blocks)
"""
import sys
from collections import Counter

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = r"E:\FPGA\Screenshot 2026-10-11 17-00-21.png"
im = Image.open(P).convert("RGB")
W, H = im.size
a = np.asarray(im)
print("image size = %dx%d" % (W, H))
print("assumed HDMI output mode = 1280x720  ->  capture scale = %.4f x %.4f"
      % (W / 1280.0, H / 720.0))

# ---- CNT text band: scaled OSD window (375,120,575,144) ----
sx, sy = W / 1280.0, H / 720.0
x0, y0, x1, y1 = int(375 * sx), int(120 * sy), int(575 * sx), int(144 * sy)
band = a[y0:y1, x0:x1].reshape(-1, 3)
cnt = Counter(map(tuple, band.tolist()))
print("\n--- CNT text band (%d,%d)-(%d,%d), %d px ---" % (x0, y0, x1, y1, len(band)))
for c, n in cnt.most_common(8):
    print("   %-16s x%-6d %s" % (str(c), n, "  <<< YELLOW TEXT" if c[0] > 200 and c[1] > 180 and c[2] < 80 else ""))
print("   pixels with R>200&G>180&B<40 : %d" % sum(1 for c, n in cnt.items() if c[0] > 200 and c[1] > 180 and c[2] < 40))
print("   pixels with R=255&G=242&B=0   : %d" % cnt.get((255, 242, 0), 0))

# ---- MODE text band: scaled OSD window (240,240,650,300)... use 260..500 x 265..295 ----
x0, y0, x1, y1 = int(240 * sx), int(240 * sy), int(520 * sx), int(300 * sy)
mb = a[y0:y1, x0:x1].reshape(-1, 3)
mc = Counter(map(tuple, mb.tolist()))
print("\n--- MODE text band (%d,%d)-(%d,%d), %d px ---" % (x0, y0, x1, y1, len(mb)))
for c, n in mc.most_common(8):
    print("   %-16s x%d" % (str(c), n))
print("   pixels with R<30&G>240&B in 120..160 (pure 00ff88) : %d"
      % sum(1 for c, n in mc.items() if c[0] < 30 and c[1] > 240 and 120 <= c[2] <= 160))

# ---- logo region (0,0,160,160) scaled ----
lg = a[0:int(160 * sy), 0:int(160 * sx)].reshape(-1, 3)
lc = Counter(map(tuple, lg.tolist()))
print("\n--- logo region histogram (large solid blocks) ---")
for c, n in lc.most_common(10):
    print("   %-16s x%d" % (str(c), n))

# ---- raw scanline through a digit stroke ----
print("\n--- raw scanline y=%d, x=%d..%d ---" % (int(132 * sy), int(430 * sx), int(500 * sx)))
y = int(132 * sy)
xs = range(int(430 * sx), int(500 * sx))
row = [(x, tuple(int(v) for v in a[y, x])) for x in xs]
print("  " + " ".join("%02x%02x%02x" % c for _, c in row))
