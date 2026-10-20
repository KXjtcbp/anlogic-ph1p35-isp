# -*- coding: utf-8 -*-
"""核实：黑电平减法那段到底有没有被 /* */ 注释掉；本工程编的又是哪一份 raw10_unpacket_2lane。"""
import os, re

TREE = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
CAND = [
    os.path.join(TREE, "isp", "raw10_unpacket_2lane.v"),
    os.path.join(TREE, "uiisp_beta", "raw10_unpacket_2lane.v"),
    os.path.join(TREE, "raw10_unpacket.v"),
]
KEYS = [b"I_camera_black_level", b">> 2", b">>2", b"O_raw8", b"S_fifo_rd_data",
        b"black_level", b"O_raw10_data", b"assign O_raw10", b"module ",
        b"endmodule", b"fifo", b"FIFO"]

for p in CAND:
    if not os.path.exists(p):
        print(f"--- 不存在: {p}")
        continue
    raw = open(p, "rb").read()
    nl = raw.count(b"\n") + 1
    # 计算每行起始偏移 -> 行号
    starts, off = [], 0
    for line in raw.split(b"\n"):
        starts.append(off); off += len(line) + 1
    def lineno(pos):
        import bisect
        return bisect.bisect_right(starts, pos)
    # 找 /* */ 区间
    spans, i = [], 0
    while True:
        a = raw.find(b"/*", i)
        if a < 0: break
        b = raw.find(b"*/", a + 2)
        if b < 0: b = len(raw) - 2
        spans.append((a, b + 2)); i = b + 2
    def in_comment(pos):
        for a, b in spans:
            if a <= pos < b: return (lineno(a), lineno(b))
        return None
    print(f"\n=== {p}  ({len(raw)} B, {nl} 行, 块注释 {len(spans)} 段)")
    for a, b in spans:
        print(f"    块注释: 第 {lineno(a)} 行 .. 第 {lineno(b)} 行  ({b-a} 字节)")
    for k in KEYS:
        hits = [m.start() for m in re.finditer(re.escape(k), raw)]
        if not hits:
            print(f"    [ ] {k.decode():<24} 0 处")
            continue
        detail = []
        for h in hits[:4]:
            c = in_comment(h)
            detail.append(f"L{lineno(h)}" + ("(注释内)" if c else ""))
        print(f"    [x] {k.decode():<24} {len(hits):>3} 处 -> {', '.join(detail)}")
    # 端口清单
    m = re.search(rb"module\s+raw10_unpacket_2lane\b(.*?);", raw, re.S)
    if m:
        ports = re.findall(rb"\b(I_\w+|O_\w+)", m.group(1))
        print("    端口:", b", ".join(dict.fromkeys(ports)).decode("ascii"))

# 工程实际编译的是哪一份
al = r"E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display.al"
txt = open(al, "rb").read().decode("utf-8", "replace")
print("\n=== .al 里与 raw10 相关的条目 ===")
for line in txt.splitlines():
    if "raw10" in line.lower() or "unpacket" in line.lower():
        print("   ", line.strip())
