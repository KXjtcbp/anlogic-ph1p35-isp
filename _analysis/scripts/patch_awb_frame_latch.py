# -*- coding: utf-8 -*-
"""awb.v 帧锁存白平衡（AWB frame-latch）。

问题（由遥测行揭出来的）：
  `sum_r[0]/sum_g[0]/sum_b[0]` 在 `I_tuser` 被清零，而除法器的 `start` 接的是
  `I_tvalid_r1`（连续电平，一直在重启），`done[0]` 只要置起就把**当时的运行求和比**
  写进 `in_r_r1/in_b_r1`。于是：
    * 帧首累加器几乎为空 -> 商抖动极大（`sum_r` 为 0 时还会饱和到 20'hfffff）；
    * 增益在一帧之内从"上一帧的终值"一路被改成本帧的运行值，
      只有帧尾那一小段才等于真正的整帧灰世界比值。
  => 同一场景、同一固定 OSD 行，读数 `W`/`B` 帧间会漂（实测 1.186~1.415，±9%）。

修法（最小、可逆、ISP 常规做法）：
  在帧边界把"跑完整帧"的比值冻结进 `in_r_hold/in_b_hold`，整帧都用这一对常量乘；
  未锁存的 `in_r_r1/in_b_r1` 继续跟踪运行比值，只在帧边界被采样一次。

  乘法改用 hold 版本；遥测抽头 `O_gain_r/O_gain_b` 也改成 hold 版本，
  这样第 1 行显示的 `W`/`B` 就是**这一帧真正施加到每个像素上的**增益。
"""
import os, shutil, sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
P = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "awb.v")
BAK = os.path.join(WS, "_backup", "20261012p_awb_framelatch")
os.makedirs(BAK, exist_ok=True)

raw = open(P, "rb").read()
nl = b"\r\n" if raw.count(b"\r\n") > raw.count(b"\n") - raw.count(b"\r\n") else b"\n"
print("改前 %d B，行尾 CRLF=%d bareLF=%d" % (len(raw), raw.count(b"\r\n"), raw.count(b"\n") - raw.count(b"\r\n")))
shutil.copy2(P, os.path.join(BAK, "awb.v.before"))
txt = raw.decode("utf-8", "replace")
txt = txt.replace("\r\n", "\n")          # 匹配前统一成 LF，写回时再还原

# ---- 1) 声明 hold 寄存器 ----
old1 = "    reg  [19:0]   in_r_r1;\n    reg  [19:0]   in_b_r1;\n"
new1 = ("    reg  [19:0]   in_r_r1;\n    reg  [19:0]   in_b_r1;\n"
        "    // [HDR-2026-10-12p] 帧锁存后的\"本帧实际使用\"的增益\n"
        "    reg  [19:0]   in_r_hold;\n    reg  [19:0]   in_b_hold;\n")
assert txt.count(old1) == 1, "声明锚点命中 %d 次" % txt.count(old1)
txt = txt.replace(old1, new1, 1)

# ---- 2) 增益更新块：加帧边界锁存 ----
old2 = ("        if(!I_rst_n)begin\n"
        "            in_r_r1 <= 20'h10000;\n"
        "            in_b_r1 <= 20'h10000;\n"
        "        end\n"
        "        else if(done[0])begin\n"
        "            if(|in_r_x1[47:20])\n"
        "                in_r_r1 <= 20'hfffff;\n"
        "            else \n"
        "                in_r_r1 <= in_r_x1[19:0];\n"
        "            if(|in_b_x1[47:20])\n"
        "                in_b_r1 <= 20'hfffff;\n"
        "            else \n"
        "                in_b_r1 <= in_b_x1[19:0];\n"
        "        end\n")
