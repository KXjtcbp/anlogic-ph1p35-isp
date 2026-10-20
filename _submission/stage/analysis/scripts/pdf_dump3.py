import pymupdf
doc = pymupdf.open(r"E:\TD\doc\SWUG\SWUG111_Debug_Tools_User_Guide.pdf")
out = []
for i in range(20, 33):          # p20..p32 = Net View / Instance View / OptGate Flow
    out.append(f"\n########## p{i} ##########\n" + doc[i-1].get_text())
open(r"E:\FPGA\_analysis\docs\SWUG111_NetView.txt","w",encoding="utf-8").write("\n".join(out))
print("ok", sum(len(x) for x in out))
