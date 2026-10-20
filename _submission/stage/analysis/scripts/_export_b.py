# -*- coding: utf-8 -*-
"""把 B 的分支上的两个交付文件导出到本地临时位置，便于阅读。"""
import subprocess, os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
os.chdir(r"E:\FPGA")
names = subprocess.run(["git", "diff", "--name-only", "main...origin/feat/awb-robust"],
                       capture_output=True, text=True, encoding="utf-8").stdout.split()
dst = r"E:\FPGA\_analysis\out"
for n in names:
    blob = subprocess.run(["git", "show", "origin/feat/awb-robust:" + n],
                          capture_output=True).stdout
    out = os.path.join(dst, "B_" + os.path.basename(n))
    open(out, "wb").write(blob)
    print("%-60s %7d B -> %s" % (n, len(blob), out))