new2 = ("        if(!I_rst_n)begin\n"
        "            in_r_r1   <= 20'h10000;\n"
        "            in_b_r1   <= 20'h10000;\n"
        "            in_r_hold <= 20'h10000;\n"
        "            in_b_hold <= 20'h10000;\n"
        "        end\n"
        "        else begin\n"
        "            if(done[0])begin\n"
        "                if(|in_r_x1[47:20])\n"
        "                    in_r_r1 <= 20'hfffff;\n"
        "                else \n"
        "                    in_r_r1 <= in_r_x1[19:0];\n"
        "                if(|in_b_x1[47:20])\n"
        "                    in_b_r1 <= 20'hfffff;\n"
        "                else \n"
        "                    in_b_r1 <= in_b_x1[19:0];\n"
        "            end\n"
        "            // [HDR-2026-10-12p] ★帧锁存★\n"
        "            //   I_tuser 是帧首那一拍。此刻 in_r_r1/in_b_r1 里放的正是\n"
        "            //   上一帧跑到帧尾时用满累加器算出来的比值 = 真正的整帧灰世界比值。\n"
        "            //   把它冻结进 *_hold，整帧所有像素都用这一对常量乘，\n"
        "            //   于是增益在帧内恒定、帧间一步到位，不再有\"帧首从空累加器起算\"的抖动。\n"
        "            if(I_tuser)begin\n"
        "                in_r_hold <= in_r_r1;\n"
        "                in_b_hold <= in_b_r1;\n"
        "            end\n"
        "        end\n")
assert txt.count(old2) == 1, "更新块锚点命中 %d 次" % txt.count(old2)
txt = txt.replace(old2, new2, 1)

# ---- 3) 乘法改用 hold 版本（8 处） ----
n = 0
for j in (1, 2, 3, 4):
    a = "            R_new_r%d <= in_r_r1 * rgb888_r_d1[%d];\n" % (j, j - 1)
    b = "            R_new_r%d <= in_r_hold * rgb888_r_d1[%d];\n" % (j, j - 1)
    assert txt.count(a) == 1, "乘法 R r%d 锚点命中 %d 次" % (j, txt.count(a))
    txt = txt.replace(a, b, 1); n += 1
    a = "            B_new_r%d <= in_b_r1 * rgb888_b_d1[%d];\n" % (j, j - 1)
    b = "            B_new_r%d <= in_b_hold * rgb888_b_d1[%d];\n" % (j, j - 1)
    assert txt.count(a) == 1, "乘法 B r%d 锚点命中 %d 次" % (j, txt.count(a))
    txt = txt.replace(a, b, 1); n += 1
print("乘法改写 %d 处" % n)

# ---- 4) 遥测抽头改成 hold 版本 ----
old4 = "    assign O_gain_r = in_r_r1;\n    assign O_gain_b = in_b_r1;\n"
new4 = ("    // [HDR-2026-10-12p] 遥测显示\"本帧实际施加\"的增益（帧锁存后的值）\n"
        "    assign O_gain_r = in_r_hold;\n    assign O_gain_b = in_b_hold;\n")
if txt.count(old4) == 1:
    txt = txt.replace(old4, new4, 1); print("遥测抽头已改为 hold 版本")
else:
    print("★ 警告：遥测抽头锚点命中 %d 次，未改（请手工确认）" % txt.count(old4))

out = txt.encode("utf-8")
if nl == b"\r\n":
    out = out.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
P_final = P
open(P_final, "wb").write(out)
print("改后 %d B  (+%d)" % (len(out), len(out) - len(raw)))

chk = open(P_final, "rb").read()
print("CRLF=%d bareLF=%d 首3字节=%r" % (chk.count(b"\r\n"), chk.count(b"\n") - chk.count(b"\r\n"), chk[:3]))
for k in (b"in_r_hold", b"in_b_hold", b"in_r_r1 * ", b"in_b_r1 * "):
    print("  %-12s 出现 %d 次" % (k.decode(), chk.count(k)))
print("备份:", os.path.join(BAK, "awb.v.before"), os.path.getsize(os.path.join(BAK, "awb.v.before")), "B")
