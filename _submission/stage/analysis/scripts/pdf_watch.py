# -*- coding: utf-8 -*-
import sys, pymupdf
pdf = r"E:\TD\doc\SWUG\SWUG111_Debug_Tools_User_Guide.pdf"
doc = pymupdf.open(pdf)
out = []
for p in range(39, 52):
    try:
        t = doc[p].get_text()
    except Exception as e:
        t = f"<<error {e}>>"
    out.append(f"\n########## page index {p} (1-based p{p+1}) ##########\n{t}")
open(r"E:\FPGA\_analysis\docs\SWUG111_Watch.txt", "w", encoding="utf-8").write("\n".join(out))
print("written", sum(len(x) for x in out), "chars")
