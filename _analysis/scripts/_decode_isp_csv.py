# -*- coding: utf-8 -*-
"""Decode ChipWatcher CSV exports to measure the ISP's end-to-end effect.

Columns (all tdata fields are BINARY strings, not hex!):
  0 Sample, 1 Trigger,
  2 S_ISP_O_tdata[127:0], 3 S_ISP_O_tlast, 4 S_ISP_O_tuser, 5 S_ISP_O_tvalid,
  6 S_axis_tdata[39:0],  7 S_axis_tlast,  8 S_axis_tuser,  9 S_axis_tvalid

ISP output reassembly (isp/data96_128/data96_128.v:57-99):
  the 128-bit output is a sliding window over the 96-bit stream:
      d1 -> {prev96,        cur96[95:64]}
      d2 -> {prev96[63:0],  cur96[95:32]}
      d3 -> {prev96[31:0],  cur96[95:0] }
  and d0 emits an invalid beat.
  So three CONSECUTIVE valid beats, concatenated MSB-first, hold exactly
  four 96-bit words = 16 pixels.
96-bit word layout: pixel j at bits [24j+23 : 24j] = {R,G,B}.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RAW = r"E:\FPGA\raw_exports"
M96 = (1 << 96) - 1


def parse(path):
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        next(fh)
        for line in fh:
            f = line.rstrip("\n").split(",")
            if len(f) < 10:
                continue
            rows.append((
                int(f[2], 2), int(f[3]), int(f[4]), int(f[5]),
                int(f[6], 2), int(f[7]), int(f[8]), int(f[9]),
            ))
    return rows


def isp_outputs(rows):
    """Return list of (R,G,B) per pixel from the reassembled ISP 128-bit stream."""
    valid = [r for r in rows if r[3] == 1]
    out = []
    i = 0
    while i + 3 <= len(valid):
        w0, w1, w2 = valid[i][0], valid[i + 1][0], valid[i + 2][0]
        big = (w0 << 256) | (w1 << 128) | w2          # 384 bits, MSB first
        for k in range(4):
            word = (big >> (96 * (3 - k))) & M96
            for j in range(4):
                px = (word >> (24 * j)) & 0xFFFFFF
                out.append(((px >> 16) & 0xFF, (px >> 8) & 0xFF, px & 0xFF))
        i += 3
    return out, valid


def raw_beats(rows):
    """Return (field_values[4], tlast_index) for the RAW10 40-bit beats."""
    fields = [[], [], [], []]
    for r in rows:
        if r[7] != 1:            # r[7] = S_axis_tvalid
            continue
        v = r[4]
        for f in range(4):
            fields[f].append((v >> (10 * f)) & 0x3FF)
    return fields


def mean(x):
    return sum(x) / len(x) if x else 0.0


print("%-16s | %-34s | %s" % ("csv", "ISP output (post AWB+gamma)", "RAW10 input (pre BLC)"))
print("-" * 110)
for name in ["test1.csv", "室内常光.csv", "室内常光2.csv", "全黑.csv", "全黑2.csv"]:
    p = os.path.join(RAW, name)
    if not os.path.exists(p):
        continue
    rows = parse(p)
    out, valid = isp_outputs(rows)
    R = [x[0] for x in out]
    G = [x[1] for x in out]
    B = [x[2] for x in out]
    rF = raw_beats(rows)
    fm = [mean(f) for f in rF]
    print("%-16s | px=%5d  R=%7.2f G=%7.2f B=%7.2f  R/G=%.4f B/G=%.4f | beats=%4d fld0..3=%7.2f/%7.2f/%7.2f/%7.2f"
          % (name, len(out), mean(R), mean(G), mean(B),
             mean(R) / max(mean(G), 1e-9), mean(B) / max(mean(G), 1e-9),
             len(rF[0]), fm[0], fm[1], fm[2], fm[3]))

print()
print("per-word dump of the first 3 valid ISP beats (hex, MSB..LSB):")
for name in ["test1.csv"]:
    rows = parse(os.path.join(RAW, name))
    v = [r for r in rows if r[3] == 1][:3]
    for k, r in enumerate(v):
        print("  beat%d = %032x  (valid=%d tuser=%d tlast=%d)" % (k, r[0], r[3], r[4], r[2]))
    out, _ = isp_outputs(rows)
    print("  first 8 pixels (R,G,B):", out[:8])
