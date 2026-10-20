# -*- coding: utf-8 -*-
"""收尾补丁：把脚本里对自己的"用法/说明"自引用路径改到 scripts\\ 子目录。"""
import os, glob

SC = r"E:\FPGA\_analysis\scripts"
names = [os.path.basename(p) for p in glob.glob(os.path.join(SC, "*.py"))]
rep = files = 0
for f in glob.glob(os.path.join(SC, "*.py")):
    try:
        t = open(f, encoding="utf-8").read()
    except UnicodeDecodeError:
        t = open(f, encoding="gbk").read()
    o = t
    for n in names:
        for a, b in ((r"E:\FPGA\_analysis\%s" % n, r"E:\FPGA\_analysis\scripts\%s" % n),
                     ("E:/FPGA/_analysis/%s" % n, "E:/FPGA/_analysis/scripts/%s" % n)):
            if a in t and os.path.basename(f) != n:
                t = t.replace(a, b); rep += 1
    if t != o:
        open(f, "w", encoding="utf-8").write(t); files += 1
print("自引用修正 %d 处 / %d 文件" % (rep, files))
