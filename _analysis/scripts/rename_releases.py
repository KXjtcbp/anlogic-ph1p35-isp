# -*- coding: utf-8 -*-
"""把 proj/releases 下的中文目录名改成纯 ASCII，并同步修正仓库里写死旧名的引用。"""
import os, re, sys, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"E:\FPGA"
REL = os.path.join(WS, "proj", "releases")

MAP = {
    "2026-10-12_两行遥测版":            "2026-10-12_osd_telemetry_2line",
    "2026-10-12_AE_1":                  "2026-10-12_ae_v1",
    "2026-10-12_AE修正版":              "2026-10-12_ae_fixed",
    "2026-10-12_AWB四路修正版":         "2026-10-12_awb_4lane",
    "2026-10-12_K45基线":               "2026-10-12_k45_baseline",
    "2026-10-12_OSD遥测版":             "2026-10-12_osd_telemetry",
    "2026-10-13_AWB帧锁存版":           "2026-10-13_awb_framelatch",
    "2026-10-13_AWBsheruban":           "2026-10-13_awb_rounding",
    "2026-10-14_无调试中枢版":          "2026-10-14_no_debughub",
    "2026-10-14_无调试中枢版_v2":       "2026-10-14_no_debughub_v2",
    "2026-10-14_LSC版":                 "2026-10-14_lsc_v1",
    "2026-10-14_LSC精度版":             "2026-10-14_lsc_precision",
    "2026-10-14_LSC完整二维版":         "2026-10-14_lsc_2d_full",
    "2026-10-14_LSC修正版":             "2026-10-14_lsc_gainfix",
    "2026-10-14_LSC诊断版":             "2026-10-14_lsc_diag",
    "2026-10-14_LSCshuangxianxin":      "2026-10-14_lsc_bilinear",
    "2026-10-14_SW1-LSC旁路诊断版":     "2026-10-14_sw1_lsc_bypass_diag",
    "2026-10-15_运动检测OSD版":         "2026-10-15_motion_osd",
    "2026-10-15_运动检测OSD版_v2":      "2026-10-15_motion_osd_v2",
    "2026-10-15_运动灵敏度版":          "2026-10-15_motion_sensitivity",
    "2026-10-15_SW34运动控制版":        "2026-10-15_sw34_motion_control",
    "2026-10-15_wb_recip版":            "2026-10-15_wb_recip",
    "2026-10-16_真S曲线版":             "2026-10-16_true_s_curve",
    "lab3_原厂_2026-09-10":             "lab3_vendor_2026-09-10",
}

print("=== 第 0 步：改名前先记录关键比特流 md5（改名后必须完全不变）===")
before = {}
for old, new in MAP.items():
    p = os.path.join(REL, old, "camera_to_dsi_display.bit")
    if os.path.exists(p):
        before[new] = hashlib.md5(open(p, "rb").read()).hexdigest()
print("  记录了 %d 个比特流的 md5" % len(before))

print("\n=== 第 1 步：重命名目录 ===")
for old, new in MAP.items():
    so = os.path.join(REL, old)
    dn = os.path.join(REL, new)
    if not os.path.isdir(so):
        print("  SKIP  %-34s (不存在)" % old); continue
    if os.path.isdir(dn):
        print("  SKIP  %-34s (目标已存在)" % old); continue
    os.rename(so, dn)
    print("  OK    %-34s -> %s" % (old, new))

print("\n=== 第 2 步：修正仓库里写死旧目录名的引用 ===")
TARGETS = [
    os.path.join(WS, "HISTORY.md"),
    os.path.join(WS, "_analysis", "scripts", "_archive_batch3.py"),
    os.path.join(WS, "_analysis", "scripts", "_diag_b.py"),
    os.path.join(WS, "_analysis", "scripts", "_rel_readme_commit.py"),
    os.path.join(WS, "_analysis", "scripts", "fill_report.py"),
    os.path.join(WS, "README.md"),
    os.path.join(WS, "docs", "团队协作指南.md"),
    os.path.join(WS, "docs", "协作流程与时间表.md"),
]
n_fix = 0
for t in TARGETS:
    if not os.path.exists(t):
        continue
    src = open(t, "rb").read().decode("utf-8", errors="replace")
    orig = src
    for old, new in MAP.items():
        src = src.replace(old, new)
    if src != orig:
        open(t, "w", encoding="utf-8", newline="").write(src)
        n_fix += 1
        print("  修正 %s" % os.path.relpath(t, WS))
print("  共修正 %d 个文件" % n_fix)

print("\n=== 第 3 步：全仓库再扫一遍是否还有旧名残留 ===")
left = []
for f in TARGETS + [os.path.join(WS, "inbox", "README_采集说明.txt")]:
    if not os.path.exists(f):
        continue
    src = open(f, "rb").read().decode("utf-8", errors="replace")
    for old in MAP:
        if old in src:
            left.append((os.path.relpath(f, WS), old))
if left:
    for r, o in left:
        print("  !! 残留 %s : %s" % (r, o))
else:
    print("  干净，无残留")

print("\n=== 第 4 步：校验 proj/releases 下已无中文路径 ===")
bad = []
for root, dirs, files in os.walk(REL):
    for f in files:
        p = os.path.join(root, f)
        if re.search(r"[\u4e00-\u9fff]", p):
            bad.append(os.path.relpath(p, WS))
print("  含中文的路径：%d 个" % len(bad))
for b in bad[:10]:
    print("    " + b)
print("  目录名清单：")
for d in sorted(os.listdir(REL)):
    print("    " + d)

print("\n=== 第 5 步：校验比特流 md5 未变 ===")
ok = True
for new, h in sorted(before.items()):
    p = os.path.join(REL, new, "camera_to_dsi_display.bit")
    now = hashlib.md5(open(p, "rb").read()).hexdigest()
    flag = "OK" if now == h else "!! CHANGED"
    if now != h:
        ok = False
    print("  %-8s %-34s %s" % (flag, new, now))
print("\n  => %s" % ("全部一致" if ok else "有文件内容发生变化，需排查"))
