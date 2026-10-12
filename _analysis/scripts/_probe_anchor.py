# -*- coding: utf-8 -*-
p = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\demosaic_4x_2_0\mipi_to_raw_converter.v"
b = open(p, "rb").read()
i = b.find(b"BLACK_LEVEL = 10'd42")
seg = b[i - 20:i + 640]
print("--- raw bytes with repr, decoded gbk(errors=replace) ---")
txt = seg.decode("gbk", errors="replace")
for l in txt.split("\n"):
    print(repr(l))
print()
print("--- exact byte-level check of the 3 candidate separators ---")
for name, s in [
    ("CRLF", "    parameter [9:0] BLACK_LEVEL = 10'd42\r\n"),
    ("LF",   "    parameter [9:0] BLACK_LEVEL = 10'd42\n"),
]:
    print(name, b.count(s.encode("gbk")))
