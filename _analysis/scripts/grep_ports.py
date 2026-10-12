import os, re, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

root = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
pats = sys.argv[1:] or [r'camera_black_level', r'blk_bypass', r'gamma_bypass']
rx = re.compile('|'.join(pats), re.I)

for dp, dn, fn in os.walk(root):
    for f in fn:
        if not f.lower().endswith(('.v', '.sv', '.vh')):
            continue
        p = os.path.join(dp, f)
        try:
            raw = open(p, 'rb').read()
        except Exception:
            continue
        txt = raw.decode('utf-8', 'replace')
        hits = [(i + 1, l) for i, l in enumerate(txt.splitlines()) if rx.search(l)]
        if hits:
            print('===', os.path.relpath(p, root), '(%d hits)' % len(hits))
            for n, l in hits:
                print('  %4d| %s' % (n, l.strip()[:160]))
