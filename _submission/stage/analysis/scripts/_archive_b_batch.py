# -*- coding: utf-8 -*-
"""归档 B1/B2/B3（BLC 旁路实验）+ 追加采集记录 CSV 真值行（幂等）"""
import os, shutil, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
dst = os.path.join(WS, "captures", "2026-10-13_黑电平旁路实验")
os.makedirs(dst, exist_ok=True)

plan = [("B1.png", "01_B1_SW1down_BLCbypass_CNT094903.png"),
        ("B2.png", "02_B2_SW1down_BLCbypass_相机转90_CNT095314.png"),
        ("B3.png", "03_B3_SW1up_BLCrestore_CNT095885.png")]
for src, new in plan:
    sp = os.path.join(WS, "inbox", src)
    if os.path.exists(sp):
        shutil.move(sp, os.path.join(dst, new))
        print("moved %-8s -> %s (%d B)" % (src, new, os.path.getsize(os.path.join(dst, new))))
    else:
        print("SKIP (not in inbox):", src)

p = os.path.join(WS, "inbox", "采集记录.csv")
txt = open(p, "rb").read().decode("utf-8")
rows = [
 "01_B1_SW1down_BLCbypass_CNT094903.png,黑电平旁路实验,10-13 21:58:44,白纸贴满画面,台灯直照,下,上,上,上,094903,0,00,2,"
 "SW1 拨下=BLC 旁路。整帧 Y=80.74 R/G=0.9547 B/G=0.9501；逐行剖面形状与 B3 完全相同(仅整体 +12 码)⇒固定黑电平 56 不是行位置偏色的来源",
 "02_B2_SW1down_BLCbypass_相机转90_CNT095314.png,黑电平旁路实验,10-13 21:58:51,白纸贴满画面 + 相机原地转90度,台灯直照,下,上,上,上,095314,0,00,2,"
 "逐行/逐列剖面与 B1 几乎完全一致(中心最绿 0.929、边缘中性)⇒图案固定在画面坐标",
 "03_B3_SW1up_BLCrestore_CNT095885.png,黑电平旁路实验,10-13 21:59:01,白纸贴满画面,台灯直照,上,上,上,上,095885,0,00,2,"
 "SW1 拨回上。Y=68.70，比 B1 低 12.0 码=黑电平扣除量；剖面形状与 B1 一致",
]
add = [r for r in rows if r.split(",")[0] not in txt]
if add:
    if not txt.endswith("\n"):
        txt += "\n"
    txt += "\n".join(add) + "\n"
    open(p, "wb").write(txt.encode("utf-8"))
    print("CSV: added %d rows -> %d B" % (len(add), os.path.getsize(p)))
else:
    print("CSV: nothing to add")
print("inbox left:", sorted(os.listdir(os.path.join(WS, "inbox"))))
