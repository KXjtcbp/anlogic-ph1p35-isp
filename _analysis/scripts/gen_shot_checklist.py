# -*- coding: utf-8 -*-
"""生成《实验室拍摄与录制分镜检查表》docx（可打印、现场勾选）。

与《演示视频脚本_20261020.docx》的分工：
  脚本 = 讲什么、按什么顺序讲
  本表 = 现场怎么执行、每段合格的判据是什么、不合格怎么补录
"""
import os
import sys

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = r"E:\FPGA\分镜检查表_20261023.docx"
CN, EN = "宋体", "Times New Roman"


def set_run(r, size=12, bold=False, color=None):
    r.font.name = EN
    r.font.size = Pt(size)
    r.font.bold = bold
    if color:
        r.font.color.rgb = color
    if r._element.rPr is not None and r._element.rPr.rFonts is not None:
        r._element.rPr.rFonts.set(qn("w:eastAsia"), CN)


def para(doc, text, size=12, bold=False, indent=True, space_after=4, color=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_run(r, size, bold, color)
    pf = p.paragraph_format
    pf.line_spacing = 1.35
    pf.space_after = Pt(space_after)
    if indent:
        pf.first_line_indent = Pt(size * 2)
    return p


def heading(doc, text, size=14):
    p = doc.add_paragraph()
    r = p.add_run(text)
    set_run(r, size, True)
    p.paragraph_format.space_before = Pt(12)
    p.paragraph_format.space_after = Pt(6)
    return p


def table(doc, header, rows, widths, sizes=9):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    # 固定列宽：必须同时关 autofit、把 tblLayout 设成 fixed、并改 tblGrid
    t.autofit = False
    tblPr = t._tbl.tblPr
    layout = tblPr.find(qn("w:tblLayout"))
    if layout is None:
        from docx.oxml import OxmlElement
        layout = OxmlElement("w:tblLayout")
        tblPr.append(layout)
    layout.set(qn("w:type"), "fixed")
    grid = t._tbl.find(qn("w:tblGrid"))
    if grid is not None:
        for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
            gc.set(qn("w:w"), str(int(w * 567)))   # 1 cm ≈ 567 twip
    hdr = t.rows[0].cells
    for i, h in enumerate(header):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        set_run(p.add_run(h), sizes, True)
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(1)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = ""
            first = True
            for line in str(v).split("\n"):
                p = cells[i].paragraphs[0] if first else cells[i].add_paragraph()
                first = False
                bold = line.startswith("★")
                set_run(p.add_run(line.replace("★", "")), sizes, bold,
                        RGBColor(0xB0, 0x00, 0x00) if bold else None)
                p.paragraph_format.space_after = Pt(1)
                p.paragraph_format.line_spacing = 1.15
    for r in t.rows:
        for i, w in enumerate(widths):
            r.cells[i].width = Cm(w)
    return t


# ------------------------------------------------------------------ 文档
doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.left_margin = sec.right_margin = Cm(1.9)
sec.top_margin = sec.bottom_margin = Cm(2.0)

title = doc.add_paragraph()
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_run(title.add_run("实验室拍摄与录制分镜检查表"), 18, True)
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_run(sub.add_run("基于安路 PH1P35 的实时数字图像处理系统　｜　2026-10-23"), 11)
sub.paragraph_format.space_after = Pt(2)

para(doc,
     "用法：打印这一份带去实验室。每完成一项就在最左边打勾，不合规当场重来，不要指望回宿舍再补。"
     "配套文件《演示视频脚本_20261020.docx》讲的是「讲什么」，本表讲的是「怎么执行、什么算合格」。",
     10, indent=False, space_after=8)

# ---------------------------------------------------------------- 0 基本信息
heading(doc, "零、这一次拍摄的基本信息（出门前填好）")
table(doc,
      ["项", "内容", ""],
      [["日期", "2026 年 10 月 ____ 日（预定 10-31 或 11-01，实验室无人）", "☐"],
       ["到场时间 / 预计离场", "____:____ 　→　____:____", "☐"],
       ["烧录版本", "proj\\releases\\2026-10-18_a2_hold60\\camera_to_dsi_display.bit", "☐"],
       ["该版 md5（必须核对）", "DB39A5CEB2D0D9A11C797EA6712708CA", "☐"],
       ["固化状态", "已用 BitWriter Program Flash 烧入，上电即启动，不接电脑", "☐"]],
      [4.0, 11.2, 1.2], 9)

# ---------------------------------------------------------------- 1 器材
heading(doc, "一、出发前器材清单")
table(doc,
      ["☐", "物品", "为什么不能忘 / 备注"],
      [["☐", "开发板 + 摄像头（已装 MIPI 排线）", "排线是 FPC，弯折会断，装包里要垫硬纸板"],
       ["☐", "12V 电源适配器", "★没有它一切归零；现场不一定借得到同规格★"],
       ["☐", "显示器（支持 HDMI，≥1024×600）", "赛题要求；我们跑 1280×720，最好带 1080p 的屏"],
       ["☐", "HDMI 线 ×2（一根备用）", "★现场坏得最多的就是线；赛题要求 ≤5 m 纯铜★"],
       ["☐", "手电筒 或 手机手电", "第 4 段 AE 演示要用：照一下画面变亮"],
       ["☐", "红笔 ×1（尽量粗）", "第 8 段目标检测的靶子；细笔命中块太少，框会贴不上"],
       ["☐", "白纸 或 白板（A4 以上）", "第 3 段调曲线时的中性参照；不用纯白墙（太远看不出）"],
       ["☐", "小十字螺丝刀", "万一要重新插 MIPI 线"],
       ["☐", "笔记本 + USB 线", "只在出故障时用：重烧、看日志。正常录制全程不开"],
       ["☐", "本表（打印件）+ 笔", "现场勾选，别靠记忆"]],
      [1.0, 5.0, 10.4], 9)

# ---------------------------------------------------------------- 2 布置
heading(doc, "二、到场后的布置顺序（照这个顺序做，别跳步）")
for i, s in enumerate([
    "**铺开设备**：显示器、开发板、摄像头。开发板放在显示器侧前方 20~30 cm，让摄像头能拍到显示器之外的实景（书架/桌面/墙面明暗交界）。",
    "**接 HDMI**：开发板 → 显示器。线不要盘成活结，接头处垫平，斜拉最容易接触不良。",
    "**先别上电**。打开本表第 3 节，准备按顺序做通电自检。",
    "**上电**（只接电源，USB 不接）→ 等 10 秒 → 画面应当自动出现。",
    "**做第 3 节通电自检**，五项全过再开始拍。任何一项不过，先解决，不要边拍边修。",
    "**固定机位与拨码**：机位定下来之后，本次录制全程不再移动；四个拨码先全部拨上，记下起始状态。",
], 1):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.6)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.3
    seg = s.split("**")
    set_run(p.add_run("%d. " % i), 10.5, True)
    for j, piece in enumerate(seg):
        if piece:
            set_run(p.add_run(piece), 10.5, bold=(j % 2 == 1))

