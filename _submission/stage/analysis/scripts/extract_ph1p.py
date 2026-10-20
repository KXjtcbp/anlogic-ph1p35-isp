# -*- coding: utf-8 -*-
"""
extract_ph1p.py —— 抽 PH1P 数据手册/选型手册的文字层，并打印与 PH1P35 资源相关的行。

目的：①确认 PH1P35 的 ERAM 块数 / LUT / FF / DSP 总数（用于资源占比与 ROM 实现选型）；
      ②确认 S_csi_rx_clk 与像素域时钟频率（用于时序预算）。
"""
import os
import re

from pypdf import PdfReader

OUT = r'E:\FPGA\_analysis\board_pdf_text'
PDFS = [
    r'E:\FPGA\官方资料\6_PH1P35数据手册\DS1300_PH1P_Datasheet.pdf',
    r'E:\FPGA\官方资料\6_PH1P35数据手册\DS1301_PH1P_FamilyOverview.pdf',
    r'E:\FPGA\官方资料\6_PH1P35数据手册\安路选型手册_202503.pdf',
]

KEY = re.compile(r'PH1P\s*-?\s*35|ERAM|BRAM|EBR|LUT|DSP|资源|Logic|Register', re.I)


def main():
    os.makedirs(OUT, exist_ok=True)
    for path in PDFS:
        name = os.path.splitext(os.path.basename(path))[0]
        if not os.path.isfile(path):
            print('[MISS] %s' % path)
            continue
        try:
            reader = PdfReader(path)
        except Exception as exc:                      # noqa: BLE001
            print('[FAIL] %s -> %s' % (name, exc))
            continue
        chunks = []
        for i, page in enumerate(reader.pages):
            try:
                t = page.extract_text() or ''
            except Exception as exc:                  # noqa: BLE001
                t = ''
            chunks.append('\n===== page %d =====\n%s' % (i + 1, t))
        merged = ''.join(chunks)
        out = os.path.join(OUT, name + '.txt')
        with open(out, 'w', encoding='utf-8') as fh:
            fh.write(merged)
        print('==== [OK] %s pages=%d chars=%d -> %s' % (name, len(reader.pages), len(merged), out))
        # 就地打印含关键词的行，省得再检索
        for line in merged.splitlines():
            s = line.strip()
            if s and KEY.search(s):
                print('   | ' + s[:220])


if __name__ == '__main__':
    main()
