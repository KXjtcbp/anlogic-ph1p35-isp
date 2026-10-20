# -*- coding: utf-8 -*-
"""_polish.py —— 仅注释文字的小修饰（保留编码/换行）。"""
import io

P = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\hdmi_phy_wrapper.v"
raw = open(P, "rb").read()
bom = raw[:3] == b"\xef\xbb\xbf"
t = raw.decode("utf-8")
if bom:
    t = t[1:]
old = "// 依赖      : 依赖：例化 4 次"
new = "// 依赖      : 例化 4 次"
assert t.count(old) == 1, t.count(old)
t = t.replace(old, new)
open(P, "wb").write((b"\xef\xbb\xbf" if bom else b"") + t.encode("utf-8"))
print("polished hdmi_phy_wrapper.v")
