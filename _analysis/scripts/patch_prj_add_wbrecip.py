# -*- coding: utf-8 -*-
"""把 wb_recip.v 加进两个 run 的 .prj 以及 td_project 的 .al，并修正 awb.v 头部注释。

★ 为什么必须写 .prj 而不只是 .al ★
  TD 命令行流程读的是 run 目录下的 camera_to_dsi_display.prj，不是 td_project 的 .al；
  而且 TD 跑完会按自己的内部状态把 .al 回写覆盖。本项目已因此踩过两次「假成功」
  （HDL-8007 black box 却照常产出新时间戳 .bit）。
"""
import os, re, sys, shutil
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"E:\FPGA"
LAB3 = os.path.join(ROOT, "proj", "baseline", "lab3")
PRJ_REL = "../../../user_source/hdl_source/wb_recip.v"
NEW_ORDER = "58"          # lsc.v 是 57
TAG = "wb_recip.v"

targets = [
    os.path.join(LAB3, "td_project", "camera_to_dsi_display_Runs", "syn_1", "camera_to_dsi_display.prj"),
    os.path.join(LAB3, "td_project", "camera_to_dsi_display_Runs", "phy_1", "camera_to_dsi_display.prj"),
    os.path.join(LAB3, "td_project", "camera_to_dsi_display.al"),
]

BLOCK = (
    '                                    <File Path="%s">\n'
    '                                        <FileInfo>\n'
    '                                            <Attr Name="UsedInSyn" Val="true"/>\n'
    '                                            <Attr Name="UsedInP&R" Val="true"/>\n'
    '                                            <Attr Name="BelongTo" Val="design_1"/>\n'
    '                                            <Attr Name="CompileOrder" Val="%s"/>\n'
    '                                        </FileInfo>\n'
    '                                    </File>\n'
) % (PRJ_REL, NEW_ORDER)

for p in targets:
    if not os.path.exists(p):
        print("MISSING %s" % p); continue
    shutil.copy2(p, p + ".bak_wbrecip")
    txt = open(p, "rb").read().decode("utf-8", errors="replace")
    before = len(txt)
    if TAG in txt:
        print("SKIP (already present) %s" % os.path.basename(p)); continue
    # 找到 lsc.v 那个 <File ...> ... </File> 块的结尾，插在它后面
    m = re.search(r'<File Path="[^"]*lsc\.v">.*?</File>\s*', txt, re.S)
    if not m:
        print("!! lsc.v block not found in %s" % os.path.basename(p)); continue
    ins = m.end()
    txt = txt[:ins] + BLOCK + txt[ins:]
    open(p, "wb").write(txt.encode("utf-8"))
    print("OK  %-34s %d -> %d B" % (os.path.basename(p), before, len(txt)))

# ---- 修正 awb.v 头部注释（原描述仍写"例化两个 divider"）----
awb = os.path.join(LAB3, "user_source", "hdl_source", "awb.v")
s = open(awb, "rb").read().decode("utf-8")
old5 = "②除法区：例化两个 divider（div_gen_G_R_r1 / divide_G_B_r1），.numerator({sum_g[0],16d0})、.denominator(sum_r[0])/(sum_b[0])、.start(I_tvalid_r1)，得到 48bit 的 dout_R[0]/dout_B[0]；"
new5 = "②除法区：[HDR-2026-10-15a] 已由两个 TD 流水 divider 改为 wb_recip.v（归一化+倒数ROM+一次乘法），.I_den(sum_r[0])/(sum_b[0])、.I_num(sum_g[0])，输出 48bit in_r_x1/in_b_x1；"
old7 = "// 依赖      : 例化 divider（除法器 IP，两处）与 signal_delay（本目录 signal_delay.v，内部再例化 BRAM blk_mem_gen_awb_delay_signal）。"
new7 = "// 依赖      : [HDR-2026-10-15a] wb_recip.v（倒数查表除法，替代原两个 TD divider）与 signal_delay（本目录 signal_delay.v，内部再例化 BRAM blk_mem_gen_awb_delay_signal）。"
n = 0
if old5 in s: s = s.replace(old5, new5); n += 1
if old7 in s: s = s.replace(old7, new7); n += 1
if n:
    open(awb, "wb").write(s.encode("utf-8"))
    print("awb.v 头部注释修正 %d 处" % n)
else:
    print("awb.v 头部注释未匹配（跳过）")

print("\n=== 校验：三个文件里 wb_recip.v 出现次数 ===")
for p in targets:
    t = open(p, "rb").read().decode("utf-8", errors="replace")
    print("  %-34s %d 次" % (os.path.basename(p), t.count(TAG)))
