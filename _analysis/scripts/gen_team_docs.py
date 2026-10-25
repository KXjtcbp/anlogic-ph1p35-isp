# -*- coding: utf-8 -*-
"""① 把系统框图插入比赛报告 §2（替换「待补充」占位）；② 生成给成员 B / C 的两份上手指南 docx。

所有事实均取自当前工作区可核对的文件：
  报告 = E:\\FPGA\\比赛报告_填空版_20261023.docx
  资源 = proj\\baseline\\lab3\\td_project\\camera_to_dsi_display_Runs\\phy_1\\{route.qor, camera_to_dsi_display_phy.area}
  拨码 = design_top_wrapper.v 的 S_lsc_bypass / S_gamma_bypass / S_mot_en / S_mot_strict
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

REPORT = r"E:\FPGA\比赛报告_填空版_20261023.docx"
FIG = r"E:\FPGA\系统框图_FPGA数据通路.png"


def set_run(run, size=12, bold=False, eastasia="宋体", color=None):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), eastasia)
    if color:
        run.font.color.rgb = RGBColor.from_string(color)


# ============================================================
# ① 报告：插入系统框图
# ============================================================
def insert_figure():
    d = Document(REPORT)
    tgt = None
    for p in d.paragraphs:
        if "系统整体框图见图 1" in p.text:
            tgt = p
            break
    if tgt is None:
        print("!! 未找到图 1 占位段落")
        return

    # 改写引导句
    for r in tgt.runs:
        r.text = ""
    tgt.runs[0].text = (
        "本部分按「整体 → 硬件 → 软件」逐级展开。系统整体框图见图 1；模块级的文件位置、"
        "资源占用与维护归属见仓库根目录的 `WORKSPACE_MAP.md`。"
    )
    for r in tgt.runs:
        set_run(r, 12)

    # 在引导句之后插入图片段落
    new_p = OxmlElement("w:p")
    tgt._p.addnext(new_p)
    from docx.text.paragraph import Paragraph
    pic_par = Paragraph(new_p, tgt._parent)
    pic_par.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic_par.paragraph_format.space_before = Pt(6)
    pic_par.paragraph_format.space_after = Pt(3)
    pic_par.add_run().add_picture(FIG, width=Cm(15.6))

    # 图注
    cap_p = OxmlElement("w:p")
    new_p.addnext(cap_p)
    cap = Paragraph(cap_p, tgt._parent)
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_after = Pt(8)
    r = cap.add_run("图 1  系统整体框图（四条通路：输入 / 图像处理 / 显示 / 控制）")
    set_run(r, 10.5, bold=False)

    d.save(REPORT)
    print("① 图 1 已插入，报告 %d B" % os.path.getsize(REPORT))


# ============================================================
# ② 给 B / C 的两份上手文档
# ============================================================
def new_doc():
    d = Document()
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = Pt(11)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    for s in d.sections:
        s.top_margin = Cm(2.4); s.bottom_margin = Cm(2.4)
        s.left_margin = Cm(2.8); s.right_margin = Cm(2.8)
    return d


def H(d, text, size=15, before=10, after=6):
    p = d.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    set_run(p.add_run(text), size, bold=True)
    return p


def P(d, text, size=11, indent=True, after=4):
    p = d.add_paragraph()
    p.paragraph_format.line_spacing = 1.4
    p.paragraph_format.space_after = Pt(after)
    if indent:
        p.paragraph_format.first_line_indent = Pt(size * 2)
    set_run(p.add_run(text), size)
    return p


def BUL(d, text, size=11):
    p = d.add_paragraph()
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Pt(size)
    set_run(p.add_run("· " + text), size)
    return p


def TABLE(d, rows, widths=None, size=9.5):
    t = d.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = 1.12
            p.paragraph_format.space_after = Pt(0)
            set_run(p.add_run(txt), size, bold=(i == 0))
    if widths:
        for j, w in enumerate(widths):
            for i in range(len(rows)):
                t.cell(i, j).width = Cm(w)
    return t


COMMON_HW = [
    "【开发板】安路 HX1P35A，主芯片 PH1P35MDG324（-3 速度等级）。板载：MIPI 输入 1 路、HDMI 输出 1 路、4 组拨码开关、4 组按键、4 组 LED、128Mb QSPI 配置 Flash（美光 N25Q128）、千兆网口、TF 卡槽。",
    "【传感器】思特威 SC500CS，500 万像素，RAW10 2-lane MIPI。不支持自动对焦。",
    "【显示器】1280×720@60Hz，HDMI 1.4。",
    "【工具链】TangDynasty V6.2.168116（安路官方 IDE）；ModelSim ASE（行为仿真）；Python 3（统计分析脚本）。",
    "【仓库】https://gitee.com/wuhu-captain-kx/fpgacnds  ，分支 main，仓库根就是 E:\\FPGA。",
]

COMMON_PIPE = [
    ["序号", "模块", "作用", "资源（LUT6/FF）"],
    ["1", "demosaic", "BGGR 去马赛克，40bit RAW → 128bit RGB", "官方 IP"],
    ["2", "data128_96", "128bit → 96bit 位宽转换（4 像素/拍）", "官方 IP"],
    ["3", "lsc", "镜头色彩暗角校正（20×12 节点 + 双线性插值，只校 R/B）", "795 / 274"],
    ["4", "awb（内含 wb_recip）", "灰世界自动白平衡；除法器换成倒数查表", "844 / 601"],
    ["5", "isp_gamma", "真 S 曲线色调映射（12 份并行 256×8 内联 ROM）", "115 / 196"],
    ["6", "my_algo", "五模式风格化：直通/灰度/伪彩/彩条/卡通化", "630 / 116"],
    ["7", "data96_128", "96bit → 128bit 位宽转换", "官方 IP"],
    ["旁路", "ae_stat", "帧亮度和统计（供 AE 用，只收不发）", "264 / 268"],
    ["旁路", "obj_detect", "颜色目标检测（16×9 块，绿色框标注）", "855 / 878"],
    ["旁路", "motion_detect", "块级帧差运动检测（红色框标注）", "1150 / 1809"],
]

COMMON_SW = [
    ["拨码/按键", "引脚", "功能", "拨上 / 按下", "拨下 / 抬起"],
    ["SW1", "A4", "LSC 使能", "启用暗角校正", "旁路（直通）"],
    ["SW2", "B4", "S 曲线使能", "启用真 S 曲线", "旁路（线性）"],
    ["SW3", "E11", "运动检测使能", "开（可出红框）", "关（不出框）"],
    ["SW4", "D11", "运动检测灵敏度", "严格档", "宽松档"],
    ["K1", "D5", "算法模式", "MODE0 直通", "—"],
    ["K2", "A9", "算法模式", "MODE1 灰度", "—"],
    ["K3", "B9", "算法模式", "MODE2 伪彩热力图", "—"],
    ["K4", "C7", "算法模式", "MODE4 卡通化", "—"],
    ["长按 K1~K4 ≥1s", "—", "算法模式", "MODE3 五段彩条", "—"],
]

COMMON_TRAP = [
    ["编号", "坑", "现象", "正确做法"],
    ["1", "TD 只认 run 目录的 .prj，不认 td_project/*.al",
     "新加的 .v 报 HDL-8007 … is a black box，但 .bit 时间戳照常刷新（假成功）",
     "新增文件必须同时写进 .al 和两个 run 的 .prj；构建后复查 .al 有没有被 TD 回写覆盖"],
    ["2", "AXI4-Stream 的 tlast 是「帧末」不是「行末」",
     "块索引永远不变，画面上只有一整列贯穿全帧",
     "行末要用 beat 计数器自造：(bx == H_BEATS-1)"],
    ["3", "Verilog 里 8bit 无符号相减会回绕",
     "R-G 在 G>R 时变成 200+，阈值判断恒真，暗场景满屏误检",
     "扩位比较：{1'b0,R} >= {1'b0,G} + 阈值"],
    ["4", "block 被综合工具当冗余删掉",
     "资源不增反减、功能完全失效，但没有任何报错",
     "构建后必须在 gate.area / phy.area 里按实例名搜一遍，确认它在网表里"],
    ["5", "HDMI 采集链会做 limited→full 展开",
     "每通道先减 12 码再乘 1.1644，暗部放大偏色，所有调色结论都失真",
     "OBS 里把色彩范围设成「扩展 (Full)」、色彩空间 Rec.709；用 Logo ROM 当色卡校准"],
]

def build_doc(title, subtitle, reader, sections):
    d = new_doc()
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_run(p.add_run(title), 18, bold=True)
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    set_run(p.add_run(subtitle), 11)
    p = d.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(14)
    set_run(p.add_run(reader), 10)
    for title_i, body in sections:
        H(d, title_i)
        body(d)
    return d


def sec_overview(d):
    P(d, "本作品参加全国大学生嵌入式芯片与系统设计竞赛 FPGA 创新设计赛道选题二——"
         "「基于安路 PH1P35 的实时数字图像处理系统」。目标是构建一条从 MIPI 摄像头到 HDMI "
         "显示器的完整实时视频通路，全部图像处理算法与控制逻辑都在 FPGA 内部以流水线方式自主实现，"
         "不依赖任何额外处理器。")
    P(d, "系统当前状态：四条通路全部打通并已上板验收，输出 1280×720@60Hz，无掉帧；"
         "ISP 包含黑电平、去马赛克、镜头暗角校正、自动白平衡、真 S 曲线、自动曝光六个环节；"
         "OSD 有 7 个图层；另有风格化五模式切换、硬件运动检测、硬件目标检测三项扩展功能。")
    P(d, "交付版比特流：proj/releases/ 下最新目录的 camera_to_dsi_display.bit，"
         "md5 DB39A5CE50591330A6D6E9C0CFCFB2E3，1789539 字节。")
    P(d, "资源水位（TangDynasty phy.area）：slice 17448 / 21216 = 82.24%；LUT6 16400 / 21216 = 77.30%；"
         "DFF 12092 / 42432；ERAM 51 / 108；DSP 10 / 40；Setup WNS +104 ps、0 违例。"
         "注意 TD 报的 LUT6 总量是 21216，与宣传的「38189 等效 LUT」不是同一口径，不要混用。")
    H(d, "1.1  硬件平台", 12, 8, 4)
    for t in COMMON_HW:
        BUL(d, t)


def sec_pipeline(d):
    P(d, "数据通路分四段，全部以 AXI4-Stream 逐拍握手，ISP 域时钟 60MHz、每拍 4 像素、"
         "每像素 24bit（R/G/B 各 8bit），所以一拍是 96bit。ISP 域内没有帧级缓存，"
         "延迟是固定的流水线级数。")
    P(d, "① 视频输入：SC500CS → MIPI D-PHY RX（硬核）→ csi_unpacket_2lane → raw10_unpacket_2lane，"
         "输出 40bit/4 像素的 RAW10。")
    P(d, "② 图像处理（ISP 域 60MHz）：按 isp_top.v 里的例化顺序是 demosaic → data128_96 → lsc → "
         "awb（内含 wb_recip）→ isp_gamma → my_algo → data96_128。其中 ae_stat、obj_detect、"
         "motion_detect 是「旁路观察者」——只收数据、不发数据、没有 tready，不占用主流水的节拍。")
    P(d, "③ 显示：ISP 输出 128bit → DDR2 帧缓存 → uivtc（1280×720@60 时序）→ hdmi_mixer（7 层 OSD）"
         "→ hdmi_tx → 显示器。")
    P(d, "④ 控制（24MHz 域）：key_mode_ctrl（按键去抖与模式切换）、ae_ctrl（自动曝光状态机）、"
         "uicfgcs500_720p（经 I2C 配置 SC500CS 的寄存器）、拨码同步。")
    TABLE(d, COMMON_PIPE, widths=[1.0, 3.4, 7.4, 3.0])
    P(d, "上表的资源列取自 phy_1/camera_to_dsi_display_phy.area 里的逐实例统计。")


def sec_sw(d):
    P(d, "现场交互全靠 4 个拨码和 4 个按键。拨码的实测极性是「拨下 = 逻辑 1、拨上 = 逻辑 0」，"
         "与很多资料写的相反，代码里统一用取反来处理。")
    TABLE(d, COMMON_SW, widths=[2.6, 1.4, 3.4, 4.2, 3.2])


def sec_trap(d):
    P(d, "以下五条是本项目真实踩过、并且每条都花了半天以上才定位的坑。改动前请先读一遍，"
         "它们都属于「代码没错、但结果全错」的类型。")
    TABLE(d, COMMON_TRAP, widths=[1.0, 4.0, 5.4, 4.4])


def sec_nowork(d):
    H(d, "5.1  没有板子时能做什么", 12, 8, 4)
    P(d, "板子只有一块，在负责人手上。你不需要板子也能完成绝大部分工作：")
    BUL(d, "编译检查：python _analysis\\scripts\\compile_check.py，正常结果是 42/43 通过。"
           "唯一失败的是 proj/baseline/lab3/user_source/hdl_source/ph1p35_ddr/ph1p35_324_ddr_wrapper.v，"
           "那是官方 DDR 黑盒保护文件，属预期失败。")
    BUL(d, "行为仿真：ModelSim ASE 装在 E:\\modelsim\\modelsim_ase\\win32aloem\\。"
           "各模块的 testbench 在 _analysis\\sim\\<模块名>\\ 下，跑法都是 vlib work → vlog 源文件 tb 文件 "
           "→ vsim -c -do \"run -all; quit -f\" <tb名>。")
    BUL(d, "综合与时序：E:\\TD 的 TangDynasty 命令行可跑完整 syn+phy 流程，"
           "驱动脚本是 _analysis\\misc\\td_run_direct.ps1，约 10~15 分钟出 route.qor 和 .bit。")
    BUL(d, "统计分析：_analysis\\scripts\\ 下大量 Python 脚本用于分析采集图，依赖 numpy 与 Pillow。")
    BUL(d, "文档与报告：比赛报告在仓库根的 比赛报告_填空版_20261023.docx，"
           "工作区地图在 WORKSPACE_MAP.md。")
    H(d, "5.2  提交约定", 12, 8, 4)
    BUL(d, "分支：main 由负责人推送；你从 main 拉自己的分支（feat/xxx），改完提 PR 或直接请负责人合。")
    BUL(d, "只提交源码与文档。仿真中间产物（work/、*.qpg、*.vstf、*.wlf、runs/*/run.log）不要进 git。")
    BUL(d, "改了 design_top_wrapper.v 或 isp_top.v 这类公共文件的，请在 commit 标题第一行写 TOUCHES: <文件名>，"
           "避免和别人冲突。")
    BUL(d, "任何改动都要跑一遍 compile_check.py，并说明 42/43 是否保持。")


def sec_b_own(d):
    P(d, "你负责的是 ISP 的颜色链路，具体是 proj/baseline/lab3/user_source/hdl_source/ 下的：")
    BUL(d, "awb.v —— 灰世界自动白平衡。输入 96bit（4 像素），逐帧累加 R/G/B，"
           "用 wb_recip.v 的倒数查表算出 R 与 B 的增益，然后在帧首 latch 成常量乘到整帧上。")
    BUL(d, "wb_recip.v —— 倒数查表除法器，用它替换了原来的两个 TangDynasty 流水除法器。"
           "把 slice 从 83.78% 压到 66.10% 就是这一步的功劳。")
    BUL(d, "lsc.v —— 镜头色彩暗角校正。20×12 节点二维增益表、双线性插值、只校 R/B 不动 G。")
    H(d, "6.1  当前颜色链的实测状态", 12, 8, 4)
    P(d, "白纸靶面上整帧 R/G = 0.9800 / 0.9804 / 0.9797，B/G = 0.9803 / 0.9807 / 0.9799，"
         "落在 0.98~1.02 的验收带内，帧间极差 0.22%，判为通过。")
    P(d, "但有一个已知的残余：R 与 B 相对 G 存在约 2~3 个码的固定负偏置，与亮度无关。"
         "暗场景下这个固定值占比大，看起来会偏绿；亮场景下可以忽略。这个残余的归属至今没有完全定案——"
         "可以通过 OSD 上的两行橙色遥测读到 AWB 的实际增益（字段 W 与 B，屏幕上的四位十六进制除以 4096 就是倍率）。")
    H(d, "6.2  建议你先做的三件事", 12, 8, 4)
    BUL(d, "把 tb 跑起来：_analysis\\sim\\awb\\ 下有 tb_awb_means.v 等，先确认你能复现「输入 R/G=0.800 "
           "→ 输出 R/G=1.0000」这个结论，理解灰世界是怎么闭环的。")
    BUL(d, "读一遍 awb.v 的四路累加与帧锁存部分：一句话概括是「四个像素组的和各自累加，"
           "帧首把上一帧算出的整帧比值 latch 成常量，整帧用这个常量乘」。"
           "如果发现增益在帧内变化，那就是 latch 被破坏了。")
    BUL(d, "把那个 2~3 码的残余定位清楚。允许的排查手段：ChipWatcher 探针（需要重新综合一次，"
           "约 12 分钟）、或者让负责人在 OSD 上加字段。结论要能用「哪个模块、哪一行、为什么」写出来。")
    P(d, "注意：所有颜色结论都受 HDMI 采集链影响。采集链已经校准过（用 Logo ROM 当色卡，"
         "主蓝 27,44,75、主红 235,29,36 逐码对齐），但 OBS 的设置一旦改动就会重新引入失真。"
         "分析采集图之前，先用 captures/ 里的 logo 色值核对一遍。")


def sec_c_own(d):
    P(d, "你负责的是 OSD 与色调曲线两块，具体是 proj/baseline/lab3/user_source/hdl_source/ 下的：")
    BUL(d, "hdmi_mixer.v —— OSD 叠加，7 个图层。这是全工程最大的一个模块（2874 个 LUT6）。")
    BUL(d, "isp_gamma.v —— 真 S 曲线色调映射，12 份并行的 256×8 内联 ROM。")
    BUL(d, "osd_char_lib.v —— OSD 字符字模库（5×7 点阵），含汉字「安路」的自绘字模。")
    H(d, "6.1  OSD 的 7 个图层", 12, 8, 4)
    TABLE(d, [
        ["层", "内容", "位置（1280×720 内部坐标）", "颜色"],
        ["1", "安路 Logo", "左上角，160×160 ROM", "全彩（源自 logo ROM）"],
        ["2", "帧计数器 CNT", "(360,110) 起", "黄 24hfff200"],
        ["3", "算法模式行 MODE n", "(165,165) 起", "绿 24h00ff88"],
        ["4", "遥测第 1 行", "(376,152) 起，304×10", "橙 24hff8000"],
        ["5", "遥测第 2 行", "(376,164) 起，304×10", "橙 24hff8000"],
        ["6", "参数状态行", "(176,200) 起，512×16", "亮青 24h00e6ff"],
        ["7", "运动框 / 目标框", "按块坐标动态生成", "红 24hff2020 / 亮绿 24h00ff40"],
    ], widths=[0.9, 4.4, 5.9, 4.0])
    P(d, "图层按优先级从高到低依次判定，命中即停止。所有图层共用 hdmi_mixer.v 里唯一一份 "
         "osd_char_lib 例化，靠时分复用的 mux 切换字符来源，所以加图层不额外占 ERAM。")
    P(d, "★重要★：OSD 用的是 1280×720 的内部坐标，屏幕上是 1920×1080，所以实际位置 = 内部坐标 × 1.5。"
         "分析采集截图时要记得乘这个系数，否则会算错位置。")
    H(d, "6.2  S 曲线的当前参数", 12, 8, 4)
    P(d, "曲线是分段幂函数：x ≤ 128 时 y = 128·(x/128)^1.15；x > 128 时 "
         "y = 128 + 127·(1 − ((255−x)/127)^1.10)；再叠一层黑位软恢复 y = y − K·(1 − y/255)²，取 K = 1。")
    P(d, "锚点（输入 → 输出）：0→0, 1→0, 2→0, 4→1, 8→4, 16→11, 32→25, 64→57, 96→92, "
         "128→128, 160→163, 192→196, 224→228, 255→255。")
    P(d, "效果：p10 38→19、p50 134→127、p90 203→233、p10~p90 跨度 165→215、中调斜率 0.695→1.125、"
         "被压成纯黑的输入码 41→3。已上板做过同机位新旧比特流 A/B，判为通过。")
    P(d, "★改曲线的方法★：表是内联在 isp_gamma.v 里的 Verilog 赋值语句（mem_b00[0] = 8'h00; 这样 256 行），"
         "★绝对不能用 $readmemh★——TangDynasty 的综合工作目录在 run 目录下，相对路径会静默读不到，"
         "表全变 0，上板全黑，而所有报告都是正常的。生成脚本在 _analysis\\scripts\\ 下。")
    H(d, "6.3  建议你先做的三件事", 12, 8, 4)
    BUL(d, "把 tb_gamma_bp.v 跑起来，确认你能复现曲线表。改表后要同步改 TB 里 `include 的 .vh 文件，"
           "否则会出现几百个假 FAIL。")
    BUL(d, "读一遍 hdmi_mixer.v 的图层判定链和字符 mux，搞清楚再加一层要动哪几处。"
           "注意字符索引位宽：窗口宽超过 256 像素时 S_par_idx 必须用 5bit，用 4bit 会回卷。")
    BUL(d, "报告里 §1.4 的两张表、§2.3 的模块清单需要随代码同步。报告的当前版本是 "
           "比赛报告_填空版_20261023.docx，报告里的所有数值都要能在 phy.area / route.qor 里核对到。")


def main():
    insert_figure()

    d1 = build_doc(
        "基于安路 PH1P35 的实时数字图像处理系统",
        "—— 成员 B 上手指南（颜色链路 / AWB / LSC）",
        "目标读者：负责 ISP 颜色链路的成员 B　　编写日期：2026-10-20　　对应交付版 md5：DB39A5CE",
        [("1  项目是什么", sec_overview),
         ("2  数据通路", sec_pipeline),
         ("3  现场交互：拨码与按键", sec_sw),
         ("4  五条必须知道的坑", sec_trap),
         ("5  没有板子时的工作方式", sec_nowork),
         ("6  你负责的部分", sec_b_own)])
    f1 = r"E:\FPGA\给成员B_项目上手指南_20261020.docx"
    d1.save(f1)
    print("② 已生成:", f1, os.path.getsize(f1), "B")

    d2 = build_doc(
        "基于安路 PH1P35 的实时数字图像处理系统",
        "—— 成员 C 上手指南（OSD 叠加 / 真 S 曲线 / 报告同步）",
        "目标读者：负责 OSD 与色调曲线的成员 C　　编写日期：2026-10-20　　对应交付版 md5：DB39A5CE",
        [("1  项目是什么", sec_overview),
         ("2  数据通路", sec_pipeline),
         ("3  现场交互：拨码与按键", sec_sw),
         ("4  五条必须知道的坑", sec_trap),
         ("5  没有板子时的工作方式", sec_nowork),
         ("6  你负责的部分", sec_c_own)])
    f2 = r"E:\FPGA\给成员C_项目上手指南_20261020.docx"
    d2.save(f2)
    print("② 已生成:", f2, os.path.getsize(f2), "B")


if __name__ == "__main__":
    main()
