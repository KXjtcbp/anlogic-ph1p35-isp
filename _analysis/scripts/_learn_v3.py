# -*- coding: utf-8 -*-
"""《项目学习清单》改造 v3（针对用户 m10741 的三条要求）

1) 术语通俗化：插入「术语速查表」（24 个词，一句话解释）
2) 代码完整化：把 isp_top.v 里 6 个只有一行的例化块换成完整例化 + 逐行中文注释
3) 补充图示：插入 4 张示意图

在已交付的 docx 上做后处理，不重新生成整份文档。
"""
import copy
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from docx import Document
from docx.shared import Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

DOC = r"E:\FPGA\项目学习清单_20261023.docx"
FIG = r"E:\FPGA\_analysis\out\figs"
BACKUP = r"E:\FPGA\_backup\20261028_learn_before_v3.docx"

# ---------------- 通用 ----------------

def set_cell_bg(cell, hexfill):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexfill)
    tcPr.append(shd)


def mkrpr(bold=False, mono=False, size=10.5, color=None):
    rPr = OxmlElement("w:rPr")
    if mono:
        rf = OxmlElement("w:rFonts")
        rf.set(qn("w:ascii"), "Consolas")
        rf.set(qn("w:hAnsi"), "Consolas")
        rf.set(qn("w:eastAsia"), "Consolas")
        rPr.append(rf)
    else:
        rf = OxmlElement("w:rFonts")
        rf.set(qn("w:ascii"), "Times New Roman")
        rf.set(qn("w:hAnsi"), "Times New Roman")
        rf.set(qn("w:eastAsia"), "宋体")
        rPr.append(rf)
    if bold:
        rPr.append(OxmlElement("w:b"))
    if color:
        c = OxmlElement("w:color")
        c.set(qn("w:val"), color)
        rPr.append(c)
    sz = OxmlElement("w:sz")
    sz.set(qn("w:val"), str(int(size * 2)))
    rPr.append(sz)
    return rPr


def add_run_mixed(p, text, size=10.5):
    """把一行代码拆成「代码黑 + // 注释绿」两色。"""
    if "//" in text:
        code, _, cmt = text.partition("//")
        for seg, col in ((code, "1F3864"), ("//" + cmt, "2E7D32")):
            if not seg:
                continue
            r = OxmlElement("w:r")
            r.append(mkrpr(mono=True, size=size, color=col))
            t = OxmlElement("w:t")
            t.set(qn("xml:space"), "preserve")
            t.text = seg
            r.append(t)
            p._p.append(r)
    else:
        r = OxmlElement("w:r")
        r.append(mkrpr(mono=True, size=size, color="1F3864"))
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = text
        r.append(t)
        p._p.append(r)


def new_para(text="", bold=False, size=10.5, color=None, mono=False,
             indent=True, before=0, after=4, spacing=1.38, align=None):
    p = Document().add_paragraph()
    pPr = p._p.get_or_add_pPr()
    if spacing:
        sp = OxmlElement("w:spacing")
        sp.set(qn("w:line"), str(int(240 * spacing)))
        sp.set(qn("w:lineRule"), "auto")
        sp.set(qn("w:before"), str(int(before * 20)))
        sp.set(qn("w:after"), str(int(after * 20)))
        pPr.append(sp)
    if indent:
        ind = OxmlElement("w:ind")
        ind.set(qn("w:firstLine"), str(int(size * 2 * 20)))
        pPr.append(ind)
    if align:
        jc = OxmlElement("w:jc")
        jc.set(qn("w:val"), align)
        pPr.append(jc)
    if text:
        r = OxmlElement("w:r")
        r.append(mkrpr(bold=bold, mono=mono, size=size, color=color))
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = text
        r.append(t)
        p._p.append(r)
    return p


