# -*- coding: utf-8 -*-
import os, sys, re
sys.stdout.reconfigure(encoding='utf-8')
base = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
pat = re.compile(r'gain|Gain|GAIN|_awb|O_tdata|parameter|module |assign O_|R_GAIN|B_GAIN|saturat|clip|>>|<<|threshold|TH_', re.I)
for f in ['isp/awb/awb.v']:
    p = os.path.join(base, f)
    print('=' * 100)
    print(p, os.path.getsize(p), 'B')
    s = open(p, 'rb').read()
    try:
        s = s.decode('utf-8')
    except Exception:
        s = s.decode('gbk', 'replace')
    lines = s.splitlines()
    print('lines', len(lines))
    for i, t in enumerate(lines, 1):
        if pat.search(t):
            print('%5d| %s' % (i, t[:170]))
