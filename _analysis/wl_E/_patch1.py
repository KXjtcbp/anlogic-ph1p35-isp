# -*- coding: utf-8 -*-
import re, io
p = 'do_annotate.py'
b = open(p, 'rb').read()
t = b.decode('utf-8')

A = chr(39)
bad = '16' + A*3 + 'd0'
print('bad found:', t.count(bad))
t = t.replace(bad, '16' + A + 'd0')
# 去掉 raw 字符串里残留的反斜杠转义（ur''' 里 \' 是字面两字符）
t = t.replace('20' + chr(92) + A + 'h', '20' + A + 'h')
t = t.replace('8' + chr(92) + A + 'h', '8' + A + 'h')
t = t.replace('4' + chr(92) + A + 'd', '4' + A + 'd')
t = t.replace('3' + chr(92) + A + 'b', '3' + A + 'b')
open(p, 'wb').write(t.encode('utf-8'))
print('patched')
