# -*- coding: utf-8 -*-
"""把比赛报告同步到 2026-10-19 的实际进度。

原则：只改与「当前实现/当前资源/已完成的验收」不一致的地方，不重写已完成章节。
所有定位都按内容前缀匹配，不依赖固定段落索引（插入会漂移）。
"""
import copy
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

WS = r"E:\FPGA"
SRC = os.path.join(WS, "比赛报告_填空版_20261018.docx")
DST = os.path.join(WS, "比赛报告_填空版_20261023.docx")
BAK = os.path.join(WS, "_backup", "20261019_report_before_sync.docx")

os.makedirs(os.path.dirname(BAK), exist_ok=True)
shutil.copy2(SRC, BAK)
print("备份:", BAK)

d = Document(SRC)
log = []


def P(i):
    return d.paragraphs[i]


def find(prefix):
    for i, p in enumerate(d.paragraphs):
        if p.text.strip().startswith(prefix):
            return i
    return -1


def replace_text(i, new, tag):
    """替换段落文本，沿用第一个 run 的格式。"""
    p = d.paragraphs[i]
    if not p.runs:
        p.add_run(new)
    else:
        p.runs[0].text = new
        for r in p.runs[1:]:
            r.text = ""
    log.append((tag, i))


def insert_after(i, text, tag, size=12):
    """在第 i 段之后插入一段，复制第 i 段的段落格式与首个 run 的字体格式。"""
    src = d.paragraphs[i]
    new_p = copy.deepcopy(src._p)
    src._p.addnext(new_p)
    from docx.text.paragraph import Paragraph
    np = Paragraph(new_p, src._parent)
    if not np.runs:
        np.add_run("")
    np.runs[0].text = text
    for r in np.runs[1:]:
        r.text = ""
    log.append((tag, i))
    return np


def set_cell(table, row, col, text):
    c = table.cell(row, col)
    c.text = ""
    p = c.paragraphs[0]
    p.paragraph_format.line_spacing = 1.15
    p.paragraph_format.space_after = Pt(0)
    r = p.add_run(text)
    r.font.size = Pt(9)
    r.font.name = "Times New Roman"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def add_row(table, values):
    """复制最后一行格式，追加一行。"""
    last = table.rows[-1]
    new_tr = copy.deepcopy(last._tr)
    last._tr.addnext(new_tr)
    from docx.table import _Row
    row = _Row(new_tr, table)
    for j, v in enumerate(values):
        set_cell(table, len(table.rows) - 1, j, v)


t1, t2 = d.tables[0], d.tables[1]

# ---------- §1.1 功能与特性 ----------
i = find("（4）OSD 信息叠加")
if i >= 0:
    replace_text(i, "（4）OSD 信息叠加：安路 Logo、帧计数器（黄）、两行实时遥测（橙）、算法模式行（绿）、"
                    "参数状态行（亮青）、目标检测框（绿）、运动块框（红），共 7 层。", "§1.1(4) 6层->7层")

i = find("（5）硬件运动目标检测")
if i >= 0:
    replace_text(i, "（5）硬件运动目标检测：16×9 块级帧差，零帧存，运动中块以红色描边实时标注。", "§1.1(5) 保持")
    insert_after(i, "（6）硬件目标检测：按颜色特征识别红色目标，16×9 块级判决 + 两帧确认去抖 + 孤立块滤除 + "
                    "60 帧（1 秒）跟踪保持，命中的目标以绿色框在 OSD 上标注，空场景零误检。", "§1.1 新增(6) 目标检测")

# 原来的 (6)(7) 顺延为 (7)(8)
i = find("（6）实时参数调节")
if i >= 0:
    replace_text(i, "（7）实时参数调节：SW1 控 LSC 使能、SW2 控 S 曲线使能、SW3 控运动检测使能、"
                    "SW4 控运动检测灵敏度档（严格/宽松），画面上同步显示各参数状态。", "§1.1 (6)->(7)")
