# -*- coding: utf-8 -*-
import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from docx import Document

d = Document(r"E:\FPGA\项目学习清单_20261023.docx")
ps = d.paragraphs

# 找出代码块区间：从 ▎ 行开始，到下一个 ▸ 行或下一个非等宽段落为止
blocks = []
i = 0
while i < len(ps):
    t = ps[i].text.strip()
    if t.startswith("\u258e"):
        start = i
        j = i + 1
        body = []
        while j < len(ps):
            tt = ps[j].text.strip()
            if tt.startswith("\u25b8"):
                break
            if tt.startswith("\u258e") or (ps[j].runs and ps[j].runs[0].font.size and ps[j].runs[0].font.size.pt >= 15):
                break
            body.append(ps[j].text)
            j += 1
        has_note = j < len(ps) and ps[j].text.strip().startswith("\u25b8")
        blocks.append((t, len(body), has_note, body[:3]))
        i = j
    else:
        i += 1

print("代码块总数 %d" % len(blocks))
print()
print("=== 缺 ▸ 解释的块 ===")
for hdr, n, has, sample in blocks:
    if not has:
        print("  [%d 行正文] %s" % (n, hdr))
print()
print("=== 正文很短的块（可能读不到文件）===")
for hdr, n, has, sample in blocks:
    if n <= 1:
        print("  [%d 行] %s   内容=%r" % (n, hdr, sample))
print()
print("=== 重复的块（同一 文件+行号 出现多次）===")
from collections import Counter
c = Counter(b[0] for b in blocks)
for k, v in c.items():
    if v > 1:
        print("  x%d  %s" % (v, k))
