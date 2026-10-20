# -*- coding: utf-8 -*-
"""恢复后的一致性核对：
  1) .al 里 55 条路径是否都在盘上存在（相对 .al 所在目录解析）
  2) 源码侧两处关键改动是否还在（增益 11.25x / 8 根 MARK_DEBUG）
  3) hdmi 链路三个文件的例化关系是否仍然闭合
  4) TD 进程是否又起来了
"""
import os, re, sys, subprocess

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TP  = r"E:\FPGA\proj\baseline\lab3\td_project"
AL  = os.path.join(TP, "camera_to_dsi_display.al")
HS  = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"

txt = open(AL, "rb").read().decode("utf-8", "surrogateescape")
paths = re.findall(r"<File\b[^>]*Path=\"([^\"]+)\"", txt)

print("=" * 78)
print("[1] .al 的 %d 条路径逐个解析（相对 %s）" % (len(paths), TP))
missing = []
for p in paths:
    full = os.path.normpath(os.path.join(TP, p.replace("/", os.sep)))
    if not os.path.exists(full):
        missing.append((p, full))
print("    存在 %d / 缺失 %d" % (len(paths) - len(missing), len(missing)))
for p, full in missing:
    print("    MISSING  %s" % full)

print("=" * 78)
print("[2] 关键源码改动核对")
reg = open(os.path.join(HS, "uics500_cfg", "uics500reg_720p60.v"), "rb").read().decode("utf-8", "surrogateescape")
m = re.findall(r"REG_DATA=\{16'h3e09,\s*8'h([0-9a-fA-F]{2})\}", reg)
print("    uics500reg_720p60.v : 3e09 = %s   (期望 2d = 11.25x)" % (m if m else "NOT FOUND"))
m2 = re.findall(r"parameter\s+TEST_PATTERN\s*=\s*1'b(\d)", reg)
print("    uics500reg_720p60.v : TEST_PATTERN = %s   (期望 0)" % (m2 if m2 else "NOT FOUND"))
m3 = re.findall(r"assign\s+REG_SIZE\s*=\s*9'd(\d+)", reg)
print("    uics500reg_720p60.v : REG_SIZE = %s   (期望 117)" % (m3 if m3 else "NOT FOUND"))
n_tp = len(re.findall(r"4501", reg))
print("    uics500reg_720p60.v : 0x4501 条目数 = %d   (期望 1)" % n_tp)

dtw = open(os.path.join(HS, "design_top_wrapper.v"), "rb").read().decode("utf-8", "surrogateescape")
md = re.findall(r'\(\*MARK_DEBUG\s*=\s*"TRUE"\*\)\s*wire[^;]*?(\w+)\s*;', dtw)
print("    design_top_wrapper.v: MARK_DEBUG wire 共 %d 根 -> %s" % (len(md), md))

hdr = {}
for rel in ("design_top_wrapper.v", os.path.join("isp", "isp_top.v"),
            os.path.join("uics500_cfg", "uics500reg_720p60.v")):
    p = os.path.join(HS, rel)
    b = open(p, "rb").read()
    hdr[rel] = (len(b), "HDR-2026-10-09" in b.decode("utf-8", "surrogateescape"))
for k, (sz, has) in hdr.items():
    print("    %-38s %7d B   文件头标记=%s" % (k, sz, has))

print("=" * 78)
print("[3] HDMI 链路例化关系")
def grep(rel, pat):
    p = os.path.join(HS, rel)
    t = open(p, "rb").read().decode("utf-8", "surrogateescape")
    return [i + 1 for i, l in enumerate(t.split("\n")) if re.search(pat, l) and not l.strip().startswith("//")]
g1 = grep("hdmi_tx.v", r"\bhdmi_phy_wrapper\b")
print("    hdmi_tx.v           : 例化 hdmi_phy_wrapper 行 = %s" % g1)
g2 = grep("hdmi_phy_wrapper.v", r"\blane_lvds_10_1\b")
print("    hdmi_phy_wrapper.v  : 例化 lane_lvds_10_1 行 = %s" % g2)
g3 = grep("hdmi_phy_wrapper.v", r"O_tmds_ch\d_p|O_tmds_clk_p")
print("    hdmi_phy_wrapper.v  : TMDS 输出端口行 = %s" % g3)
for f in ("hdmi_phy_wrapper.v", "lane_lvds_10_1.v"):
    p = os.path.join(HS, f)
    print("    %-22s exists=%s size=%s" % (f, os.path.exists(p), os.path.getsize(p) if os.path.exists(p) else "-"))

print("=" * 78)
print("[4] TD / bw 进程")
r = subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-Process td,bw -ErrorAction SilentlyContinue | Select-Object Id,ProcessName,StartTime | Format-Table -AutoSize | Out-String -Width 120"],
                   capture_output=True, text=True)
print("    " + (r.stdout.strip() if r.stdout.strip() else "(无 td / bw 进程在运行)"))
