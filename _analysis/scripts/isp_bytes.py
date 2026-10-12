# -*- coding: utf-8 -*-
"""逐字节解析 ChipWatcher 导出的 ISP 128bit / AXIS 40bit 数据，确定字节结构。"""
import sys, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FILES = [r"E:\FPGA\raw_exports\全黑.csv", r"E:\FPGA\raw_exports\室内常光.csv"]


def load(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        hdr = f.readline().strip().split(",")
        rows = [l.strip().split(",") for l in f if l.strip()]
    return hdr, rows


for p in FILES:
    hdr, rows = load(p)
    i_isp = next(i for i, h in enumerate(hdr) if h.startswith("S_ISP_O_tdata"))
    i_ispv = hdr.index("S_ISP_O_tvalid")
    i_ispu = hdr.index("S_ISP_O_tuser")
    i_axt = next(i for i, h in enumerate(hdr) if h.startswith("S_axis_tdata"))
    i_axv = hdr.index("S_axis_tvalid")
    print("=" * 100)
    print(p, "|", len(rows), "rows")
    print("ISP tdata col=%d (width %d) | AXIS tdata col=%d (width %d)"
          % (i_isp, len(rows[0][i_isp]), i_axt, len(rows[0][i_axt])))

    # ---- ISP 有效字逐字节 ----
    vis = [r for r in rows if r[i_ispv] == "1"]
    print("ISP valid words: %d" % len(vis))
    print("-- 前 6 个有效 ISP 字的 16 个字节（MSB 先，byte15=最高 8 位）--")
    for k, r in enumerate(vis[:6]):
        v = int(r[i_isp], 2)
        bs = v.to_bytes(16, "big")          # bs[0] = bits[127:120]
        print("  #%2d sample=%-5s tuser=%s  %s" % (k, r[0], r[i_ispu],
              " ".join("%02x" % b for b in bs)))
    print("-- 前 6 个有效 ISP 字的 24bit 像素切分（两种相位）--")
    for k, r in enumerate(vis[:3]):
        v = int(r[i_isp], 2)
        for ph in (0, 8, 16):
            pix = []
            for n in range((128 - ph) // 24):
                pix.append("%06x" % ((v >> (128 - ph - 24 * (n + 1))) & 0xFFFFFF))
            print("  #%d phase=%2d: %s" % (k, ph, " ".join(pix)))
    # ---- 非零字节位置统计（对齐到整个 128bit 字）----
    poscnt = collections.Counter()
    valcnt = collections.Counter()
    for r in vis:
        v = int(r[i_isp], 2)
        for j in range(16):
            b = (v >> (8 * (15 - j))) & 0xFF     # j=0 是最高的字节
            if b:
                poscnt[j] += 1
                valcnt[b] += 1
    print("非零字节所在字节号(0=最高字节..15=最低字节) 计数: %s" % dict(sorted(poscnt.items())))
    print("非零字节值分布(前 24 个): %s" % valcnt.most_common(24))
    print("非零字节值是否全为 5 的倍数: %s" % all(v % 5 == 0 for v in valcnt))
    print("非零字节总值个数 %d / %d 个字节" % (sum(poscnt.values()), 16 * len(vis)))

    # ---- AXIS 40bit -> 4x10bit ----
    vax = [r for r in rows if r[i_axv] == "1"]
    print("AXIS valid words: %d" % len(vax))
    for k, r in enumerate(vax[:4]):
        v = int(r[i_axt], 2)
        f = [(v >> 30) & 0x3FF, (v >> 20) & 0x3FF, (v >> 10) & 0x3FF, v & 0x3FF]
        print("  #%d sample=%-5s  f3=%4d f2=%4d f1=%4d f0=%4d" % (k, r[0], f[0], f[1], f[2], f[3]))
    allv = []
    for r in vax:
        v = int(r[i_axt], 2)
        allv += [(v >> 30) & 0x3FF, (v >> 20) & 0x3FF, (v >> 10) & 0x3FF, v & 0x3FF]
    print("AXIS 10bit: n=%d min=%d max=%d mean=%.1f  >1000 的个数=%d"
          % (len(allv), min(allv), max(allv), sum(allv) / len(allv), sum(1 for x in allv if x > 1000)))
