# -*- coding: utf-8 -*-
"""
把 lsc.v 直接写进两个 run 目录的 .prj（TD 真正读的那份），不经过 .al。

★为什么必须这样★：2026-10-14 那轮构建里，我先把 lsc.v 加进 td_project/*.al
（24762 -> 25135 B），但 TD 跑完把 .al 原样写回了 24762 B（mtime 落在构建窗口内），
结果 sync_al_to_prj.py 读到的是被 TD 回滚过的 .al，.prj 里就没有 lsc.v，
综合阶段报 HDL-8007 ERROR: lsc ... is a black box，而 phy_1 又用旧 DB 跑出
一份"数字与前一轮逐位相同"的假成功。
⇒ .prj 是权威，.al 只是 GUI 的投影；新文件必须直接写进 .prj。

顺带把 .al 也补上（GUI 里能看到）。CRLF，幂等。
"""
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"E:\FPGA"
PRJS = [
    os.path.join(WS, "proj", "baseline", "lab3", "td_project",
                 "camera_to_dsi_display_Runs", "syn_1", "camera_to_dsi_display.prj"),
    os.path.join(WS, "proj", "baseline", "lab3", "td_project",
                 "camera_to_dsi_display_Runs", "phy_1", "camera_to_dsi_display.prj"),
]
AL = os.path.join(WS, "proj", "baseline", "lab3", "td_project", "camera_to_dsi_display.al")

NEW_PATH = "../../../user_source/hdl_source/isp/lsc.v"     # .prj 里相对 run 目录
NEW_PATH_AL = "../user_source/hdl_source/isp/lsc.v"        # .al  里相对 td_project
ANCHOR = "ae_ctrl.v"


def add(path, newpath, tag):
    b = open(path, "rb").read()
    txt = b.decode("utf-8")
    if "lsc.v" in txt:
        print("  %-6s 已有 lsc.v，跳过" % tag)
        return
    m = re.search(r'[ \t]*<File Path="[^"]*%s">.*?</File>\r?\n' % re.escape(ANCHOR),
                  txt, flags=re.S)
    if not m:
        print("  !! %-6s 找不到 %s 的 <File> 块" % (tag, ANCHOR))
        sys.exit(1)
    indent = re.match(r'[ \t]*', m.group(0)).group(0)
    blk = (indent + '<File Path="%s">\n' % newpath +
           indent + '    <FileInfo>\n' +
           indent + '        <Attr Name="UsedInSyn" Val="true"/>\n' +
           indent + '        <Attr Name="UsedInP&R" Val="true"/>\n' +
           indent + '        <Attr Name="BelongTo" Val="design_1"/>\n' +
           indent + '        <Attr Name="CompileOrder" Val="57"/>\n' +
           indent + '    </FileInfo>\n' +
           indent + '</File>\n')
    out = txt[:m.end()] + blk + txt[m.end():]
    open(path, "wb").write(out.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))
    print("  %-6s %d -> %d B" % (tag, len(b), os.path.getsize(path)))


for p in PRJS:
    add(p, NEW_PATH, os.path.basename(os.path.dirname(p)))
add(AL, NEW_PATH_AL, ".al")

# 复核：两个 .prj 里 lsc.v 的位置与顺序
for p in PRJS:
    t = open(p, "rb").read().decode("utf-8")
    tag = os.path.basename(os.path.dirname(p))
    files = re.findall(r'<File Path="([^"]+)"', t)
    print("%-6s 共 %d 个 File 条目，lsc.v 在序号 %s" %
          (tag, len(files), files.index(NEW_PATH) if NEW_PATH in files else "缺失"))
