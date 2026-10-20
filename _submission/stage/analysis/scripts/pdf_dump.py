import pymupdf
doc = pymupdf.open(r"E:\TD\doc\SWUG\SWUG111_Debug_Tools_User_Guide.pdf")
pgs = [i for i in range(doc.page_count) if "ChipWatcher" in doc[i].get_text()]
print("ChipWatcher 出现的页(1基):", [p+1 for p in pgs])
for i in pgs[:10]:
    t = doc[i].get_text()
    print(f"\n########## p{i+1} (len={len(t)}) ##########")
    print(t[:2300])
