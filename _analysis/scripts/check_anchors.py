# -*- coding: utf-8 -*-
"""check_anchors.py —— 读 spec JSON，报告每个插入点会用哪种换行符（以及锚点是否唯一）"""
import json, os, sys

SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"


def norm(l):
    return l.rstrip("\r\n").strip()


def main(specfile):
    spec = json.load(open(specfile, encoding="utf-8"))
    for f in spec["files"]:
        p = os.path.join(SRC, f["path"])
        raw = open(p, "rb").read()
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            text = raw.decode("gbk")
        lines = text.split("\n")
        lines = [ln + "\n" for ln in lines[:-1]] + ([lines[-1]] if lines[-1] != "" else [])
        print("== %s (共 %d 行, 第0行 EOL=%s)" % (f["path"], len(lines), "CRLF" if lines[0].endswith("\r\n") else "LF"))
        bad = 0
        for ins in f.get("inserts", []):
            a = norm(ins["anchor"])
            hits = [i for i, ln in enumerate(lines) if norm(ln) == a]
            if len(hits) != 1:
                print("   !! 命中 %d 次: %r" % (len(hits), a[:70])); bad += 1; continue
            i = hits[0]
            eol = "CRLF" if lines[i].endswith("\r\n") else "LF"
            tag = "   " if eol == ("CRLF" if lines[0].endswith("\r\n") else "LF") else " <<<"
            print("   L%-5d eol=%-4s%s %s" % (i + 1, eol, tag, norm(ins["anchor"])[:64]))
        for seq in f.get("insert_seqs", []):
            cur = -1
            for ins in seq:
                a = norm(ins["anchor"])
                h = [i for i, ln in enumerate(lines) if i > cur and norm(ln) == a]
                if not h:
                    print("   !! seq 未按序找到: %r" % a[:70]); bad += 1; continue
                cur = h[0]
                eol = "CRLF" if lines[cur].endswith("\r\n") else "LF"
                tag = "   " if eol == ("CRLF" if lines[0].endswith("\r\n") else "LF") else " <<<"
                print("   L%-5d eol=%-4s%s %s" % (cur + 1, eol, tag, norm(ins["anchor"])[:64]))
        if bad:
            print("   ---- %d 个问题" % bad)


if __name__ == "__main__":
    main(sys.argv[1])
