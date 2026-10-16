# -*- coding: utf-8 -*-
"""B 提出的 P0/P1/P3/P4 诊断：一次性回答。
用法: python _diag_b.py
"""
import os, re, sys, glob, hashlib, datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"E:\FPGA"
line = "=" * 78


def sec(t):
    print("\n" + line + "\n" + t + "\n" + line)


# ---------------------------------------------------------------- P0-1
sec("P0-1  板上跑的到底是哪份 awb.v？—— 所有 .prj 里与 awb / signal_delay 有关的行")
root = os.path.join(WS, "proj", "baseline", "lab3", "td_project")
prjs = sorted(glob.glob(os.path.join(root, "**", "*.prj"), recursive=True))
print("找到 %d 个 .prj：" % len(prjs))
for p in prjs:
    print("   " + os.path.relpath(p, WS) + "   (%d B, %s)" % (
        os.path.getsize(p),
        datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M:%S")))

for p in prjs:
    raw = open(p, "rb").read().decode("utf-8", errors="replace")
    hits = [l.strip() for l in raw.splitlines()
            if re.search(r"awb|signal_delay", l, re.I)]
    if hits:
        print("\n--- %s ---" % os.path.relpath(p, WS))
        for h in hits:
            print("   " + h)

sec("P0-1b  .al 里与 awb / signal_delay 有关的行")
als = sorted(glob.glob(os.path.join(root, "..", "*.al")))
for p in als:
    raw = open(p, "rb").read().decode("utf-8", errors="replace")
    hits = [l.strip() for l in raw.splitlines()
            if re.search(r"awb|signal_delay", l, re.I)]
    print("--- %s ---" % os.path.relpath(p, WS))
    for h in hits:
        print("   " + h)
    if not hits:
        print("   (无)")

# ---------------------------------------------------------------- P0-2
sec("P0-2  两个 awb.v 的身份")
for rel in (r"proj\baseline\lab3\user_source\hdl_source\awb.v",
            r"proj\baseline\lab3\user_source\hdl_source\isp\awb\awb.v"):
    p = os.path.join(WS, rel)
    if os.path.exists(p):
        raw = open(p, "rb").read()
        n = raw.decode("utf-8", errors="replace").count("\n") + 1
        print("  %-70s %7d B  %4d 行  md5=%s" % (
            rel, len(raw), n, hashlib.md5(raw).hexdigest()))
    else:
        print("  %-70s 不存在" % rel)

# ---------------------------------------------------------------- P0-2 md5 of bits
sec("P0-2b  历史比特流的 md5（验证 B 手上的散列）")
bits = [
    r"proj\releases\2026-10-12_osd_telemetry\camera_to_dsi_display.bit",
    r"proj\releases\2026-10-12_ae_fixed\camera_to_dsi_display.bit",
    r"proj\releases\2026-10-12_AE首版\camera_to_dsi_display.bit",
    r"_backup\20261012_bit_K45_0149\camera_to_dsi_display.bit",
    r"proj\baseline\lab3\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display.bit",
]
for rel in bits:
    p = os.path.join(WS, rel)
    if os.path.exists(p):
        print("  %-72s %9d B  md5=%s" % (
            rel, os.path.getsize(p),
            hashlib.md5(open(p, "rb").read()).hexdigest()))
    else:
        print("  %-72s 不存在" % rel)

# ---------------------------------------------------------------- P3-6 / P3-7 / P4-8
sec("P3-6 / P3-7 / P4-8  文件与目录存在性")
paths = [
    r"_analysis\out\_tb_awb_fix.log",
    r"_analysis\out\_tb_awb_zones_raw.log",
    r"_analysis\out\_tb_awb_means.log",
    r"_analysis\out\_tb_div_pattern.log",
    r"_analysis\out\_tb_ae_ctrl.log",
    r"_analysis\sim\awb",
    r"_analysis\sim\awb\run_tb_means",
    r"proj\baseline\lab3\td_project\camera_to_dsi_display_Runs",
    r"proj\baseline\lab3\td_project\camera_to_dsi_display_Runs\syn_1\camera_to_dsi_display.prj",
    r"proj\baseline\lab3\td_project\camera_to_dsi_display_Runs\syn_1\camera_to_dsi_display_gate.area",
    r"proj\baseline\lab3\td_project\camera_to_dsi_display_Runs\phy_1\route.qor",
    r"proj\baseline\lab3\td_project\camera_to_dsi_display_Runs\phy_1\camera_to_dsi_display_phy.area",
    r"E:\TD\sim_release\common",
    r"E:\TD\sim_release\ph1",
    r"E:\TD\sim_release\common\al_phy_glbl.v",
    r"E:\modelsim\modelsim_ase\win32aloem",
    r"E:\modelsim\modelsim_ase\win32aloem\vlog.exe",
    r"proj.zip",
]
for rel in paths:
    p = rel if os.path.isabs(rel) else os.path.join(WS, rel)
    if os.path.exists(p):
        extra = ""
        if os.path.isfile(p):
            extra = "  %9d B  %s" % (os.path.getsize(p),
                datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M"))
        else:
            extra = "  <dir>  %d 项" % len(os.listdir(p))
        print("  [有] %-78s%s" % (rel, extra))
    else:
        print("  [无] %s" % rel)

# ---------------------------------------------------------------- P1-4
sec("P1-4  两批基准图的 README")
for d in (r"captures\2026-10-12_AWB诊断基准面",
          r"captures\2026-10-12_照亮后三图",
          r"captures\2026-10-12_照亮前两图"):
    p = os.path.join(WS, d, "README.md")
    print("\n--- %s ---" % d)
    if os.path.exists(p):
        print(open(p, encoding="utf-8", errors="replace").read())
    else:
        print("   (README.md 不存在)")
        for f in sorted(os.listdir(os.path.join(WS, d))):
            print("     " + f)
