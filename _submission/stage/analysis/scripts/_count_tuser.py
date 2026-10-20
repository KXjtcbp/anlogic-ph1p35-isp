# -*- coding: utf-8 -*-
"""统计 ChipWatcher CSV 里 tuser / tlast 的出现次数与间隔，判定 I_tuser 是"每帧"还是"每行"。"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8')
D = r'E:\FPGA\raw_exports'
for fn in ['室内常光.csv', 'test1.csv', '室内常光2.csv', '全黑.csv']:
    rows = []
    with open(os.path.join(D, fn), 'r', errors='replace') as f:
        hdr = f.readline().rstrip('\n').split(',')
        idx = {h: i for i, h in enumerate(hdr)}
        for ln in f:
            p = ln.rstrip('\n').split(',')
            if len(p) >= len(hdr):
                rows.append(p)
    print('=' * 90)
    print(fn, 'samples=%d' % len(rows))
    for sig in ['S_axis_tuser', 'S_axis_tlast', 'S_axis_tvalid', 'S_ISP_O_tuser', 'S_ISP_O_tlast', 'S_ISP_O_tvalid']:
        if sig not in idx:
            continue
        v = [i for i, r in enumerate(rows) if r[idx[sig]] == '1']
        gaps = [v[i + 1] - v[i] for i in range(len(v) - 1)]
        print('  %-16s count=%4d  first_at=%s  gaps(head)=%s' % (sig, len(v), v[:6], gaps[:8]))
