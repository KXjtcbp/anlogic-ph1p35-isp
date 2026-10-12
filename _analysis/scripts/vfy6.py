# -*- coding: utf-8 -*-
"""vfy6.py —— 用 code-only 归一化（剥离 // 尾注释后 strip）验证 spec6 的锚点唯一性与顺序。"""
import io
import json
import os

SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"


def code_only(line):
    return line.rstrip("\r\n").split("//")[0].strip()


def load(rel):
    raw = open(os.path.join(SRC, rel), "rb").read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("gbk")
    lines = text.split("\n")
    out = []
    for i, ln in enumerate(lines):
        out.append(ln + "\n" if i < len(lines) - 1 else ln)
    return out


spec = json.load(io.open(r"E:\FPGA\_analysis\docs\spec6.json", encoding="utf-8"))
ok = True
for f in spec["files"]:
    rel = f["path"]
    lines = load(rel)
    codes = [code_only(l) for l in lines]
    print("== %s (%d 行), 头 %d 行" % (rel, len(lines), len(f["header"])))
    for ins in f.get("inserts", []):
        a = code_only(ins["anchor"])
        hits = [i + 1 for i, c in enumerate(codes) if c == a]
        flag = "" if len(hits) == 1 else "   <<< BAD"
        if len(hits) != 1:
            ok = False
        print("   ins  L%-6s n=%d%s  %s" % (hits[:4], len(hits), flag, a[:60]))
    for si, seq in enumerate(f.get("insert_seqs", [])):
        cur = -1
        for ins in seq:
            a = code_only(ins["anchor"])
            hits = [i for i, c in enumerate(codes) if i > cur and c == a]
            flag = "" if hits else "   <<< BAD-ORDER"
            if not hits:
                ok = False
                print("   seq%d ??  %s" % (si, a[:60]))
            else:
                cur = hits[0]
                print("   seq%d L%-6d n_lines=%d  %s" % (si, cur + 1, len(ins["lines"]), a[:60]))
print("ALL OK" if ok else "PROBLEMS FOUND")
