import re, sys, io, collections

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

path = r'E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display_Runs\phy_1\final_timing.rpt'
txt = open(path, 'r', errors='replace').read().splitlines()

# A path entry looks like:
#   Slack               : -0.080ns
#   ...
#   Startpoint          : ...
#   Endpoint            : ...
entries = []
cur = None
group = None
for i, l in enumerate(txt):
    m = re.match(r'\s*Path Group\s*:\s*(.*)$', l)
    if m:
        group = m.group(1).strip()
        continue
    m = re.match(r'\s*Slack\s*:\s*(-?[0-9.]+)ns', l)
    if m:
        if cur:
            entries.append(cur)
        cur = {'slack': float(m.group(1)), 'group': group, 'line': i + 1,
               'start': '', 'end': '', 'via': []}
        continue
    if cur is not None:
        m = re.match(r'\s*Startpoint\s*:\s*(.*)$', l)
        if m and not cur['start']:
            cur['start'] = m.group(1).strip()
        m = re.match(r'\s*Endpoint\s*:\s*(.*)$', l)
        if m and not cur['end']:
            cur['end'] = m.group(1).strip()
        m = re.match(r'\s*(?:via|Through)\s*:?\s*(.*)$', l)
        if m:
            cur['via'].append(m.group(1).strip()[:120])
if cur:
    entries.append(cur)

neg = [e for e in entries if e['slack'] < 0]
print('total path entries parsed = %d ; negative = %d' % (len(entries), len(neg)))
print('worst slack overall = %s' % min([e['slack'] for e in entries], default=None))
print()
bygroup = collections.Counter(e['group'] for e in neg)
print('--- negative paths by group ---')
for g, c in bygroup.most_common():
    worst = min(e['slack'] for e in neg if e['group'] == g)
    print('  %-60s count=%3d  worst=%.3f ns' % (g[:60], c, worst))

print()
print('--- all negative paths (sorted) ---')
for e in sorted(neg, key=lambda x: x['slack'])[:30]:
    print('%.3f ns  line %d  group=%s' % (e['slack'], e['line'], e['group'][:40]))
    print('    start: %s' % e['start'][:150])
    print('    end  : %s' % e['end'][:150])

# module histogram of endpoints
mods = collections.Counter()
for e in neg:
    for f in (e['end'], e['start']):
        mm = re.findall(r'([A-Za-z_][A-Za-z0-9_]*)', f)
        if mm:
            mods[mm[0]] += 1
print()
print('--- negative-path endpoint/startpoint module histogram ---')
for k, v in mods.most_common(15):
    print('  %-40s %d' % (k, v))
