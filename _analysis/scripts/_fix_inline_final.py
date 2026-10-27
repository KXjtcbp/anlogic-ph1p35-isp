# -*- coding: utf-8 -*-
"""docx 内联 markdown 终极解析器（后处理版）。

在最终 docx 上遍历所有 <w:t>，把 `x` 转成等宽 run、**x** 转成加粗 run。
拆 run 时复制原 run 的 rPr，并把相邻同格式的 run 合并，避免碎片化。
这样无论生成器哪条输出路径漏了 inline()，最终产物都不会残留字面 markdown。
"""
import sys, os, zipfile, shutil
from copy import deepcopy
from lxml import etree

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SRC = r"E:\FPGA\项目学习清单_20261023.docx"
BAK = r"E:\FPGA\_backup\20261027_learn_before_inline.docx"
MONO = "Consolas"

TOKEN = None
import re
TOKEN = re.compile(r"(\*\*.+?\*\*|`[^`\n]+`)", re.S)


def get_or_add(rpr, tag):
    e = rpr.find(W + tag)
    if e is None:
        e = etree.SubElement(rpr, W + tag)
    return e


def set_mono(run, on):
    rpr = run.find(W + "rPr")
    if rpr is None:
        rpr = etree.Element(W + "rPr")
        run.insert(0, rpr)
    for tag in ("rFonts",):
        e = rpr.find(W + tag)
        if on:
            if e is None:
                e = etree.Element(W + tag)
                rpr.insert(0, e)
            e.set(W + "ascii", MONO)
            e.set(W + "hAnsi", MONO)
            e.set(W + "cs", MONO)
    if on:
        sz = rpr.find(W + "sz")
        # 等宽代码在原字号基础上略缩 1 磅，视觉更协调
        if sz is not None:
            try:
                v = int(sz.get(W + "val"))
                sz.set(W + "val", str(max(16, v - 2)))
            except Exception:
                pass


def set_bold(run):
    rpr = run.find(W + "rPr")
    if rpr is None:
        rpr = etree.Element(W + "rPr")
        run.insert(0, rpr)
    b = rpr.find(W + "b")
    if b is None:
        b = etree.Element(W + "b")
        # w:b 必须在 w:color/sz/... 之前，简单起见插到 rPr 最前
        rpr.insert(0, b)


def split_run(run, text, parent):
    """把 run 的文本按 markdown 拆成多个 run，返回新建的 run 列表。"""
    out = []
    pos = 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            out.append((text[pos:m.start()], None))
        tok = m.group(0)
        if tok.startswith("**"):
            out.append((tok[2:-2], "b"))
        else:
            out.append((tok[1:-1], "m"))
        pos = m.end()
    if pos < len(text):
        out.append((text[pos:], None))
    if not out:
        return []
    base_rpr = run.find(W + "rPr")
    made = []
    for seg, kind in out:
        nr = etree.Element(W + "r")
        if base_rpr is not None:
            nr.append(deepcopy(base_rpr))
        t = etree.SubElement(nr, W + "t")
        t.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
        t.text = seg
        if kind == "m":
            set_mono(nr, True)
        elif kind == "b":
            set_bold(nr)
        made.append(nr)
    # 用新 run 替换原 run
    idx = list(parent).index(run)
    parent.remove(run)
    for k, nr in enumerate(made):
        parent.insert(idx + k, nr)
    return made


def main():
    if not os.path.exists(BAK):
        os.makedirs(os.path.dirname(BAK), exist_ok=True)
        shutil.copy2(SRC, BAK)
        print("backup ->", BAK)

    zin = zipfile.ZipFile(SRC)
    items = [(i, zin.read(i.filename)) for i in zin.infolist()]
    zin.close()

    total = 0
    zout = zipfile.ZipFile(SRC, "w", zipfile.ZIP_DEFLATED)
    for info, data in items:
        if info.filename != "word/document.xml":
            zout.writestr(info, data)
            continue
        root = etree.fromstring(data)
        n = 0
        for run in list(root.iter(W + "r")):
            # 代码块里的 run 已经整行是等宽，跳过，避免把 Verilog 里的 ` 当标记
            rpr = run.find(W + "rPr")
            if rpr is not None:
                f = rpr.find(W + "rFonts")
                if f is not None and f.get(W + "ascii") == MONO:
                    continue
            ts = run.findall(W + "t")
            if len(ts) != 1:
                continue
            txt = ts[0].text or ""
            if "`" not in txt and "**" not in txt:
                continue
            parent = run.getparent()
            if parent is None:
                continue
            made = split_run(run, txt, parent)
            if made:
                n += 1
        print("%s: 拆分 %d 个 run" % (info.filename, n))
        total += n
        zout.writestr(info, etree.tostring(root, xml_declaration=True,
                                           encoding="UTF-8", standalone=True))
    zout.close()
    print("合计拆分", total, "| 文件", os.path.getsize(SRC), "B")


if __name__ == "__main__":
    main()
