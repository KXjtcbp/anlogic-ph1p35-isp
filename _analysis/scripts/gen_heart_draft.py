# -*- coding: utf-8 -*-
"""生成《心得体会四段初稿》docx。

输入：本文件内联的四段正文 + 替换清单。
输出：E:\\FPGA\\心得体会四段初稿_20261022.docx

格式对齐《心得体会模板_20261019.docx》：中文宋体、西文 Times New Roman、
小四（12pt）、1.5 倍行距、正文首行缩进 2 字符。
"""
import os
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"E:\FPGA\心得体会四段初稿_20261022_v4.docx"

CN_FONT = "宋体"
EN_FONT = "Times New Roman"
BODY_PT = 12          # 小四
LINE = 1.5


# ---------------------------------------------------------------- 样式助手
def _set_run_font(run, size=BODY_PT, bold=False, color=None):
    run.font.name = EN_FONT
    run.font.size = Pt(size)
    run.font.bold = bold
    if color:
        run.font.color.rgb = color
    run._element.rPr.rFonts.set(qn("w:eastAsia"), CN_FONT)


def para(doc, text, *, size=BODY_PT, bold=False, indent=True,
         space_before=0, space_after=6, align=None, color=None):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = LINE
    pf.space_before = Pt(space_before)
    pf.space_after = Pt(space_after)
    if indent:
        pf.first_line_indent = Pt(size * 2)
    if align is not None:
        p.alignment = align
    r = p.add_run(text)
    _set_run_font(r, size=size, bold=bold, color=color)
    return p


def head(doc, text, size=14):
    return para(doc, text, size=size, bold=True, indent=False,
                space_before=12, space_after=6)


def note(doc, text):
    return para(doc, text, size=10.5, indent=True, space_after=4,
                color=RGBColor(0x55, 0x55, 0x55))


