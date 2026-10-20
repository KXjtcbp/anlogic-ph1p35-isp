# -*- coding: utf-8 -*-
"""把 23:20 那 8 张（冻结 4 + 闭环 4）改名归档并写进 CSV。"""
import os, shutil, sys, datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
SRC = os.path.join(WS, "inbox")
DST = os.path.join(WS, "captures", "2026-10-12_AWB帧锁存前基线")
os.makedirs(DST, exist_ok=True)

# 遥测实测（decode_telemetry.py 解出）
ROWS = [
    ("Screenshot 2026-10-12 23-20-33.png", "F1_SW4下_AE冻结_gi4D_M5B_S3.png", "4D", "5B", "3"),
    ("Screenshot 2026-10-12 23-20-35.png", "F2_SW4下_AE冻结_gi4D_M5A_S3.png", "4D", "5A", "3"),
    ("Screenshot 2026-10-12 23-20-38.png", "F3_SW4下_AE冻结_gi4D_M5A_S3.png", "4D", "5A", "3"),
    ("Screenshot 2026-10-12 23-20-42.png", "F4_SW4下_AE冻结_gi4D_M5C_S3.png", "4D", "5C", "3"),
    ("Screenshot 2026-10-12 23-20-49.png", "E1_SW4上_AE闭环_gi3E_M44_S2.png", "3E", "44", "2"),
    ("Screenshot 2026-10-12 23-20-52.png", "E2_SW4上_AE闭环_gi3E_M44_S2.png", "3E", "44", "2"),
    ("Screenshot 2026-10-12 23-20-55.png", "E3_SW4上_AE闭环_gi3E_M44_S2.png", "3E", "44", "2"),
    ("Screenshot 2026-10-12 23-20-58.png", "E4_SW4上_AE闭环_gi3E_M44_S2.png", "3E", "44", "2"),
]
print("=== 归档到 %s ===" % os.path.relpath(DST, WS))
for old, new, gi, m, s in ROWS:
    sp, dp = os.path.join(SRC, old), os.path.join(DST, new)
    if not os.path.exists(sp):
        print("  MISSING", old); continue
    shutil.move(sp, dp)
    print("  %-40s -> %-46s %d B" % (old[-12:], new, os.path.getsize(dp)))

csvp = os.path.join(SRC, u"\u91c7\u96c6\u8bb0\u5f55.csv")
lines = open(csvp, encoding="utf-8").read().rstrip("\n").split("\n")
new_rows = []
for old, new, gi, m, s in ROWS:
    dp = os.path.join(DST, new)
    ts = datetime.datetime.fromtimestamp(os.path.getmtime(dp)).strftime("%m-%d %H:%M:%S")
    frozen = "3" in s
    note = (u"AE\u51bb\u7ed3\u56db\u8fde\u62cd\uff08\u955c\u5934\u9759\u6b62\uff09" if frozen
            else u"AE\u95ed\u73af\u56db\u8fde\u62cd\uff08M=0x44=68\uff0c\u76ee\u6807 70 \u6b7b\u533a\u5185\uff09")
    new_rows.append(u",".join([new, u"AWB\u5e27\u9501\u5b58\u524d\u57fa\u7ebf", ts,
                               u"\u767d\u5899+\u663e\u793a\u5668", u"\u5ba4\u5185\u5f00\u706f",
                               u"\u4e0a", u"\u4e0a", u"\u4e0a",
                               u"\u4e0b" if frozen else u"\u4e0a",
                               u"", u"0", gi, s, note]))
# 插到历史注释之前
idx = next((i for i, l in enumerate(lines) if l.startswith(u"# \u4ee5\u4e0b\u4e3a\u5386\u53f2")), len(lines))
lines = lines[:idx] + new_rows + lines[idx:]
open(csvp, "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("\nCSV -> %d B / %d 行" % (os.path.getsize(csvp), len(lines)))
print("inbox 剩余:", sorted(os.listdir(SRC)))
print("DST 共 %d 张" % len([f for f in os.listdir(DST) if f.lower().endswith(".png")]))
