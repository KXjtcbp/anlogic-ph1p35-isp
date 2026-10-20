# -*- coding: utf-8 -*-
"""把注释里引用旧行号的 :NNN 改成改动后文件的实际行号（只动注释文本）"""
import sys

path = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\hdmi_mixer.v"
raw = open(path, 'rb').read()
t = raw.decode('utf-8')

REPL = [
    ("//             十进制，COLOR_DYN_TEXT=24'hfff200）", None),  # placeholder guard (unused)
]

# (old, new, expected_count)
pairs = [
    ("F_alg_char_bits 真正被调用（:1005-:1010）；",
     "F_alg_char_bits 真正被调用（:1084-:1087 与 :1095-:1097）；", 1),
    ("直接观察 I_debug_status 的 4 个 bit（见 :1123）",
     "直接观察 I_debug_status 的 4 个 bit（见 :1210）", 1),
    ("也是 DDR 读请求的源头（见 :634）",
     "也是 DDR 读请求的源头（见 :701 的 assign）", 1),
    ("行末回卷（见 :647 的计数逻辑）",
     "行末回卷（见 :717-:730 的计数逻辑）", 1),
    ("已无读取点（只被 :733-:737 赋默认值）",
     "已无读取点（只被 :807-:811 赋默认值，位于 :800 起的 always @(*) 内）", 1),
    ("局部 y*LOGO_W + 局部 x，见 :791）",
     "局部 y*LOGO_W + 局部 x，见 :866）", 1),
    ("屏上从左到右显示 _5.._0（见 :917）",
     "屏上从左到右显示 _5.._0（见 :746 起的帧起始进位链）", 1),
    ("数字的字符码 = CHAR_0 + 数字值（见 :952）",
     "数字的字符码 = CHAR_0 + 数字值（见 :1028）", 1),
    ("调用点在 :1005-:1010。",
     "调用点在 :1084-:1087 与 :1095-:1097。", 1),
    ("//   ★索引 4 是数字 '0' 而不是 '4'（见 :456），",
     "//   ★索引 4 是数字 '0' 而不是 '4'（见 :517），", 1),
    ("详见 :1010 处的 BUG(待修) 注释。",
     "详见 :1089 处的 BUG(待修) 注释。", 1),
    ("实际取字形走 :641 例化的 osd_char_lib 子模块，",
     "实际取字形走 :708 例化的 osd_char_lib 子模块，", 1),
    ("//   而 F_alg_char_bits 的索引 4 是数字 '0'（见 :456），",
     "//   而 F_alg_char_bits 的索引 4 是数字 '0'（见 :517），", 1),
]

ok = True
for old, new, n in pairs:
    c = t.count(old)
    if c != n:
        print("FAIL count=%d expected=%d for %r" % (c, n, old[:60]))
        ok = False
        continue
    t = t.replace(old, new)

if not ok:
    sys.exit(1)

open(path, 'wb').write(t.encode('utf-8'))
print("OK: %d 处行号引用已更新为改动后的实际行号" % len(pairs))
