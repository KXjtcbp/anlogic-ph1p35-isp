# -*- coding: utf-8 -*-
"""抽 SC500CS 数据手册里增益表（表2-3/2-4/2-5）与曝光表所在的页，输出 UTF-8 文本。"""
import glob, os, sys
try:
    import pymupdf as fitz
except ImportError:
    import fitz

cands = glob.glob(r"E:\FPGA\官方资料\**\*SC500CS*.pdf", recursive=True)
print("候选 PDF:", cands)
if not cands:
    sys.exit("找不到数据手册")
pdf = max(cands, key=os.path.getsize)
print("使用:", pdf, os.path.getsize(pdf), "B")

doc = fitz.open(pdf)
out = []
kws = ("gain", "GAIN", "增益", "3e06", "3e07", "3e08", "3e09", "3e00", "曝光")
for i, page in enumerate(doc):
    t = page.get_text()
    if any(k in t for k in kws):
        out.append(f"\n########## p{i+1} ##########\n{t}")
dst = r"E:\FPGA\_analysis\docs\SC500CS_gain.txt"
open(dst, "w", encoding="utf-8").write("".join(out))
print("写出:", dst, sum(len(x) for x in out), "字符")
