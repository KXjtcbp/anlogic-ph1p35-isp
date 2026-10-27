# -*- coding: utf-8 -*-
"""修补学习清单生成器：
   1) _L0.py —— 给 para()/bullet() 加内联 markdown 解析（**加粗** / `等宽`）
   2) _L2.py —— 给 isp_top.v 六个例化补 note=、合并重复的 187 行块
"""
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
T = os.environ.get("TEMP", r"C:\Users\KX\AppData\Local\Temp")
L0 = os.path.join(T, "_L0.py")
L2 = os.path.join(T, "_L2.py")

# ---------------- 1) _L0.py ----------------
s = open(L0, encoding="utf-8-sig").read()
if "def inline(" in s:
    print("[_L0] 已有 inline()，跳过")
else:
    anchor = "def para(text=\"\""
    ins = '''import re as _re
_TOK = _re.compile(r"(\\*\\*.+?\\*\\*|`[^`]+`)")

def inline(p, text, size=BODY, color=None, bold=False, mono=False):
    """把 **加粗** 与 `等宽` 解析成对应格式的 run"""
    for seg in _TOK.split(text):
        if not seg:
            continue
        if seg.startswith("**") and seg.endswith("**") and len(seg) > 4:
            run(p, seg[2:-2], bold=True, size=size, color=color, mono=mono)
        elif seg.startswith("`") and seg.endswith("`") and len(seg) > 2:
            run(p, seg[1:-1], bold=bold, size=size, color=color, mono=True)
        else:
            run(p, seg, bold=bold, size=size, color=color, mono=mono)

'''
    assert anchor in s, "_L0 里找不到 para() 定义"
    s = s.replace(anchor, ins + anchor, 1)
    s = s.replace('    if text: run(p, text, bold, size, color, mono)',
                  '    if text: inline(p, text, size=size, color=color, bold=bold, mono=mono)', 1)
    s = s.replace('    run(p, text, size=size)\n    return p', '    inline(p, text, size=size)\n    return p', 1)
    assert "inline(p, text, size=size, color=color" in s, "_L0 para 未替换"
    assert "inline(p, text, size=size)\n    return p" in s, "_L0 bullet 未替换"
    open(L0, "w", encoding="utf-8").write(s)
    print("[_L0] 已加入 inline() 并改写 para()/bullet()，长度 %d" % len(s))

# ---------------- 2) _L2.py ----------------
t = open(L2, encoding="utf-8-sig").read()
print("\n[_L2] 现有 code( 调用共 %d 处：" % t.count("code("))
for m in re.finditer(r"code\((.*?)\)\n", t, re.S):
    line = m.group(0).replace("\n", " ")
    print("   ", line[:170])