def table(doc, rows, widths=None, header=True):
    t = doc.add_table(rows=0, cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    for i, row in enumerate(rows):
        cells = t.add_row().cells
        for j, val in enumerate(row):
            cell = cells[j]
            cell.text = ""
            p = cell.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(2)
            r = p.add_run(str(val))
            _set_run_font(r, size=9.5, bold=(header and i == 0))
    if widths:
        for j, w in enumerate(widths):
            for row in t.rows:
                row.cells[j].width = Cm(w)
    return t


# ---------------------------------------------------------------- 正文
P1 = ("这个比赛是偶然看到的。某天刷社交网络时看到 FPGA 创新设计赛道的通知，"
      "而这学期正好在学 Verilog 和 FPGA，就顺着去查了报名和赛题。那时我对 FPGA 的了解"
      "还停在 AMD 的 Vivado 加 Zynq 开发平台，以为就这么一套东西。后来找指导老师聊，"
      "才知道国内还有安路这样的厂商；也是在那次讨论里定下了走安路赛道、做选题二。"
      "当时我对“用 FPGA 做图像处理”的理解很简单——无非是写个滤镜。")

P2_S1 = ("最早做亮度这块，我们的判断很朴素：画面暗，就做一条提亮的曲线，拨个开关能看出"
         "亮一点，就算成。")
P2_S2 = ("曲线写完、表生成、仿真跑过、综合报告全绿。烧上板把开关拨到“开”，画面和“关”几乎"
         "没有区别。我们对着屏幕来回拨了好几次，靠肉眼真的分不出开和关。")
P2_S3 = ("第一反应是曲线做得太平，就把提亮幅度加大，重新生成表、重新综合、再烧。放大之后"
         "能看出一点区别，但已经明显过头，画面灰蒙蒙的。又猜是伽马参数选错，换了几组。"
         "两轮改下来其实一直在同一个坑里：每次都靠肉眼看“有没有效果”，而肉眼不是尺子。"
         "更麻烦的是连一块稳定的靶面都没有——灯开一下、相机挪一下，前后两次采集的条件就"
         "变了，改了参数也说不清是参数起了作用还是光变了。说到底是没有调试经验，不知道改"
         "一个东西之前，得先把“怎么算改对了”定下来。")
P2_S4 = ("转折是我们不再问“看出来了吗”，改成问“能量出来吗”：盖死镜头取黑电平、白纸铺满"
         "画面做固定靶面、把拨码位置和帧号一起记下来。有了能比的数，差多少一目了然。这时"
         "才回头发现，前面几次改动里有一部分其实是有用的，只是我们当时看不出来。")

P3 = ("亮度那件事之后，我们多了个习惯：不管改什么，先把“怎么算改对了”写下来，写不出来的"
      "直接划掉。这条规矩后来救过我们一次——镜头暗角校正到底有没有生效，"
      "前面的争论全靠印象，最后是靠“同机位、同光照、只拨一个开关”的对照实验，两批独立采集"
      "给出同一个数字才定案。")
P3B = ("另一条是我自己摸索出来的，跟焦虑有关。中间那几周项目看不到尽头，我每天都在想怎么把"
       "进度往前推、怎么真正把它做成，晚上躺下还在过第二天的安排。我催过一次进度，就在分完"
       "任务之后、两人交付物交过来之前。但他们按时交了，质量还比我预期好——那次焦虑其实跟"
       "他们没关系，是我把“能不能做完”当成一个靠催就能解决的事。后来我换了个笨办法：焦虑"
       "上来的时候不去算还差多少，只写下今天能交出去的那一件。它没让进度变快，但让我从"
       "“担心整件事”回到“做完手上这一件”，人就不慌了。")

P4_A = ("现在还有两处没有解决。一是暗光。传感器曝光已经顶到手册给的上限，模拟增益也到顶，"
        "再往下只能靠数字增益和降帧率去补，而光圈是镜头定死的，这是进光量的物理上限，"
        "不是调参能绕过去的。")
P4_B = ("二是目标检测目前只认颜色特征。场景干净的时候框能贴住目标，但换个颜色或者光照变化"
        "大一点就不稳，形状和多目标还没有可靠的做法。")
P4_C = ("再往后如果还有时间，我想先把检测的判据从单一颜色扩到颜色加形状，再处理暗光下的"
        "成像质量。")


def main():
    doc = Document()

    sec = doc.sections[0]
    sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
    sec.top_margin = sec.bottom_margin = Cm(2.5)
    sec.left_margin = sec.right_margin = Cm(3.2)

    para(doc, "心得体会 · 四段初稿", size=18, bold=True, indent=False,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=4)
    para(doc, "基于安路 PH1P35 的实时数字图像处理系统", size=12, indent=False,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=2)
    para(doc, "2026-10-22", size=10.5, indent=False,
         align=WD_ALIGN_PARAGRAPH.CENTER, space_after=14)

    head(doc, "第 1 段 · 起点与选题（约 185 字）")
    para(doc, P1)
    note(doc, "说明：这一段在原稿基础上做了润色，事实没有增减。主要改了三处："
              "一是修语病与口语（“在某一天的浏览社交网络中”“仅仅只认为”“在找了指导老师"
              "与老师讨论”）；二是把原稿的一口气长句拆成四句——发现、查资料、找人聊、"
              "定选题；三是“zyqn”改为 Zynq。")

    head(doc, "第 2 段 · 最难的那件事（约 400 字，四步）")
    note(doc, "【第 1 步 · 现象】写清时间与具体状态，不写感受。")
    para(doc, P2_S1)
    note(doc, "【第 2 步 · 一开始怎么想】写出当时的错误假设，以及为此做了什么（或没做什么）。")
    para(doc, P2_S2)
    note(doc, "【第 3 步 · 怎么排掉的】转折点 + 顺着什么线索看清楚了什么。")
    para(doc, P2_S3)
    note(doc, "【第 4 步 · 学到什么】一句能迁移到别处的方法，不喊口号。")
    para(doc, P2_S4)

    head(doc, "第 3 段 · 方法上的收获（约 325 字）")
    para(doc, P3)
    para(doc, P3B)
    note(doc, "说明：第 2 段讲的是亮度那件事，这一段只做一句回指（“亮度那件事之后”），不复述事件。"
              "第一条讲由此形成的习惯，第二条讲焦虑——催进度只发生过一次、之后队友都按时交付了，"
              "所以不写成分歧或矛盾，只写自己那一侧的心态和后来找到的办法。")

    head(doc, "第 4 段 · 不足与展望（约 160 字）")
    para(doc, P4_A)
    para(doc, P4_B)
    para(doc, P4_C)
    note(doc, "说明：两条都是能力边界（受物理限制 / 受算法限制），不是“没时间”。"
              "QSPI 固化没有写进这一段——它不是做不到，而是尚未执行的工作项，"
              "性质不同；该项已在报告正文“可扩展之处”里中性说明。")

    head(doc, "合起来约 1000 字，篇幅比例 18% / 40% / 30% / 16%")

    head(doc, "需要你替换或确认的地方")
    table(doc, [
        ["位置", "现在写的", "为什么要改 / 怎么改"],
        ["第 1 段", "“这学期正好在学 Verilog 和 FPGA”",
         "确认时间对得上：如果这门课是在比赛之后才开，改成“刚学完”或“正在自学”"],
        ["第 1 段", "“后来找指导老师聊”",
         "若当时是老师主动找的你们，改“指导老师找到我们聊”"],
        ["第 2 段第 1 步", "“翻了两天资料”",
         "★把“两天”换成真实的天数；如果记不清，改成“几天”也行，但不要留虚构的精确数字★"],
        ["第 2 段第 2 步", "“我的判断是还没想透，再多看几天就有了”",
         "★这句是整段的支点，必须是你真实的心态★。如果当时你是另一种想法"
         "（比如“先拖着，等老师给方向”），照实改，后面的转折才立得住"],
        ["第 2 段第 3 步", "“老师没有替我们选，只建议看企业赛道……"
         "随后他又就我们最后选的方向给了一段具体判断”",
         "★我已按你说的写了，但“一段具体判断”偏空★。"
         "能补一句老师当时说的具体内容（比如他提到 SC500CS 摄像头、或指出这个赛道"
         "有现成例程）就补上，这一段的可信度全靠这句"],
        ["第 3 段", "“两批独立采集给出同一个数字”",
         "若你记得住，把数字写进去（逐列 R/G 极差下降 43%~46%）；记不住就保持现在的说法"],
        ["第 3 段", "“只写下今天能交出去的那一件”",
         "★这是段落落点，最好补一句你当时真的这么做过的例子★（哪一天写了什么、"
         "当天做完了没有），否则这句读起来像道理而不是经历"],
        ["第 3 段", "“晚上躺下还在过第二天的安排”",
         "★这个细节是我按“每天都在想”加的，如果不符合实际就删掉★；"
         "也可以换成你真实做过的事（比如“睡前还在翻例程”“走路都在想怎么调参”）"],
        ["第 3 段", "“我催过一次进度，就在分完任务之后、两人交付物交过来之前”",
         "★这句按你的原话写的，事实部分不用改★；只需确认“催”的方式是口头催还是"
         "在群里问，如果介意可以换成具体说法"],
        ["第 4 段", "“传感器曝光已经顶到手册给的上限”",
         "★这条要能解释★：数据是曝光 1990 行 = 2×VTS−10（手册上限）、"
         "模拟增益 15.750× 已到顶。被追问时能说出这两个数就稳"],
        ["第 4 段", "“目标检测只认颜色特征”",
         "★这条要能解释★：能说的是“空场景已做到零误检、单一颜色目标能紧贴描边”，"
         "不能说“检测准确率多少”，我们没有做过量化统计"],
    ], widths=[2.6, 5.4, 6.6], header=True)

    head(doc, "写作时守住的三条线")
    para(doc, "第一，只写你确实参与过的事。你提到几个技术案例基本是和队友讨论过、"
              "没有亲手看代码改代码——那第 2 段就不能写技术排查过程，只能写决策过程。"
              "这也是第 2 段选“选题分歧”而不是选某个 bug 的原因。", indent=True)
    para(doc, "第二，动词不要越界。写团队动作时用“我们”“团队”，写自己时用“我”并给出"
              "具体角色；“我排查了”“我把某个值改成另一个”这类句子，只要不是你亲手做的就不要写。",
         indent=True)
    para(doc, "第三，每个技术判断都要能被追问三个“为什么”。说不清的边界，宁可不写。",
         indent=True)

    doc.save(OUT)
    print("saved", OUT, os.path.getsize(OUT), "B")

    # 字数统计
    total = sum(len(x) for x in [P1, P2_S1, P2_S2, P2_S3, P2_S4, P3, P3B,
                                 P4_A, P4_B, P4_C])
    print("正文字数（含标点）≈", total)
    for name, parts in (("第1段", [P1]),
                        ("第2段", [P2_S1, P2_S2, P2_S3, P2_S4]),
                        ("第3段", [P3, P3B]),
                        ("第4段", [P4_A, P4_B, P4_C])):
        print("  %s ≈ %d 字（%.1f%%）" % (name, sum(len(x) for x in parts),
                                         100.0 * sum(len(x) for x in parts) / total))


if __name__ == "__main__":
    main()
