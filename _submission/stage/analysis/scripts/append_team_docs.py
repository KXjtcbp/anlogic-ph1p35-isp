# -*- coding: utf-8 -*-
"""给成员 B / C 的两份上手指南【补充章节】。

补齐第一次遗漏的四类内容（全部逐条对照代码/文件核实过，未确认的不写）：
  1. 构建怎么做、以及「什么才算构建成功」（本项目最容易踩的假成功）
  2. 两行橙色遥测的逐字段定义（板上唯一的调试窗口）
  3. 34 个发布版本与回滚路径
  4. 当前仍未解决的问题清单
  5. 各自改代码前必须知道的三个接口契约
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from docx import Document
from docx.shared import Pt, Cm
from docx.oxml.ns import qn


def set_run(run, size=11, bold=False):
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def H(d, text, size=14, before=12, after=5):
    p = d.add_paragraph()
    p.paragraph_format.space_before = Pt(before)
    p.paragraph_format.space_after = Pt(after)
    set_run(p.add_run(text), size, bold=True)


def H2(d, text, size=12, before=9, after=4):
    H(d, text, size, before, after)


def P(d, text, size=11, indent=True, after=4):
    p = d.add_paragraph()
    p.paragraph_format.line_spacing = 1.4
    p.paragraph_format.space_after = Pt(after)
    if indent:
        p.paragraph_format.first_line_indent = Pt(size * 2)
    set_run(p.add_run(text), size)


def BUL(d, text, size=11):
    p = d.add_paragraph()
    p.paragraph_format.line_spacing = 1.35
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.left_indent = Pt(size)
    set_run(p.add_run("· " + text), size)


def TABLE(d, rows, widths=None, size=9):
    t = d.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, txt in enumerate(row):
            c = t.cell(i, j)
            c.text = ""
            p = c.paragraphs[0]
            p.paragraph_format.line_spacing = 1.1
            p.paragraph_format.space_after = Pt(0)
            set_run(p.add_run(txt), size, bold=(i == 0))
    if widths:
        for j, w in enumerate(widths):
            for i in range(len(rows)):
                t.cell(i, j).width = Cm(w)
    return t


# ---------- 两篇共用 ----------
def sec_build(d):
    H(d, "7  构建：怎么跑，以及什么才算「成功」")
    P(d, "本项目最容易踩的坑不是代码写错，而是「构建看起来成功了、但功能根本没进去」。"
         "请务必按下面的顺序判断。")
    H2(d, "7.1  命令")
    BUL(d, "完整的 syn + phy 流程：在仓库根执行 "
           "Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass -Force 然后 "
           "& \"E:\\FPGA\\_analysis\\misc\\td_run_direct.ps1\" syn_1 phy_1。约 10~15 分钟。")
    BUL(d, "只做语法/elaboration 检查：python _analysis\\scripts\\compile_check.py，基线是 42/43。")
    BUL(d, "★不要用 Start-Process 起 TD★——实测会卡死在 phy_1 之前，进程活着但没有任何输出，"
           "而 route.qor 与 .bit 仍是上一次的旧产物，看起来像「构建没跑完」。必须用普通后台任务。")
    H2(d, "7.2  ★判断成功的四个必要判据（缺一不可）★")
    TABLE(d, [
        ["判据", "怎么查", "不满足说明什么"],
        ["没有黑盒报错",
         "在 _analysis\\td_direct_syn_1.log 与 td_direct_phy_1.log 里搜 HDL-8007 / black box，必须为 0 条",
         "新加的 .v 没进 run 目录的 .prj。.bit 时间戳照样会刷新，这是假成功"],
        ["模块真的在网表里",
         "在 phy_1\\camera_to_dsi_display_phy.area 和 syn_1\\camera_to_dsi_display_gate.area 里按实例名（如 u_obj_detect）搜，必须命中",
         "模块被综合工具当冗余删掉了。资源反而会下降，没有任何报错"],
        ["时序收敛",
         "phy_1\\route.qor：Setup WNS > 0、TNS = 0、违例 S-EP = 0；Hold 同理",
         "WNS 掉到 +2 ps 这种也算「0 违例」但极危险，余量不足 50 ps 就要警惕"],
        ["功能指标没漂",
         "phy_1\\camera_to_dsi_display_phy.area 的 #RAMs 应为 51、#DSPs 应为 10",
         "数字不对说明某条链路被优化掉了或接错了"],
    ], widths=[2.6, 7.6, 4.4])
    P(d, "★一句话记法：.bit 的时间戳变新 ≠ 构建成功。必须同时看日志、看网表、看 route.qor。★")
    H2(d, "7.3  新增一个 .v 文件的完整步骤")
    P(d, "这是最容易出错的地方，四步缺一不可，而且 TD 跑完会按自己的内部状态回写 .al，所以顺序很重要：")
    BUL(d, "① 把 .v 放进 proj\\baseline\\lab3\\user_source\\hdl_source\\ 下对应子目录。")
    BUL(d, "② 写进 td_project\\camera_to_dsi_display.al（TD 图形界面读的那份）。")
    BUL(d, "③ 同时写进两个 run 目录的 .prj：td_project\\camera_to_dsi_display_Runs\\syn_1\\ "
           "与 \\phy_1\\ 下的 camera_to_dsi_display.prj。★TD 命令行只认 .prj，不认 .al★。")
    BUL(d, "④ 构建完之后再查一次 .al，确认第 ② 步的条目还在（TD 可能把它覆盖回去）。")
    P(d, "仓库里已有现成脚本可参考：_analysis\\scripts\\patch_prj_add_lsc.py、patch_prj_add_wbrecip.py、"
         "add_obj_to_filelist.py，都是干这件事的。")


def sec_telemetry(d):
    H(d, "8  两行橙色遥测怎么读（板上唯一的调试窗口）")
    P(d, "板子上没有串口打印，所有运行期状态都靠画面上这两行 19 字符的橙色文字。"
         "它们的位置在 1280×720 内部坐标的 (376,152) 与 (376,164)，换算到 1920×1080 的屏幕坐标要 ×1.5。")
    H2(d, "8.1  第 1 行：AE / 亮度 / 白平衡增益")
    P(d, "格式：AE<gi2>S<st1>M<ml2>W<gr4>B<gb4>，例：AE2E S2 M3B W158B B1B6E", indent=False)
    TABLE(d, [
        ["字段", "位数", "含义", "怎么换算"],
        ["AE", "固定标签", "就是个标记，不含数值", "—"],
        ["gi", "2 位十六进制", "AE 的 7bit 单调增益索引，0~127", "0=1.000×，127=15.750×；"
                                                                 "粗档 {0x03,0x07,0x0F,0x1F}=×1/×2/×4/×8，"
                                                                 "细档 0x20~0x3F = ×1.000~×1.969"],
        ["S", "1 位十进制", "AE 状态机状态", "0=等 init 表 / 1=稳定计时 / 2=闭环 / 3=冻结"],
        ["M", "2 位十六进制", "曲线之前的整帧亮度均值", "直接就是 0~255 的码值"],
        ["W", "4 位十六进制", "AWB 施加的 R 增益", "÷4096 = 倍率。0x1000 = 1.000×，0x158B = 1.346×"],
        ["B", "4 位十六进制", "AWB 施加的 B 增益", "同上"],
    ], widths=[1.5, 2.6, 5.0, 7.0])
    H2(d, "8.2  第 2 行：AE 决策链的中间变量")
    P(d, "格式：F<can><frm><req><aec><cam>T<settle2>N<next2>D<dec2>U<inc2>，"
         "前 5 个是 0/1 标志位，后 4 个是两位十六进制数。", indent=False)
    BUL(d, "can = 是否可以动作（稳定期结束且帧有效）；frm = 本帧统计是否有效；"
           "req = 是否有待发的寄存器请求；aec = AE 表配置是否完成；cam = 摄像头 init 表是否下载完。")
    BUL(d, "T = 稳定计时器当前值；N = 下一档增益索引；D = 若降档会到多少；U = 若升档会到多少。")
    P(d, "★读数值要小心★：小字号下 '7' 和 '2' 很容易看错（'7' 的顶行是满宽 5 格、'2' 的顶行是 01110）。"
         "本项目曾经把 gi=0x7F 误读成 0x2E，导致在「AE 不动作」这个假问题上花了好几个小时。"
         "关键数值请放大截图，或者直接用 8.3 的方法交叉验算。")
    H2(d, "8.3  交叉验算（防读错）")
    P(d, "U 与 D 必须满足：U = min(127, gi + step)、D = max(0, gi − step)，step ≤ 8。"
         "如果你读出的 gi、U、D 三者凑不出这个关系，那就是字号看错了，不是 RTL 错。")


def sec_versions(d):
    H(d, "9  版本与回滚")
    P(d, "proj/releases/ 下现有 34 个版本目录，每个都含 .bit、压缩版 .bit、route.qor、"
         "camera_to_dsi_display_phy.area 与 readMe.txt。")
    P(d, "★所有 .bit 的大小都恰好是 1 789 539 字节★，所以「大小对」不能证明「版本对」，"
         "必须比 md5。烧录前一定要核对 md5。", indent=False)
    TABLE(d, [
        ["用途", "目录", "bit md5"],
        ["★当前交付版★", "2026-10-18_a2_hold60", "DB39A5CE50591330A6D6E9C0CFCFB2E3"],
        ["已知良好，可回滚", "2026-10-18_a2_hold（保持窗口 8 帧版）", "8F17896E045B770AECE1E0AA75CA692C"],
        ["已知良好，可回滚", "2026-10-17_baseline_p0_closed（闭环最干净的基线）", "6CB52C8463FB6E96A7EC7DE69AE6E754"],
        ["★不要用★", "2026-10-18_a2_hold60_fix9", "04942553…（WNS 掉到 +2 ps，已回退）"],
        ["原厂基线", "lab3_vendor_2026-09-10", "B12FF9AE…（未改过的官方例程）"],
    ], widths=[3.2, 7.4, 4.4])
    P(d, "板子烧坏了怎么救：先烧一个「已知良好」的版本确认硬件没坏，再回去查自己改的东西。"
         "烧完必须拔电 5 秒重新上电（不是按复位键），因为摄像头 init 表与传感器状态只在冷启动时重来。")


def sec_open(d):
    H(d, "10  当前仍未解决的问题")
    P(d, "以下都是截至 2026-10-20 的真实状态，不是「待办猜测」：")
    TABLE(d, [
        ["编号", "问题", "当前状态", "影响"],
        ["1", "R/B 相对 G 有约 2~3 码的固定负偏置（与亮度无关）",
         "亮场景已进 0.98~1.02 验收带；暗场景仍会偏绿。归属未定案",
         "画面暗时偏绿；不阻塞交付"],
        ["2", "目标检测只支持「红色」一种颜色特征",
         "16×9 块级 + 两帧确认 + 孤立块滤除 + 60 帧保持，已上板验收通过",
         "换别的颜色需要改 obj_detect.v 的三个阈值参数"],
        ["3", "运动检测对「整幅画面突然变暗」不敏感",
         "块均值同时下降时块间差异拉不开，属算法固有特性，不是 bug",
         "现场开关灯不会误报，但也检测不到"],
        ["4", "OSD 画面顶部第 0~3 行有品红瞬态",
         "1080 行里坏 3 行，一直存在，未定位到具体模块",
         "可忽略；1080 行里 3 行"],
        ["5", "QSPI 固化未做",
         "板载 N25Q128 就是配置 Flash，用 TD 的 Program Flash 写入即可，不需要写 RTL 加载器；但尚未执行",
         "★竞赛硬性要求：最终设计必须上电即可运行★，这是通过/不通过级别"],
        ["6", "报告仍缺实物照片、系统框图以外的插图、心得正文",
         "框图已插入（图 1）；实物照片与心得需负责人本人提供",
         "影响报告完整性，不影响设计本身"],
    ], widths=[1.0, 4.6, 6.0, 3.6])
    P(d, "时间节点：竞赛要求在 11-04 前提交电子版材料。当前阶段以「把功能做完、做稳」优先，"
         "QSPI 固化与实物录像排在最后。")


# ---------- B 专属 ----------
def sec_b_contract(d):
    H(d, "11  你改代码前必须知道的三个契约")
    H2(d, "11.1  96bit 数据流的字节序")
    P(d, "ISP 域一拍是 4 个像素、每像素 24bit，共 96bit。四个像素在总线上的排列是：")
    P(d, "p0r = I_tdata[23:16]、p0g = I_tdata[15:8]、p0b = I_tdata[7:0]；"
         "p1 整体 +24bit，即 p1r = [47:40]、p1g = [39:32]、p1b = [31:24]；p2、p3 依次 +48、+72。",
      indent=False)
    P(d, "代码里能看到对应写法（awb.v:151-163 用的是 I_tdata_d0[16+:8] 这种形式，等价）。"
         "★如果字节序搞反，R 和 B 会互换，所有颜色结论都会变成假的偏色，而且很难从画面上看出来。★")
    H2(d, "11.2  awb.v 的四个关键常量")
    TABLE(d, [
        ["位置", "写法", "含义", "改它的后果"],
        ["awb.v:184~196", "rgb_sum[n] < 720", "白点排除：四个像素各自的 R+G+B 超过 720 就不参与累加",
         "调低会更容易被高光带偏；调高会把高光纳入统计"],
        ["awb.v 累加初值", "sum_r / sum_g / sum_b 初值 = 1", "避免除零", "改成 0 会在帧首除零，增益饱和"],
        ["awb.v 增益复位值", "20'h10000", "Q16 定点的 1.000×", "改成别的会让 AWB 从非 1.0 起步"],
        ["awb.v 增益饱和", "20'hfffff", "增益上限（约 8.0×）", "改小会限制可校正范围；改大可能溢出乘法器"],
    ], widths=[3.0, 3.0, 5.0, 4.2])
    H2(d, "11.3  lsc.v 的坐标映射")
    P(d, "lsc 的表是 20 列 × 12 行 = 240 个节点，每个节点存 {kR[9:0], kB[9:0]} 共 20bit。映射关系：")
    BUL(d, "水平方向：S_hidx = S_bx[8:4]。S_bx 是「拍计数」，一拍 4 像素，所以 16 拍 = 64 个内部像素"
           "（= 屏幕 96 像素）对应一个节点。")
    BUL(d, "垂直方向：S_vidx = S_y[11:6]。每 64 行（= 屏幕 96 像素）对应一个节点。")
    BUL(d, "节点内做双线性插值：S_fx = S_bx[3:0]（拍内 16 等分）、S_fy = S_y[5:2]（行内 16 等分）。")
    BUL(d, "增益公式：g = 1 + k/1024，施加方式是 out = v + ((v*k) >> 10)，再饱和到 255。"
           "K_MAX = 1023，所以单点最大增益约 2.0×。")
    P(d, "★坐标是 1280×720 的内部坐标系，不是屏幕的 1920×1080★。"
         "做软件对照实验时一定要按 96 屏幕像素一个节点去切，否则会把节点边界算错。")

    H(d, "12  建议的下一步")
    P(d, "按这个顺序做，每一步都能独立验证：")
    BUL(d, "先跑通仿真：_analysis\\sim\\awb\\ 下的 tb，确认能复现「输入 R/G=0.800 → 输出 R/G=1.0000」。")
    BUL(d, "再跑 compile_check，确认 42/43。这一步能挡住绝大部分语法问题。")
    BUL(d, "然后改一小处、跑一次完整构建、按 §7.2 的四个判据验一遍。不要攒着一起改。")
    BUL(d, "最后把结论写成「哪个文件、哪一行、为什么」，交给负责人上板验证。你没有板子，"
           "所以任何改动都必须先自证到「逻辑上成立 + 仿真通过 + 构建通过」这三条。")


# ---------- C 专属 ----------
def sec_c_contract(d):
    H(d, "11  你改代码前必须知道的三个契约")
    H2(d, "11.1  OSD 字模的格式（osd_char_lib.v）")
    P(d, "字库是纯组合 ROM，3 个端口：I_char[7:0] 字符编码、I_row[3:0] 行号（0~15）、"
         "O_row_bits[15:0] 该行的 16 位点阵。")
    BUL(d, "字模是 16 列 × 16 行，字形实际只占左侧约 12 列、上方约 13 行，其余补 0。")
    BUL(d, "★bit15 对应最左列，bit0 对应最右列★，即「高位在左」。例：16'h1c00 表示 bit12~bit10 亮，"
           "也就是第 3~5 列。")
    BUL(d, "★没有小写字母★。参数行里需要 x 的地方一律写大写 X（8'h58）。")
    BUL(d, "现在共 41 个字符：A~Z、0~9、冒号、连字符、小数点，外加两个自定义编码 8'h80（安）、"
           "8'h81（路）。加新字符要三步：加一个 localparam、在 8.1 节的外层 case 里加一个分支、"
           "在内层 case(I_row) 里写 16 行行码。")
    BUL(d, "★注意★：hdmi_mixer.v 里另有一份内容相同的 function F_osd_char16_row（约 535~632 行），"
           "但实际取模走的是 osd_char_lib 这个模块。改字模改模块那份，别只改 function。")
    H2(d, "11.2  加一个 OSD 图层要动哪几处（hdmi_mixer.v）")
    BUL(d, "① 顶层端口：加你需要的输入信号。")
    BUL(d, "② localparam：加窗口坐标（X/Y/W/H）与颜色。★注意所有窗口用的是 1280×720 内部坐标★。")
    BUL(d, "③ 打拍同步：跨时钟域进来的信号要打两拍（参考现有的 S_par_sw_1d/2d）。")
    BUL(d, "④ 字符预译码：把要显示的字符码提前算好，放进 reg。★窗口宽度超过 256 像素时，"
           "字符索引必须用 5bit，用 4bit 会回卷★（参数行就是 512 宽，踩过这个坑）。")
    BUL(d, "⑤ 图层判定：插到优先级链里。现有优先级从高到低是 Logo → CNT → MODE → 遥测1 → 遥测2 → "
           "参数行 → 运动框 → 目标框，命中即停止。")
    BUL(d, "⑥ 字符 mux：把新图层的字符送进唯一那份 osd_char_lib 例化的输入选择里。")
    P(d, "★加图层几乎不额外占 ERAM★，因为所有图层共用一份字符 ROM，靠时分复用切换。"
         "但每加一层都要增加 144bit 掩码那条紧张路径上的逻辑，而本项目 slice 已经到 82%，"
         "所以★改完必须看 route.qor 的 Setup WNS★。曾经有一次只是把一个组合信号改成寄存器输出，"
         "WNS 就从 +104 ps 掉到 +2 ps。")
    H2(d, "11.3  S 曲线表的生成与写入")
    P(d, "曲线表是 256 行内联在 isp_gamma.v 里的 Verilog 赋值（mem_b00[0] = 8'h00; 这种形式）。"
         "★绝对不能用 $readmemh★——TD 的综合工作目录在 run 目录下，相对路径会静默读不到，"
         "表全变 0，上板全黑，而所有报告都是正常的。")
    P(d, "仓库里现成的脚本：")
    BUL(d, "_analysis\\scripts\\gen_gamma_lut_toe.py（8974 B）—— 生成曲线的 Python 实现，"
           "改锚点/指数改这里。")
    BUL(d, "_analysis\\scripts\\patch_gamma_inline.py（4291 B）—— 把生成的表写进 isp_gamma.v 的内联赋值。")
    BUL(d, "_analysis\\scripts\\gen_tb_gamma.py（5304 B）—— 重新生成 TB 里 `include 的 .vh 文件。"
           "★改表不同步改 .vh，会出现几百个假 FAIL★。")
    P(d, "流程：改 gen_gamma_lut_toe.py 的参数 → 跑它生成 .hex → 跑 patch_gamma_inline.py 写进 RTL → "
         "跑 gen_tb_gamma.py 更新 .vh → 跑 TB → compile_check → 构建。")

    H(d, "12  建议的下一步")
    P(d, "按这个顺序做，每一步都能独立验证：")
    BUL(d, "先跑 tb_gamma_bp.v，确认能复现当前的表（14 个锚点：0→0, 1→0, 2→0, 4→1, 8→4, 16→11, "
           "32→25, 64→57, 96→92, 128→128, 160→163, 192→196, 224→228, 255→255）。")
    BUL(d, "再通读 hdmi_mixer.v 的图层判定链与字符 mux，把「加一层要动哪六处」在纸上标出来。")
    BUL(d, "报告同步：报告里的所有数值都要能在 phy_1\\route.qor 与 camera_to_dsi_display_phy.area 里核对到。"
           "改完代码后先查这两个文件，再改报告，不要凭记忆。")
    BUL(d, "任何改动都必须先自证到「逻辑上成立 + 仿真通过 + 构建通过」三条，再交给负责人上板。")


def append_doc(path, sections):
    d = Document(path)
    for fn in sections:
        fn(d)
    d.save(path)
    print("已补充:", path, os.path.getsize(path), "B")


def main():
    base = [sec_build, sec_telemetry, sec_versions, sec_open]
    fb = r"E:\FPGA\给成员B_项目上手指南_20261020.docx"
    fc = r"E:\FPGA\给成员C_项目上手指南_20261020.docx"
    append_doc(fb, base + [sec_b_contract])
    append_doc(fc, base + [sec_c_contract])


if __name__ == "__main__":
    main()
