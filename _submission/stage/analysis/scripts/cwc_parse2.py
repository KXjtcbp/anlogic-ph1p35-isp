# -*- coding: utf-8 -*-
"""ChipWatcher CSV 采集数据的完整体检 + 内容分析。
格式：Sample,Trigger,<128个0/1>,tlast,tuser,tvalid,<40个0/1>,tlast,tuser,tvalid
每个信号导出成「宽度个 0/1 字符」的二进制串（MSB 在先）。
"""
import os, sys, hashlib
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FILES = [("HEI", r"E:\FPGA\raw_exports\全黑.csv"),
         ("LIANG", r"E:\FPGA\raw_exports\室内常光.csv"),
         ("TEST1", r"E:\FPGA\raw_exports\test1.csv")]

IDX = {"Sample": 0, "Trigger": 1, "ISP_tdata": 2, "ISP_tlast": 3, "ISP_tuser": 4,
       "ISP_tvalid": 5, "AXIS_tdata": 6, "AXIS_tlast": 7, "AXIS_tuser": 8, "AXIS_tvalid": 9}


def parse(path):
    raw = open(path, "rb").read()
    txt = raw.decode("utf-8", "replace")
    lines = [l for l in txt.replace("\r\n", "\n").replace("\r", "\n").split("\n") if l.strip()]
    hdr = lines[0].split(",")
    rows, bad = [], []
    for i, l in enumerate(lines[1:], 1):
        f = l.split(",")
        if len(f) == len(hdr):
            rows.append(f)
        else:
            bad.append((i, len(f)))
    return raw, hdr, rows, bad


def dec_raw10(s):
    if len(s) != 40:
        return None
    return [int(s[k * 10:(k + 1) * 10], 2) for k in range(4)]


