# -*- coding: utf-8 -*-
"""生成《演示视频旁白稿》docx。

对应 150 s / 9 段的分镜检查表；内容以检查表「必看现象」为准（与脚本冲突处按检查表改口）。
"""
import os
import sys
from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"E:\FPGA\演示视频旁白稿_20261023.docx"

CN = "宋体"
EN = "Times New Roman"


# ---------- 基础排版helper ----------
def set_run(run, size=12, bold=False, color=None, italic=False):
    run.font.name = EN
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = rpr.makeelement(qn("w:rFonts"), {})
        rpr.append(fonts)
    fonts.set(qn("w:ascii"), EN)
    fonts.set(qn("w:hAnsi"), EN)
    fonts.set(qn("w:eastAsia"), CN)
    if color:
        run.font.color.rgb = RGBColor(*color)


def para(doc, text="", size=12, bold=False, align=None, indent=False,
         space_before=0, space_after=0, line=1.5, color=None, italic=False):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = line
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if indent:
        pf.first_line_indent = Pt(24)
    if align == "center":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if text:
        set_run(p.add_run(text), size=size, bold=bold, color=color, italic=italic)
    return p


def h1(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(18)
    pf.space_after = Pt(6)
    pf.line_spacing = 1.3
    set_run(p.add_run(text), size=15, bold=True, color=(0x1F, 0x3B, 0x66))
    return p


def h2(doc, text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.space_before = Pt(14)
    pf.space_after = Pt(4)
    pf.line_spacing = 1.3
    set_run(p.add_run(text), size=13, bold=True)
    return p


def note(doc, text):
    """灰色小字说明。"""
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.3
    pf.space_before = Pt(2)
    pf.space_after = Pt(6)
    pf.left_indent = Pt(24)
    set_run(p.add_run(text), size=10.5, color=(0x66, 0x66, 0x66))
    return p


def make_table(doc, headers, rows, widths_cm, font=10.5):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    tbl_pr = t._tbl.tblPr
    layout = tbl_pr.makeelement(qn("w:tblLayout"), {})
    layout.set(qn("w:type"), "fixed")
    tbl_pr.append(layout)
    for i, w in enumerate(widths_cm):
        for c in t.columns[i].cells:
            c.width = Cm(w)
    hdr = t.rows[0].cells
    for i, htxt in enumerate(headers):
        hdr[i].width = Cm(widths_cm[i])
        hp = hdr[i].paragraphs[0]
        hp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        hp.paragraph_format.line_spacing = 1.15
        set_run(hp.add_run(htxt), size=font, bold=True)
    for r in rows:
        cells = t.add_row().cells
        for i, val in enumerate(r):
            cells[i].width = Cm(widths_cm[i])
            p = cells[i].paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            bold = val.startswith("★")
            set_run(p.add_run(val), size=font, bold=bold)
    return t


# ---------- 正文内容 ----------
SEGS = [
    ("第 1 段 · 开机即用（12 秒）",
     "只接了电源和 HDMI，没接电脑。上电十秒左右，画面自己就出来。摄像头从 MIPI 进来，"
     "处理完直接送 HDMI，中间没有帧缓存。",
     "≈52 字 / 12 秒。说完「没有帧缓存」刚好切下一段。镜头此时从书架缓缓扫到桌面，语速跟着镜头走。"),

    ("第 2 段 · 数据通路总览（16 秒）",
     "画面上的信息分四块。左上角是安路 Logo。中间一行是帧计数，一直在一秒六十地涨。"
     "下面是当前的算法模式。两行橙字是实时遥测。最下面青色一行，是四个拨码的生效状态。",
     "≈77 字 / 16 秒。「左上角」「中间」「下面」「最下面」各配一次手指点过去，手指到哪说到哪。"),

    ("第 3 段 · ISP 在线可关（22 秒）",
     "先看对比度。SW2 拨下去——画面马上变平，暗部发灰。拨回来，暗部又沉下去，亮部更透。"
     "这一下不用重新烧录，拨完一秒内就生效。再看暗角校正。SW1 拨下去，画面边角开始偏色。"
     "拨回来，边角就干净了。",
     "≈73 字 / 22 秒。节奏是「拨 → 停 3 秒 → 说话」：拨下去先别说话，让观众看清变化，停满 3 秒再开口；"
     "拨回同理。这两下是整套系统能不能被信任的关键，宁可这一段说慢一点。"),

    ("第 4 段 · AE 与 AWB（16 秒）",
     "拿手电照一下画面中间。自动曝光会把增益压下来，画面不过曝。移开，亮度又自己提回去。"
     "橙色那行最左边的 M，是曲线前的画面均值，它跟着光照走。",
     "≈63 字 / 16 秒。照光 3~5 秒期间不说话，等亮度回落了再说后半句。"
     "★ 只提 M，不提 gi —— 增益早已顶到上限，不会再动。"),

    ("第 5 段 · 拨码总开关（12 秒）",
     "青色这一行，第四、第五个字段。SW3 拨下去，MOT 变 0，画面上的绿框全没了。拨回来。"
     "SW4 拨下去，SENS 从 H 变 L，这是灵敏度两档。",
     "≈50 字 / 12 秒。这一段话说得比动作快是正常的——一边拨一边说，最后留 2 秒静默让观众看参数行。"),

    ("第 6 段 · 风格化五模式（30 秒）",
     "现在按 K1，是原始画面，什么都不做。K2，灰度，按 BT.601 加权算的亮度。"
     "K3，伪彩，把亮度映射成蓝到绿到黄。长按任意一个键一秒，出来五段彩条，这是测试图。"
     "再按 K4，卡通化——先把亮度分四档平涂，再在相邻像素差异大的地方描黑边。"
     "右下角的 MODE 数字跟着从 0 变到 4。",
     "≈123 字 / 30 秒。每档停 5~6 秒，旁白在档位切换的瞬间报名字，然后静默 3~4 秒让画面自己说话。"
     "最后一句「MODE 数字从 0 变到 4」在 K4 出来后补。"),

    ("第 7 段 · 运动检测（16 秒）",
     "静止的时候画面里没有框。手从五十厘米外横着划过去，出红色方块，跟着手走。"
     "手一离开，框就消失。它是块级帧差，全画面只存一百四十四个字节的块均值，所以不用帧缓存。",
     "≈69 字 / 16 秒。先静 3 秒（让观众确认「真的没框」），再划过，停下 3 秒。"
     "★ 千万不要把手贴到镜头上。"),

    ("第 8 段 · 目标检测（16 秒）",
     "红笔进画面，马上出一个绿框，紧贴笔身。笔动，框跟着动。笔移出去，框保持一秒再消失。"
     "它是按颜色分块判的，两帧确认加孤立块滤除，所以空场景不会误出框。",
     "≈66 字 / 16 秒。举笔停 3 秒 → 缓慢左右移 3 秒 → 移出，数满 1 秒再说「保持一秒再消失」。"),

    ("第 9 段 · 参数收尾（10 秒）",
     "最后回到卡通化。整套系统 1280×720，60 帧，LUT6 用了 77.3%，ERAM 用了 47.2%，"
     "时序余量正 104 皮秒。从头到尾没有接电脑。",
     "≈47 字 / 10 秒。数字念得慢一点，最好屏幕上有字幕同步。「从头到尾没有接电脑」是收尾锤，说完定格。"),
]


def main():
    doc = Document()

    # 页面：A4，常规页边距
    sec = doc.sections[0]
    sec.page_width = Cm(21.0)
    sec.page_height = Cm(29.7)
    sec.left_margin = Cm(2.6)
    sec.right_margin = Cm(2.6)
    sec.top_margin = Cm(2.4)
    sec.bottom_margin = Cm(2.4)

    # 正文默认样式
    normal = doc.styles["Normal"]
    normal.font.name = EN
    normal.font.size = Pt(12)
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), CN)

    # 标题区
    para(doc, "演示视频旁白稿", size=22, bold=True, align="center", line=1.2)
    para(doc, "基于安路 PH1P35 的实时数字图像处理系统", size=12, align="center",
         space_before=6, line=1.2)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.line_spacing = 1.2
    set_run(p.add_run("对应 9 段 / 150 秒 · 以《分镜检查表_20261023.docx》「必看现象」为准 · 2026-10-23"),
            size=10.5, color=(0x66, 0x66, 0x66))

    # 一
    h1(doc, "一、时长与语速基准")
    para(doc, "9 段总长 150 秒，但可说话的时间比段长少，因为第 3、5 段要留出拨码后的停顿。"
              "按 4.2 字/秒来配字（比日常说话略慢，方便现场看画面）。", indent=True)
    rows = [
        ["1", "开机即用", "12 s", "0", "≈52", "0:12"],
        ["2", "数据通路总览", "16 s", "0（只指）", "≈77", "0:28"],
        ["3", "ISP 在线可关", "22 s", "12 s（四次拨动）", "≈73", "0:50"],
        ["4", "AE 与 AWB", "16 s", "4 s（手电照射）", "≈63", "1:06"],
        ["5", "拨码总开关", "12 s", "12 s（四次拨动）", "≈50", "1:18"],
        ["6", "风格化五模式", "30 s", "25 s（五次按键）", "≈123", "1:48"],
        ["7", "运动检测", "16 s", "1 s（手划过）", "≈69", "2:04"],
        ["8", "目标检测", "16 s", "6 s（举笔移动）", "≈66", "2:20"],
        ["9", "参数收尾", "10 s", "0", "≈47", "2:30"],
        ["★合计", "", "★150 s", "", "★≈620 字", ""],
    ]
    make_table(doc, ["段", "名称", "时长", "其中动作占时", "旁白字数", "累计"],
               rows, [1.3, 4.2, 2.0, 3.6, 2.6, 2.1])
    note(doc, "约 4.1 字/秒，留出换气与看画面的间隙。录的时候宁可说少、不要抢——空 1~2 秒比念不完好。")

    # 二
    h1(doc, "二、必须强调的四件事")
    for t in [
        ("没接电脑。", "第 1 段和第 9 段各说一次。这是赛题 slide26 的硬性要求（上电即运行、无需 PC 下载），"
                     "也是已经做到的事，值得说两遍。"),
        ("不用帧缓存。", "第 1 段说整条链路，第 7 段说「144 个块只存 144 字节」。这是低延迟的根据，"
                       "评委最认这一条。"),
        ("拨完一秒内生效、不用重新烧录。", "第 3 段加这一句。它说明这些处理是在线可配置的，不是编译期写死的。"),
        ("客观数字一次性报完。", "第 9 段报：1280×720@60、LUT6 77.3%、ERAM 47.2%、时序余量 +104 ps。"
                              "数字要报，但只报这一处，中间不要零散报数。"),
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.first_line_indent = Pt(24)
        set_run(p.add_run(t[0]), size=12, bold=True)
        set_run(p.add_run(t[1]), size=12)

    # 三
    h1(doc, "三、必须回避的五件事")
    rows = [
        ["任何关于 AI、生成工具、辅助编码的字眼", "不是答辩议题，主动提等于给自己挖坑"],
        ["「检测准确率 / 识别率 XX%」",
         "★ 没有测过。只有「空场景零误检、红笔出现即出框」这两条是验过的"],
        ["「零延迟 / 无延迟」", "不成立。要说「固定流水线级数，延迟不随帧率变化」"],
        ["「卡通化效果很好」", "脚本自己写着「观感偏硬」。说「四色平涂加黑描边」描述做法即可，不评价好坏"],
        ["第 4 段说「gi 会跟着变」", "★ 这是脚本里的说法，与检查表冲突。gi 已顶到上限时不动是正常的，见第五节"],
    ]
    make_table(doc, ["不要说的", "为什么"], rows, [6.2, 9.6])
    note(doc, "另外，第 7 段千万不要把手贴到镜头上。手挡住镜头会让整幅变暗，块级帧差对这种全局变化不敏感，"
              "反而不出框——现场看起来像坏了。必须在 50 cm 外横着划。")

    # 四
    h1(doc, "四、9 段旁白正文")
    for name, body, hint in SEGS:
        h2(doc, name)
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing = 1.5
        pf.left_indent = Pt(24)
        pf.right_indent = Pt(12)
        pf.space_after = Pt(4)
        set_run(p.add_run("「"), size=12)
        set_run(p.add_run(body), size=12)
        set_run(p.add_run("」"), size=12)
        note(doc, hint)

    # 五
    h1(doc, "五、两处必须按检查表改口的地方")
    para(doc, "这两处是核对两份文档时发现的脚本与检查表冲突。检查表自己写着「两处若有不一致，"
              "以本表的『必看现象』为准」，所以旁白按检查表写，要知道为什么：", indent=True)

    h2(doc, "改动 1 · 第 4 段不能说「gi 会跟着变」")
    for t in [
        "脚本表 1 原话：「橙字里的 M 和 W 会跟着变」。",
        "检查表原话：「gi 一直不动其实正常（已顶到上限时不动）；只要画面亮度有反应就算过」。",
        "实际情况：光照偏暗时 AE 早已把增益顶到 127 上限，再照手电也不会往上动。",
        "处理：旁白只提 M（曲线前画面均值，它会随光照变），不提 gi。说错了评委一盯遥测就露。",
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.first_line_indent = Pt(24)
        set_run(p.add_run("· " + t), size=12)

    h2(doc, "改动 2 · 第 3 段不要说「四角泛绿」")
    for t in [
        "脚本原话：「画面四角泛绿」。",
        "检查表原话：「边角偏色变化」（更含糊）。",
        "处理：按检查表说「边角开始偏色」，不指定颜色——偏色方向会随场景和光照变。"
        "说「偏色」永远不会错，说「泛绿」可能对不上现场。",
    ]:
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = 1.5
        p.paragraph_format.first_line_indent = Pt(24)
        set_run(p.add_run("· " + t), size=12)

    # 尾
    para(doc, "", space_before=10)
    p = doc.add_paragraph()
    p.paragraph_format.line_spacing = 1.5
    p.paragraph_format.first_line_indent = Pt(24)
    set_run(p.add_run("录制提示：一遍录完不要停，念错了整段重录（不要剪接单句，剪接后语速会突跳）。"
                      "提词卡按本稿逐句排，一人念一人操作拨码。"), size=11, italic=True,
            color=(0x55, 0x55, 0x55))

    doc.save(OUT)
    print("saved", OUT, os.path.getsize(OUT), "B")
    print("paragraphs =", len(Document(OUT).paragraphs), " tables =", len(Document(OUT).tables))


if __name__ == "__main__":
    main()
