# -*- coding: utf-8 -*-
import fitz  # pymupdf
p = r"E:\FPGA\官方资料\3_原理图\摄像头SC500CS\SC500CS_数据手册_V1.8.pdf"
d = fitz.open(p)
for i in (23, 24, 25):     # 表2-4 在 p24 前后（0-based 23..25）
    t = d[i].get_text()
    print("=" * 70)
    print(f"--- page {i+1} ---")
    print(t)
