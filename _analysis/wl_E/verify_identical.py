# -*- coding: utf-8 -*-
"""严格校验：新文件去掉“本次插入的注释行”后，必须与备份逐行完全相同。"""
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
BASE = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
BK   = r'E:\FPGA\_backup\20261009_comments\legacy'
paths = [u'osd_char_lib.v', u'isp\\data96_128\\data96_128.v', u'isp\\data128_96\\data128_96.v',
         u'data_96bit_to_128bit.v', u'raw10_unpacket.v', u'csi_unpacket.v',
         u'raw8_to_rgb888.v', u'auto_white_balance.v', u'image_correction.v',
         u'awb.v', u'signal_delay.v', u'uics500_cfg\\uii2c.v',
         u'uics500_cfg\\uics500reg.v', u'uics500_cfg\\uicfgcs500.v']

# 本次插入的行只有两种：文件头行 与 //---- ... ---- 段落行
hdr_ok = [
    u'//=============================================================================',
    u'// 文件      : ', u'// 模块      : ', u'// 功能      : ', u'// 数据通路  : ',
    u'// 时钟/复位 : ', u'// 依赖      : ', u'// 综合/实现 : ',
    u'//-----------------------------------------------------------------------------',
    u'// 修改记录  :',
    u'//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改',
    u'// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\\FPGA\\_analysis\\rename_report.txt',
]

def is_inserted(line):
    s = line.rstrip(u'\r')
    t = s.strip()
    for h in hdr_ok:
        if t == h or (h.endswith(u': ') and t.startswith(h)):
            return True
    if t.startswith(u'//---- ') and t.endswith(u' ----'):
        return True
    return False

bad = 0
for p in paths:
    b = open(os.path.join(BK, p.replace(u'\\', u'__') + u'.bak'), 'rb').read()
    n = open(os.path.join(BASE, p), 'rb').read()
    try:
        nb = n.decode('utf-8'); be = 'utf-8'
    except Exception:
        nb = n.decode('gb18030'); be = 'gb18030'
    bl = b.decode(be).split(u'\n')
    nl = nb.split(u'\n')
    kept = [l for l in nl if not is_inserted(l)]
    ins = len(nl) - len(kept)
    if kept == bl:
        print(u'OK   %-38s 原 %3d 行 / 新 %3d 行 (新增注释 %d 行)  编码 %s' % (p, len(bl), len(nl), ins, be))
    else:
        bad += 1
        print(u'DIFF %-38s 原 %3d 行 / 保留 %3d 行' % (p, len(bl), len(kept)))
        for i in range(max(len(bl), len(kept))):
            a = bl[i] if i < len(bl) else u'<EOF>'
            c = kept[i] if i < len(kept) else u'<EOF>'
            if a != c:
                print(u'   首个差异 行 %d' % (i + 1))
                print(u'   orig: %r' % a)
                print(u'   new : %r' % c)
                break
print(u'---- 结果: %s ----' % (u'全部一致' if bad == 0 else u'%d 个文件不一致' % bad))
