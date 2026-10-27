# -*- coding: utf-8 -*-
"""再修一步：让 rich() 的纯字符串分支也走 inline()，然后重新装配生成并复审。"""
import os, sys, re, importlib.util, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
T = os.environ.get("TEMP", r"C:\Users\KX\AppData\Local\Temp")
L0 = os.path.join(T, "_L0.py")

s = open(L0, encoding="utf-8-sig").read()
OLD = '        if isinstance(t, str): run(p, t, size=size)'
NEW = '        if isinstance(t, str): inline(p, t, size=size)'
if NEW in s:
    print("[_L0] rich() 已改过，跳过")
else:
    assert OLD in s, "_L0 rich() 里没找到预期分支"
    s = s.replace(OLD, NEW, 1)
    open(L0, "w", encoding="utf-8").write(s)
    print("[_L0] rich() 纯字符串分支已改走 inline()，长度 %d" % len(s))

# ---- 装配 ----
parts = []
for nm in ("_L0.py", "_L1.py", "_L2.py", "_L3.py", "_L4.py"):
    parts.append(open(os.path.join(T, nm), encoding="utf-8-sig").read().replace("\ufeff", ""))
ALL = "\n".join(parts)
pa = os.path.join(T, "_ALL.py")
open(pa, "w", encoding="utf-8").write(ALL)
print("[_ALL] %d chars, BOM 残留 %d" % (len(ALL), ALL.count("\ufeff")))

spec = importlib.util.spec_from_file_location("gen", pa)
mod = importlib.util.module_from_spec(spec)
sys.argv = ["gen"]
spec.loader.exec_module(mod)

OUT = r"E:\FPGA\项目学习清单_20261023.docx"
from docx import Document
d = Document(OUT)
ps = [p.text for p in d.paragraphs]
print("\n=== 结果 ===")
print("  %d B  md5=%s  段落 %d  表格 %d"
      % (os.path.getsize(OUT), hashlib.md5(open(OUT, "rb").read()).hexdigest(),
         len(ps), len(d.tables)))

print("\n=== 复审 ===")
b1 = [i for i, t in enumerate(ps) if "**" in t]
b2 = [i for i, t in enumerate(ps) if "`" in t]
print("  残留 ** : %s" % ([(i, ps[i][:50]) for i in b1] if b1 else "无"))
print("  残留 `  : %s" % ([(i, ps[i][:50]) for i in b2] if b2 else "无"))
srcs = [t for t in ps if t.startswith("▎")]
notes = [t for t in ps if t.startswith("▸")]
print("  代码块 %d 个 / ▸ 解释 %d 条" % (len(srcs), len(notes)))
dup = {}
for s2 in srcs:
    dup[s2] = dup.get(s2, 0) + 1
print("  重复块: %s" % ({k: v for k, v in dup.items() if v > 1} or "无"))
miss = [t for i, t in enumerate(ps) if t.startswith("▎")
        and not any(x.startswith("▸") for x in ps[i:i + 40])]
print("  缺 ▸ 的块: %s" % (miss or "无"))
# 统计 h1（用样式名判断，不用启发式）
h1s = [p.text for p in d.paragraphs if p.style.name.startswith("Heading 1")] \
    or [p.text for p in d.paragraphs if p.runs and p.runs[0].font.size
        and p.runs[0].font.size.pt == 15]
print("  一级标题 %d 个: %s" % (len(h1s), " | ".join(h1s)))
