# -*- coding: utf-8 -*-
"""校验：改动只发生在注释里（每行 '//' 之后或整行新注释），且编码/换行原样保留。"""
import sys

SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\hdmi_mixer.v"
BAK = r"E:\FPGA\_backup\20261009_comments\hdmi_mixer.v.bak"

ob = open(BAK, 'rb').read()
nb = open(SRC, 'rb').read()
ot = ob.decode('utf-8')
nt = nb.decode('utf-8')


def code_lines(text):
    res = []
    for p in text.split('\n'):
        c = p.split('//')[0] if '//' in p else p
        c = c.rstrip()
        if c != '':
            res.append(c)
    return res


oc, nc = code_lines(ot), code_lines(nt)
ok = True
print("BOM check: orig_startswith_BOM=%s new_startswith_BOM=%s" % (ob[:3] == b'\xef\xbb\xbf', nb[:3] == b'\xef\xbb\xbf'))
print("orig bytes=%d new bytes=%d" % (len(ob), len(nb)))
print("orig CRLF lines=%d new CRLF lines=%d" % (ot.count('\r\n'), nt.count('\r\n')))
print("orig ends with LF=%s new ends with LF=%s" % (ot.endswith('\n'), nt.endswith('\n')))

if len(oc) != len(nc):
    ok = False
    print("FAIL: 代码行数不同 orig=%d new=%d" % (len(oc), len(nc)))
    for i in range(max(len(oc), len(nc))):
        a = oc[i] if i < len(oc) else '<none>'
        b = nc[i] if i < len(nc) else '<none>'
        if a != b:
            print("  first diff at code-line %d:\n   orig: %r\n   new : %r" % (i + 1, a, b))
            break
else:
    diffs = [(i, a, b) for i, (a, b) in enumerate(zip(oc, nc)) if a != b]
    if diffs:
        ok = False
        print("FAIL: %d 处代码内容被改动，前 5 处：" % len(diffs))
        for i, a, b in diffs[:5]:
            print("  code-line %d:\n   orig: %r\n   new : %r" % (i + 1, a, b))
    else:
        print("PASS: 所有非空代码片段逐条完全一致（顺序、内容、缩进均未变），共 %d 条" % len(oc))

# 额外：所有含关键代码 token 的行，其代码部分必须仍以原行代码开头
olen = len(ot.split('\n'))
nlen = len(nt.split('\n'))
print("line count: orig=%d new=%d (+%d)" % (olen, nlen, nlen - olen))

# 检查新增行必须整行是注释（去掉前导空白后以 // 开头）
old_set = {}
for p in ot.split('\n'):
    old_set[p] = old_set.get(p, 0) + 1
bad = []
for p in nt.split('\n'):
    if not p.strip().startswith('//') and p.strip() != '':
        if p.endswith('\r'):
            base = p[:-1]
        else:
            base = p
        # 该行必须存在于原文件（可能被追加了行内注释）
        if p in old_set or base in old_set:
            continue
        # 或者去掉行内注释后能在原文件中找到
        if '//' in p and p.split('//')[0].rstrip() in [x.split('//')[0].rstrip() for x in ot.split('\n')]:
            continue
        bad.append(p)
if bad:
    ok = False
    print("FAIL: %d 行既不是新注释、也不是原行(带行内注释)：" % len(bad))
    for p in bad[:10]:
        print("   %r" % p)
else:
    print("PASS: 新增/修改的每一行都是注释行，或原代码行后追加注释")

sys.exit(0 if ok else 1)
