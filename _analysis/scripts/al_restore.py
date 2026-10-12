# -*- coding: utf-8 -*-
"""修复 camera_to_dsi_display.al：TD 在 2026-10-09 17:25:09 重写工程文件时丢掉了
hdmi_phy_wrapper.v 条目、并把 lane_lvds_10_1.v 标成 AutoExcluded=true ——
这两条正是 HDMI PHY 链（hdmi_tx.v:231 例化 hdmi_phy_wrapper；
hdmi_phy_wrapper.v:71/83/95/107 各例化一个 lane_lvds_10_1），
而 10-08 23:20 那次成功编译的日志里两者都被 analyze 过。

修法：用改名前的备份（内容 = 10-08 已知good 的工程文件）覆盖，只把笔误路径
hdmi_phy_warpper -> hdmi_phy_wrapper 同步过来。
"""
import os, re, shutil

OLD = r"E:\FPGA\_backup\20261009_rename\hdl_source\camera_to_dsi_display.al.orig"
CUR = r"E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display.al"
BAK = r"E:\FPGA\_backup\20261009_al修复"
os.makedirs(BAK, exist_ok=True)

# 1) 先把当前（坏的）状态存档
shutil.copy2(CUR, os.path.join(BAK, "camera_to_dsi_display.al.broken_20261009_1725"))
before = open(CUR, "rb").read()

# 2) 用备份 + 路径改正 写回
data = open(OLD, "rb").read()
fixed = data.replace(b"hdl_source/hdmi_phy_warpper", b"hdl_source/hdmi_phy_wrapper")
assert b"hdmi_phy_warpper" not in fixed, "仍残留笔误路径"
open(CUR, "wb").write(fixed)

# 3) 复验
after = open(CUR, "rb").read()


def parse(b):
    txt = b.decode("utf-8", "replace")
    return {m.group(1).replace("hdmi_phy_warpper", "hdmi_phy_wrapper"):
            dict(re.findall(r'<Attr\s+Name="([^"]+)"\s+Val="([^"]*)"\s*/>', m.group(2)))
            for m in re.finditer(r'<File\s+Path="([^"]+)">(.*?)</File>', txt, re.S)}


a = parse(after)
lines = []
lines.append("修复前: %d B, %d 个 File 条目" % (len(before), len(parse(before))))
lines.append("修复后: %d B, %d 个 File 条目" % (len(after), len(a)))
lines.append("")
lines.append("hdmi_phy_wrapper.v 在表里: %s" % ("../user_source/hdl_source/hdmi_phy_wrapper.v" in a))
lines.append("lane_lvds_10_1.v 的 attrs: %s" % a.get("../user_source/hdl_source/lane_lvds_10_1.v"))
lines.append("AutoExcluded=true 的条目数: %d" % sum(1 for v in a.values() if v.get("AutoExcluded") == "true"))
lines.append("")
lines.append("CompileOrder 序列（41~55）:")
seq = sorted(((int(v["CompileOrder"]), k) for k, v in a.items() if "CompileOrder" in v))
for n, k in seq:
    if n >= 41:
        lines.append("   %2d  %s" % (n, k))
lines.append("")
lines.append("备份: " + os.path.join(BAK, "camera_to_dsi_display.al.broken_20261009_1725"))

open(r"E:\FPGA\_analysis\reports\al_restore_report.txt", "w", encoding="utf-8").write("\n".join(lines))
print("\n".join(lines[:8]))
