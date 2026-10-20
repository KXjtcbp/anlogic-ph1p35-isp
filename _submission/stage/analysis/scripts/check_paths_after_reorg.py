# -*- coding: utf-8 -*-
"""校验：_analysis\\scripts 下所有脚本里出现的 E:\\FPGA 绝对路径是否都存在（找出整理后失效的引用）。"""
import re, os, glob

pat = re.compile(r"E:[\\/]{1,2}FPGA[\\/]{1,2}[^\"'\)\s]+")
bad, ok = [], 0
for f in glob.glob(r"E:\FPGA\_analysis\scripts\*.py"):
    try:
        t = open(f, encoding="utf-8").read()
    except UnicodeDecodeError:
        t = open(f, encoding="gbk").read()
    for m in sorted(set(pat.findall(t))):
        p = m.replace("\\\\", "\\").replace("/", "\\")
        if "*" in p or "<" in p or p.endswith("\\"):
            continue
        if os.path.exists(p):
            ok += 1
        else:
            bad.append((os.path.basename(f), p))
print("存在 %d 条, 缺失 %d 条" % (ok, len(bad)))
seen = set()
for fn, p in bad:
    if p in seen:
        continue
    seen.add(p)
    print("  MISSING  %-34s -> %s" % (fn, p))
