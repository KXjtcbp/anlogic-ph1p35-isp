# -*- coding: utf-8 -*-
import sys
p = sys.argv[1]
a = int(sys.argv[2]); b = int(sys.argv[3])
t = open(p, "rb").read().decode("gbk")
for i, ln in enumerate(t.split("\n")[a - 1:b], start=a):
    print("%4d| %s" % (i, ln.rstrip("\r")))