def code_para(line, size=8.5):
    """一行代码 + 灰底。"""
    p = new_para(indent=False, before=0, after=0, spacing=1.0)
    pPr = p._p.get_or_add_pPr()
    ind = OxmlElement("w:ind")
    ind.set(qn("w:left"), "200")
    pPr.append(ind)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F4F4F4")
    pPr.append(shd)
    add_run_mixed(p, line, size=size)
    return p


# ---------------- 6 个完整例化（带逐行注释） ----------------

BLOCKS = {
    "demosaic": (187, 209, [
        "demosaic #(                              // 模块名 demosaic；#( ... ) 里是「参数」，综合时定死",
        "    .IMG_HEIGHT          (720 ),          // 一帧 720 行",
        "    .IMG_WIDTH           (1280),          // 一行 1280 列",
        "    .data_complete_delay (50  ),          // 内部先等 50 拍，让流水线装满再往外吐数据",
        "    .BAYER_MODE          (\"BGGR\")         // 拜耳排列：本行左起 蓝、绿、蓝、绿…",
        ")",
        "u_demosaic                                   // 这个「实例」的名字；同一模块可例化多次，靠名字区分",
        "(",
        "    .I_clk               (axi4s_video_aclk), // 时钟，就是像素流所在的 60 MHz",
        "    .I_rst_n             (I_rst_n),          // 复位，低有效（0 = 正在复位）",
        "    .I_blk_bypass        (I_blk_bypass),     // 黑电平扣除的旁路（1 = 直通不扣）",
        "    .axi4s_video_tdata   (I_tdata),          // 输入：128 bit / 拍（4 像素 × 32 bit）",
        "    .axi4s_video_tdest   (I_tdest),          // 输入：通道号，本工程没用到",
        "    .axi4s_video_tlast   (I_tlast),          // 输入：行末？不，在本工程里是帧末（见 2.2）",
        "    .axi4s_video_tvalid  (I_tvalid),         // 输入：这一拍的数据有效吗",
        "    .axi4s_video_tuser   (I_tuser),          // 输入：帧开始标记",
        "    .axi4s_video_tready  (I_tready),         // 输出：我这级忙不忙（0 = 别给我发）",
        "    .O_tlast             (m_axis_tlast),     // 输出：帧末标记",
        "    .O_tuser             (m_axis_tuser),     // 输出：帧开始标记",
        "    .O_tdata             (m_axis_tdata),     // 输出：128 bit，已经补成 R/G/B 三通道",
        "    .O_tvalid            (m_axis_tvalid),    // 输出：数据有效",
        "    .O_tready            (m_axis_tready)     // 输入：下一级忙不忙",
        ");",
    ]),
    "data128_96": (211, 214, [
        "data128_96 u_data128_96 (                     // 位宽转换：128 bit/拍 → 96 bit/拍",
        "    .I_tdata(m_axis_tdata),                   // 进来：4 像素 × 32 bit（R/G/B 各 8 + 8 bit 填充）",
        "    .O_tdata(m_axis_tdata_96)                 // 出去：4 像素 × 24 bit（R/G/B 正好各 8，最省）",
        ");                                            // 注意它没有 tvalid/tuser —— 因为它只是重排，不改变节奏",
    ]),
    "lsc": (228, 245, [
        "lsc #(                                        // 镜头暗角校正（Lens Shading Correction）",
        "    .LSC_ENABLE(1'b1       ),                 // 1 = 启用；设 0 则综合时整个模块被消掉，不占资源",
        "    .H_BEATS   (12'd320    ),                 // 一行 320 拍（1280 像素 ÷ 4）",
        "    .V_LINES   (12'd720    ),                 // 一帧 720 行",
        "    .K_MAX     (10'd1023   )                  // 增益系数上限：g = 1 + k/1024，k 最大 1023 ⇒ 最大 1.999×",
        ") u_lsc (",
        "    .I_clk    (axi4s_video_aclk),             // 时钟",
        "    .I_rst_n  (I_rst_n         ),             // 复位，低有效",
        "    .I_bypass (I_lsc_bypass    ),             // 运行期旁路（1 = 直通），可以不重综合就做 A/B 对照",
        "    .I_tdata  (m_axis_tdata_96 ),             // 输入：lsc 之前的那一级（data128_96 的输出）",
        "    .I_tvalid (m_axis_tvalid   ),             // 输入：有效",
        "    .I_tuser  (m_axis_tuser    ),             // 输入：帧开始",
        "    .I_tlast  (m_axis_tlast    ),             // 输入：帧末",
        "    .O_tdata  (lsc_tdata_96    ),             // 输出：校完的画面 96 bit/拍",
        "    .O_tvalid (lsc_tvalid      ),             // 输出：有效（比输入晚 2 拍）",
        "    .O_tuser  (lsc_tuser       ),             // 输出：帧开始（同样晚 2 拍，必须用这个不能还用输入的）",
        "    .O_tlast  (lsc_tlast       )              // 输出：帧末",
        ");",
    ]),
    "awb": (298, 316, [
        "awb #(                                        // 自动白平衡（Auto White Balance）",
        "    .IMG_HEIGHT(720 ),                        // 一帧高",
        "    .IMG_WIDTH (1280)                         // 一帧宽",
        ") u_awb (",
        "    .I_clk   (axi4s_video_aclk),              // 时钟",
        "    .I_rst_n (I_rst_n),                       // 复位",
        "    .I_tlast (lsc_tlast    ),                 // 输入取自 lsc 的输出（不是 data128_96！）",
        "    .I_tuser (lsc_tuser    ),                 // 帧开始",
        "    .I_tdata (lsc_tdata_96 ),                 // 数据 96 bit/拍",
        "    .I_tvalid(lsc_tvalid   ),                 // 有效",
        "    .I_tready(m_axis_tready),                 // 我这级忙不忙",
        "    .O_tlast (awb_O_tlast ),                  // 输出：帧末",
        "    .O_tuser (awb_O_tuser ),                  // 输出：帧开始",
        "    .O_tdata (awb_O_tdata ),                  // 输出：白平衡之后的画面",
        "    .O_tvalid(awb_O_tvalid),                  // 输出：有效",
        "    .O_tready(awb_O_tready),                  // 输入：下一级忙不忙",
        "    .O_gain_r(O_wb_gain_r),                   // ★额外输出★ 当前 R 通道用的增益，接到 OSD 遥测显示",
        "    .O_gain_b(O_wb_gain_b)                    // ★额外输出★ 当前 B 通道用的增益",
        ");",
    ]),
    "isp_gamma": (325, 339, [
        "isp_gamma u_isp_gamma (                       // S 曲线查表级（色调曲线），固定 2 拍延迟",
        "    .I_clk          ( axi4s_video_aclk ),     // 时钟",
        "    .I_rst_n        ( I_rst_n          ),     // 复位",
        "    .I_tlast        ( awb_O_tlast      ),     // 输入：来自 awb 的输出",
        "    .I_tuser        ( awb_O_tuser      ),     // 输入：帧开始",
        "    .I_tdata        ( awb_O_tdata      ),     // 输入：96 bit / 拍",
        "    .I_tvalid       ( awb_O_tvalid     ),     // 输入：有效",
        "    .I_tready       ( gam_I_tready     ),     // 我这级忙不忙",
        "    .I_gamma_bypass ( I_gamma_bypass   ),     // 旁路（1 = 直通）；★旁路也是 2 拍，所以切换不错帧★",
        "    .O_tdata        ( gam_O_tdata      ),     // 输出：查完表的数据",
        "    .O_tlast        ( gam_O_tlast      ),     // 输出：帧末",
        "    .O_tuser        ( gam_O_tuser      ),     // 输出：帧开始",
        "    .O_tvalid       ( gam_O_tvalid     ),     // 输出：有效",
        "    .O_tready       ( algo_I_tready    )      // 输入：下一级（my_algo）忙不忙",
        ");",
    ]),
    "my_algo": (349, 367, [
        "my_algo #(                                    // 我们自己的算法层：五种风格化",
        "    .THRESH     ( 8'd128 ),                   // 老的二值化阈值；现在 MODE 3 改用固定五段，这个参数已不参与",
        "    .MODE_INIT  ( 3'd0   )                    // 上电默认模式 0（原图直通）",
        ") u_my_algo (",
        "    .I_clk      ( axi4s_video_aclk ),         // 时钟",
        "    .I_rst_n    ( I_rst_n          ),         // 复位",
        "    // 输入源是 isp_gamma 的输出，不是 awb —— 比原来多 2 拍延迟",
        "    .I_tlast    ( gam_O_tlast      ),         // 输入：帧末",
        "    .I_tuser    ( gam_O_tuser      ),         // 输入：帧开始",
        "    .I_tdata    ( gam_O_tdata      ),         // 输入：96 bit / 拍",
        "    .I_tvalid   ( gam_O_tvalid     ),         // 输入：有效",
        "    .I_tready   ( algo_I_tready    ),         // 我这级忙不忙",
        "    .O_tdata    ( algo_O_tdata     ),         // 输出：风格化之后的画面",
        "    .O_tlast    ( algo_O_tlast     ),         // 输出：帧末",
        "    .O_tuser    ( algo_O_tuser     ),         // 输出：帧开始",
        "    .O_tvalid   ( algo_O_tvalid    ),         // 输出：有效",
        "    .O_tready   ( O_tready         ),         // 输入：整条 ISP 的出口反压，一直给 1",
        "    .I_mode     ( I_algo_mode      )          // ★输入★ 3 bit 模式号，由按键 K1~K4 实时给",
        ");",
    ]),
    "data_96bit_to_128bit": (402, 413, [
        "data_96bit_to_128bit u_data_96bit_to_128bit(  // 96 bit/拍 → 128 bit/拍（最后一道位宽转换）",
        "    .I_clk              ( axi4s_video_aclk  ),// 时钟",
        "    .I_rst_n            ( I_rst_n           ),// 复位",
        "    .I_96b_frame_start  ( algo_O_tuser      ),// 输入：帧开始（来自 my_algo 输出）",
        "    .I_96b_valid        ( algo_O_tvalid     ),// 输入：有效",
        "    .I_96b_data         ( algo_O_tdata      ),// 输入：96 bit 数据",
        "    .O_128b_frame_start ( awb_O_tuser_128   ),// 输出：帧开始（给 OSD 与 HDMI）",
        "    .O_128b_valid       ( awb_O_tvalid_128  ),// 输出：有效，注意节奏变成「4 拍输入 → 3 拍输出」",
        "    .O_128b_data        ( awb_O_tdata_128   ) // 输出：128 bit（3 个 128 = 4 个 96，凑齐 16 像素）",
        ");",
    ]),
}

