# -*- coding: utf-8 -*-
import csv, io
from collections import Counter

txt = open(r"E:\FPGA\raw_exports\test1.csv", "r", encoding="utf-8").read()
rdr = list(csv.reader(io.StringIO(txt)))
hdr, rows = rdr[0], [r for r in rdr[1:] if r and len(r) >= 10]
N = len(rows)
out = []
P = out.append

S  = lambda i: [int(r[i]) for r in rows]
smp, trg = S(0), S(1)
isp_td, isp_last, isp_user, isp_tv = [r[2] for r in rows], S(3), S(4), S(5)
ax_td, ax_last, ax_user, ax_tv = [r[6] for r in rows], S(7), S(8), S(9)

P(f"样本数 N = {N}")

def runs(vec, val=1):
    res, i = [], 0
    while i < len(vec):
        if vec[i] == val:
            j = i
            while j + 1 < len(vec) and vec[j+1] == val: j += 1
            res.append((i, j - i + 1)); i = j + 1
        else: i += 1
    return res

P("\n===== 关键位置 =====")
P(f"Trigger=1 的采样点索引: {[i for i,v in enumerate(trg) if v]}")
P(f"S_axis_tuser=1  (RAW 帧首): {[i for i,v in enumerate(ax_user) if v]}")
P(f"S_axis_tlast=1  (RAW 行末): {[i for i,v in enumerate(ax_last) if v]}")
P(f"S_ISP_O_tuser=1 (ISP 帧首): {[i for i,v in enumerate(isp_user) if v]}")
P(f"S_ISP_O_tlast=1 (ISP 行末): {[i for i,v in enumerate(isp_last) if v]}")

ra, ri = runs(ax_tv), runs(isp_tv)
P(f"\nS_axis_tvalid  为 1 的连续段数 = {len(ra)}，段长分布 = {Counter(l for _,l in ra).most_common()}")
P(f"  前 12 段 (起点,长度): {ra[:12]}")
P(f"S_ISP_O_tvalid 为 1 的连续段数 = {len(ri)}，段长分布 = {Counter(l for _,l in ri).most_common()}")
P(f"  前 12 段 (起点,长度): {ri[:12]}")
if ra and ri:
    P(f"  ★ ISP 相对 RAW 的起始偏移 = {ri[0][0] - ra[0][0]} 拍（流水线延迟）")

# ---------- RAW10 解码 ----------
P("\n===== S_axis_tdata[39:0] 解码（每拍 4 个 10bit 像素）=====")
msb = [[int(ax_td[i][k*10:(k+1)*10], 2) for k in range(4)] for i in range(N) if ax_tv[i]]
lsb = [[int(ax_td[i][k*10:(k+1)*10][::-1], 2) for k in range(4)] for i in range(N) if ax_tv[i]]
P(f"有效拍数 = {len(msb)} ⇒ 像素总数 = {len(msb)*4}")

def stat(name, data):
    flat = [x for row in data for x in row]
    flat_s = sorted(flat)
    c = Counter(flat)
    P(f"\n--- {name} ---")
    P(f"  像素数={len(flat)}  min={min(flat)} max={max(flat)} 均值={sum(flat)/len(flat):.2f} "
      f"中位={flat_s[len(flat_s)//2]} p1={flat_s[len(flat_s)//100]} p99={flat_s[-len(flat_s)//100]}")
    P(f"  最频繁 12 个码值: {c.most_common(12)}")
    P(f"  码值 0 的个数={c.get(0,0)}  <=4 的个数={sum(v for k,v in c.items() if k<=4)}  "
      f">=1000 的个数={sum(v for k,v in c.items() if k>=1000)}")
    for k in range(4):
        col = [row[k] for row in data]
        P(f"  第{k+1}字段: 均值={sum(col)/len(col):7.2f}  min={min(col):5d} max={max(col):5d}")

stat("MSB 优先（bit[39] 在前，字段=[39:30],[29:20],[19:10],[9:0]）", msb)
P("\n  (对照) LSB 优先前 3 拍的字段值: " + str(lsb[:3]))
P("  (对照) MSB 优先前 3 拍的字段值: " + str(msb[:3]))

# ---------- ISP 128bit 解码 ----------
P("\n===== S_ISP_O_tdata[127:0] 解码 =====")
val = [isp_td[i] for i in range(N) if isp_tv[i]]
P(f"有效拍数 = {len(val)}")
P("  前 6 个非零值（原始 128 位串）:")
for v in [x for x in val if '1' in x][:6]:
    P(f"    {v}")
P("  同上，按 4×32bit 分组（十六进制）:")
for v in [x for x in val if '1' in x][:6]:
    P("    " + " | ".join(f"{(int(v[k*32:(k+1)*32],2)):08X}" for k in range(4)))
P("  同上，按 8×16bit 分组（十六进制）:")
for v in [x for x in val if '1' in x][:6]:
    P("    " + " | ".join(f"{(int(v[k*16:(k+1)*16],2)):04X}" for k in range(8)))
P("  同上，按 16×8bit 分组（十六进制）:")
for v in [x for x in val if '1' in x][:6]:
    P("    " + " ".join(f"{(int(v[k*8:(k+1)*8],2)):02X}" for k in range(16)))

open(r"E:\FPGA\_analysis\reports\csv_decode.txt", "w", encoding="utf-8").write("\n".join(out))
print("written", len(out), "lines")
