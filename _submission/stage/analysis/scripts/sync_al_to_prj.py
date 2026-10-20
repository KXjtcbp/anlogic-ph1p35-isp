# -*- coding: utf-8 -*-
"""把 td_project/camera_to_dsi_display.al 的 Verilog 文件清单同步进各个 run 目录的 .prj。

★为什么需要这个脚本（2026-10-12 踩的坑）★
TD 命令行流程（`DefaultFlow.tcl`）读的是 **run 目录里的 `camera_to_dsi_display.prj`**，
**不是** `td_project/camera_to_dsi_display.al`。
只改 `.al` 而不改 `.prj` 的后果是：新加的 .v 文件根本没被 analyze，
综合把它当**黑盒**，打印

    HDL-8007 ERROR: ae_ctrl(...) is a black box in .../design_top_wrapper.v(603)
    HDL-8007 ERROR: ae_stat is a black box in .../isp_top.v(192)

然后**照常跑完 place/route/bitgen 并产出一个 .bit**，退出码 0，
route.qor 的数字与上一轮**逐位相同**（因为网表里压根没变）。
这就是本项目第二次踩到「假成功」（第一次是 Tcl 脚本路径里的反斜杠被吃掉）。

用法：
    python sync_al_to_prj.py [--check] [--repo E:\\FPGA]

- 默认：就地修改每个 run 目录的 .prj，打印新增了哪些条目
- `--check`：只报告差异，不写文件（返回码 1 表示有差异）
"""
import os
import re
import sys

_AL_REL = os.path.join("proj", "baseline", "lab3", "td_project", "camera_to_dsi_display.al")
_RUNS_REL = os.path.join("proj", "baseline", "lab3", "td_project",
                         "camera_to_dsi_display_Runs")

# .al 里写 "../user_source/..."，run 目录要写成 "../../../user_source/..."
_AL_PREFIX = "../"
_PRJ_PREFIX = "../../../"

_FILE_BLOCK = (
    '            <File Path="{path}">\n'
    '                <FileInfo>\n'
    '                    <Attr Name="UsedInSyn" Val="true"/>\n'
    '                    <Attr Name="UsedInP&R" Val="true"/>\n'
    '                    <Attr Name="BelongTo" Val="design_1"/>\n'
    '                    <Attr Name="CompileOrder" Val="{order}"/>\n'
    '                </FileInfo>\n'
    '            </File>\n'
)

_ENTRY_RE = re.compile(
    r'<File\s+Path="([^"]+)">\s*'
    r'<FileInfo>\s*(.*?)\s*</FileInfo>\s*'
    r'</File>',
    re.S,
)
_ORDER_RE = re.compile(r'<Attr\s+Name="CompileOrder"\s+Val="(\d+)"\s*/>')


def parse_al(al_path):
    """返回 [(prj_path, compile_order)]，按 CompileOrder 升序。

    ★必须先把范围夹到 <Verilog> ... </Verilog> 之间★ —— .al 里还有别的
    段落（<FileSets> 等）也带 <File Path="...">，全文件扫会把
    `camera_to_dsi_display.sdc` 这类条目误判成"缺失"，插出一条错误的记录。
    """
    text = open(al_path, "r", encoding="utf-8", errors="replace").read()
    m = re.search(r'<Verilog>(.*?)</Verilog>', text, re.S)
    section = m.group(1) if m else text
    out = []
    for path, info in _ENTRY_RE.findall(section):
        o = _ORDER_RE.search(info)
        if not o:
            continue
        prj_path = path
        if prj_path.startswith(_AL_PREFIX):
            prj_path = _PRJ_PREFIX + prj_path[len(_AL_PREFIX):]
        out.append((prj_path, int(o.group(1))))
    out.sort(key=lambda t: t[1])
    return out