def analyse(tag, path):
    raw, hdr, rows, bad = parse(path)
    print("=" * 92)
    print("### %s   %s" % (tag, path))
    print("    字节=%d  sha256=%s  数据行=%d  坏行=%d %s"
          % (len(raw), hashlib.sha256(raw).hexdigest()[:24], len(rows), len(bad), bad[:5]))
    print("    表头=%s" % hdr)
    for j, name in enumerate(hdr):
        lens, chars = Counter(), Counter()
        for r in rows:
            lens[len(r[j])] += 1
            chars.update(r[j])
        cs = "".join(sorted(chars))
        note = ""
        if name.startswith("S_ISP_O_tdata") and list(lens) != [128]:
            note = " <== 宽度异常"
        if name.startswith("S_axis_tdata") and list(lens) != [40]:
            note = " <== 宽度异常"
        if j >= 2 and set(cs) - set("01"):
            note += " <== 含非 0/1 字符"
        print("      [%d] %-20s 长度=%-10s 字符集=%s%s" % (j, name, dict(lens), cs, note))

    def g(r, k):
        return r[IDX[k]]

    isp_on = [i for i, r in enumerate(rows) if g(r, "ISP_tvalid") == "1"]
    ax_on = [i for i, r in enumerate(rows) if g(r, "AXIS_tvalid") == "1"]
    isp_tl = [i for i, r in enumerate(rows) if g(r, "ISP_tlast") == "1"]
    ax_tl = [i for i, r in enumerate(rows) if g(r, "AXIS_tlast") == "1"]
    isp_tu = [i for i, r in enumerate(rows) if g(r, "ISP_tuser") == "1"]
    ax_tu = [i for i, r in enumerate(rows) if g(r, "AXIS_tuser") == "1"]
    print("    ISP_tvalid=1 : %-5d 位置 %s" % (len(isp_on), isp_on[:12]))
    print("    AXIS_tvalid=1: %-5d 位置 %s" % (len(ax_on), ax_on[:12]))
    print("    ISP_tlast=1  : %-5d 位置 %s" % (len(isp_tl), isp_tl[:12]))
    print("    AXIS_tlast=1 : %-5d 位置 %s" % (len(ax_tl), ax_tl[:12]))
    print("    ISP_tuser=1  : %-5d 位置 %s" % (len(isp_tu), isp_tu[:12]))
    print("    AXIS_tuser=1 : %-5d 位置 %s" % (len(ax_tu), ax_tu[:12]))
    for nm, on in (("ISP", isp_on), ("AXIS", ax_on)):
        if len(on) > 1:
            d = [on[i + 1] - on[i] for i in range(len(on) - 1)]
            print("      %s 有效间隔直方图 %s" % (nm, dict(Counter(d).most_common(6))))
    trig = [i for i, r in enumerate(rows) if g(r, "Trigger") != "0"]
    print("    Trigger 标记行 %d 个 %s" % (len(trig), trig[:10]))

    nz_isp = [i for i, r in enumerate(rows) if set(g(r, "ISP_tdata")) != {"0"}]
    nz_ax = [i for i, r in enumerate(rows) if set(g(r, "AXIS_tdata")) != {"0"}]
    print("    ISP_tdata 非全零行 = %d    AXIS_tdata 非全零行 = %d" % (len(nz_isp), len(nz_ax)))

    print("    ---- S_axis_tdata[39:0] RAW10 解码（tvalid=1，MSB 先，字段 [39:30][29:20][19:10][9:0]）----")
    rawv = [(i, dec_raw10(g(rows[i], "AXIS_tdata"))) for i in ax_on]
    nz_rawv = [(i, dec_raw10(g(rows[i], "AXIS_tdata"))) for i in nz_ax]
    print("      tvalid=1 行数 %d ；其中非零 %d" % (len(rawv), len([1 for _, v in rawv if v and any(v)])))
    for i, v in nz_rawv[:24]:
        print("        sample %-5d -> %s   tvalid=%s tlast=%s tuser=%s"
              % (i, v, g(rows[i], "AXIS_tvalid"), g(rows[i], "AXIS_tlast"), g(rows[i], "AXIS_tuser")))
    flat = [x for _, v in nz_rawv for x in v]
    if flat:
        print("      值域 [%d .. %d]  均值 %.2f  计数 %d" % (min(flat), max(flat), sum(flat) / len(flat), len(flat)))
        print("      四字段均值 %s" % [round(sum(v[k] for _, v in nz_rawv) / len(nz_rawv), 2) for k in range(4)])

    print("    ---- S_ISP_O_tdata[127:0] 4x32bit 分块（tvalid=1 前 10 行）----")
    for i in isp_on[:10]:
        s = g(rows[i], "ISP_tdata")
        print("        sample %-5d  %s" % (i, " | ".join(s[k * 32:(k + 1) * 32] for k in range(4))))
    print("    ---- S_ISP_O_tdata 非全零行（前 10）----")
    for i in nz_isp[:10]:
        s = g(rows[i], "ISP_tdata")
        print("        sample %-5d  %s" % (i, " | ".join(s[k * 32:(k + 1) * 32] for k in range(4))))
    return dict(tag=tag, raw=raw, hdr=hdr, rows=rows, isp_on=isp_on, ax_on=ax_on,
                nz_isp=nz_isp, nz_ax=nz_ax, rawv=rawv, nz_rawv=nz_rawv,
                isp_tl=isp_tl, ax_tl=ax_tl, isp_tu=isp_tu, ax_tu=ax_tu)


res = {}
for tag, p in FILES:
    if os.path.exists(p):
        res[tag] = analyse(tag, p)

print()
print("=" * 92)
print("### 交叉比对")
a, b = res.get("HEI"), res.get("LIANG")
if a and b:
    print("    ISP_tvalid=1 : %d vs %d" % (len(a["isp_on"]), len(b["isp_on"])))
    print("    AXIS_tvalid=1: %d vs %d" % (len(a["ax_on"]), len(b["ax_on"])))
    print("    AXIS_tdata 非零: %d vs %d" % (len(a["nz_ax"]), len(b["nz_ax"])))
    d = [i for i in range(1024) if a["rows"][i][2] != b["rows"][i][2]]
    print("    ISP_tdata 内容不同的行 = %d / 1024  前几个 %s" % (len(d), d[:8]))
    d2 = [i for i in range(1024) if a["rows"][i][6] != b["rows"][i][6]]
    print("    AXIS_tdata 内容不同的行 = %d / 1024  前几个 %s" % (len(d2), d2[:8]))
    for nm, r in (("HEI", a), ("LIANG", b)):
        vals = [int(r["rows"][i][2][k * 32:(k + 1) * 32], 2) for i in r["isp_on"] for k in range(4)]
        if vals:
            print("    %s ISP 分块值域 [%d .. %d] 均值 %.1f 个数 %d"
                  % (nm, min(vals), max(vals), sum(vals) / len(vals), len(vals)))
