# -*- coding: utf-8 -*-
"""_analysis 根目录最后整备：
1) 删除 7 个已空的 Questa 工作库目录（hdlbase / wl_A..wl_D_orig / wl_blk，可再生）
2) 松散文件归类：lut\\  docs\\  reports\\  misc\\
3) 同步改写 scripts\\*.py 里对这些文件的引用
"""
import os, glob, shutil, re

AN = r"E:\FPGA\_analysis"
SC = os.path.join(AN, "scripts")

# 1) 删空目录
empties = ["hdlbase", "wl_A", "wl_B", "wl_C", "wl_D", "wl_D_orig", "wl_blk"]
for d in empties:
    p = os.path.join(AN, d)
    if os.path.isdir(p) and not os.listdir(p):
        os.rmdir(p); print("RMDIR(空)", d)

# 2) 归类
for b in ("lut", "docs", "reports", "misc"):
    os.makedirs(os.path.join(AN, b), exist_ok=True)

LUT_EXT = {".hex", ".coe", ".mif", ".vh"}
DOC_HINT = ("SC500CS_", "SWUG111_", "segments.md", "spec", "module_map", "ident_inventory")
MISC_EXT = {".ps1", ".tcl", ".v", ".log"}
skip = {"scripts", "out", "lut", "docs", "reports", "misc", "board_pdf_text", "sim", "tb",
        "utf8_view", "orig_copy", "wl_E", "wl_agc", "wl_blk2", "hdlbase", "wl_A", "wl_B",
        "wl_C", "wl_D", "wl_D_orig", "wl_blk", ".", ".."}

MAP = {}
for name in sorted(os.listdir(AN)):
    p = os.path.join(AN, name)
    if not os.path.isfile(p) or name in skip:
        continue
    ext = os.path.splitext(name)[1].lower()
    if ext in LUT_EXT or (ext == ".txt" and name.startswith("gamma_lut_")):
        dst = "lut"
    elif any(name.startswith(h) for h in DOC_HINT):
        dst = "docs"
    elif ext in MISC_EXT:
        dst = "misc"
    elif ext == ".txt":
        dst = "reports"
    else:
        continue
    MAP[os.path.join(AN, name)] = os.path.join(AN, dst, name)

for a, b in MAP.items():
    if os.path.exists(b):
        os.remove(b)
    shutil.move(a, b)
print("MOVE %d 个松散文件 -> lut/docs/reports/misc" % len(MAP))

# 3) 改写脚本引用
rep = files = 0
for f in glob.glob(os.path.join(SC, "*.py")):
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
print("引用改写 %d 处 / %d 文件" % (rep, files))

# 4) 结果
print("\n_analysis 根目录剩余条目：")
print("  " + "  ".join(sorted(os.listdir(AN))))
