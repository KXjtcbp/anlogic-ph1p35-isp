# -*- coding: utf-8 -*-
"""整理后补丁：把脚本里指向"已移动文件"的绝对路径改到新位置。
- CSV:      E:\\FPGA\\<x>.csv        -> E:\\FPGA\\raw_exports\\<x>.csv
- demo:     E:\\FPGA\\tools\\compare\\demo           -> E:\\FPGA\\tools\\compare\\demo
- 分析产物: E:\\FPGA\\_analysis\\<x>  -> E:\\FPGA\\_analysis\\out\\<x>   （x 为已移入 out\\ 的文件名）
"""
import os, glob

AN = r"E:\FPGA\_analysis"
OUT = os.path.join(AN, "out")
outnames = set(os.listdir(OUT))
csvnames = [os.path.basename(p) for p in glob.glob(r"E:\FPGA\raw_exports\*.csv")]

MAP = {}
for c in csvnames:
    MAP[r"E:\FPGA\%s" % c] = r"E:\FPGA\raw_exports\%s" % c
MAP[r"E:\FPGA\tools\compare\demo"] = r"E:\FPGA\tools\compare\demo"
for n in outnames:
    MAP[r"E:\FPGA\_analysis\%s" % n] = r"E:\FPGA\_analysis\out\%s" % n

rep = 0; files = 0
for f in glob.glob(os.path.join(AN, "scripts", "*.py")):
    try:
        t = open(f, encoding="utf-8").read()
    except UnicodeDecodeError:
        t = open(f, encoding="gbk").read()
    o = t
    for a, b in MAP.items():
        for aa, bb in ((a, b), (a.replace("\\", "/"), b.replace("\\", "/")),
                       (a.replace("\\", "\\\\"), b.replace("\\", "\\\\"))):
            if aa in t:
                t = t.replace(aa, bb); rep += 1
    if t != o:
        open(f, "w", encoding="utf-8").write(t); files += 1
print("补丁替换 %d 处 / %d 文件" % (rep, files))
print("映射表条目: %d (csv %d + demo 1 + out %d)" % (len(MAP), len(csvnames), len(outnames)))
