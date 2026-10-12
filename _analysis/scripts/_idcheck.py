# -*- coding: utf-8 -*-
import re
SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\hdmi_mixer.v"
raw = open(SRC, 'rb').read().decode('utf-8')
lines = raw.split('\n')
print("total lines(incl trailing):", len(lines))
for i, l in enumerate(lines, 1):
    if l.endswith('\r'):
        print("CRLF at line", i)
print("has_timescale:", 'timescale' in raw, " has_block_comment:", '/*' in raw)

names = set()
for l in lines:
    code = l.split('//')[0]
    for m in re.finditer(r'\b(reg|wire)\b\s*(\[[^\]]*\]\s*)?([A-Za-z_]\w*)', code):
        names.add(m.group(3))
    for m in re.finditer(r'^\s*function\s+(\[[^\]]*\]\s*)?([A-Za-z_]\w*)', code):
        names.add(m.group(2))
    for m in re.finditer(r'\blocalparam\s+(?:\w+\s+)?([A-Za-z_]\w*)', code):
        names.add(m.group(1))
    for m in re.finditer(r'^\s*(?:parameter|input|output)\b[^;=]*?([A-Za-z_]\w*)\s*(?:=|,|$)', code):
        names.add(m.group(1))

results = []
for n in sorted(names):
    if n in ('reg', 'wire', 'begin', 'end', 'input', 'output'):
        continue
    cnt = len(re.findall(r'\b' + re.escape(n) + r'\b', raw))
    # count excluding pure-comment occurrences
    cnt_code = 0
    for l in lines:
        code = l.split('//')[0]
        cnt_code += len(re.findall(r'\b' + re.escape(n) + r'\b', code))
    results.append((cnt, cnt_code, n))
print("\n-- declared-only (code occurrences == 1, i.e. declaration only) --")
for cnt, cnt_code, n in results:
    if cnt_code <= 1:
        print("  %-22s code_occ=%d all_occ=%d" % (n, cnt_code, cnt))
print("\n-- code occurrences 2..3 (check manually) --")
for cnt, cnt_code, n in results:
    if 2 <= cnt_code <= 3:
        print("  %-22s code_occ=%d all_occ=%d" % (n, cnt_code, cnt))
