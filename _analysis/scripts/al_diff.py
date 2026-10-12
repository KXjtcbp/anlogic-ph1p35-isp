# -*- coding: utf-8 -*-
import difflib

OLD = r"E:\FPGA\_backup\20261009_rename\hdl_source\camera_to_dsi_display.al.orig"
NEW = r"E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display.al"

old = open(OLD, "rb").read().decode("utf-8", "replace")
old = old.replace("hdl_source/hdmi_phy_warpper", "hdl_source/hdmi_phy_wrapper")
new = open(NEW, "rb").read().decode("utf-8", "replace")

ol, nl = old.splitlines(), new.splitlines()
d = list(difflib.unified_diff(ol, nl, "al.orig(改名后)", "al.当前", lineterm="", n=1))
out = ["旧行数 %d / 新行数 %d" % (len(ol), len(nl)), ""] + d
open(r"E:\FPGA\_analysis\reports\al_diff.txt", "w", encoding="utf-8").write("\n".join(out))
print("diff lines:", len(d))
