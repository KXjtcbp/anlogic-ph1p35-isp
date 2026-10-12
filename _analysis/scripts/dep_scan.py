import os, re, glob, sys

base = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
targets = ['video_in.v','video_out.v','hdmi_tx.v','hdmi_phy_wrapper.v','pll_hdmi.v',
           'lane_lvds_10_1.v','mipi_rx_error_detect.v','key_remove_shakes.v',
           'video_cuttting.v','ps_wrapper.v','mc_to_user_interface.v','I2S_receiver.v',
           'audio_arc_calculate.v', os.path.join('vtc','uivtc.v')]

allv = glob.glob(os.path.join(base, '**', '*.v'), recursive=True)
mods = {}
for p in allv:
    if p.endswith('.enc.v'):
        continue
    try:
        t = open(p, 'rb').read().decode('utf-8')
    except Exception:
        try:
            t = open(p, 'rb').read().decode('gbk')
        except Exception:
            continue
    for m in re.finditer(r'^\s*module\s+([A-Za-z_]\w*)', t, re.M):
        mods.setdefault(m.group(1), []).append(p)

print('total modules found:', len(mods))
print()
# find instantiations inside target files
inst_re = re.compile(r'^\s*([A-Za-z_]\w*)\s*(?:#\s*\(|([A-Za-z_]\w*)\s*\()', re.M)
kw = set('module endmodule input output inout wire reg assign always begin end if else '
         'case endcase parameter localparam generate endgenerate for while initial '
         'posedge negedge or and not xor default function endfunction integer real '
         'timescale define ifdef endif else casex casez signed unsigned'.split())
for tf in targets:
    p = os.path.join(base, tf)
    try:
        t = open(p, 'rb').read().decode('utf-8')
    except Exception:
        t = open(p, 'rb').read().decode('gbk')
    need = set()
    for m in re.finditer(r'^\s*([A-Za-z_]\w*)\s*(#\s*\(|\w+\s*\()', t, re.M):
        n = m.group(1)
        if n in kw:
            continue
        seg = t[m.start():m.start()+400]
        if 'module' in t[max(0,m.start()-60):m.start()]:
            continue
        li = t[:m.start()].count('\n')+1
        need.add((n, li))
    out = []
    for n, li in sorted(need, key=lambda x: x[1]):
        status = 'DEFINED' if n in mods else '*** UNDEFINED ***'
        out.append('   L%-4d %-45s %s' % (li, n, status))
    print('== %s : %s' % (tf, mods and ''))
    print('\n'.join(out))
