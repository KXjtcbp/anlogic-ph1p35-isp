import pymupdf
doc = pymupdf.open(r"E:\TD\doc\SWUG\SWUG111_Debug_Tools_User_Guide.pdf")
out = []
for i in list(range(11, 18)) + [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31]:
    out.append(f"\n########## p{i} ##########\n" + doc[i-1].get_text())
open(r"E:\FPGA\_analysis\docs\SWUG111_MarkDebug.txt","w",encoding="utf-8").write("\n".join(out))
print("ok", sum(len(x) for x in out))