# ---------------------------------------------------------------- 3 通电自检
heading(doc, "三、通电自检（五项全过才开拍）")
table(doc,
      ["☐", "检查项", "怎么做", "合格判据", "不通过的处置"],
      [["☐", "能自动启动", "只接电源，USB 不插，等待 10 秒", "画面自动出现，不需要连电脑",
        "拔电 5 秒重上电；仍不出→用笔记本 USB + BitWriter 重烧"],
       ["☐", "帧计数在涨", "看黄色 `CNT:` 后六位数", "数字持续递增，约每秒 +60",
        "不涨说明视频通路卡住，断电重启再看"],
       ["☐", "橙色遥测正常", "看黄字下方那一行橙色小字", "第一行以 `AE` 开头，第二行以 `F` 开头，数字不乱跳",
        "数字乱跳=读错；先截图放大，不要凭肉眼判"],
       ["☐", "青色参数行正常", "看橙色字下方那一行青色字", "显示 `S-CURVE ON　LSC ON　MOT:1　SENS H`",
        "★若显示 `MOT:0`→SW3 被拨下了；若 `SENS L`→SW4 被拨下了★"],
       ["☐", "四个拨码手感", "每个都拨上拨下一次再回来", "能听到/感到咔哒，画面随之变化",
        "接触不良→换备用拨码或换板；没备件就先录不涉及该拨码的段"]],
      [0.9, 3.0, 4.6, 4.6, 4.3], 8.5)

para(doc,
     "★第 4 项是现场最容易误判的一项：MOT 显示 1 还是 0、SENS 是 H 还是 L，直接决定第 7、8 段录出来有没有框。"
     "每换一次拨码都要低头看一眼这一行，不要靠“我记得我拨上去了”。★", 9.5, indent=False)