# ---------------- 术语表 ----------------

GLOSSARY = [
    ("RTL", "用 Verilog 写出来的、能被综合成电路的那一层代码；不是 C 程序，是描述线路连法。" ),
    ("综合（syn）", "把 Verilog 翻译成「用哪些逻辑单元、怎么连」的网表，相当于把图纸变成零件清单。"),
    ("布线（phy）", "把网表里的单元真正摆到芯片上并连好线，两步合起来才出能烧的比特流。"),
    ("比特流（.bit）", "烧进 FPGA 的那串配置位；本工程固定 1 789 539 字节，所以只能比 md5 判断版本。"),
    ("LUT / LUT6", "芯片里最小的可编程查找表，一个 LUT6 能实现任意 6 输入 1 输出的逻辑；我们用了 16 400 个。"),
    ("DFF / 寄存器", "存 1 bit 的触发器，代表「记忆」；我们用了 12 092 个。流水线每打一拍就多一批 DFF。"),
    ("ERAM", "芯片里成块的片上存储器（每块 20 Kbit），用来放查找表或行缓存；共 108 块，我们用 51 块。"),
    ("DSP", "芯片里专门做乘法的硬核；共 40 个，我们用 10 个。乘法很贵，所以能移位就移位。"),
    ("Slice", "一小组 LUT 加触发器加连线资源的打包单位；报告里 `#slices` 和 `#lut6` 的分母相同但含义不同。"),
    ("WNS", "最差那条路径还剩多少时间余量。正数=能跑，负数=跑不到；我们 +104 ps 即 0.104 ns。"),
    ("约束（.sdc）", "告诉工具「时钟多快、哪两条路径不用查时序」的文件，工具靠它判断时序过不过。"),
    ("流水线", "把一件事拆成几拍做，每拍只做一小步；好处是每拍都能出新数据，代价是多等几拍。"),
    ("打一拍", "把一个信号用寄存器延后一个时钟周期；同步信号必须和数据一起打，否则错位。"),
    ("跨时钟域", "信号从一个时钟域的电路传给另一个不同频率的时钟域的电路；不能直接连，要加同步器。"),
    ("同步器", "连着两级触发器，用来把外来信号「稳」下来，防止采到一半变化的电平。"),
    ("MIPI", "手机摄像头常用的串行接口标准；本工程用 2 条差分线，所以叫 2-lane。"),
    ("差分信号", "一根线走高、另一根走低，靠两者之差表示 0/1；抗干扰强，速度快。"),
    ("AXI4-Stream", "一种「只管数据流、不管地址」的总线约定；四个关键信号 tdata/tvalid/tready/tlast。"),
    ("tvalid / tready", "「我有数据」/「我能收」；两个同时为 1 的那一拍才算真正传了一个数据。"),
    ("Bayer / BGGR", "传感器每个像素只感一种颜色，按 B-G-G-R 交错排；所以必须靠邻居插值补出三通道。"),
    ("去马赛克", "把「每像素只有一色」补成「每像素都有 R/G/B」这一步。"),
    ("白平衡 / 灰世界", "假设整幅画面平均下来应该是灰的，于是算出 R、B 该乘多少把它拉平。"),
    ("伽马 / S 曲线", "一条把输入亮度映射成输出亮度的曲线；S 形 = 压暗部提亮部，对比更强。"),
    ("查表（LUT 表）", "不现场算，而是事先把 256 种输入的答案写进存储器，来一个查一个。"),
    ("OSD", "On-Screen Display，叠在画面上的文字和框；本工程叠了 8 层。"),
    ("点阵字库", "每个字符用 16×16 个点表示，1 个点 1 bit，所以一个字占 16 个 16 位字。"),
    ("帧差法", "把这一帧和上一帧逐块相减，差得多的地方就认为有东西在动。"),
    ("块级处理", "不逐像素判，而是把画面切成 80×80 的格子、每格算一个平均值再判；省存储但精度粗。"),
]

