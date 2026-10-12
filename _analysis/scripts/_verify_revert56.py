# -*- coding: utf-8 -*-
"""回退后的自检：确认两个文件状态正确、无 BOM、行尾一致。"""
import os

p1 = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\demosaic_4x_2_0\mipi_to_raw_converter.v"
p2 = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\design_top_wrapper.v"

b = open(p1, "rb").read()
print("1) mipi_to_raw_converter.v  (GBK)")
print("   BOM            :", b[:3] == b"\xef\xbb\xbf")
print("   bytes          :", len(b))
print("   CRLF / bare-LF :", b.count(b"\r\n"), "/", b.count(b"\n") - b.count(b"\r\n"))
print("   count 10'd42   :", b.count(b"10'd42"))
print("   count 10'd56   :", b.count(b"10'd56"))
s = b.decode("gbk")
for l in s.splitlines():
    if "BLACK_LEVEL" in l or "HDR-2026-10-11e" in l:
        print("   |", l)

t = open(p2, encoding="utf-8", newline="").read()
print()
print("2) design_top_wrapper.v  (UTF-8)")
print("   count ~S_sw1_sync1 :", t.count("~S_sw1_sync1"))
print("   count 2026-10-11d  :", t.count("2026-10-11d"))
print("   count 2026-10-11e  :", t.count("2026-10-11e"))
for i, l in enumerate(t.splitlines(), 1):
    if "S_blk_bypass" in l and "wire" in l:
        print("   :%d  %s" % (i, l.strip()))
        for j in (1, 2, 3):
            print("   :%d  %s" % (i + j, t.splitlines()[i + j - 1].strip()))

print()
print("3) 备份目录")
bak = r"E:\FPGA\_backup\20261011e_revert56"
for f in sorted(os.listdir(bak)):
    print("   %-36s %d B" % (f, os.path.getsize(os.path.join(bak, f))))
