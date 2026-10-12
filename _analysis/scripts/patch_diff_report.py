import difflib, io, sys

def rd(p):
    b = open(p, 'rb').read()
    for e in ('utf-8-sig', 'utf-8', 'gbk', 'latin-1'):
        try:
            return b.decode(e).replace('\r\n', '\n').split('\n')
        except Exception:
            pass

pairs = [
    ('E:/FPGA/proj/baseline/lab3/user_source/hdl_source/isp/isp_top.v',
     'E:/FPGA/proj/baseline/lab3/user_source/hdl_source/isp/isp_top.v.bak_20261010'),
    ('E:/FPGA/proj/baseline/lab3/user_source/hdl_source/design_top_wrapper.v',
     'E:/FPGA/proj/baseline/lab3/user_source/hdl_source/design_top_wrapper.v.bak_20261010'),
]

out = io.open('E:/FPGA/_analysis/reports/patch_diff_report.txt', 'w', encoding='utf-8')
for a, b in pairs:
    A = rd(a); B = rd(b)
    d = list(difflib.unified_diff(B, A, 'bak_20261010', 'now', lineterm='', n=1))
    add = [l for l in d if l.startswith('+') and not l.startswith('+++')]
    rem = [l for l in d if l.startswith('-') and not l.startswith('---')]
    out.write('==== %s : +%d / -%d lines ; %d -> %d lines\n' % (a.split('/')[-1], len(add), len(rem), len(B), len(A)))
    for l in d:
        out.write(l + '\n')
    out.write('\n')
out.close()
print('written E:/FPGA/_analysis/reports/patch_diff_report.txt')