FIG_ANCHORS = [
    ("fig1_datapath.png", "2.1 完整通路与每一级的职责", "图 1　视频数据通路：13 个模块与每一拍的位宽",
     "先看这张图，再看下面那张表——图给整体形状，表给每一级的细节。"),
    ("fig2_bitwidth.png", "2.2 三个必须记住的接口细节", "图 2　一拍的数据为什么一会儿 40bit、一会儿 128bit、又变成 96bit",
     "位宽反复变不是设计得啰嗦，是被「一拍 4 像素」这个前提逼出来的。"),
    ("fig3_isp.png", "3.1 为什么是这六个、为什么是这个顺序", "图 3　ISP 六个环节：顺序不能随便换",
     "图里每个方块下面的小字就是「为什么必须在这个位置」，比背顺序有用。"),
    ("fig4_blocks_osd.png", "6.1 三个算法的共同思路：不做全帧做块", "图 4　块级检测的「块」是怎么切的｜八层 OSD 的叠放顺序",
     "左边是运动检测的 144 个块怎么切；右边是八层 OSD 谁压谁。"),
]


# ---------------- 主流程 ----------------

def ptext(p):
    return "".join(n.text or "" for n in p._p.iter(qn("w:t")))


def strip_shading(p):
    pPr = p._p.find(qn("w:pPr"))
    if pPr is None:
        return
    for tag in ("w:shd",):
        e = pPr.find(qn(tag))
        if e is not None:
            pPr.remove(e)


