# -*- coding: utf-8 -*-
"""归档 E1/E2/E3（带标记的旋转对照）+ 追加采集记录 CSV（幂等）"""
import os, shutil, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
src_dir = os.path.join(WS, "inbox")
dst = os.path.join(WS, "captures", "2026-10-13_带标记旋转对照")
os.makedirs(dst, exist_ok=True)

plan = [("Screenshot 2026-10-13 22-02-32.png", "E1_220232_相机原位_标记在左下_CNT108736.png"),
        ("Screenshot 2026-10-13 22-02-43.png", "E2_220243_相机转180_标记移到中右_CNT109427.png"),
        ("Screenshot 2026-10-13 22-03-05.png", "E3_220305_转回原位_标记回到左侧_CNT110751.png")]
for s, d in plan:
    sp = os.path.join(src_dir, s)
    if os.path.exists(sp):
        shutil.move(sp, os.path.join(dst, d))
        print("moved -> %s (%d B)" % (d, os.path.getsize(os.path.join(dst, d))))
    else:
        print("SKIP:", s)

p = os.path.join(src_dir, "采集记录.csv")
txt = open(p, "rb").read().decode("utf-8")
rows = [
 "E1_220232_相机原位_标记在左下_CNT108736.png,带标记旋转对照,10-13 22:02:32,白色塑料面+一支出记标记物,台灯直照,上,上,上,上,108736,0,00,2,"
 "基准。整帧 Y=98.66 R/G=0.9658 B/G=0.9613；逐列最绿 x=640 R/G=0.921、两端边缘 1.03/1.03；标记物质心 (283,797)",
 "E2_220243_相机转180_标记移到中右_CNT109427.png,带标记旋转对照,10-13 22:02:43,同上（相机原地转180度，标记物世界位置不动）,台灯直照,上,上,上,上,109427,0,00,2,"
 "★标记物质心从 (283,797) 移到 (1136,737) => 旋转确实发生★。逐列最绿 x=800 R/G=0.933、两端 1.00/1.01 —— 色碗位置未动",
 "E3_220305_转回原位_标记回到左侧_CNT110751.png,带标记旋转对照,10-13 22:03:05,同 E1（相机转回）,台灯直照,上,上,上,上,110751,0,00,2,"
 "标记物回到左侧、纸面点阵纹理与 E1 同位 => 转回成功。逐列最绿 x=800/960 R/G=0.938、两端 1.07/1.02 —— 色碗仍在画面中心",
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
print("inbox left:", sorted(os.listdir(src_dir)))
