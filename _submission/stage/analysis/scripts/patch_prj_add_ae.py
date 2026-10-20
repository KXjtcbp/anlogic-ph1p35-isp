# -*- coding: utf-8 -*-
"""把 ae_stat.v / ae_ctrl.v 插进 TD run 目录的 camera_to_dsi_display.prj。

★背景★：TD 命令行流程读的是 run 目录的 .prj，不是 td_project 的 .al。
只改 .al 会让新 .v 变成黑盒（HDL-8007），综合照样跑完并产出一个"数字与上轮完全相同"的 .bit。

用法：python patch_prj_add_ae.py [--check]
"""
import os
import re
import sys

R = r"E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display_Runs"
RUNS = ("syn_1", "phy_1")

NEW = [
    ("../../../user_source/hdl_source/isp/ae_stat.v", 55),
    ("../../../user_source/hdl_source/isp/ae_ctrl.v", 56),
]


def block(path, order):
    return (
        '            <File Path="%s">\n'
        '                <FileInfo>\n'
        '                    <Attr Name="UsedInSyn" Val="true"/>\n'
        '                    <Attr Name="UsedInP&R" Val="true"/>\n'
        '                    <Attr Name="BelongTo" Val="design_1"/>\n'
        '                    <Attr Name="CompileOrder" Val="%d"/>\n'
        '                </FileInfo>\n'
        '            </File>\n' % (path, order)
    )


def entry_re(path):
    return re.compile(
        r'[ \t]*<File\s+Path="' + re.escape(path) + r'">\s*'
        r'<FileInfo>.*?</FileInfo>\s*</File>\s*\n?', re.S)


def main():
    check_only = "--check" in sys.argv
    for run in RUNS:
        p = os.path.join(R, run, "camera_to_dsi_display.prj")
        raw = open(p, "rb").read()
        had_crlf = raw.count(b"\r\n")
        t = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")

        # 1) 清掉上一版脚本误插的裸 camera_to_dsi_display.sdc 条目
        bogus = entry_re("camera_to_dsi_display.sdc")
        nbogus = len(bogus.findall(t))
        if nbogus:
            t = bogus.sub("", t)

        # 2) 逐个插入
        added = []
        for path, order in NEW:
            if path in t:
                continue
            m = entry_re("../../../user_source/hdl_source/isp/isp_gamma.v").search(t)
            if not m:
                print("  !! %s: 找不到 isp_gamma.v 锚点" % run)
                break
            t = t[:m.end()] + block(path, order) + t[m.end():]
            added.append(path)

        if check_only:
            print("%-7s bogus_sdc=%d  to_add=%s" % (run, nbogus, [a.rsplit('/', 1)[-1] for a in added]))
            continue
        raw2 = t.replace("\n", "\r\n").encode("utf-8")
        open(p, "wb").write(raw2)
        print("%-7s removed bogus_sdc=%d  added=%s  CRLF %d->%d  size %d->%d"
              % (run, nbogus, [a.rsplit('/', 1)[-1] for a in added],
                 had_crlf, raw2.count(b"\r\n"), len(raw), len(raw2)))

    # 复核
    print("\n===== verify =====")
    for run in RUNS:
        p = os.path.join(R, run, "camera_to_dsi_display.prj")
        t = open(p, "rb").read().decode("utf-8", errors="replace")
        print("  %-7s ae_stat=%s ae_ctrl=%s  isp_gamma_order=%s"
              % (run, "ae_stat.v" in t, "ae_ctrl.v" in t,
                 (re.search(r'ae_stat\.v">\s*<FileInfo>.*?CompileOrder"\s+Val="(\d+)"', t, re.S) or ["?", "?"])[1]))


if __name__ == "__main__":
    main()