def main():
    if os.path.exists(DOC):
        import shutil
        os.makedirs(os.path.dirname(BACKUP), exist_ok=True)
        shutil.copy2(DOC, BACKUP)
        print("备份 →", BACKUP)

    doc = Document(DOC)
    paras = doc.paragraphs
    txts = [ptext(p) for p in paras]
    n0 = len(paras)

    # ===== 1) 代码块完整化 =====
    done = []
    for mod, (a, b, lines) in BLOCKS.items():
        # 找 marker：▎...第 a~b 行（b==a 时是 a~a）
        idx = None
        for i, t in enumerate(txts):
            if t.startswith("▎") and ("第 %d~%d 行" % (a, b) in t or "第 %d~%d 行" % (a, a) in t):
                idx = i
                break
        if idx is None:
            print("  !! 找不到 marker:", mod, a, b)
            continue
        # marker 之后连续的灰底代码段（到 ▸ 之前）
        j = idx + 1
        code_idx = []
        while j < len(paras) and not txts[j].startswith("▸"):
            pPr = paras[j]._p.find(qn("w:pPr"))
            has_shd = pPr is not None and pPr.find(qn("w:shd")) is not None
            if has_shd or txts[j].strip() == "":
                code_idx.append(j)
                j += 1
            else:
                break
        if not code_idx:
            print("  !! 没有找到代码行:", mod)
            continue
        # 改 marker 的行号范围
        mp = paras[idx]
        for t in mp._p.iter(qn("w:t")):
            if t.text and "第 " in t.text:
                import re
                t.text = re.sub(r"第 \d+~\d+ 行", "第 %d~%d 行" % (a, b), t.text)
                break
        # 用新代码段替换掉旧的（插在第一个旧代码行之前，再删旧的）
        anchor = paras[code_idx[0]]
        prev = anchor._p
        for ln in lines:
            np_ = code_para(ln, size=8.0)
            prev.addnext(np_._p)
            prev = np_._p
        for k in code_idx:
            el = paras[k]._p
            el.getparent().remove(el)
        done.append("%s→%d 行" % (mod, len(lines)))

    print("代码块已完整化：", " | ".join(done))

    # ===== 2) 术语速查表 =====
    paras = doc.paragraphs
    txts = [ptext(p) for p in paras]
    anchor_i = None
    for i, t in enumerate(txts):
        if t.strip().startswith("第 0 章"):
            anchor_i = i
            break
    if anchor_i is None:
        print("  !! 找不到「第 0 章」，术语表未插入")
    else:
        # 在「第 0 章」之前插入：H2 标题 + 引言句式（用正文样式）+ 表格
        h = new_para("术语速查表（看不懂哪个词就回来查）", bold=True, size=12.5,
                     color="2E5C8A", indent=False, before=10, after=6)
        paras[anchor_i]._p.addprevious(h._p)

        intro = new_para("下面这些词在正文里第一次出现时我会顺手解释一句，但如果读到一半卡住了，回来扫一眼这张表最快。"
                         "按「它会出现在哪一章」大概排的序，不用背，混个眼熟就行。", indent=True, after=6)
        paras[anchor_i]._p.addprevious(intro._p)

        tbl = doc.add_table(rows=1, cols=3)
        tbl.style = "Table Grid"
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        tbl.autofit = False
        tblPr = tbl._tbl.tblPr
        lay = OxmlElement("w:tblLayout")
        lay.set(qn("w:type"), "fixed")
        tblPr.append(lay)
        widths = [Cm(2.6), Cm(2.6), Cm(10.8)]
        hdr = ["术语", "出现在哪", "一句话解释"]
        for i, hh in enumerate(hdr):
            c = tbl.rows[0].cells[i]
            c.width = widths[i]
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            r = OxmlElement("w:r")
            r.append(mkrpr(bold=True, size=9))
            t = OxmlElement("w:t")
            t.text = hh
            r.append(t)
            c.paragraphs[0]._p.append(r)
            set_cell_bg(c, "E8EEF6")
        CHAP = {
            "RTL": "1", "综合（syn）": "1", "布线（phy）": "1", "比特流（.bit）": "1",
            "LUT / LUT6": "1", "DFF / 寄存器": "1", "ERAM": "1", "DSP": "1",
            "Slice": "1", "WNS": "5", "约束（.sdc）": "5", "流水线": "5", "打一拍": "5",
            "跨时钟域": "5", "同步器": "5", "MIPI": "2", "差分信号": "2",
            "AXI4-Stream": "2", "tvalid / tready": "2", "Bayer / BGGR": "3", "去马赛克": "3",
            "白平衡 / 灰世界": "3", "伽马 / S 曲线": "3", "查表（LUT 表）": "4",
            "OSD": "7", "点阵字库": "7", "帧差法": "6", "块级处理": "6",
        }
        for term, expl in GLOSSARY:
            row = tbl.add_row()
            for i, val in enumerate([term, "第 %s 章" % CHAP.get(term, "—"), expl]):
                c = row.cells[i]
                c.width = widths[i]
                if i == 1:
                    c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                r = OxmlElement("w:r")
                r.append(mkrpr(bold=(i == 0), size=9))
                t = OxmlElement("w:t")
                t.set(qn("xml:space"), "preserve")
                t.text = val
                r.append(t)
                c.paragraphs[0]._p.append(r)
        # 表格插到 anchor 之前
        paras[anchor_i]._p.addprevious(tbl._tbl)
        # 表后补一个空段，避免表格紧贴下一个标题
        gap = new_para("", indent=False, after=2)
        paras[anchor_i]._p.addprevious(gap._p)
        print("术语速查表已插入，%d 条" % len(GLOSSARY))

    # ===== 3) 插图 =====
    paras = doc.paragraphs
    for fn, anchor_title, caption, lead in FIG_ANCHORS:
        path = os.path.join(FIG, fn)
        if not os.path.exists(path):
            print("  !! 缺图:", fn)
            continue
        # 找到 anchor 标题段之后的第一个正文段（用来插在它后面）
        idx = None
        for i, p in enumerate(paras):
            if ptext(p).strip().startswith(anchor_title.split(" ")[0]) and anchor_title[:6] in ptext(p):
                idx = i
                break
        if idx is None:
            # 退化：按标题前 10 字找
            for i, p in enumerate(paras):
                if anchor_title[:10] in ptext(p):
                    idx = i
                    break
        if idx is None:
            print("  !! 找不到插图锚点:", anchor_title)
            continue
        # 句子 → 图 → 图注
        p_lead = new_para(lead, indent=True, after=4)
        p_pic = doc.add_paragraph()
        p_pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_pic.paragraph_format.space_before = Pt(4)
        p_pic.paragraph_format.space_after = Pt(2)
        p_pic.add_run().add_picture(path, width=Cm(15.6))
        p_cap = new_para(caption, size=9, color="595959", indent=False, after=10, align="center")
        paras[idx]._p.addnext(p_cap._p)
        paras[idx]._p.addnext(p_pic._p)
        paras[idx]._p.addnext(p_lead._p)
        print("已插图：", fn)

    doc.save(DOC)
    print("完成 →", DOC, os.path.getsize(DOC), "B")


if __name__ == "__main__":
    main()
