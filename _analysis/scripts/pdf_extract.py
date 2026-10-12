# -*- coding: utf-8 -*-
# 从 TD 官方调试手册里抽出 ChipWatcher 章节
import sys
import pymupdf

PDF = r"E:\TD\doc\SWUG\SWUG111_Debug_Tools_User_Guide.pdf"
doc = pymupdf.open(PDF)
print(f"总页数 = {doc.page_count}")

print("\n===== 目录（书签）=====")
for lvl, title, page in doc.get_toc():
    print(f"{'  '*(lvl-1)}[p{page}] {title}")

print("\n===== 提到 ChipWatcher / CWC 的页 =====")
hits = []
for i in range(doc.page_count):
    t = doc[i].get_text()
    if "ChipWatcher" in t or "chipwatcher" in t.lower():
        hits.append(i)
print("页号(0基):", hits)

kw = sys.argv[1] if len(sys.argv) > 1 else None
if kw:
    print(f"\n===== 含关键字 {kw} 的页 =====")
    for i in range(doc.page_count):
        if kw.lower() in doc[i].get_text().lower():
            print(i, end=" ")
    print()
