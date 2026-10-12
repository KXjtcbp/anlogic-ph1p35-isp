# -*- coding: utf-8 -*-
import csv, io
from collections import Counter

txt = open(r"E:\FPGA\raw_exports\test1.csv", "r", encoding="utf-8").read()
rdr = list(csv.reader(io.StringIO(txt)))
rows = [r for r in rdr[1:] if r and len(r) >= 10]
N = len(rows)
out = []
P = out.append
S = lambda i: [int(r[i]) for r in rows]
ax_tv, ax_user, ax_last, ax_td = S(9), S(8), S(7), [r[6] for r in rows]
isp_tv, isp_td, isp_user, isp_last = S(5), [r[2] for r in rows], S(4), S(3)
trg = S(1)

def runs(vec, val=1):
    res, i = [], 0
    while i < len(vec):
        if vec[i] == val:
            j = i
            while j + 1 < len(vec) and vec[j+1] == val: j += 1
            res.append((i, j - i + 1)); i = j + 1
        else: i += 1
    return res

ra, ri = runs(ax_tv), runs(isp_tv)
P("===== 时序结构 =====")
P(f"S_axis_tvalid : {len(ra)} 段，每段长 {set(l for _,l in ra)}；首段起点={ra[0][0]}，末段起点={ra[-1][0]}")
P(f"  起点差分前 20: {[ra[i+1][0]-ra[i][0] for i in range(min(20,len(ra)-1))]}")
P(f"S_ISP_O_tvalid: {len(ri)} 段，每段长 {set(l for _,l in ri)}；首段起点={ri[0][0]}，末段起点={ri[-1][0]}")
P(f"  起点差分前 20: {[ri[i+1][0]-ri[i][0] for i in range(min(20,len(ri)-1))]}")
P(f"trigger=1 @ {[i for i,v in enumerate(trg) if v]}")

# ---------- RAW10：按 tuser..tlast 取"一行" ----------
u = [i for i,v in enumerate(ax_user) if v][0]
l = [i for i,v in enumerate(ax_last) if v][0]
beats = [i for i in range(103, 103+1024) if i < N and ax_tv[i]]
P(f"\n===== RAW10 侧 =====")
P(f"tuser@{u}  tlast@{l}  (跨度 {l-u} 拍)")
P(f"全窗口有效拍 = {len(beats)}  ⇒ {len(beats)*4} 像素（一行应为 320 拍/1280 像素）")

def raw_fields(idxs):
    return [[int(ax_td[i][k*10:(k+1)*10], 2) for k in range(4)] for i in idxs]

allf = raw_fields(beats)
P("全窗口 4 个字段均值: " + str([round(sum(r[k] for r in allf)/len(allf),2) for k in range(4)]))
line_beats = [i for i in beats if u <= i <= l]
lf = raw_fields(line_beats)
P(f"tuser..tlast 内有效拍 = {len(line_beats)} ⇒ {len(line_beats)*4} 像素")
if lf:
    P("该区间 4 字段均值: " + str([round(sum(r[k] for r in lf)/len(lf),2) for k in range(4)]))
    flat = [x for r in lf for x in r]
    P(f"该区间码值: min={min(flat)} max={max(flat)} 均值={sum(flat)/len(flat):.2f}")

# ---------- ISP 128bit：拼位流切成 24bit 像素 ----------
val = [isp_td[i] for i in range(N) if isp_tv[i]]
bits = "".join(val)
npix = len(bits)//24
P(f"\n===== S_ISP_O_tdata[127:0] =====")
P(f"有效拍 = {len(val)}，位流 = {len(bits)} bit ÷ 24 = {npix} 像素（余 {len(bits)%24} bit）")
pix = [int(bits[i*24:(i+1)*24], 2) for i in range(npix)]
b0 = [(p >> 16) & 0xFF for p in pix]
b1 = [(p >> 8) & 0xFF for p in pix]
b2 = [p & 0xFF for p in pix]
for nm, arr in (("字节0 (暂名 R)", b0), ("字节1 (暂名 G)", b1), ("字节2 (暂名 B)", b2)):
    c = Counter(arr)
    P(f"  {nm}: min={min(arr)} max={max(arr)} 均值={sum(arr)/len(arr):.2f} "
      f"全0个数={c.get(0,0)}/{len(arr)}  最常见: {c.most_common(8)}")
P(f"  非零字节的位置规律（前 24 个像素的三元组）:")
P("    " + " ".join(f"({a},{b},{c})" for a,b,c in zip(b0[:8],b1[:8],b2[:8])))
P("    " + " ".join(f"({a},{b},{c})" for a,b,c in zip(b0[8:16],b1[8:16],b2[8:16])))

# 若只有 b2 非零，验证 f_heat: B = 5*luma, luma<51
if all(x == 0 for x in b0) and all(x == 0 for x in b1):
    luma = sorted(set(x // 5 for x in b2))
    P(f"  ★ 只有字节2非零 ⇒ 纯色输出。按 my_algo f_heat (B=5*luma, luma<51) 反推 luma 集合 = {luma}")
    c = Counter(x // 5 for x in b2)
    P(f"  反推 luma 分布: {sorted(c.items())}")
    P(f"  校验 B%5 非零的个数 = {sum(1 for x in b2 if x % 5)}")

open(r"E:\FPGA\_analysis\reports\csv_decode2.txt", "w", encoding="utf-8").write("\n".join(out))
print("ok")
