# -*- coding: utf-8 -*-
"""直接 dump 几个 128bit ISP 输出字，人工判断 24bit 像素边界。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
D = r'E:\FPGA\raw_exports'
for fn in ['test1.csv', '室内常光.csv']:
    print('=' * 100)
    print(fn)
    with open(os.path.join(D, fn), 'r', errors='replace') as f:
        hdr = f.readline().rstrip('\n').split(',')
        idx = {h: i for i, h in enumerate(hdr)}
        shown = 0
        for ln in f:
            p = ln.rstrip('\n').split(',')
            if len(p) < len(hdr):
                continue
            if p[idx['S_ISP_O_tvalid']] == '1' and shown < 6:
                w = p[idx['S_ISP_O_tdata[127:0]']]
                h = '%032x' % int(w, 2)
                print('  word%d = %s' % (shown, ' '.join(h[i:i + 8] for i in range(0, 32, 8))))
                # 按 24bit 从 MSB 切：hex 里每 6 个 hex 字符 = 1 像素
                px = []
                for k in range(5):
                    seg = h[k * 6:(k + 1) * 6]
                    if len(seg) == 6:
                        px.append((seg[0:2], seg[2:4], seg[4:6]))
                print('         MSB-24bit slices (R,G,B hex):', px)
                shown += 1
        # 也 dump 前半段 tvalid / tlast / tuser 序列
        f.seek(0)
        f.readline()
        seq = ''.join(p[idx['S_ISP_O_tvalid']] for p in (l.rstrip('\n').split(',') for l in f) if len(p) >= len(hdr))
    print('  tvalid 前 200 拍:', seq[:200])
    tr = ''
    f2 = open(os.path.join(D, fn), 'r', errors='replace'); f2.readline()
    for l in f2:
        p = l.rstrip('\n').split(',')
        if len(p) >= len(hdr):
            tr += p[idx['S_ISP_O_tlast']]
    print('  tlast  前 200 拍:', tr[:200])
    tu = ''
    f3 = open(os.path.join(D, fn), 'r', errors='replace'); f3.readline()
    for l in f3:
        p = l.rstrip('\n').split(',')
        if len(p) >= len(hdr):
            tu += p[idx['S_ISP_O_tuser']]
    print('  tuser  前 200 拍:', tu[:200])
