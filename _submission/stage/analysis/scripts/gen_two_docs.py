# -*- coding: utf-8 -*-
"""生成两份 Word 交付物：演示视频脚本 / 心得体会模板。"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH

WS = r"E:\FPGA"


def new_doc():
    d = Document()
    s = d.sections[0]
    s.page_width, s.page_height = Cm(21.0), Cm(29.7)
    s.top_margin = s.bottom_margin = Cm(2.5)
    s.left_margin = s.right_margin = Cm(3.2)
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(12)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    return d


def para(d, text, size=12, bold=False, align=None, first_indent=True, after=0):
    p = d.add_paragraph()
    pf = p.paragraph_format
    pf.line_spacing = 1.5
    pf.space_after = Pt(after)
    if first_indent:
        pf.first_line_indent = Pt(size * 2)
    if align == "c":
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.bold = bold
    r.font.name = "Times New Roman"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    return p


def heading(d, text, size=14):
    return para(d, text, size=size, bold=True, first_indent=False, after=6)


def table(d, rows):
    t = d.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, cell in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(str(cell))
            r.font.size = Pt(9)
            r.bold = (i == 0)
            r.font.name = "Times New Roman"
            r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    return t


# ============ 文档 1：演示视频脚本 ============
d = new_doc()
para(d, "演示视频分镜脚本", size=18, bold=True, align="c", first_indent=False, after=6)
para(d, "基于安路 PH1P35 的实时数字图像处理系统", size=14, bold=True,
     align="c", first_indent=False, after=6)
para(d, "总时长约 2 分 40 秒 ｜ 2026-10-19", size=10, align="c", first_indent=False, after=12)

heading(d, "一、拍摄前提")
for s in [
    "烧录版本：proj/releases/ 下当前交付版（.bit md5 DB39A5CE50591330A6D6E9C0CFCFB2E3）。",
    "冷启动：烧完拔电 5 秒再上电，不接 PC、不按复位键。",
    "拨码初始：SW1、SW2、SW3 全部拨上（LSC 开 / S 曲线开 / 运动检测开）；SW4 拨上（严格档）。",
    "相机机位：对准有纹理的室内实景（书架、桌面），不要对纯白墙。",
    "显示器：1280x720@60Hz，HDMI 1.4 及以上纯铜线，长度不超过 5 米。",
]:
    para(d, "· " + s, first_indent=False, after=0)

heading(d, "二、分镜表")
rows = [
    ["段", "时长", "画面内容", "对应操作", "旁白 / 字幕要点"],
    ["1 开机即用", "15 s", "只接电源与 HDMI，画面直接出图；镜头缓缓扫过桌面", "不操作",
     "上电即启动，无需 PC；MIPI 摄像头 -> FPGA -> HDMI，零帧缓存直通"],
    ["2 数据通路总览", "20 s", "画面停在有明暗层次的桌面，字幕逐行点亮 6 层 OSD", "不操作",
     "依次说明：安路 Logo / CNT 帧计数 / MODE / 两行橙色遥测 / 青色参数行"],
    ["3 ISP 在线可关", "25 s", "A/B 对比：SW2 拨下（曲线关）再拨上；SW1 拨下（LSC 关）再拨上", "拨 SW2、SW1",
     "S 曲线开，中调对比度 0.695 -> 1.125；LSC 关时四角发绿，开后干净。字幕：逐列 R/G 极差 0.164 -> 0.092（-44%）"],
    ["4 AE 与 AWB", "20 s", "手电照画面 -> 不过曝；移开 -> 恢复；遥测 M/W/B 实时变化", "只照光",
     "AE 闭环自动调模拟增益与曝光，白平衡按帧锁存，整帧 R/G 稳定 0.98~1.02"],
    ["5 拨码总开关", "15 s", "SW3 下变 MOT:0；上变 MOT:1；SW4 下变 SENS L；上变 SENS H", "拨 SW3、SW4",
     "SW3 运动检测总开关，SW4 灵敏度两档；参数行实时反映每个开关的生效状态"],
    ["6 风格化五模式", "35 s", "K1 直通 / K2 灰度 / K3 伪彩 / 长按 1 s 彩条 / K4 卡通化", "K1 -> K2 -> K3 -> 长按 -> K4",
     "每次停留 5 s；字幕打模式号与算法名：灰度 BT.601 / 伪彩 / 彩条 / 卡通化（边缘 + 四色平涂）"],
    ["7 运动检测", "20 s", "手在镜头前 0.5 m 横向划过 -> 红色块状描边框跟手；停下消失", "不操作",
     "帧差法，16x9 = 144 个 80x80 块，只存上帧块均值共 144 字节，零帧缓存、零 ERAM"],
    ["8 目标检测", "20 s", "红笔举到镜头前 -> 绿色框紧贴笔身；移开后保持 1 s 再消失；空场景无框", "不操作",
     "红色目标检测，两帧确认去抖 + 孤立块滤除，空场景零误检；漏检保持 1 s，框不闪断"],
    ["9 参数收尾", "10 s", "定格在卡通化 + 全部 OSD 的画面", "回到 K4",
     "字幕：1280x720@60Hz / LUT6 77.3% / ERAM 47.2% / DSP 25% / Setup WNS +104 ps"],
]
table(d, rows)

heading(d, "三、整体顺序逻辑")
para(d, "先证明「能跑」（段 1-2），再证明「跑得好」（段 3-4），再证明「能交互」（段 5-6），"
        "最后亮两个加分项（段 7-8）。")

heading(d, "四、操作与现象对应表")
rows2 = [
    ["操作", "出现的现象"],
    ["上电", "画面直出，CNT 递增"],
    ["SW2 上 / 下", "画面对比度变化（暗部更沉、亮部更透）"],
    ["SW1 上 / 下", "画面四角发绿 / 不发绿"],
    ["手电照射", "画面不过曝，遥测 M 回落"],
    ["SW3 下", "运动红框全部消失"],
    ["SW4 上 / 下", "参数行 SENS H / SENS L"],
    ["K2", "全屏灰度"],
    ["K3", "全屏蓝/绿/黄伪彩"],
    ["长按任意键 1 s", "竖直五段彩条"],
    ["K4", "画面四色平涂 + 黑描边"],
    ["手划过镜头", "红色块框跟手"],
    ["红笔入画", "绿色框贴笔"],
]
table(d, rows2)

heading(d, "五、待确认")
for s in [
    "段 6 的卡通化观感目前偏四色平涂，是否需要在录制前调优配色与描边粗细，待定。",
    "段 7/8 的检测行为在前一版比特流上已验收；若录制时行为不符，以实际为准并回退说明。",
]:
    para(d, "· " + s, first_indent=False, after=0)

p1 = os.path.join(WS, "演示视频脚本_20261019.docx")
d.save(p1)
print("已生成:", p1, os.path.getsize(p1), "B")

# ============ 文档 2：心得体会模板 ============
d = new_doc()
para(d, "心得体会写作模板", size=18, bold=True, align="c", first_indent=False, after=6)
para(d, "基于安路 PH1P35 的实时数字图像处理系统", size=14, bold=True,
     align="c", first_indent=False, after=6)
para(d, "建议总篇幅约 1000 字 ｜ 2026-10-19", size=10, align="c", first_indent=False, after=12)

para(d, "使用说明：以下为写作框架与要点提示，不是正文。第 2 段与第 3 段是评委判断「是否为本人完成」的关键，"
        "请务必写自己真实走过的弯路，不要写成技术综述。", after=10)

heading(d, "第 1 段 · 起点与选题（约 200 字）")
for s in [
    "写清为什么选这道题、拿到开发板时的第一印象。",
    "写最初对「用 FPGA 做图像」的理解——可以如实写「以为就是写个滤镜」。",
    "不要堆技术名词，写当时的真实认知水平。",
]:
    para(d, "· " + s, first_indent=False, after=0)

heading(d, "第 2 段 · 最难的那件事（约 350 字，重点段）")
para(d, "从下面三个真实案例里挑一个自己参与过的，按「现象 -> 一开始怎么想的 -> 怎么排掉的 -> 学到什么」四步写：")
rows3 = [
    ["案例", "现象", "真实根因"],
    ["A", "相机对着真实房间，画面却是零纹理的完美线性渐变",
     "传感器内置灰度测试图被「四个开关全拨上」这个出厂推荐档点开了"],
    ["B", "构建显示成功、.bit 时间戳更新，但网表里模块被删光了",
     "TD 把没有下游消费者的模块当冗余，在 phy 阶段整条扫掉"],
    ["C", "红笔一直检测不到，同时暗场景绿框乱闪",
     "8 位无符号减法在 G > R 时回绕，判定条件恒真"],
]
table(d, rows3)
para(d, "写作要点：重点写弯路——你一开始以为是什么、怎么一步步排除的。评委最能分辨真假的就是这一段。", after=6)

heading(d, "第 3 段 · 方法上的收获（约 300 字）")
para(d, "从下面三条里选，每条都要配一个具体例子：")
for s in [
    "可复现比能跑重要——每次采集必须留帧号（CNT）、拨码状态、比特流 md5，否则 A/B 结论会反复被推翻。",
    "分模块验证不够——两个模块各自仿真全过，接起来照样错；曾经有一次是统计模块与决策模块的量纲差 256 倍。",
    "一眼看不出问题时要主动造对照——用开发板自带 Logo 当色卡校采集链、用旋转 180 度排除照明因素、用盖住镜头排除黑电平。",
]:
    para(d, "· " + s, first_indent=False, after=0)
para(d, "这一节是加分点：写方法论比写技术细节更有价值。", after=6)

heading(d, "第 4 段 · 不足与展望（约 150 字）")
para(d, "诚实列 2~3 条真实短板，从下列中挑：")
for s in [
    "暗光下进光量受镜头光圈物理限制，只能靠增益与降帧率改善。",
    "目标检测目前只支持颜色特征，形状与多目标还不够稳。",
    "目标坐标标注因 slice 资源余量不足未实施。",
    "QSPI 固化与长期稳定性验证的时间窗口偏紧。",
]:
    para(d, "· " + s, first_indent=False, after=0)
para(d, "不要写「因为时间不足所以」这类万能句，要写具体的技术边界。", after=6)

heading(d, "格式要求")
rows4 = [
    ["项", "要求"],
    ["字体", "中文宋体，西文 Times New Roman"],
    ["字号", "小四（12 pt）"],
    ["行距", "1.5 倍"],
    ["首行缩进", "2 字符"],
    ["与报告一致性", "与比赛报告正文同格式（模板已固化）"],
]
table(d, rows4)

p2 = os.path.join(WS, "心得体会模板_20261019.docx")
d.save(p2)
print("已生成:", p2, os.path.getsize(p2), "B")