i = find("（7）自动曝光闭环")
if i >= 0:
    replace_text(i, "（8）自动曝光闭环：24MHz 域状态机在 7bit 单调增益索引（0~127，对应模拟增益 1.000×~15.750×）"
                    "上闭环收敛，附带高光与暗场护栏。", "§1.1 (7)->(8)")

# ---------- 摘要 ----------
i = find("在扩展与进阶功能方面")
if i >= 0:
    old = d.paragraphs[i].text.strip()
    if "目标检测" not in old:
        replace_text(i, old.rstrip("。") + "。此外还实现了按颜色特征识别的硬件目标检测：块级判决 + 两帧确认去抖 + "
                                            "孤立块滤除 + 1 秒跟踪保持，命中的目标以绿色框叠加，空场景零误检。",
                     "摘要 补目标检测")

i = find("系统在 60fps 下零掉帧运行")
if i >= 0:
    old = d.paragraphs[i].text.strip()
    old = old.replace("全部源码、约束、脚本与 16 个版本的比特流", "全部源码、约束、脚本与 27 个版本的比特流")
    replace_text(i, old, "摘要 16->27 版本")

# ---------- §1.4 指标来源 ----------
i = find("系统主要性能指标如下表")
if i >= 0:
    replace_text(i, "系统主要性能指标如下表（数据来源：当前交付版构建，比特流归档于 "
                    "`proj/releases/` 下对应目录，.bit md5 DB39A5CE50591330A6D6E9C0CFCFB2E3）：",
                 "§1.4 数据来源更新")

# ---------- 表 1 ----------
for r in range(len(t1.rows)):
    k = t1.cell(r, 0).text.strip()
    if k == "逻辑资源":
        set_cell(t1, r, 1, "slice 17448 / 21216 = 82.24%；LUT6 16400 / 21216 = 77.30%")
        log.append(("表1 逻辑资源", r))
    elif k == "存储 / 运算资源":
        set_cell(t1, r, 1, "ERAM 51 / 108 = 47.22%；DSP 10 / 40 = 25.00%；DFF 12092")
        log.append(("表1 存储运算", r))
    elif k == "时序收敛":
        set_cell(t1, r, 1, "Setup WNS +104ps / TNS 0 / 0 违例；Hold WNS +20ps / TNS 0 / 0 违例")
        log.append(("表1 时序", r))

keys1 = [t1.cell(r, 0).text.strip() for r in range(len(t1.rows))]
if "目标检测" not in keys1:
    # 插到「长跑稳定性」之前不方便，直接追加到表尾
    add_row(t1, ["目标检测", "红色目标；16×9 块级；两帧确认 + 孤立块滤除 + 60 帧跟踪保持；空场景零误检"])
    log.append(("表1 新增 目标检测行", len(t1.rows) - 1))

# ---------- 表 2 ----------
for r in range(len(t2.rows)):
    k = t2.cell(r, 0).text.strip()
    if k == "色调曲线":
        set_cell(t2, r, 1, "曲线分析脚本 + 同机位新旧比特流 A/B")
        set_cell(t2, r, 2, "p10 38→19；p50 134→127；p90 203→233；跨度 165→214；中调斜率 0.695→1.086；"
                           "已合入主线并于 2026-10-16 12:31 完成上板 A/B（两张曲线前信号逐位相同，仅 LUT 不同）")
        set_cell(t2, r, 3, "跨度增大、中点回 128")
        set_cell(t2, r, 4, "通过")
        log.append(("表2 色调曲线 状态更新", r))
    elif k == "运动目标检测":
        set_cell(t2, r, 2, "四段 SW3/SW4 组合录制：SW3 拨下两段红描边全程为 0；SW3 拨上两段出现块框并随物体移动，"
                           "最大 2 424~3 048 像素")
        set_cell(t2, r, 4, "通过")
        log.append(("表2 运动检测 状态更新", r))

