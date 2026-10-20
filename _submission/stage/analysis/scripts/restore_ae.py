# -*- coding: utf-8 -*-
# 内容说明：从 E:\FPGA\_analysis\reports\ae_dump.txt（latin-1 转义备份，2026-10-10 由被清空的
#   uics500regAE.v 现场导出）重建 uics500regAE.v 的原始内容，再施加 2026-10-10d 的补丁
#   （端口 +I_digital_gain/+I_test_pattern、REG_SIZE 5->8、新增 3e06/3e07/4501 三条）。
#   输出写到 _analysis\ae_restored_new.v（不直接覆盖目标，先人工/编译器核对）。
import re, os, sys

DUMP = r'E:\FPGA\_analysis\reports\ae_dump.txt'
OUT  = r'E:\FPGA\_analysis\misc\ae_restored_new.v'
VEND = r'E:\FPGA\官方资料\2_Example\32_cs500_mipi_hdmi\src\uics500_cfg\uics500regAE.v'

raw = open(DUMP, 'r', encoding='utf-8').read()
lines = raw.split('\n')
if lines and lines[-1] == '':
    lines.pop()
out = []
for ln in lines:
    num, _, body = ln.partition('\t')
    body = re.sub(r'\\\\x([0-9a-fA-F]{2})', lambda m: chr(int(m.group(1), 16)), body)
    out.append(body)
orig = '\n'.join(out) + '\n'
open(r'E:\FPGA\_analysis\reports\ae_restored_orig.txt', 'w', encoding='utf-8').write(orig)
print('reconstructed lines =', len(out), 'bytes(latin-1) =', len(orig.encode('latin-1')))

# --- 与原厂副本对比，列出差异行（预期只有：我的 2026-10-09 头部 + 改名）---
vb = open(VEND, 'rb').read().decode('latin-1').replace('\r\n', '\n').split('\n')
ob = orig.split('\n')
import difflib
d = [l for l in difflib.unified_diff(vb, ob, 'vendor', 'restored', lineterm='', n=0)]
print('--- diff vendor vs restored (%d lines) ---' % len(d))
for l in d[:80]:
    print(l.encode('utf-8', 'replace').decode('utf-8'))

# --- 施加补丁 ---
s = orig
a = 'input      [15:0]  I_analog_gain\n);'
assert s.count(a) == 1, ('port anchor', s.count(a))
s = s.replace(a, 'input      [15:0]  I_analog_gain,\n'
                 'input      [15:0]  I_digital_gain,      // [2026-10-10d] 16bit digital gain {3e06,3e07}\n'
                 'input               I_test_pattern       // [2026-10-10d] 1 = write 0x4501 = 0xbc (gray ramp self-check)\n);')
a2 = "assign\tREG_SIZE = 9'd5;"
assert s.count(a2) == 1, ('size anchor', s.count(a2))
s = s.replace(a2, "assign\tREG_SIZE = 9'd8;      // [2026-10-10d] 5 -> 8: + 3e06 / 3e07 / 4501")
a3 = "I_analog_gain[7 :0]};"
assert s.count(a3) == 1, ('case anchor', s.count(a3))
s = s.replace(a3, a3 + '\n'
    "\t\t5:\tREG_DATA = {16'h3e06, I_digital_gain[15:8]};\n"
    "\t\t6:\tREG_DATA = {16'h3e07, I_digital_gain[7 :0]};\n"
    "\t\t7:\tREG_DATA = {16'h4501, I_test_pattern ? 8'hbc : 8'hb4};")
a4 = 'I_exposure_time/I_analog_gain'
i = s.index(a4); j = s.index('\n', i)
s = s[:j+1] + '//   2026-10-10d 运行时表（AE 表）由 5 条扩到 8 条：新增 3e06/3e07（数字增益）与 4501（灰度递增测试图自检）；REG_SIZE 5→8\n' + s[j+1:]

open(OUT, 'wb').write(s.encode('utf-8'))
print('wrote', OUT, len(s.encode('utf-8')), 'bytes (utf-8)')