def parse_prj(prj_path):
    text = open(prj_path, "r", encoding="utf-8", errors="replace").read()
    entries = []
    for m in _ENTRY_RE.finditer(text):
        o = _ORDER_RE.search(m.group(2))
        entries.append({
            "path": m.group(1),
            "order": int(o.group(1)) if o else -1,
            "start": m.start(),
            "end": m.end(),
        })
    return text, entries


def sync_one(prj_path, wanted, check_only):
    text, entries = parse_prj(prj_path)
    have = {e["path"] for e in entries}
    missing = [(p, o) for p, o in wanted if p not in have]
    # CompileOrder 撞车也报一下（TD 对重复 order 的容忍度不明）
    orders = {}
    for e in entries:
        orders.setdefault(e["order"], []).append(e["path"])
    dup = {o: v for o, v in orders.items() if len(v) > 1}
    if not missing:
        return 0, dup
    if check_only:
        return len(missing), dup

    for path, order in missing:
        # 插到 CompileOrder 刚好比它大的那条前面；没有就插在 </Verilog> 之前
        anchor = None
        for e in sorted(entries, key=lambda x: x["order"]):
            if e["order"] > order:
                anchor = e
                break
        block = _FILE_BLOCK.format(path=path, order=order)
        if anchor is not None:
            text = text[:anchor["start"]] + block + text[anchor["start"]:]
        else:
            text = text.replace("           </Verilog>", block + "           </Verilog>", 1)
        # 重新解析，保证后续插入的位置正确
        _, entries = parse_prj_text(text)
    # ★必须以字节写回并保留 CRLF★ —— 用文本模式 + newline="" 读进来的是 LF，
    # 写回去会把整个文件的 CRLF 变成 LF（第一次跑就把两个 .prj 各缩了约 140 B）。
    raw = open(prj_path, "rb").read()
    crlf_before = raw.count(b"\r\n")
    body = text.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8")
    open(prj_path, "wb").write(body)
    print("     (CRLF %d -> %d, size %d -> %d)" % (crlf_before, body.count(b"\r\n"), len(raw), len(body)))
    return len(missing), dup


def parse_prj_text(text):
    entries = []
    for m in _ENTRY_RE.finditer(text):
        o = _ORDER_RE.search(m.group(2))
        entries.append({"path": m.group(1),
                        "order": int(o.group(1)) if o else -1,
                        "start": m.start(), "end": m.end()})
    return text, entries


def main():
    argv = sys.argv[1:]
    check_only = "--check" in argv
    repo = r"E:\FPGA"
    if "--repo" in argv:
        repo = argv[argv.index("--repo") + 1]

    al = os.path.join(repo, _AL_REL)
    runs = os.path.join(repo, _RUNS_REL)
    if not os.path.exists(al):
        print("MISSING", al)
        return 2
    wanted = parse_al(al)
    print("=== .al 共 %d 条 Verilog 文件 ===" % len(wanted))
    for p, o in wanted:
        print("   %3d  %s" % (o, p))

    total = 0
    for run in sorted(os.listdir(runs)):
        d = os.path.join(runs, run)
        prj = os.path.join(d, "camera_to_dsi_display.prj")
        if not os.path.isfile(prj):
            continue
        n, dup = sync_one(prj, wanted, check_only)
        total += n
        print("\n=== %s : %s" % (run, "缺 %d 条" % n if n else "已同步"))
        if n and check_only:
            # 打印具体缺哪些
            _, entries = parse_prj(prj)
            have = {e["path"] for e in entries}
            for p, o in wanted:
                if p not in have:
                    print("     MISSING  %3d  %s" % (o, p))
        if dup:
            for o, v in dup.items():
                print("     NOTE CompileOrder %s 有 %d 个条目: %s" % (o, len(v), v))

    if check_only:
        print("\n==> %s" % ("有差异，需要同步" if total else "全部已同步"))
        return 1 if total else 0
    print("\n==> 同步完成，共插入 %d 条" % total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