# ---------------------------------------------------------------- 4 照片
heading(doc, "四、实物照片拍摄清单（2 张，报告 §3.1 / §3.2.2 要用）")
table(doc,
      ["☐", "照片", "构图要点", "合格判据"],
      [["☐", "P1 系统正面全景", "整机入画：开发板 + 摄像头朝向 + 显示器 + 全部连线；画面内容开一个有明暗层次的实景（书架/桌面），不要对着白墙；拨码位置要能看清",
        "★画面里能看到显示器正在出图，且没有笔记本连着（证明上电即用）★"],
       ["☐", "P2 斜 45° 近景", "从显示器侧上方 45° 拍开发板，重点是 MIPI 排线、HDMI 线、电源接口三处连接",
        "★三处连接都清晰可辨，没有虚焦★"],
       ["☐", "（可选）P3 拨码特写", "四个拨码 + 板丝印一起入画", "能看清四个拨码都在上方"]],
      [0.9, 3.6, 7.4, 5.3], 8.5)

para(doc,
     "拍完立刻在相机里回放放大看一遍。现场光线和构图都能重来，回宿舍就只能认了。手机拍也可以，注意别开超广角（边缘会畸变）。",
     9.5, indent=False)

# ---------------------------------------------------------------- 5 逐段录制
heading(doc, "五、逐段录制检查表（共 9 段，合计 150 秒）")
para(doc,
     "建议分段录：每段录 20~30 秒，留够余量，最后统一剪到表里的时长。"
     "「必看现象」这一栏就是该段的合格判据——录完当场回放，对不上就重录这一段，不要往下拍。",
     9.5, indent=False, space_after=6)
table(doc,
      ["☐", "段", "设计时长", "手上做什么", "★必看现象（合格判据）★", "对不上怎么办"],
      [["☐", "1 开机即用", "12 s", "不操作，镜头缓慢横扫书架",
        "上电后画面直接出现，全程没有电脑参与；`CNT` 在涨",
        "画面没出→回第 3 节；出了但有电脑连着→拔掉 USB 重上电再录"],
       ["☐", "2 数据通路总览", "16 s", "不操作，画面停住，手指依次点 OSD 各元素",
        "安路 Logo / `CNT` / `MODE` / 两行橙色遥测 / 青色参数行，五处都能在画面里找到",
        "某处找不到→检查是否被画面亮部盖住，换个背景再录"],
       ["☐", "3 ISP 在线可关", "22 s", "★先 SW2 拨下停 3 秒，拨上停 3 秒；再 SW1 拨下停 3 秒，拨上停 3 秒★",
        "SW2 拨下：画面对比度明显变平（暗部发灰）；拨上恢复。SW1 拨下：边角偏色变化",
        "★看不出变化=最严重的情况，停止录制，先排查 SW1/SW2 是否真的接在 LSC/曲线上★"],
       ["☐", "4 AE 与 AWB", "16 s", "用手电或手机手电从侧面照向镜头 3~5 秒后移开",
        "照亮时画面不过曝、移开后亮度回落；橙色第一行的 `M` 数字（曲线前均值）随光照变化，`gi` 也在动",
        "`gi` 一直不动→其实正常（已顶到上限时不动）；只要画面亮度有反应就算过"],
       ["☐", "5 拨码总开关", "12 s", "★SW3 拨下停 3 秒、拨上停 3 秒；SW4 拨下停 3 秒、拨上停 3 秒★",
        "SW3 拨下：青色参数行变成 `MOT:0`，画面上的绿框全部消失；SW4 拨下变 `SENS L`",
        "★这一行字是硬判据，肉眼就能核对；不对就当场重来，别靠后期解释★"],
       ["☐", "6 风格化五模式", "30 s", "K1 → K2 → K3 → 长按任意键 ≥1 秒 → K4，每档停 5~6 秒",
        "五档依次为：原图 / 灰度 / 伪彩热力图 / 五段彩条 / 卡通化；`MODE` 后数字跟着变 0→1→2→3→4",
        "某一档没切过去→按键接触问题，按重一点再试；长按不足 1 秒会当成短按"],
       ["☐", "7 运动检测", "16 s", "静止 3 秒 → 手在镜头前 50 cm 外横向划过一次 → 静止 3 秒",
        "静止时无绿框；手划过时出现红色方块描边并跟着移动；手离开后约 1 秒框消失",
        "★整幅变暗（手挡住镜头）不出框是算法正常特性，不是故障★；要拍的是「远处划过」那种"],
       ["☐", "8 目标检测", "16 s", "把红笔举到画面中偏左，停 3 秒；缓慢左右移动 3 秒；移出画面",
        "红笔一进画面就出现绿色矩形紧贴笔身；移动时框跟着走；移开后约 1 秒消失；空场景无框",
        "框不贴笔→拉近或换粗红笔；框贴但位置偏→如实录，字幕说明是块级精度（80×80 像素）"],
       ["☐", "9 参数收尾", "10 s", "不操作，画面停在能同时看到 OSD 与实景的角度",
        "画面稳定、无花屏、无撕裂；`CNT` 持续增长",
        "有花屏→线接触问题，换 HDMI 线重录这一段"]],
      [0.8, 2.6, 1.5, 4.4, 5.3, 4.6], 8)