keys2 = [t2.cell(r, 0).text.strip() for r in range(len(t2.rows))]
if "目标检测" not in keys2:
    add_row(t2, ["目标检测", "空场景 / 红笔入画 两张对照",
                 "空场景绿色框像素 0；红笔场景框 2490 像素，命中块 row[3..6]×col[1..5] 共 9 块连续簇，紧贴笔身",
                 "空场景无误检 + 目标有框", "通过"])
    log.append(("表2 新增 目标检测行", len(t2.rows) - 1))

# ---------- §2.3 模块数量 ----------
i = find("① RTL 设计")
if i >= 0:
    replace_text(i, "① RTL 设计：`proj/baseline/lab3/user_source/hdl_source/` 下的 Verilog 源码，"
                    "含官方 lab_ex_3 基线、9 个自研模块与 6 个改造模块。", "§2.3 12->9自研+6改造")

i = find("⑤ 版本管理")
if i >= 0:
    replace_text(i, "⑤ 版本管理：Git 仓库（Gitee `fpgacnds`），27 个比特流版本归档于 `proj/releases/`，"
                    "每版包含 `.bit`、压缩版、`route.qor`、`phy.area` 与 `readMe.txt`（记录 md5、时序、资源）。",
                 "§2.3 16->27 版本")

# ---------- §2.3 新增 obj_detect 模块说明 ----------
i = find("（12）`hdmi_mixer`")
if i >= 0:
    insert_after(i, "（12）`obj_detect`（自研，硬件目标检测）：与 `motion_detect` 同为像素级观察者，不接主通路握手。"
                    "逐像素判「红色主导」后按 16×9 的 80×80 块累加命中数，块内命中超过阈值判为该块为目标；"
                    "再做两帧确认（`S_now & S_prev`）与孤立块滤除（要求上下左右至少一个邻居也命中），"
                    "最后加 60 帧（1 秒）跟踪保持，使目标短暂漏检时框不闪断。"
                    "关键输出 `O_blk_mask[143:0]`，由 `hdmi_mixer` 绘制为绿色外轮廓框。"
                    "资源 855 LUT6 / 220 ripple / 878 FF / 0 ERAM / 0 DSP；全模块零乘法、零除法。",
                 "§2.3 新增 obj_detect")
    # 原 (12) 及之后顺延
    for old_pf, new_pf in (("（12）`hdmi_mixer`", "（13）`hdmi_mixer`"),
                           ("（13）`uicfgcs500_720p`", "（14）`uicfgcs500_720p`")):
        j = find(old_pf)
        if j >= 0 and not d.paragraphs[j].text.strip().startswith(new_pf):
            replace_text(j, new_pf + d.paragraphs[j].text.strip()[len(old_pf):], "§2.3 编号顺延 " + new_pf)

i = find("（13）`hdmi_mixer`")
if i >= 0:
    replace_text(i, "（13）`hdmi_mixer`（OSD 叠加）：7 个图层依次判定——安路 Logo（ROM）、帧计数器 CNT"
                    "（黄 `24'hfff200`）、遥测第 1 行（橙 `24'hff8000`）、遥测第 2 行（橙）、算法模式行 MODE"
                    "（绿 `24'h00ff88`）、参数状态行（亮青 `24'h00e6ff`）、目标检测框（绿 `24'h00ff40`）；"
                    "运动块红色描边也在此层绘制。七层共用唯一一份字符 ROM `osd_char_lib`，ERAM 无新增。",
                 "§2.3 hdmi_mixer 6->7层")

# ---------- §3.2.3 软件成果 ----------
i = find("（5）比特流版本台账")
if i >= 0:
    replace_text(i, "（5）目标检测截图：空场景绿色框像素为 0；红笔入画时绿色框紧贴笔身，命中块构成 4×5 连续簇。",
                 "§3.2.3 (5) 新增目标检测")

i = find("（5）比特流版本台账")
if i < 0:
    i = find("（6）比特流版本台账")
