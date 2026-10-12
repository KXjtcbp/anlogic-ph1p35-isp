# -*- coding: utf-8 -*-
"""解码 raw_exports 的 ChipWatcher CSV：
  S_axis_tdata[39:0]   = isp_top 输入（4像素x10bit RAW，Bayer）
  S_ISP_O_tdata[127:0] = isp_top 输出（data96_128 重切后的连续比特流，24bit/像素，MSB 在前）
目的：直接量 ISP 输出（= AWB 之后）的 mean(R)/mean(G)，看 AWB 到底有没有把三通道拉平。
"""
import os, sys, re
from collections import defaultdict
import numpy as np
sys.stdout.reconfigure(encoding='utf-8')

D = r'E:\FPGA\raw_exports'


def parse(fn):
    rows = []
    with open(fn, 'r', errors='replace') as f:
        hdr = f.readline().rstrip('\n').split(',')
        for ln in f:
            p = ln.rstrip('\n').split(',')
            if len(p) < len(hdr):
                continue
            rows.append(p)
    return hdr, rows


for fn in ['室内常光.csv', '全黑.csv', '全黑2.csv', 'test1.csv', '室内常光2.csv']:
    fp = os.path.join(D, fn)
    hdr, rows = parse(fp)
    print('=' * 100)
    print(fn, 'rows=%d' % len(rows))
    if not rows:
        continue
    print('  header:', hdr)
    idx = {h: i for i, h in enumerate(hdr)}
    td_isp = idx.get('S_ISP_O_tdata[127:0]')
    tv_isp = idx.get('S_ISP_O_tvalid')
    td_ax = idx.get('S_axis_tdata[39:0]')
    tv_ax = idx.get('S_axis_tvalid')
    charset = sorted(set(''.join(r[td_isp] for r in rows[:200]) + ''.join(r[td_ax] for r in rows[:200])))
    print('  field-len isp=%s axis=%s ; charset used = %s  (<= {"0","1"} 说明是二进制，不是十六进制)'
          % (sorted({len(r[td_isp]) for r in rows[:200]}), sorted({len(r[td_ax]) for r in rows[:200]}), charset))
    BASE = 2 if set(charset) <= {'0', '1'} else 16

    # ---------- ISP 输出：拼连续比特流 ----------
    words = []
    for r in rows:
        if r[tv_isp] == '1':
            words.append(int(r[td_isp], BASE))
    print('  ISP valid words = %d  ->  bitstream bits = %d  ->  pixels = %d'
          % (len(words), len(words) * 128, len(words) * 128 // 24))
    if words:
        bits = ''.join(format(w, '0128b') for w in words)
        npx = len(bits) // 24
        arr = np.array([int(bits[24 * k:24 * k + 24], 2) for k in range(npx)], dtype=np.int64)
        R = (arr >> 16) & 0xFF
        G = (arr >> 8) & 0xFF
        B = arr & 0xFF
        # 去掉全 0 的填充像素（模块 gap 拍会出 0）
        nz = ~((R == 0) & (G == 0) & (B == 0))
        R2, G2, B2 = R[nz], G[nz], B[nz]
        print('  ISP out (all %d px):    R=%7.3f G=%7.3f B=%7.3f  R/G=%.4f  B/G=%.4f'
              % (npx, R.mean(), G.mean(), B.mean(), R.mean() / max(G.mean(), 1e-9), B.mean() / max(G.mean(), 1e-9)))
        print('  ISP out (drop-all-zero n=%d): R=%7.3f G=%7.3f B=%7.3f  R/G=%.4f  B/G=%.4f'
              % (len(R2), R2.mean(), G2.mean(), B2.mean(), R2.mean() / max(G2.mean(), 1e-9), B2.mean() / max(G2.mean(), 1e-9)))
        # 也看看非零像素里 R/G 的分布
        print('  ISP out R/G percentiles(non-zero): p5=%.3f p50=%.3f p95=%.3f | G mean over nonzero=%7.3f'
              % tuple(list(np.percentile(R2 / np.maximum(G2, 1), [5, 50, 95])) + [G2.mean()]))
        print('  ISP out first 12 px (R,G,B):', list(zip(R[:12], G[:12], B[:12])))

    # ---------- 输入 RAW10：按 tlast 分行，按 BGGR 提 R/G/B ----------
    raw_rows = [(int(r[td_ax], BASE), r[idx['S_axis_tlast']] if 'S_axis_tlast' in idx else '0')
                for r in rows if r[tv_ax] == '1']
    print('  AXIS valid beats = %d' % len(raw_rows))
    if raw_rows:
        lines = []
        cur = []
        for v, tl in raw_rows:
            cur.append(v)
            if tl == '1':
                lines.append(cur); cur = []
        if cur:
            lines.append(cur)
        print('  AXIS lines = %d, beats/line = %s' % (len(lines), [len(l) for l in lines][:10]))
        # BGGR: even line -> col even=B col odd=G ; odd line -> col even=G col odd=R
        acc = defaultdict(list)
        for li, l in enumerate(lines):
            for b in l:
                f = [(b >> 0) & 0x3FF, (b >> 10) & 0x3FF, (b >> 20) & 0x3FF, (b >> 30) & 0x3FF]
                for k in range(4):
                    col_odd = (k % 2) == 1
                    if li % 2 == 0:
                        col = 'B' if not col_odd else 'G'
                    else:
                        col = 'G' if not col_odd else 'R'
                    acc[col].append(f[k])
        for c in 'RGB':
            v = np.array(acc[c], float)
            print('  RAW10 %s: n=%6d mean=%8.3f  (after BL56: %7.3f)' % (c, len(v), v.mean(), np.maximum(v - 56, 0).mean()))
        if 'R' in acc and 'G' in acc:
            r = np.array(acc['R'], float).mean(); g = np.array(acc['G'], float).mean(); b = np.array(acc['B'], float).mean()
            r2 = np.maximum(np.array(acc['R'], float) - 56, 0).mean()
            g2 = np.maximum(np.array(acc['G'], float) - 56, 0).mean()
            b2 = np.maximum(np.array(acc['B'], float) - 56, 0).mean()
            print('  RAW10 native   R/G=%.4f B/G=%.4f   |  after BL56: R/G=%.4f B/G=%.4f'
                  % (r / g, b / g, r2 / max(g2, 1e-9), b2 / max(g2, 1e-9)))
            print('  => 若 AWB 生效，ISP 输出应把上面这组比值拉到 1.0000')
