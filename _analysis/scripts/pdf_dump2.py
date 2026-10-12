# -*- coding: utf-8 -*-
import pymupdf
doc = pymupdf.open(r"E:\TD\doc\SWUG\SWUG111_Debug_Tools_User_Guide.pdf")
want = [4,5,8,9,10,18,19,32,33,34,35,36,37,38,48,49,50,51]
out = []
for i in want:
    if i-1 < doc.page_count:
        out.append(f"\n########## p{i} ##########\n" + doc[i-1].get_text())
open(r"E:\FPGA\_analysis\docs\SWUG111_ChipWatcher.txt","w",encoding="utf-8").write("\n".join(out))
print("written", sum(len(x) for x in out), "chars")