if i >= 0:
    replace_text(i, "（6）比特流版本台账：`proj/releases/` 下 27 个版本目录，每版含 `.bit`、压缩版、"
                    "`route.qor`、`phy.area` 与 `readMe.txt`。", "§3.2.3 版本台账 16->27")

# ---------- §3.2.3 遥测示例 ----------
i = find("（2）两行橙色遥测的字段定义")
if i >= 0:
    replace_text(i, "（2）两行橙色遥测的字段定义与实际读数示例：`AE2E S2 M3B W158B B1B6E`，其中 `AE` 为固定标签、"
                    "`2E` 为 7bit 增益索引（0x2E = 46）、`S2` 为闭环状态、`M3B` 为 FPGA 实测曲线前帧亮度"
                    "（0x3B = 59）、`W158B` 为 AWB 的 R 通道增益（÷4096 = 1.346×）、`B1B6E` 为 B 通道增益"
                    "（1.714×）。第二行依次给出 AE 的 9 个决策标志与稳定帧计数。",
                 "§3.2.3 遥测字段说明修正")

# ---------- §2.2.1 QSPI 容量 ----------
i = find("硬件平台为安路 HX1P35A 开发板")
if i >= 0:
    old = d.paragraphs[i].text.strip()
    if "128MB QSPI Flash" in old:
        replace_text(i, old.replace("128MB QSPI Flash", "128Mb（16MB）QSPI Flash N25Q128"),
                     "§2.2.1 QSPI 容量修正")

# ---------- §4.1 可扩展之处 ----------
i = find("（1）目标检测与识别")
if i >= 0:
    replace_text(i, "（1）目标检测的进一步扩展：现有 `obj_detect` 已实现颜色特征的块级检测与绿色框标注，"
                    "后续可增加形状特征与多目标分类，并按块坐标输出目标中心点。", "§4.1 (1) 目标检测已实现")

i = find("（2）动态跟踪")
if i >= 0:
    replace_text(i, "（2）动态坐标标注：现有 60 帧保持已实现「框不闪断」，进一步可把命中块的质心坐标"
                    "转成 OSD 数值上屏；受 slice 余量限制暂未实施。", "§4.1 (2) 跟踪->坐标标注")

i = find("（5）QSPI 固化")
if i >= 0:
    replace_text(i, "（5）QSPI 固化：赛题要求最终设计上电即可运行、无需 PC 下载。板载 N25Q128 QSPI Flash "
                    "即 FPGA 的配置存储器，用 TangDynasty 的 Program Flash 把 `.bit` 写入即可上电自启动，"
                    "不需要额外的加载 RTL。当前尚未执行这一步。", "§4.1 (5) QSPI 修正")

# ---------- §4.2 心得体会 ----------
i = find("待补充——这一节需要参赛队员本人撰写")
if i >= 0:
    replace_text(i, "待补充——这一节需参赛队员本人撰写，不宜由他人代笔。写作框架见同目录 "
                    "`心得体会模板_20261019.docx`（四段结构：起点与选题 / 最难的那件事 / 方法上的收获 / 不足与展望，"
                    "合计约 1000 字）。下列线索可直接取用：", "§4.2 引用心得体会模板")

# ---------- §2 整体框图 ----------
i = find("本部分按「整体")
if i >= 0:
    replace_text(i, "本部分按「整体 → 硬件 → 软件」逐级展开。系统整体框图见图 1（待补充：需要一张系统框图）；"
                    "模块级的文件位置、资源占用与维护归属见仓库根目录的 `WORKSPACE_MAP.md`，"
                    "各子模块的端口、时钟域与相互衔接关系在下文逐一说明。", "§2 引用 WORKSPACE_MAP")

d.save(DST)
print("已生成:", DST, os.path.getsize(DST), "B")
print("改动条数:", len(log))
for tag, idx in log:
    print("  · %-34s 段落/行 %s" % (tag, idx))
