# -*- coding: utf-8 -*-
"""把 W1-W3 / R1-R2 的真值行追加进 inbox/采集记录.csv（幂等：已存在同名行就跳过）"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
p = os.path.join(WS, "inbox", "采集记录.csv")
txt = open(p, "rb").read().decode("utf-8")
rows = [
 "W1.png,白纸靶面_舍入版后,10-13 21:33:51,白纸贴满画面,台灯直照,上,上,上,上,004414,0,00,2,R/G=0.9854 B/G=0.9834 R-G=-2.47；AE 把模拟增益压到最低档",
 "W2.png,白纸靶面_舍入版后,10-13 21:34:00,白纸贴满画面,台灯直照,上,上,上,上,004911,0,00,2,R/G=0.9843 B/G=0.9826 R-G=-2.70",
 "W3.png,白纸靶面_舍入版后,10-13 21:34:08,白纸贴满画面,台灯直照,上,上,上,上,005434,0,00,2,R/G=0.9865 B/G=0.9852 R-G=-2.18",
 "R1.png,白纸靶面_舍入版后,10-13 21:54:53,白纸贴满画面 + 相机原地旋转180度,台灯直照,上,上,上,上,080874,0,00,2,逐行剖面与 W1 几乎逐行重合(未反相)= 残余偏差固定在画面坐标而非场景",
 "R2.png,白纸靶面_舍入版后,10-13 21:55:15,白纸 + 周围墙地面,台灯直照,上,上,上,上,082237,0,00,2,上半暗区噪声主导；亮纸区 y900-1079 R/G=0.9827 B/G=0.9558",
]
add = [r for r in rows if r.split(",")[0] not in txt]
if add:
    if not txt.endswith("\n"):
        txt += "\n"
    txt += "\n".join(add) + "\n"
    open(p, "wb").write(txt.encode("utf-8"))
    print("added %d rows -> %d B" % (len(add), os.path.getsize(p)))
else:
    print("nothing to add (already present)")
print(open(p, "rb").read().decode("utf-8").count("\n") + 1, "lines total")
