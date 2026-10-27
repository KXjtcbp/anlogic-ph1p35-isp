# -*- coding: utf-8 -*-
"""修正 docx 里 pPr / rPr / tblPr / tcPr 子元素的 XML schema 顺序。

Word 对 OOXML 子元素顺序是严格的，LibreOffice 宽松。
python-docx 用 append() 塞进去的元素（pBdr / shd / tblLayout）会排到 spacing / tblLook 之后，
结果就是：LibreOffice 打开一切正常，Word 打开排版错乱甚至打不开。
本脚本把四类容器的子元素按 ECMA-376 规定的顺序重排，并把表格 tblW 改成 dxa 实宽。
"""
import sys, zipfile, shutil, os
from lxml import etree

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

SRC = r"E:\FPGA\项目学习清单_20261023.docx"
BAK = r"E:\FPGA\_backup\20261027_learn_before_orderfix.docx"

ORD = {
    "pPr": ("pStyle keepNext keepLines pageBreakBefore framePr widowControl numPr "
            "suppressLineNumbers pBdr shd tabs suppressAutoHyphens kinsoku wordWrap "
            "overflowPunct topLinePunct autoSpaceDE autoSpaceDN bidi adjustRightInd "
            "snapToGrid spacing ind contextualSpacing mirrorIndents suppressOverlap jc "
            "textDirection textAlignment textboxTightWrap outlineLvl divId cnfStyle rPr "
            "sectPr pPrChange").split(),
    "rPr": ("rStyle rFonts b bCs i iCs caps smallCaps strike dstrike outline shadow "
            "emboss imprint noProof snapToGrid vanish webHidden color spacing w kern "
            "position sz szCs highlight u effect bdr shd fitText vertAlign rtl cs em "
            "lang eastAsianLayout specVanish oMath").split(),
    "tblPr": ("tblStyle tblpPr tblOverlap bidiVisual tblStyleRowBandSize "
              "tblStyleColBandSize tblW jc tblCellSpacing tblInd tblBorders shd "
              "tblLayout tblCellMar tblLook tblCaption tblDescription").split(),
    "tcPr": ("cnfStyle tcW gridSpan hMerge vMerge tcBorders shd noWrap tcMar "
             "textDirection tcFitText vAlign hideMark").split(),
}
IDX = {k: {n: i for i, n in enumerate(v)} for k, v in ORD.items()}


def local(t):
    return etree.QName(t).localname


def reorder(el, order, idx):
    kids = list(el)
    known = [k for k in kids if local(k) in idx]
    unknown = [k for k in kids if local(k) not in idx]
    known.sort(key=lambda k: idx[local(k)])
    for k in kids:
        el.remove(k)
    for k in known + unknown:
        el.append(k)


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
        if info.filename in ("word/document.xml", "word/styles.xml", "word/stylesWithEffects.xml"):
            root = etree.fromstring(data)
            n = 0
            for el in root.iter():
                q = local(el)
                if q in IDX:
                    reorder(el, ORD[q], IDX[q])
                    n += 1
            if info.filename == "word/document.xml":
                tw_fix = 0
                for tbl in root.iter(W + "tbl"):
                    pr = tbl.find(W + "tblPr")
                    grid = tbl.find(W + "tblGrid")
                    if pr is None or grid is None:
                        continue
                    cols = [int(g.get(W + "w")) for g in grid.findall(W + "gridCol")]
                    tw = pr.find(W + "tblW")
                    if tw is not None and cols:
                        tw.set(W + "w", str(sum(cols)))
                        tw.set(W + "type", "dxa")
                        tw_fix += 1
                print("  %-28s 重排 %d 个容器, tblW 改为 dxa %d 张" % (info.filename, n, tw_fix))
            else:
                print("  %-28s 重排 %d 个容器" % (info.filename, n))
            total += n
            data = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                                  standalone=True)
        zout.writestr(info, data)
    zout.close()
    print("总计重排", total, "个容器；文件", os.path.getsize(SRC), "B")


if __name__ == "__main__":
    main()
