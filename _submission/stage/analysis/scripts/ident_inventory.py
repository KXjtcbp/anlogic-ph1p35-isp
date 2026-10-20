# -*- coding: utf-8 -*-
"""盘点 HDL 源文件里的标识符，挑出「看不出含义」的名字，供改名映射表使用。"""
import re, os
from collections import defaultdict, Counter

FILELIST = r"E:\FPGA\_analysis\reports\hdl_filelist.txt"
OUT = r"E:\FPGA\_analysis\docs\ident_inventory.txt"
ROOT = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"

KEYWORDS = set("""
module endmodule input output inout wire reg parameter localparam assign always always_ff always_comb
begin end if else case endcase casez casex default for while posedge negedge or and not xor nand nor
integer genvar generate endgenerate function endfunction task endtask initial signed unsigned
defparam specify endspecify primitive endprimitive table endtable time real realtime event
automatic fork join join_any join_none disable wait repeat forever return break continue
typedef logic bit byte shortint int longint enum struct union packed void
class endclass extends virtual pure extern static local protected
interface endinterface modport package endpackage import export
assert assume cover property endproperty sequence endsequence
supply0 supply1 tri triand trior trireg tri0 tri1 wand wor
scalared vectored small medium large highz0 highz1 strong0 strong1 pull0 pull1 weak0 weak1
macromodule config endconfig design instance cell liblist use
""".split())

# 端口/信号前缀属本工程约定，视为「有意义」
CONVENTION = re.compile(r'^[IOSWr]{1,2}_')

files = [l.strip() for l in open(FILELIST, encoding="utf-8") if l.strip().endswith((".v", ".sv"))
         and ".enc." not in l]

def strip_code(text):
    """去掉注释与字符串，避免把中文注释里的词当标识符。"""
    text = re.sub(r'/\*.*?\*/', ' ', text, flags=re.S)
    text = re.sub(r'//[^\n]*', ' ', text)
    text = re.sub(r'"[^"\n]*"', '""', text)
    return text

occ = defaultdict(list)       # name -> [(file, lineno)]
for f in files:
    try:
        raw = open(f, encoding="utf-8", errors="replace").read().splitlines()
    except Exception as e:
        continue
    rel = f.replace(ROOT + "\\", "")
    for ln, line in enumerate(raw, 1):
        code = strip_code(line)
        for m in re.finditer(r'\b([A-Za-z_]\w*)\b', code):
            n = m.group(1)
            if n in KEYWORDS or n.isupper() and len(n) > 6:
                continue
            if re.fullmatch(r'\d+', n):
                continue
            occ[n].append((rel, ln))

out = []
P = out.append
P("================ 短标识符（长度 <= 3，且不符合 I_/O_/S_ 前缀约定）================")
P("名字 | 次数 | 出现的文件数 | 前几个位置")
short = [(n, v) for n, v in occ.items() if len(n) <= 3 and not CONVENTION.match(n) and not n.startswith("$")]
for n, v in sorted(short, key=lambda kv: -len(kv[1])):
    fl = sorted({a for a, _ in v})
    P(f"  {n:<6} {len(v):<6} {len(fl):<4} {fl[:4]}")

P("")
P("================ 疑似拼写错误（含 aixs / warpper / tempreture 等）================")
for n, v in sorted(occ.items()):
    if re.search(r'aixs|warpper|recieve|seperate|adress|lenght|widht|heigth|neccessary|occurance', n, re.I):
        fl = sorted({a for a, _ in v})
        P(f"  {n:<28} {len(v):<6} {fl}")

P("")
P("================ 全长名字总表（用于人工挑）================")
P(f"共 {len(occ)} 个不同标识符")
for n, v in sorted(occ.items()):
    if len(n) <= 2:
        continue
    fl = sorted({a for a, _ in v})
    if len(fl) >= 1:
        P(f"  {n:<34} 次数={len(v):<6} 文件数={len(fl)}")

open(OUT, "w", encoding="utf-8").write("\n".join(out))
print(f"标识符 {len(occ)} 个，已写 {OUT}")
