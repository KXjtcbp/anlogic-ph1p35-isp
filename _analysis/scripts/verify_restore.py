# -*- coding: utf-8 -*-
"""校验：把插入块摘掉后，文件是否与还原源逐字节相同（确认零丢字）。"""
import os

HDL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\my_algo"
BAK = r"E:\FPGA\_backup\20261009_comments\core"
RTL = r"E:\FPGA\proj\rtl\my_algo"

CASES = [
    ("my_algo.v", os.path.join(BAK, "my_algo__my_algo.v.bak"), 10),
    ("key_mode_ctrl.v", os.path.join(RTL, "key_mode_ctrl.v"), 9),
]

for name, src, nblk in CASES:
    cur = open(os.path.join(HDL, name), "rb").read()
    org = open(src, "rb").read()
    lines = cur.split(b"\n")
    stripped = b"\n".join(lines[nblk:])
    print(f"### {name}")
    print(f"    现文件 {len(cur)} B / {len(lines)-1} 行")
    print(f"    摘掉前 {nblk} 行后：{len(stripped)} B，与还原源 {len(org)} B "
          f"{'完全一致 (OK)' if stripped == org else '不一致 (NG)'}")
    # 若 J14->D5 生效，会有一处 3 字节差异，单独比对
    if stripped != org:
        d = sum(1 for a, b in zip(stripped, org) if a != b)
        print(f"    字节差异数 = {d}（若为 3，且长度相同，即为 J14->D5 修正所致）")
    print("    插入块前 3 行：")
    for l in lines[:3]:
        print("      |", l.decode("utf-8", "replace")[:90])
    print("    第 %d 行（块后第一行）：" % (nblk + 1), lines[nblk].decode("utf-8", "replace")[:90])
