# -*- coding: utf-8 -*-
"""把 docx 里所有表格的列宽压进正文可用宽度，并给每个单元格写实的 tcW。

Word 在 tblLayout=fixed 时按 tblGrid 的列宽排版；如果列宽之和超过
「页面宽 − 左右边距」，表格会越过右边距画到页面外，看起来就是排版错乱。
LibreOffice 会悄悄缩回页内，所以用 LibreOffice 渲染看不出问题。
本脚本按比例缩放，并同步 tcW，保证 grid / 单元格 / tblW 三者一致且不超宽。
"""
import sys, zipfile, shutil, os
from lxml import etree

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
SRC = r"E:\FPGA\项目学习清单_20261023.docx"
BAK = r"E:\FPGA\_backup\20261027_learn_before_widthfix.docx"

TWIP_PER_CM = 567


def main():
    if not os.path.exists(BAK):
        os.makedirs(os.path.dirname(BAK), exist_ok=True)
        shutil.copy2(SRC, BAK)
        print("backup ->", BAK)

    zin = zipfile.ZipFile(SRC)
    items = [(i, zin.read(i.filename)) for i in zin.infolist()]
    zin.close()

    zout = zipfile.ZipFile(SRC, "w", zipfile.ZIP_DEFLATED)
    for info, data in items:
        if info.filename != "word/document.xml":
            zout.writestr(info, data)
            continue

        root = etree.fromstring(data)

        # 1) 读 section 的页面宽与边距，算出可用宽度
        sect = None
        for sp in root.iter(W + "sectPr"):
            sect = sp
        pg = sect.find(W + "pgSz")
        mar = sect.find(W + "pgMar")
        page_w = int(pg.get(W + "w"))
        left = int(mar.get(W + "left"))
        right = int(mar.get(W + "right"))
        avail = page_w - left - right
        target = avail - 60            # 留 60 twip（约 0.1 cm）松弛
        print("页面宽 %d twip, 边距 %d + %d, 可用 %d twip (%.2f cm)"
              % (page_w, left, right, avail, avail / TWIP_PER_CM))
        print("表格目标总宽 %d twip (%.2f cm)" % (target, target / TWIP_PER_CM))

        scaled = 0
        for tbl in root.iter(W + "tbl"):
            grid = tbl.find(W + "tblGrid")
            if grid is None:
                continue
            gcols = grid.findall(W + "gridCol")
            old = [int(g.get(W + "w")) for g in gcols]
            total = sum(old)
            if total == 0:
                continue
            if total > target:
                new = [max(1, int(round(w * target / total))) for w in old]
                # 修掉取整误差，保证和正好等于 target
                diff = target - sum(new)
                new[-1] += diff
                for g, w in zip(gcols, new):
                    g.set(W + "w", str(w))
                scaled += 1
            else:
                new = old

            # 2) tblW 同步
            pr = tbl.find(W + "tblPr")
            if pr is not None:
                tw = pr.find(W + "tblW")
                if tw is None:
                    tw = etree.SubElement(pr, W + "tblW")
                tw.set(W + "w", str(sum(new)))
                tw.set(W + "type", "dxa")
                # tblInd 归零，避免额外缩进把表推出边界
                ind = pr.find(W + "tblInd")
                if ind is not None:
                    ind.set(W + "w", "0")
                    ind.set(W + "type", "dxa")

            # 3) 每个单元格写 tcW（考虑 gridSpan）
            for tr in tbl.findall(W + "tr"):
                ci = 0
                for tc in tr.findall(W + "tc"):
                    tcpr = tc.find(W + "tcPr")
                    if tcpr is None:
                        tcpr = etree.SubElement(tc, W + "tcPr")
                        tc.remove(tcpr)
                        tc.insert(0, tcpr)
                    span = 1
                    gs = tcpr.find(W + "gridSpan")
                    if gs is not None:
                        span = int(gs.get(W + "val"))
                    wsum = sum(new[ci:ci + span]) if ci < len(new) else 0
                    tw = tcpr.find(W + "tcW")
                    if tw is None:
                        tw = etree.Element(W + "tcW")
                        tcpr.insert(0, tw)
                    tw.set(W + "w", str(wsum))
                    tw.set(W + "type", "dxa")
                    ci += span

        print("缩放的表格数量:", scaled)
        data = etree.tostring(root, xml_declaration=True, encoding="UTF-8",
                              standalone=True)
        zout.writestr(info, data)
    zout.close()
    print("文件", os.path.getsize(SRC), "B")


if __name__ == "__main__":
    main()
