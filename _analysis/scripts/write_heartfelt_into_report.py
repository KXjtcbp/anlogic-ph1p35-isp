# -*- coding: utf-8 -*-
"""把去 AI 感后的心得体会四段写进比赛报告 §4.2。

做法：定位「心得体会」标题段，用 insert_paragraph_before 在其后（即原
「待补充——这一节需参赛队员本人撰写」那段的位置）插入正文，最后删除该占位段。

原文的每条事实、每个数字、每个专业术语都保持不变；只调整用词与句式。
"""
import os
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORT = r"E:\FPGA\比赛报告_填空版_20261019.docx"
BACKUP = r"E:\FPGA\_backup\20261022_report_before_heartfelt.docx"

CN, EN, PT = "宋体", "Times New Roman", 12

# ---------------------------------------------------------------- 正文
# 第 1 段 · 起点与选题
P_START = ("比赛是刷社交网络刷到的。当时看到 FPGA 创新设计赛道的通知，想起来这学期正好在上 "
           "Verilog 和 FPGA，就去查了报名怎么弄、题目是什么。在那之前我对 FPGA 的认识只有 AMD 的 "
           "Vivado 加 Zynq 开发平台，别的都没听过。后来跟指导老师聊了一次，才知道国内还有安路这类"
           "厂商，走安路赛道、做选题二也是那次聊出来的。当时我以为“用 FPGA 做图像处理”就是写个"
           "滤镜，没别的。")

# 第 2 段 · 最难的那件事（四步，每步一段）
P_HARD1 = ("最早弄亮度的时候想法很简单。画面暗，那就做一条提亮的曲线，拨个开关能看出亮一点，"
           "就算成了。曲线写完，表也生成了，仿真过了，综合报告全绿。结果烧上板把开关拨到“开”，"
           "画面跟“关”基本没区别。我们在屏幕前边拨了好几次，肉眼确实分不出来。")
P_HARD2 = ("一开始想的是曲线太平了，那把提亮幅度调大就行。重新生成表、重新综合、再烧，这次能"
           "看出一点区别，但已经过头了，画面发灰。后来又怀疑是伽马参数不对，换了几组试。折腾两轮"
           "下来其实一直在原地：每次都是靠肉眼看有没有效果，可肉眼不是尺子。更要命的是根本没有"
           "一块稳定的靶面，灯亮一点、相机挪一点，前后两次拍的条件就不一样了，改完也说不清是参数"
           "起作用还是光变了。那时候真没什么调试经验，不知道改东西之前得先想清楚怎么判断改对了。")
P_HARD3 = ("后来换了个问法。不问“看出来了吗”，问“能量出来吗”。盖住镜头取黑电平，白纸铺满"
           "画面当固定靶面，拨码位置和帧号一起记下来。有了能比的数，差多少一下就看到了。这时候"
           "回头翻前面几次改动，发现有一部分其实是有用的，只是当时看不出来。")

# 第 3 段 · 方法上的收获（两层）
P_METHOD1 = ("亮度这件事之后，我们养成一个习惯，不管改什么，先把“怎么算改对了”写下来，写不出来"
             "的直接划掉。后来这条规矩真救了场。镜头暗角校正到底有没有生效，之前争了很久都是凭"
             "印象，最后是靠对照实验定的：同机位、同光照，只拨一个开关，两批独立采集下来给出同"
             "一个数字，这才算完。")
P_METHOD2 = ("还有一条是我自己慢慢摸出来的，跟焦虑有关。中间那几周一直看不到头，我每天都在想怎么"
             "往前推、怎么把这个东西真做出来，晚上躺下还在过第二天要干什么。有一次我催了进度，就在"
             "分完任务之后、两人交付物交过来之前。结果他们按时交了，质量比我预期还好。所以那次焦虑"
             "其实跟队友没关系，是我自己把“能不能做完”当成了一个靠催能解决的事。后来我换了个很笨"
             "的办法，焦虑上来的时候不去算还差多少，只写下今天能交出去的那一件。进度没因此变快，但"
             "我从“担心整件事”变成“先做完手上这一件”，就不慌了。")

# 第 4 段 · 不足与展望（三层）
P_LIMIT1 = ("现在还有两处没解决。一个是暗光。传感器曝光已经顶到手册给的上限，模拟增益也到顶了，"
            "再往上只能靠数字增益和降帧率去补。光圈是镜头定死的，进光量就那么多，不是调参数能"
            "绕过去的。")
P_LIMIT2 = ("另一个是目标检测现在只认颜色。场景干净的时候框能贴住目标，换个颜色或者光照一变就"
            "不稳了，形状和多目标还没找到靠谱的做法。")
P_LIMIT3 = ("后面还有时间的话，我想先把检测从只看颜色改成颜色加形状一起判，再去磨暗光下的成像。")

BLOCKS = [P_START, P_HARD1, P_HARD2, P_HARD3, P_METHOD1, P_METHOD2,
          P_LIMIT1, P_LIMIT2, P_LIMIT3]


def _fmt(p):
    """统一成正文格式：中宋 + 西 Times、小四、1.5 倍行距。"""
    pf = p.paragraph_format
    pf.line_spacing = 1.5
    for r in p.runs:
        r.font.name = EN
        r.font.size = Pt(PT)
        if r._element.rPr is not None and r._element.rPr.rFonts is not None:
            r._element.rPr.rFonts.set(qn("w:eastAsia"), CN)


def main():
    if not os.path.exists(BACKUP):
        import shutil
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        shutil.copy2(REPORT, BACKUP)
        print("备份 →", BACKUP)

    d = Document(REPORT)

    # 1) 找「心得体会」标题段
    hdr = None
    for i, p in enumerate(d.paragraphs):
        if p.text.strip() == "心得体会":
            hdr = i
            break
    if hdr is None:
        raise SystemExit("找不到「心得体会」标题段")

    # 2) 找其后的占位段（第一段含“待补充”的）
    holder = None
    for p in d.paragraphs[hdr + 1: hdr + 4]:
        if "待补充" in p.text:
            holder = p
            break
    if holder is None:
        raise SystemExit("找不到心得体会的“待补充”占位段")
    print("定位：标题段 [%d]，占位段首句 = %s" % (hdr, holder.text.strip()[:40]))

    # 3) 在占位段前插入九个正文段
    for txt in BLOCKS:
        np = holder.insert_paragraph_before(txt)
        _fmt(np)

    # 4) 删掉占位段
    holder._element.getparent().remove(holder._element)

    d.save(REPORT)
    print("写入完成 →", REPORT, os.path.getsize(REPORT), "B")

    # 5) 复核
    d2 = Document(REPORT)
    tag = False
    n = 0
    for p in d2.paragraphs:
        t = p.text.strip()
        if t == "心得体会":
            tag = True
            continue
        if tag:
            if t.startswith("4.1") or (t.startswith("4.") and len(t) < 12):
                break
            print("  ¶ %3d 字 | %s" % (len(t), t[:46]))
            n += 1
            if n >= 14:
                break
    print("正文段数 =", n)


if __name__ == "__main__":
    main()
