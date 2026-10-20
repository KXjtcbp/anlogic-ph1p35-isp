#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""[HDR-2026-10-10] 校验 AGC 补丁后的寄存器表不变量（v2：整表计数）。"""
import re

P = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source\uics500_cfg\uics500reg_720p60.v'
t = open(P, 'rb').read().decode('utf-8')
sz = int(re.search(r"assign REG_SIZE = 9'd(\d+)", t).group(1))
body = t.split('case (REG_INDEX)')[1].split('endcase')[0]
idx = sorted(int(m.group(1)) for m in re.finditer(r'(?:\A|;|\s)(\d+): REG_DATA=', body))
print('条目标签: %d 个，min=%d max=%d' % (len(idx), idx[0], idx[-1]))
print('唯一且连续 0..N-1 : %s' % (idx == list(range(len(idx)))))
print('与 REG_SIZE=%d 一致 : %s' % (sz, idx == list(range(sz))))
dup = [x for x in set(idx) if idx.count(x) > 1]
print('重复索引: %s' % (dup if dup else '无'))
miss = [x for x in range(sz) if x not in idx]
print('缺失索引: %s' % (miss if miss else '无'))

F = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source\uics500_cfg\uicfgcs500_720p.v'
c = open(F, 'rb').read().decode('utf-8')
assert "reg_index == 9'd115" in c, '延时触发点被改动！'
print('延时触发点仍是 9\'d115 ✓')

T = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source\design_top_wrapper.v'
w = open(T, 'rb').read().decode('utf-8')
for s in ('wire S_test_pattern = ~S_sw3_sync1;', 'wire S_gain_high    = ~S_sw4_sync1;',
          '.I_test_pattern(S_test_pattern),', '.I_gain_high(S_gain_high),'):
    print('%-44s %s' % (s, '✓' if s in w else '*** 缺失 ***'))
