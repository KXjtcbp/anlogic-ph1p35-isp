# -*- coding: utf-8 -*-
"""对比四份 ChipWatcher 采集：全黑.csv vs 全黑2.csv、室内常光.csv vs 室内常光2.csv。
目的：定位「暗部更暗、细节更少」的程度与范围，并区分成因
      （传感器侧 RAW10 变了？还是 ISP 侧的黑电平扣除把它压掉了？）"""
import sys, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PAIRS = [
    (r"E:\FPGA\raw_exports\全黑.csv",     r"E:\FPGA\raw_exports\全黑2.csv",     "全黑(19:34) vs 全黑2(20:09)"),
    (r"E:\FPGA\raw_exports\室内常光.csv", r"E:\FPGA\raw_exports\室内常光2.csv", "室内常光(19:35) vs 室内常光2(20:09)"),
]


def load(p):
    with open(p, "r", encoding="utf-8", errors="replace") as f:
        hdr = f.readline().strip().split(",")
        rows = [l.strip().split(",") for l in f if l.strip()]
    return hdr, rows


def axis_vals(hdr, rows):
    i = next(k for k, h in enumerate(hdr) if h.startswith("S_axis_tdata"))
    iv = hdr.index("S_axis_tvalid")
    out = []
    for r in rows:
        if r[iv] != "1":
            continue
        v = int(r[i], 2)
        out += [(v >> 30) & 0x3FF, (v >> 20) & 0x3FF, (v >> 10) & 0x3FF, v & 0x3FF]
    return out


def isp_bytes(hdr, rows):
    """返回 (每像素非零通道数分布, 所有非零字节值列表, 8bit 值直方图)"""
    i = next(k for k, h in enumerate(hdr) if h.startswith("S_ISP_O_tdata"))
    iv = hdr.index("S_ISP_O_tvalid")
    iph, iall = [], []
    for r in rows:
        if r[iv] != "1":
            continue
        v = int(r[i], 2)
        iph.append(v)
        # 该 128bit 字覆盖的完整 24bit 像素：位偏移 0,24,48,72,96,120（取其全部）
        for n in range(5):
            p = (v >> (128 - 24 * (n + 1))) & 0xFFFFFF
            R, G, B = (p >> 16) & 0xFF, (p >> 8) & 0xFF, p & 0xFF
            iall.append((R, G, B))
    nz_per_pix = collections.Counter(sum(1 for c in t if c) for t in iall)
    vals = collections.Counter()
    for t in iall:
        for c in t:
            if c:
                vals[c] += 1
    return iall, nz_per_pix, vals


def pct_stats(v):
    v = sorted(v)
    n = len(v)
    def q(p):
        return v[min(n - 1, int(p * n))]
    return dict(n=n, min=v[0], p05=q(.05), p25=q(.25), med=q(.5), p75=q(.75), p95=q(.95),
                max=v[-1], mean=sum(v) / n)


for a, b, tag in PAIRS:
    print("=" * 104)
    print("### " + tag)
    for p in (a, b):
        hdr, rows = load(p)
        ax = axis_vals(hdr, rows)
        s = pct_stats(ax)
        print("-" * 100)
        print("%s  [RAW10 传感器侧] n=%d min=%d p05=%d p25=%d med=%d p75=%d p95=%d max=%d mean=%.1f"
              % (p.split("\\")[-1], s["n"], s["min"], s["p05"], s["p25"], s["med"], s["p75"], s["p95"], s["max"], s["mean"]))
        print("    分箱(每 128 一档): %s"
              % {k: sum(1 for x in ax if k * 128 <= x < (k + 1) * 128) for k in range(8)})
        iall, nzp, vals = isp_bytes(hdr, rows)
        tot = sum(nzp.values())
        print("    [ISP 侧] 完整 24bit 像素 %d 个；每像素非零通道数分布 %s（占比 %s）"
              % (tot, dict(sorted(nzp.items())),
                 {k: "%.3f" % (v / tot) for k, v in sorted(nzp.items())}))
        top = vals.most_common(12)
        print("    非零通道值 top12: %s ; 共 %d 个非零通道值" % (top, sum(vals.values())))
        print("    非零值是否全为 5 的倍数: %s ; 值=0 的通道数 %d / %d (=%.3f)"
              % (all(v % 5 == 0 for v in vals), 3 * tot - sum(vals.values()), 3 * tot,
                 (3 * tot - sum(vals.values())) / (3 * tot)))
        # 全零像素（R=G=B=0）
        black = sum(1 for t in iall if t == (0, 0, 0))
        print("    像素完全为 (0,0,0) 的个数 %d / %d = %.3f" % (black, tot, black / tot))