# ---------------------------------------------------------------- 6 收工验收
heading(doc, "六、收工前的验收（离场前必做，此时还能补录）")
table(doc,
      ["☐", "检查项", "判据"],
      [["☐", "9 段素材齐全", "手机/相机里能逐个点开，编号对得上 1~9"],
       ["☐", "总时长够了", "每段都比设计时长大；合计 ≥150 秒（剪辑时要能缩到 180 秒以内）"],
       ["☐", "画面无花屏、无撕裂", "逐段快速回放一遍，重点看每段开头两秒（最容易花）"],
       ["☐", "拨码段真的看出变化", "第 3、5 段回放时，遮住自己的手只看画面，能独立看出「变了」"],
       ["☐", "照片 3 张已存", "P1 / P2（/ P3）能在相机相册里看到，且放大后不虚"],
       ["☐", "拨码状态已记录", "离场前拍一张拨码特写（或写下四个位置），记进采集记录"]],
      [0.9, 5.2, 11.1], 9)

# ---------------------------------------------------------------- 7 应急
heading(doc, "七、现场应急处理（按现象查表，不要临场发挥）")
table(doc,
      ["现象", "最可能的原因", "处置顺序"],
      [["上电后显示器黑屏、无信号", "HDMI 线接触不良 / 显示器输入源选错 / 板子没从 Flash 启动",
        "① 换 HDMI 线 ② 显示器手动选输入源 ③ 拔电 5 秒重上电 ④ 仍不行→接 USB 用 BitWriter 看到 `PROGRAM_FLASH success` 再拔电重上电"],
       ["有画面但 `CNT` 不涨", "摄像头没出图（MIPI 排线松）", "① 断电重插 MIPI 排线 ② 冷启动 ③ 仍不行→换摄像头或放弃该机位"],
       ["画面能出但偏色/发灰", "SW1 或 SW2 位置不对，不是故障", "核对青色参数行的 `LSC` 与 `S-CURVE` 两项都是 `ON`"],
       ["绿框一直在、空场景也有", "SW4 在宽松档，把木纹/暖色当成了目标", "SW4 拨上（`SENS H`）再试；仍误检就只录有红笔的镜头"],
       ["红笔进画面不出绿框", "场景太暗 / 笔太细 / SW3 被拨下", "① 看参数行 `MOT:1` ② 开灯或换粗笔 ③ 笔靠近镜头"],
       ["画面几分钟后突然变暗", "传感器寄存器掉回默认（历史现象）", "★这正是要现场发现的问题★——拔电重上电，并在本表背面记下「第几分钟变暗」"],
       ["板子完全无反应、电源灯不亮", "电源适配器或线的问题", "换电源/换插座；实验室没有同规格就以「设备故障」结束本次，改期"]],
      [3.6, 4.6, 9.0], 8.5)

# ---------------------------------------------------------------- 8 参数
heading(doc, "八、录制参数与文件命名（统一，便于后期剪）")
table(doc,
      ["项", "取值", "说明"],
      [["分辨率 / 帧率", "1920×1080 / 60 fps", "与显示器同分辨率录制，避免缩放引入伪影"],
       ["编码", "H.264 或 H.265，码率 ≥20 Mbps", "字幕和 OSD 小字要看得清，码率不能省"],
       ["文件名", "V1_开机即用.mp4 … V9_参数收尾.mp4", "与本节段号对齐；照片用 P1_正面全景.jpg / P2_斜45度.jpg"],
       ["机位", "固定三脚架或桌面上做标记", "本次录制全程不移动；移动了必须在采集记录里写明"],
       ["环境光", "开顶灯 + 必要时侧向补光", "★不要只靠显示器当唯一光源，否则画面噪点偏大★"]],
      [3.2, 5.2, 8.8], 9)

doc.add_paragraph()
para(doc,
     "本表与《演示视频脚本_20261020.docx》配套使用。脚本给的是讲什么、按什么顺序讲；本表给的是现场怎么执行、每段什么算合格。"
     "两处若有不一致，以本表的「必看现象」为准——因为那是照着已验证的板上行为写的。",
     9, indent=False)

doc.save(OUT)
print("已生成", OUT, os.path.getsize(OUT), "B")
print("段落", len(Document(OUT).paragraphs), "表格", len(Document(OUT).tables))
