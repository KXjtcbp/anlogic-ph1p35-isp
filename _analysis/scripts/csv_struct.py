# -*- coding: utf-8 -*-
import csv, io, os, re
from collections import Counter

p = r"E:\FPGA\raw_exports\test1.csv"
raw = open(p, "rb").read()
print("bytes:", len(raw))
# 判断编码
enc = "utf-8"
try:
    txt = raw.decode("utf-8")
except UnicodeDecodeError:
    txt = raw.decode("gbk", errors="replace"); enc = "gbk"
print("encoding guess:", enc, "| BOM:", raw[:3] == b"\xef\xbb\xbf")
print("CRLF count:", raw.count(b"\r\n"), "| bare LF:", raw.count(b"\n") - raw.count(b"\r\n"))

lines = txt.splitlines()
out = []
out.append(f"总行数(含表头): {len(lines)}")
out.append(f"表头: {lines[0]}")
out.append("前 3 行数据:")
for l in lines[1:4]:
    out.append("  " + l)
out.append("后 2 行数据:")
for l in lines[-2:]:
    out.append("  " + l)

# 解析
rdr = list(csv.reader(io.StringIO(txt)))
hdr = rdr[0]
rows = [r for r in rdr[1:] if r and any(x.strip() for x in r)]
out.append(f"数据行数: {len(rows)}   列数: {len(hdr)}")

def toint(s):
    s = s.strip()
    if s == "": return None
    try:
        return int(s, 0) if (s.lower().startswith("0x") or s.lower().startswith("0b")) else int(s)
    except ValueError:
        try: return int(s, 16)
        except ValueError: return None

# 逐列统计
out.append("\n===== 逐列统计 =====")
for i, name in enumerate(hdr):
    vals = [r[i].strip() for r in rows if i < len(r)]
    uniq = Counter(vals)
    nums = [toint(v) for v in vals]
    nn = [x for x in nums if x is not None]
    line = f"[{i}] {name!r}  唯一值={len(uniq)}  "
    if len(nn) == len(vals) and nn:
        line += f"数值: min={min(nn)} max={max(nn)} 均值={sum(nn)/len(nn):.2f}"
        line += f"  非零占比={sum(1 for x in nn if x != 0)/len(nn):.3f}"
    else:
        line += f"非数值/空: {len(vals)-len(nn)} 个"
    out.append(line)
    if len(uniq) <= 12:
        out.append("      取值分布: " + ", ".join(f"{k!r}×{v}" for k, v in uniq.most_common()))
    else:
        out.append("      Top6: " + ", ".join(f"{k!r}×{v}" for k, v in uniq.most_common(6)))

open(r"E:\FPGA\_analysis\reports\csv_struct.txt", "w", encoding="utf-8").write("\n".join(out))
print("written")
