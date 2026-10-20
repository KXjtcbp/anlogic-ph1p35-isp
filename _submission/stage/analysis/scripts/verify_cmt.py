# -*- coding: utf-8 -*-
"""Post-write verification: the 6 files' CODE characters must be identical to their .bak."""
import os

src = open(r"E:\FPGA\_analysis\scripts\add_comments.py", "r", encoding="utf-8").read().replace("\nmain()", "\n")
ns = {}
exec(compile(src, "ac", "exec"), ns)
compact = ns["compact"]
SRC, BAK, FILES = ns["SRC"], ns["BAK"], ns["FILES"]

allok = True
for n in FILES:
    a = open(os.path.join(BAK, n + ".bak"), "rb").read().decode("gbk")
    b = open(os.path.join(SRC, n), "rb").read()
    rt = True
    try:
        bt = b.decode("gbk")
    except UnicodeDecodeError as e:
        rt = False
        bt = ""
        print(n, "GBK decode FAIL", e)
    same = rt and compact(a) == compact(bt)
    allok = allok and same
    print("%-32s code-identical=%s  gbk-ok=%s  code-chars=%d" % (n, same, rt, len(compact(bt))))
print("VERIFY ALL OK" if allok else "VERIFY FAIL")
