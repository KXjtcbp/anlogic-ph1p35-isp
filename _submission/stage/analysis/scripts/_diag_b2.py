# -*- coding: utf-8 -*-
"""B 的 P0 追问：确认 .al / .prj 到底编的是哪份 awb.v，以及改动 B 在不在活文件里。"""
import os, re, sys, glob, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
line = "=" * 78


def sec(t):
    print("\n" + line + "\n" + t + "\n" + line)


# ------------------------------------------------------------------ 1
sec("1  td_project 下的 .al —— 与 awb / isp 有关的条目")
for p in sorted(glob.glob(os.path.join(WS, "proj", "baseline", "lab3", "td_project", "*.al"))):
    raw = open(p, "rb").read().decode("utf-8", errors="replace")
    print("--- %s (%d B) ---" % (os.path.relpath(p, WS), os.path.getsize(p)))
    for i, l in enumerate(raw.splitlines(), 1):
        if re.search(r"awb|isp/|isp\\\\", l, re.I) and "Path" in l:
            print("   %4d  %s" % (i, l.strip()))

# ------------------------------------------------------------------ 2
sec("2  全工作区检索字符串 'isp/awb/awb.v' 或 'isp\\awb\\awb.v'（.al/.prj/.f/.txt/.md/.tcl）")
pat = re.compile(r"isp[\\/]awb[\\/]awb\.v", re.I)
hits = 0
for base, dirs, files in os.walk(WS):
    dirs[:] = [d for d in dirs if d not in (".git", "node_modules", "_backup")]
    for f in files:
        if not f.lower().endswith((".al", ".prj", ".f", ".txt", ".md", ".tcl", ".ps1", ".py", ".csv")):
            continue
        p = os.path.join(base, f)
        try:
            raw = open(p, "rb").read().decode("utf-8", errors="replace")
        except Exception:
            continue
        for i, l in enumerate(raw.splitlines(), 1):
            if pat.search(l):
                print("   %s:%d  %s" % (os.path.relpath(p, WS), i, l.strip()[:120]))
                hits += 1
print("   命中 %d 行（不含 _backup）" % hits)

# ------------------------------------------------------------------ 3
sec("3  两份 awb.v 的功能特征对比（决定'改动 B'在不在活文件里）")
feats = ["wb_damp_gain", "wb_clamp_gain", "S_tuser_rise", "S_gi_tgt",
         "divider", "signal_delay", "rgb_sum", "20'h10000", "20'hfffff",
         "in_r_tgt", "sum_r[4", "sum_r[0]"]
for rel in (r"proj\baseline\lab3\user_source\hdl_source\awb.v",
            r"proj\baseline\lab3\user_source\hdl_source\isp\awb\awb.v"):
    p = os.path.join(WS, rel)
    raw = open(p, "rb").read().decode("utf-8", errors="replace")
    print("\n--- %s  (%d B, %d 行) ---" % (rel, os.path.getsize(p), raw.count("\n") + 1))
    for ft in feats:
        n = raw.count(ft)
        print("     %-16s %s" % (ft, ("出现 %d 次" % n) if n else "—— 无"))

# ------------------------------------------------------------------ 4
sec("4  .prj 里所有 isp/ 下的源文件（确认没有第二份 awb）")
p = os.path.join(WS, r"proj\baseline\lab3\td_project\camera_to_dsi_display_Runs\syn_1\camera_to_dsi_display.prj")
raw = open(p, "rb").read().decode("utf-8", errors="replace")
for i, l in enumerate(raw.splitlines(), 1):
    if "isp/" in l and "Path" in l:
        print("   %4d  %s" % (i, l.strip()))
