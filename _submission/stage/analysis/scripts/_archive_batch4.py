# -*- coding: utf-8 -*-
"""把 Sup/Sdown/Tdown/Tup 四张重命名归档进同一批次目录，并追加 CSV 四行。"""
import os, shutil, sys, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
SRC = os.path.join(WS, "inbox")
DST = os.path.join(WS, "captures", "2026-10-12_AE遥测两行验证")

# (原文件名, 新文件名, 场景, 光照, SW1..SW4, CNT, MODE, gi, S, 备注)
PLAN = [
    (u"Sup.png", u"09_SW2\u4e0a_\u66f2\u7ebf\u542f\u7528_gi7F_M18_CNT104652.png",
     u"\u5747\u5300\u5899\u9762", u"\u5f00\u706f", u"\u4e0a", u"\u4e0a", u"\u4e0a", u"\u4e0a",
     u"104652", u"0", u"7F", u"2",
     u"\u2605\u51b3\u5b9a\u6027\u5bf9\u7167 1/2\u2605 \u4e0e 10 \u53f7\u53ea\u5dee SW2\uff1bM=0x18=24"),
    (u"Sdown.png", u"10_SW2\u4e0b_\u66f2\u7ebf\u65c1\u8def_gi7F_M18_CNT104917.png",
     u"\u5747\u5300\u5899\u9762", u"\u5f00\u706f", u"\u4e0a", u"\u4e0b", u"\u4e0a", u"\u4e0a",
     u"104917", u"0", u"7F", u"2",
     u"\u2605\u51b3\u5b9a\u6027\u5bf9\u7167 2/2\u2605 M=0x18=24\uff0c\u4e0e 9 \u53f7\u9010\u4f4d\u76f8\u540c \u21d2 AE \u7edf\u8ba1\u70b9\u5728\u66f2\u7ebf\u524d"),
    (u"Tdown.png", u"11_SW4\u4e0b_AE\u51bb\u7ed3_gi41_M55_S3_CNT120890.png",
     u"\u53f0\u706f\u7167\u767d\u5899", u"\u53f0\u706f", u"\u4e0a", u"\u4e0a", u"\u4e0a", u"\u4e0b",
     u"120890", u"0", u"41", u"3",
     u"\u2605AE \u95ed\u73af\u5bf9\u7167 1/2\u2605 SW4 \u4e0b\uff0cS=3\uff1bM=0x55=85 \u9ad8\u4e8e\u76ee\u6807 70"),
    (u"Tup.png", u"12_SW4\u4e0a_AE\u8fd0\u884c_gi40_M42_S2_CNT121361.png",
     u"\u53f0\u706f\u7167\u767d\u5899", u"\u53f0\u706f", u"\u4e0a", u"\u4e0a", u"\u4e0a", u"\u4e0a",
     u"121361", u"0", u"40", u"2",
     u"\u2605AE \u95ed\u73af\u5bf9\u7167 2/2\u2605 gi 41\u219240\u3001S 3\u21922\u3001M 85\u219266 \u2192 \u671d\u76ee\u6807 70 \u9760\u62e2"),
]

print("=== 重命名并归档 ===")
for row in PLAN:
    old, new = row[0], row[1]
    sp, dp = os.path.join(SRC, old), os.path.join(DST, new)
    if not os.path.exists(sp):
        print("  MISSING %s" % old); continue
    shutil.move(sp, dp)
    print("  %-12s -> %-58s %d B" % (old, new, os.path.getsize(dp)))

# 追加 CSV
csvp = os.path.join(SRC, u"\u91c7\u96c6\u8bb0\u5f55.csv")
txt = open(csvp, encoding="utf-8").read().rstrip("\n").split("\n")
lines = [l for l in txt if not l.startswith(u"# \u4ee5\u4e0b\u4e3a\u5386\u53f2")]
tail = [l for l in txt if l.startswith(u"# \u4ee5\u4e0b\u4e3a\u5386\u53f2") or l.startswith(u"#   ")]
for row in PLAN:
    old, new, scene, light, sw1, sw2, sw3, sw4, cnt, mode, gi, s, note = row
    ts = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(DST, new))).strftime("%m-%d %H:%M:%S")
    lines.append(u",".join([new, u"AE\u9065\u6d4b\u4e24\u884c", ts, scene, light,
                            sw1, sw2, sw3, sw4, cnt, mode, gi, s, note]))
lines += tail
open(csvp, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\nCSV -> %d B, %d \u884c" % (os.path.getsize(csvp), len(lines)))
print("inbox \u5269\u4f59:", sorted(os.listdir(SRC)))
print("DST \u5171 %d \u5f20 png" % len([f for f in os.listdir(DST) if f.lower().endswith(".png")]))
