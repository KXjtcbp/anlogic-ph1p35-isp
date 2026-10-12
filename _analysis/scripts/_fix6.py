# -*- coding: utf-8 -*-
"""_fix6.py —— 修复 gen6.py：删掉 uivtc 里坏掉的 vcnt 插入项，改由 insert_seqs 携带标题。"""
import io
import py_compile

P = "gen6.py"
t = io.open(P, encoding="utf-8").read()
lines = t.split("\n")

# --- (a) 定位坏块：以 `{"anchor": "    if(rst_sync == 1'b0)` 开头、含 ".replace( 的 3 行坏文本 ---
i0 = None
for i, l in enumerate(lines):
    if l.startswith('        {"anchor": "    if(rst_sync =='):
        i0 = i
        break
assert i0 is not None, "broken block not found"
assert '.replace("' in lines[i0 + 1], repr(lines[i0 + 1])
assert lines[i0 + 2].startswith('",""), "lines": ['), repr(lines[i0 + 2])
# 块尾：其后第一个 "        ]}," 行
i1 = None
for j in range(i0 + 3, i0 + 12):
    if lines[j].rstrip() == "        ]},":
        i1 = j
        break
assert i1 is not None, "block end not found"
del lines[i0:i1 + 1]
t = "\n".join(lines)

# --- (b) 把 vcnt 标题挪进 insert_seqs 的 L93 项 ---
old = '''            {"anchor": "        vcnt <= 12'd0;", "lines": []},
            {"anchor": "    else if(vtc_user_r1)//检测VS帧同步", "lines": []},'''
new = '''            {"anchor": "        vcnt <= 12'd0;", "lines": [
                "//---- 场计数器 vcnt（垂直方向，0 ~ V_FrameSize-1） ----",
                "// vcnt 不是每个时钟都加，而是等一行走完（hcnt 数到 H_ActiveSize-1、即最后一个有效像素）时才加 1；",
                "// 计满一帧（750）后回零，所以它代表 当前正在第几行。",
            ]},'''
assert t.count(old) == 1, "seq block not found: %d" % t.count(old)
t = t.replace(old, new)

io.open(P, "w", encoding="utf-8", newline="").write(t)
py_compile.compile(P, doraise=True)
print("fixed + compiles; removed lines", i0 + 1, "-", i1 + 1)
