# -*- coding: utf-8 -*-
"""pdf2txt.py —— 通用 PDF 抽文本（pypdf），输出到指定 txt。用法：
     python pdf2txt.py <in.pdf> <out.txt> [起始页] [结束页]
注意：不要往 GBK 控制台 print 正文（会 UnicodeEncodeError），本脚本只打印统计。"""
import sys
from pypdf import PdfReader

src = sys.argv[1]
dst = sys.argv[2]
p0 = int(sys.argv[3]) if len(sys.argv) > 3 else 1
p1 = int(sys.argv[4]) if len(sys.argv) > 4 else 10 ** 9

r = PdfReader(src)
n = len(r.pages)
out = []
for i, pg in enumerate(r.pages):
    if i + 1 < p0 or i + 1 > p1:
        continue
    try:
        t = pg.extract_text() or ""
    except Exception as e:
        t = "<<<extract_text 失败: %r>>>" % (e,)
    out.append("\n<<<page %d>>>\n" % (i + 1) + t)
with open(dst, "w", encoding="utf-8", errors="replace") as f:
    f.write("".join(out))
print("OK pages=%d wrote=%d chars -> %s" % (n, sum(len(x) for x in out), dst))
