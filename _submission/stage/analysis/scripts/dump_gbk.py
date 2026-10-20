# -*- coding: utf-8 -*-
"""按 GBK/UTF-8 自动解码 dump 文本文件指定行区间，供只读核查用。
用法: python dump_gbk.py <文件> <起始行> <结束行> [<文件> <起始行> <结束行> ...]
不带参数时执行脚本内 DEFAULTS。
"""
import sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DEFAULTS = [
    (r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\demosaic_4x_2_0\mipi_to_raw_converter.v', 1, 40),
    (r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\demosaic_4x_2_0\mipi_to_raw_converter.v', 60, 100),
]


def read_any(path):
    raw = open(path, 'rb').read()
    for enc in ('utf-8-sig', 'gbk', 'latin-1'):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return raw.decode('latin-1', 'replace'), 'latin-1'


def dump(path, a, b):
    text, enc = read_any(path)
    lines = text.splitlines()
    print('=' * 100)
    print('文件: %s' % path)
    print('编码: %s   总行数: %d   字节数: %d' % (enc, len(lines), len(open(path, 'rb').read())))
    print('-' * 100)
    for i in range(max(1, a), min(len(lines), b) + 1):
        print('%4d| %s' % (i, lines[i - 1]))
    print()


if __name__ == '__main__':
    args = sys.argv[1:]
    if not args:
        for p, a, b in DEFAULTS:
            dump(p, a, b)
    else:
        for i in range(0, len(args), 3):
            dump(args[i], int(args[i + 1]), int(args[i + 2]))
