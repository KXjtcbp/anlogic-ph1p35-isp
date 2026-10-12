# -*- coding: utf-8 -*-
"""
extract_board_pdf.py —— 把开发板手册与原理图 PDF 的文字层抽成 txt，供检索开关/按键的电平定义。

背景：本机没有 fitz / pypdf / pdftotext，故先 pip 装 pypdf（纯 Python）。
用户 m02985 要求「SW1..SW4 的电平定义请查阅工作区中的相应手册后再确认」。
"""
import os
import glob

from pypdf import PdfReader

OUTDIR = r'E:\FPGA\_analysis\board_pdf_text'

PDFS = [
    r'E:\FPGA\官方资料\9_康芯开发板使用手册及实验平台\新HX1P35A开发板手册-HDL版2604.pdf',
    r'E:\FPGA\官方资料\9_康芯开发板使用手册及实验平台\HX1P35B开发板引脚分配汇总.docx',
]
# 原理图（10 张，逐张抽文字，找出画了 SW1..SW4 的那张）
PDFS += sorted(glob.glob(r'E:\FPGA\官方资料\3_原理图\开发板原理图\*.pdf'))


def main():
    os.makedirs(OUTDIR, exist_ok=True)
    for path in PDFS:
        name = os.path.splitext(os.path.basename(path))[0]
        if not os.path.isfile(path):
            print('[MISS] %s' % path)
            continue
        if path.lower().endswith('.docx'):
            continue  # docx 已单独抽过（.extract\docx\HX1P35B开发板引脚分配汇总.txt）
        try:
            reader = PdfReader(path)
        except Exception as exc:                      # noqa: BLE001
            print('[FAIL] %s -> %s' % (name, exc))
            continue
        chunks = []
        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ''
            except Exception as exc:                  # noqa: BLE001
                text = '<<page %d extract failed: %s>>' % (i + 1, exc)
            chunks.append('\n===== page %d =====\n%s' % (i + 1, text))
        merged = ''.join(chunks)
        out = os.path.join(OUTDIR, name + '.txt')
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write(merged)
        print('[OK] %-28s pages=%-4d chars=%-7d -> %s' % (name, len(reader.pages), len(merged), out))


if __name__ == '__main__':
    main()
