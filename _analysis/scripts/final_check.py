# -*- coding: utf-8 -*-
"""收尾核对：(1) 寄存器表 case 条目数 == REG_SIZE；(2) 0x4501 只有一条真条目；
(3) .al 里 hdmi_phy_wrapper.v 与 lane_lvds_10_1.v 两个 File 块的完整原文（用于向用户展示改动）。"""
import os, re, sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

TP = r"E:\FPGA\proj\baseline\lab3\td_project"
AL = os.path.join(TP, "camera_to_dsi_display.al")
REG = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\uics500_cfg\uics500reg_720p60.v"

t = open(REG, "rb").read().decode("utf-8", "surrogateescape")
lines = t.split("\n")
# case 条目形如  "  123: REG_DATA={...};"
entries = [(i + 1, l.strip()) for i, l in enumerate(lines)
           if re.match(r"\s*\d+\s*:\s*REG_DATA\s*=", l)]
print("=" * 78)
print("[1] uics500reg_720p60.v")
print("    case 条目数 = %d" % len(entries))
print("    REG_SIZE    = %s" % re.findall(r"assign\s+REG_SIZE\s*=\s*9'd(\d+)", t))
idx = [int(re.match(r"\s*(\d+)\s*:", l).group(1)) for _, l in entries]
print("    索引范围    = %d .. %d , 连续=%s , 唯一=%s"
      % (min(idx), max(idx), idx == list(range(min(idx), max(idx) + 1)), len(set(idx)) == len(idx)))
bad = [(n, l) for n, l in entries if "16'h4501" in l and not l.strip().startswith("//")]
print("    含 16'h4501 的真条目 = %d 条:" % len(bad))
for n, l in bad:
    print("        :%d  %s" % (n, l))
print("    含 3e09 的真条目:")
for n, l in entries:
    if "3e09" in l:
        print("        :%d  %s" % (n, l))

print("=" * 78)
print("[2] .al 中两个关键 File 块的原文")
txt = open(AL, "rb").read().decode("utf-8", "surrogateescape")
al_lines = txt.split("\n")
for needle in ("hdmi_phy_wrapper.v", "lane_lvds_10_1.v"):
    start = next((i for i, l in enumerate(al_lines) if needle in l and "<File " in l), -1)
    print("  --- %s  (line %d) ---" % (needle, start + 1))
    if start >= 0:
        for l in al_lines[start:start + 6]:
            print("  | " + l.rstrip("\r"))
