# -*- coding: utf-8 -*-
"""查这几个模块到底有没有被例化（排除注释行与 module 定义行）。"""
import os, re

ROOT = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
TARGETS = ["mipi_rx_error_detect", "video_cuttting", "video_cutting", "ps_wrapper",
           "pll_hdmi", "image_correction", "video_in", "video_out", "key_remove_shakes"]

lines = []
files = []
for dp, _d, fns in os.walk(ROOT):
    for fn in fns:
        if fn.endswith((".v", ".sv")) and ".enc." not in fn:
            files.append(os.path.join(dp, fn))

for m in TARGETS:
    pat = re.compile(r"\b" + m + r"\b")
    hits = []
    for p in files:
        txt = open(p, "rb").read().decode("utf-8", "replace")
        for i, line in enumerate(txt.splitlines(), 1):
            if not pat.search(line):
                continue
            s = line.strip()
            if s.startswith("//") or s.startswith("*") or s.startswith("/*"):
                continue
            if re.match(r"^\s*module\s+" + m + r"\b", line):
                hits.append((os.path.relpath(p, ROOT), i, "【module 定义】" + s[:80]))
                continue
            hits.append((os.path.relpath(p, ROOT), i, s[:100]))
    lines.append("=" * 100)
    lines.append("■ %s  —— 非注释命中 %d 处" % (m, len(hits)))
    for rel, i, s in hits:
        lines.append("   %-44s :%-4d %s" % (rel, i, s))

open(r"E:\FPGA\_analysis\reports\find_inst.txt", "w", encoding="utf-8").write("\n".join(lines))
print("wrote find_inst.txt")
