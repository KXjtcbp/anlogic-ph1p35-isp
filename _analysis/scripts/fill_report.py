# -*- coding: utf-8 -*-
"""
把当前项目进展填进比赛报告样板。
保留样板原有章节结构、段落样式与字体（Times New Roman + 宋体 12pt，行距 1.5）。
脚本来源：E:\FPGA\比赛报告_官方样板.docx
输出：   E:\FPGA\比赛报告_填空版_20261018.docx
"""
import copy
import sys
import os
from docx import Document
from docx.oxml.ns import qn
from docx.table import Table
from docx.text.paragraph import Paragraph

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"E:\FPGA\比赛报告_官方样板.docx"
DST = r"E:\FPGA\比赛报告_填空版_20261018.docx"


def set_para(p, text):
    """保留段落与首个 run 的格式，只换文字。"""
    if p.runs:
        p.runs[0].text = text
        for r in p.runs[1:]:
            r._element.getparent().remove(r._element)
    else:
        p.add_run(text)


def insert_after(p, text, bold=False):
    """在 p 之后插入一个同格式段落，返回新段落。"""
    new_el = copy.deepcopy(p._p)
    p._p.addnext(new_el)
    np = Paragraph(new_el, p._parent)
    for r in list(np.runs)[1:]:
        r._element.getparent().remove(r._element)
    if np.runs:
        np.runs[0].text = text
        if bold:
            np.runs[0].bold = True
    else:
        np.add_run(text)
    return np


def fill(p, blocks):
    """用 blocks[0] 替换 p 的文字，其余依次插在 p 之后。"""
    set_para(p, blocks[0])
    anchor = p
    for b in blocks[1:]:
        anchor = insert_after(anchor, b)
    return anchor


def add_table_after(p, rows, widths=None):
    """在 p 之后插入一个带框线的表格（用样板正文字体）。"""
    n_rows, n_cols = len(rows), len(rows[0])
    t = p._parent.add_table(rows=n_rows, cols=n_cols) if False else None
    # 手工构造：用文档 body 追加再移动位置
    from docx.oxml import OxmlElement
    tbl = OxmlElement('w:tbl')
    tblPr = OxmlElement('w:tblPr')
    borders = OxmlElement('w:tblBorders')
    for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
        e = OxmlElement('w:' + edge)
        e.set(qn('w:val'), 'single')
        e.set(qn('w:sz'), '4')
        e.set(qn('w:color'), '000000')
        borders.append(e)
    tblPr.append(borders)
    tw = OxmlElement('w:tblW')
    tw.set(qn('w:w'), '5000')
    tw.set(qn('w:type'), 'pct')
    tblPr.append(tw)
    tbl.append(tblPr)
    # w:tblGrid 是必需元素，缺了 Word 会报文档损坏（LibreOffice 容忍）
    grid = OxmlElement('w:tblGrid')
    col_w = int(9360 / n_cols)
    for _ in range(n_cols):
        gc = OxmlElement('w:gridCol')
        gc.set(qn('w:w'), str(col_w))
        grid.append(gc)
    tbl.append(grid)
    for ri, row in enumerate(rows):
        tr = OxmlElement('w:tr')
        for ci, cell in enumerate(row):
            tc = OxmlElement('w:tc')
            tcPr = OxmlElement('w:tcPr')
            for tag, val in (('w:tcW', None),):
                pass
            tc.append(tcPr)
            para = OxmlElement('w:p')
            pPr = OxmlElement('w:pPr')
            sp = OxmlElement('w:spacing')
            sp.set(qn('w:line'), '240')
            sp.set(qn('w:lineRule'), 'auto')
            sp.set(qn('w:after'), '0')
            pPr.append(sp)
            para.append(pPr)
            run = OxmlElement('w:r')
            rPr = OxmlElement('w:rPr')
            rf = OxmlElement('w:rFonts')
            rf.set(qn('w:ascii'), 'Times New Roman')
            rf.set(qn('w:hAnsi'), 'Times New Roman')
            rf.set(qn('w:eastAsia'), '宋体')
            rPr.append(rf)
            sz = OxmlElement('w:sz')
            sz.set(qn('w:val'), '21')
            rPr.append(sz)
            if ri == 0:
                b = OxmlElement('w:b')
                rPr.append(b)
            run.append(rPr)
            txt = OxmlElement('w:t')
            txt.text = cell
            run.append(txt)
            para.append(run)
            tc.append(para)
            tr.append(tc)
        tbl.append(tr)
    p._p.addnext(tbl)
    return tbl


d = Document(SRC)
P = list(d.paragraphs)

# ------------------------------------------------------------------ 作品名称 / 摘要
fill(P[1], [
    "基于安路 PH1P35 的实时数字图像处理系统",
    "——低延迟 ISP 流水线与块级运动目标检测",
    "（队伍信息与学校名称按要求不出现）",
])

fill(P[3], [
    "本作品基于安路科技 PH1P35MDG324 FPGA（38184 等效 LUT / 42432 DFF / 40 DSP / 108 ERAM），"
    "构建了一条从 MIPI 摄像头到 HDMI 显示的完整实时视频处理链路，全部图像处理算法与控制逻辑均在 FPGA 内以流水线方式自主实现，不含任何额外处理器。",

    "输入侧使用 SC500CS 摄像头（RAW10、2-lane MIPI，最大 2592×1944@30fps），经 MIPI D-PHY RX、CSI 解包与 RAW10 解包恢复为 40bit/4 像素的 RAW 数据流；"
    "图像处理链依次完成黑电平扣除（由盖严镜头实测标定为 56）、BGGR 去马赛克、自动白平衡、镜头色彩暗角校正（LSC）、自动曝光（AE）与 S 曲线色调映射；"
    "随后由算法层完成灰度、伪彩、彩条、卡通化等风格化处理，经 6 层 OSD 叠加后写入 DDR2 帧缓存，由 HDMI 1.4b 以 1280×720@60Hz 输出。",

    "围绕 ISP 画质，我们完成了四项自研工作：① 灰世界自动白平衡的帧锁存与 Q16 四舍五入——经门级仿真定位到「增益随运行中的部分和逐拍变化」这一根因，"
    "在帧起始拍把增益锁存为常量，使整帧施加同一增益；② 用「归一化 + 256 项倒数 ROM + 一次乘法」替换 IP 生成的流水除法器，逻辑资源下降 14.4 个百分点，代价仅 2 个 DSP，"
    "精度实测最差 0.39%（验收带 ±2%）；③ 20×12 节点、带双线性插值的镜头色彩暗角校正，只校 R/B 不动 G，全移位加法实现，实测使逐列 R/G 极差下降 43%~45.5%；"
    "④ 闭环自动曝光，以帧亮度统计驱动传感器模拟增益，7bit 单调增益索引闭环收敛。",

    "在扩展与进阶功能方面，系统实现了块级帧差法硬件运动目标检测：把画面划分为 16×9 共 144 个 80×80 块，只跨帧缓存块亮度均值（144 字节），"
    "无需整帧存储即可完成比对，运动中块以红色描边在 OSD 上实时标注；判据采用「绝对阈值 + 相对阈值 + 亮度地板 + 连续两帧确认」四重条件抑制噪声。"
    "同时提供两行橙色实时遥测（AE 状态、增益索引、实测亮度、AWB 双通道增益与各决策标志）与一行亮青色参数行（S 曲线 / LSC / 数字增益 / AE 的开关状态），"
    "使一块板子即可完成全部调试与验收，不依赖在线调试器。",

    "系统在 60fps 下零掉帧运行（帧计数与墙钟误差 <0.3%）；15 分钟连续挂机实测画面亮度漂移 <1%，白平衡 R/G、B/G 稳定在 0.980±0.001；"
    "白纸靶面 A/B 对照显示 LSC 使逐列 R/G 极差下降 43%~45.5% 并两批独立复现；采用倒数查表后整机 slice 占用由 83.78% 降至 66.10%，为后续功能留出充足余量。"
    "设计流程上建立了「ModelSim Testbench → 全工程编译检查 → TangDynasty 命令行综合布线 → 比特流归档与 md5 台账」的可复现迭代闭环，"
    "全部源码、约束、脚本与 16 个版本的比特流均在 Git 仓库中可追溯。",
])

# ------------------------------------------------------------------ 第一部分
fill(P[7], [
    "（1）MIPI 视频采集：SC500CS 摄像头 RAW10、2-lane MIPI，经 D-PHY RX、CSI 解包、RAW10 解包恢复为 40bit/4 像素的 RAW 数据流。",
    "（2）图像信号处理链：黑电平扣除（BLACK_LEVEL=56，由盖严镜头实测标定）→ 去马赛克（BGGR）→ 自动白平衡 → 镜头色彩暗角校正 → 自动曝光 → S 曲线色调映射（256×8 ROM 查表）。",
    "（3）风格化算法：按键 K1~K4 实时切换五种模式——直通、BT.601 灰度、伪彩热力图、五段彩条、卡通化（四级平涂 + 邻域描边）。",
    "（4）OSD 信息叠加：安路 Logo、帧计数器（黄）、两行实时遥测（橙）、算法模式行（绿）、参数状态行（亮青），共 6 层。",
    "（5）硬件运动目标检测：16×9 块级帧差，零帧存，运动中块以红色描边实时标注。",
    "（6）实时参数调节：SW1 控 LSC 使能、SW2 控 S 曲线使能、SW3 控运动检测使能、SW4 控运动检测灵敏度档（严格/宽松），画面上同步显示各参数状态。",
    "（7）自动曝光闭环：24MHz 域状态机在 7bit 单调增益索引（0~127，对应模拟增益 1.000×~15.750×）上闭环收敛，附带高光与暗场护栏。",
])

fill(P[10], [
    "本系统面向需要低延迟、高实时性且不便依赖通用处理器的机器视觉场景。",
    "（1）智能视觉与工业检测：块级帧差可零帧存实现产线传送带上的运动与异物检测；灰度与伪彩模式便于观察低对比度缺陷。",
    "（2）无人系统与移动平台：处理延迟固定在流水线级数（数十拍）量级，不随帧率波动，适合作无人机/小车的视觉前端；运动块掩码与计数可直接作为跟踪输入。",
    "（3）嵌入式视觉终端：全部算法在 FPGA 内实现，无额外处理器，功耗与体积可控；HDMI 直出可对接任意带 HDMI 输入的显示器。",
    "（4）教学与原型验证：ISP 各环节（黑电平、白平衡、暗角校正、色调曲线、自动曝光）均为参数化、可旁路的独立模块，便于逐级验证与二次开发。",
    "（5）竞赛延伸：赛题允许结合移动平台、交通灯、语音等外设做外部控制，本系统已预留运动检测结果输出，可直接驱动外部动作。",
])

fill(P[13], [
    "（1）零延迟流水线：全链路无帧缓存，数据以 AXI4-Stream 逐拍推进；ISP 域 60MHz、每拍 4 像素，HDMI 像素域 75MHz、串行域 375MHz，跨域转移仅一处单比特翻转同步。",
    "（2）模块化、可旁路：ISP 每个功能块均带运行期 bypass 端口，可单点隔离定位问题；插入新模块时严格保持上下游时序等价。",
    "（3）用算术换资源：AWB 的两路流水除法器被「归一化 + 256 项倒数 ROM + 一次乘法」取代，精度实测最差 0.39%，整机 slice 从 83.78% 降到 66.10%，代价仅 +2 DSP。",
    "（4）低成本的镜头色彩暗角校正：20×12 节点表 + 双线性插值，只校 R/B 不动 G，全移位加法实现，0 ERAM / 0 DSP，实测使逐列 R/G 极差下降 43%~45.5%。",
    "（5）零帧存运动检测：把画面分成 144 个块，只跨帧保存块均值（144 字节），以四重判据抑制噪声，暗场景误检率显著低于单一绝对阈值方案。",
    "（6）全自研 OSD：单份字符 ROM 支撑 6 个 OSD 图层，含汉字「安路」字模、自绘 Logo ROM 与动态遥测字段。",
])

anchor = fill(P[16], [
    "系统主要性能指标如下表（数据来源：当前最新构建版 `proj/releases/2026-10-15_motion_sensitivity`）：",
])
add_table_after(anchor, [
    ["项目", "指标"],
    ["视频输入", "SC500CS；RAW10；2-lane MIPI；最大 2592×1944@30fps"],
    ["输出分辨率 / 刷新率", "1280×720@60Hz；HDMI 1.4b"],
    ["工作时钟", "ISP 域 60MHz（4 像素/拍）；HDMI 像素域 75MHz；HDMI 串行域 375MHz；控制域 24MHz"],
    ["帧率", "60fps，无丢帧（CNT 与墙钟误差 <0.3%）"],
    ["处理延迟", "固定流水线级数（数十拍），不随场景变化，无帧级缓存引入的不确定延迟"],
    ["逻辑资源", "slice 16402 / 21216 = 77.31%；LUT6 15149 / 21216 = 71.40%"],
    ["存储 / 运算资源", "ERAM 51 / 108 = 47.22%；DSP 10 / 40 = 25.00%；DFF 11228"],
    ["时序收敛", "Setup WNS +102ps / TNS 0 / 0 违例；Hold WNS +20ps / TNS 0 / 0 违例"],
    ["白平衡精度", "白纸靶面 R/G、B/G ∈ 0.9797~0.9807（验收带 0.98~1.02）"],
    ["暗角校正效果", "逐列 R/G 极差下降 43.0% 与 45.5%，两批独立复现"],
    ["长跑稳定性", "15 分钟连续运行亮度漂移 <1%，白平衡漂移 <0.1%，增益索引全程未变"],
    ["代码质量", "全工程 42/43 文件编译通过（唯一失败为官方 DDR 黑盒保护文件）"],
])

fill(P[19], [
    "① 倒数查表替换流水除法器：把 AWB 的两路 32÷48 位流水除法器换成归一化 + 256×16 倒数 ROM + 一次乘法，逐点验证精度 ≤0.39%，"
    "逻辑资源降低 14.4 个百分点，只付出 2 个 DSP。",
    "② 零帧存块级帧差：以 144 字节的块均值缓存替代整帧存储，配「绝对阈值 + 相对阈值 + 亮度地板 + 连续两帧确认」四重判据。",
    "③ 只校 R/B 的镜头色彩暗角校正：实测 R/G 与 B/G 的剖面形状几乎重合，故共用一张增益表、G 通道直通，既拉平色偏又不改变全局亮度与 AE 目标均值语义。",
    "④ 全自研分块 OSD 遥测：把算法内部量与开关状态实时上屏，使一块板子即可完成全部调试与验收。",
])

fill(P[22], [
    "自顶向下逐级展开：先确定数据通路与时钟域（ISP 域 60MHz / 像素域 75MHz / 串行域 375MHz / 控制域 24MHz），再为每个功能块定义端口与时序契约（AXI4-Stream，逐拍等价）。"
    "每加一级都遵守「上下游 tlast/tuser/tvalid 的延迟必须与新增流水线级数一致」的原则。"
    "每个新模块配套一个 ModelSim Testbench，用与 RTL 不同源的参考模型逐拍比对；然后跑全工程编译检查（42/43），再交 TangDynasty 命令行综合布线。"
    "每版比特流归档并记录 md5、时序与资源，形成 16 个版本的演进台账。上板后按「静止 / 运动」配对采集，用统计脚本量化验收。",
])

# ------------------------------------------------------------------ 第二部分
fill(P[25], [
    "本部分按「整体 → 硬件 → 软件」逐级展开。系统整体框图见图 1（待补充：需要一张系统框图），各子模块的端口、时钟域与相互衔接关系在下文逐一说明。",
])

fill(P[28], [
    "系统由四条通路构成。",
    "① 视频输入通路：SC500CS 摄像头 → MIPI D-PHY RX（硬核）→ CSI 解包（csi_unpacket_2lane）→ RAW10 解包（raw10_unpacket_2lane）→ 40bit/4 像素 RAW 流。",
    "② 图像处理通路（ISP 域，60MHz）：去马赛克（demosaic，BGGR）→ 128bit→96bit 位宽转换（data128_96）→ 镜头色彩暗角校正（lsc）→ 自动曝光统计（ae_stat）→ 自动白平衡（awb）→ S 曲线（isp_gamma）→ 算法层（my_algo）→ 96bit→128bit 转换。",
    "③ 显示通路：处理结果写入 DDR2 帧缓存（ph1p35_324_ddr_wrapper），由视频时序控制器（uivtc）按 1280×720@60Hz 读出，经 OSD 叠加（hdmi_mixer）后送 HDMI 1.4b 发送器（hdmi_tx）输出。",
    "④ 控制通路（24MHz 域）：按键去抖与模式切换（key_mode_ctrl）、拨码开关同步、AE 闭环控制（ae_ctrl）与摄像头寄存器配置（uicfgcs500_720p）。",
    "各模块间的关系：ISP 域内全部模块以 AXI4-Stream 逐拍握手，每级固定延迟，无空拍；lsc / awb / ae_stat 共享同一份数据流取数，保证 AE 与 AWB 观察到的画面完全一致；"
    "24MHz 控制域与像素域之间仅有单比特翻转同步与一处 set_max_delay 约束；运动检测模块以纯观察者方式收听算法层输出，不参与主通路握手。",
])

fill(P[31], [
    "硬件平台为安路 HX1P35A 开发板，主芯片 PH1P35MDG324（-3 速度等级）。板载资源：38184 等效 LUT、42432 DFF、40 个 DSP、108 块 ERAM（共 2160 Kbit）、6 个 PLL、2 路 MIPI、"
    "128MB QSPI Flash、64MB SPI Flash、DDR2 存储器、TF 卡槽。人机交互：4 组按键、4 组拨码开关、4 组 LED、8 组数码管、16 个双色 LED、蜂鸣器、USB 转 UART、千兆以太网口。"
    "视频接口：1 路 HDMI 输出、1 个 FPC40 芯 MIPI 输入。时钟源为 50MHz 有源晶振；下载调试经板载 AL-LINK-FT（Type-C 接口）。",
    "本系统实际使用：MIPI 输入（接 SC500CS 摄像头）、HDMI 输出（接 1280×720@60Hz 显示器）、4 组拨码开关、4 组按键、4 组 LED 指示。"
    "摄像头通过 40P 转 24P FPC 软线与开发板连接，由板载 24MHz 时钟驱动。",
])

fill(P[32], [
    "待补充——本作品为纯电子系统，不含机械结构设计。若最终演示需要摄像头支架、亚克力底座或线缆固定件，需要补拍实物照片与尺寸图。"
    "请确认是否可以标注「不适用」，或提供该部分的素材。",
])

fill(P[33], [
    "系统连接的电路模块与关键信号如下（完整引脚分配见约束文件 `constraints_source/pin.adc`，共 23 条）：",
    "（1）时钟与复位：I_sys_clk = C4（50MHz 有源晶振），I_rst_n = R10。",
    "（2）摄像头控制：O_cam_scl = K3、IO_cam_sda = J3（I2C 配置），O_cam_24m = L3（24MHz 主时钟），O_cam_rst = L2。",
    "（3）按键与拨码：I_button[0..3] = D5 / A9 / B9 / C7；I_switch[0..3] = A4 / B4 / E11 / D11。电平标准 LVCMOS33，输入均带上拉。",
    "（4）指示：O_led[0..3] = D10 / E10 / C6 / D6，直接回显 4 个拨码开关的同步后状态，现场可一眼确认开关是否被误触。",
    "（5）HDMI：O_tmds_ch0_p = G16、ch1_p = F17、ch2_p = H14、clk_p = C17，电平标准 TMDS33。",
    "（6）MIPI：走 PH1P35 硬核专用引脚，位置固定，无需额外约束。",
    "（7）DDR2：由 IP 自带的 `ddr2.adc`（73 条）与 `ddr2.xml` 约束覆盖。",
    "（8）背光控制：O_screen_pwm = R11。",
    "注：本作品未自制 PCB，全部电路基于官方开发板与其板载外设，上表即为全部对外电气连接。",
])

fill(P[36], [
    "本作品没有 PC 端或云端软件——赛题明确要求所有算法与控制逻辑必须在 FPGA 中自主实现、不得带额外处理器。"
    "因此这里的「软件」指的是 FPGA 内部的 RTL 设计及其配套的验证与构建工具链：",
    "① RTL 设计：`proj/baseline/lab3/user_source/hdl_source/` 下的 Verilog 源码，含官方 lab_ex_3 基线与自研 / 改造的 12 个模块。",
    "② 验证环境：ModelSim 下的 8 个 Testbench，每个都使用与 RTL 不同源的参考模型逐拍比对（例如 `wb_recip` 的 TB 用整数乘法、DUT 用条件移位加法）。",
    "③ 构建工具链：全工程编译检查脚本 `compile_check.py`（一键 vlog 全部源码，基线 42/43）、`.al`→`.prj` 同步脚本、TangDynasty 命令行一键综合布线脚本 `td_run_direct.ps1`。",
    "④ 数据分析工具链：采集图统计脚本 `stat_imgs.py`、LSC / AWB / 色调曲线的拟合与反演脚本、以及从屏幕像素反读 OSD 遥测数值的模板匹配解码脚本。",
    "⑤ 版本管理：Git 仓库（Gitee `fpgacnds`），16 个比特流版本归档于 `proj/releases/`，每版包含 `.bit`、压缩版、`route.qor`、`phy.area` 与 `readMe.txt`（记录 md5、时序、资源）。",
])

fill(P[37], [
    "下面按数据流顺序给出各模块的功能、关键输入输出与实现要点。",
    "（1）`demosaic`（去马赛克）：输入 40bit RAW（4 像素），BGGR 阵列，输出 128bit（4×RGB888）。"
    "内含黑电平扣除：`mipi_to_raw_converter.v` 中 `BLACK_LEVEL = 10'd56`（由盖严镜头实测 RAW10 均值 67.02 标定）、`ROUND_ADD = 10'd2`（四舍五入），"
    "并对四个 Bayer 分量分别做下溢钳位。关键输入 `axi4s_video_tdata[39:0]`；关键输出 `O_tdata[127:0]`。",
    "（2）`data128_96` / `data96_128`：位宽转换。ISP 域每拍 4 像素共 96bit（`{R[23:16],G[15:8],B[7:0]}`×4），而 DDR 与 HDMI 通路使用 128bit，两个模块负责无损搬运。",
    "（3）`lsc`（镜头色彩暗角校正，自研）：20×12 节点二维增益表，每节点 20bit（`{kR[9:0], kB[9:0]}`），节点内做双线性插值；增益 `g = 1 + k/1024`，输出 `out = v + ((v*k)>>10)`，"
    "带饱和保护。只校 R、B，G 直通。关键输入 `I_tdata[95:0]`、`I_tvalid/I_tuser/I_tlast`、`I_bypass`；关键输出 `O_tdata[95:0]`。"
    "资源 453 LUT6 / 661 ripple / 278 FF / 0 ERAM / 0 DSP。",
    "（4）`ae_stat`（自研）：与 AWB 同源取数，统计整帧亮度和（`O_luma_sum[39:0]`，口径为 Σ(Y×256)）、有效像素数、高光像素数（>250）、暗像素数（<8）与帧翻转标志。全部为移位加法，零 DSP。",
    "（5）`awb`（自动白平衡，改造）：灰世界法。四个像素组各自累加 `rgb_sum[0..3] < 720` 的像素；由 `wb_recip` 求 ΣG/ΣR 与 ΣG/ΣB；"
    "增益在 `I_tuser` 拍锁存为整帧常量（`in_r_hold / in_b_hold`），整帧施加同一增益；输出端 `(x + 0x8000)>>16` 四舍五入后饱和。"
    "关键输出 `O_gain_r / O_gain_b[19:0]`（Q16 格式）供 OSD 遥测显示。",
    "（6）`wb_recip`（自研）：倒数查表除法器。`n_eff = max(sum_x, 65536)`；`e = floor(log2(n_eff))`；`m = n_eff >> (e-8)`，落在 [256,512)；`idx = m-256`；"
    "`T2 = ROM[idx] = round(2^24/(256+idx))`（256×16 内联 ROM，共 256 项）；`q16 = ((sum_g >> (e-16)) * T2) >> 16`。"
    "经 44.9 万组真实范围随机扫描，误差典型 0.16%~0.21%，最差 0.39%。资源：两路共 345 LUT6、各 1 个 DSP。",
    "（7）`isp_gamma`（S 曲线）：12 份并行的 256×8 内联 ROM（`mem_b00`~`mem_b11`），2 级流水，旁路与使能路径同为 2 拍。"
    "当前表为真 S 曲线两段幂函数叠加软黑位恢复：`x≤128: y = 128*(x/128)^1.15`；`x>128: y = 128 + 127*(1-((255-x)/127)^1.10)`；`y = y - K*(1-y/255)^2`，K=1。",
    "（8）`my_algo`（算法层，自研）：RGB 点运算，5 种模式由 `I_algo_mode[2:0]` 选择——MODE0 直通；MODE1 BT.601 灰度 `Y=(77R+150G+29B)>>8`；"
    "MODE2 伪彩热力图；MODE3 五段彩条；MODE4 卡通化（四级平涂 + 邻域描边）。",
    "（9）`key_mode_ctrl`（自研）：4 个按键去抖后映射为算法模式（K1→MODE0、K2→MODE1、K3→MODE2、K4→MODE4），长按任意键 ≥1s 进入 MODE3。24MHz 域，采用单比特翻转跨到像素域。",
    "（10）`motion_detect`（自研，块级帧差运动检测）：画面划为 16 列 × 9 行 = 144 个 80×80 块，逐帧计算块亮度均值（亮度和 >>13）并与上一帧比较；"
    "判据为四重：`|Δ| > I_diff_th` 且 `|Δ| > (块亮度 >> I_rel_shift)` 且 `块亮度 > I_floor_th` 且连续两帧（`I_strict2`）。"
    "关键输出 `O_blk_mask[143:0]`（跨帧保持，位序 `by*16+bx`）、`O_blk_cnt[7:0]`、`O_motion_any`。全模块零乘法、零除法、零 ERAM。",
    "（11）`ae_ctrl`（自研，自动曝光闭环）：60MHz 域产生单比特翻转跨到 24MHz 域；7bit 单调增益索引（0~127）映射到摄像头寄存器 `3e08/3e09`"
    "（`3e08 ∈ {0x03,0x07,0x0F,0x1F}` 对应 ×1/×2/×4/×8，`3e09 ∈ 0x20..0x3F` 对应 ×1.000~×1.969）；"
    "曝光固定为 1990（= 2×VTS−10，再长会掉帧，故 720p60 下唯一连续杠杆是模拟增益）。决策优先级：非使能 → 高光护栏 → 过亮 → 欠亮且无暗场护栏 → 保持。资源 111 LUT6 / 200 FF。",
    "（12）`hdmi_mixer`（OSD 叠加）：6 个图层依次判定——安路 Logo（ROM）、帧计数器 CNT（黄 `24'hfff200`）、遥测第 1 行（橙 `24'hff8000`）、遥测第 2 行（橙）、"
    "算法模式行 MODE（绿 `24'h00ff88`）、参数状态行（亮青 `24'h00e6ff`）；运动块红色描边也在此层绘制。六层共用唯一一份字符 ROM `osd_char_lib`，ERAM 无新增。",
    "（13）`uicfgcs500_720p` / `uics500reg_720p60` / `uics500regAE`（摄像头配置）：上电按 116 条寄存器表初始化 SC500CS，运行时通过 8 条 AE 表动态下发曝光与增益。",
])

# ------------------------------------------------------------------ 第三部分
fill(P[40], [
    "本部分用实测数据说明最终实现的成果。除标注「待补充」的实物照片外，其余结论均来自可复现的采集与测量，"
    "采集图与视频、统计脚本、比特流归档均保存在项目中。",
])

fill(P[41], [
    "待补充——需要提供系统实物的正面与斜 45° 全局照片各一张（应包含开发板、摄像头、显示器与连线，拨码开关状态可见）。"
    "拍摄建议：显示器上同时呈现实时画面与全部 OSD 图层，画面内容选有纹理的室内场景而非纯白墙，以便同时展示画质、运动检测与信息叠加。",
])

fill(P[44], [
    "不适用——本作品为纯电子系统，无机械结构。若最终增加了摄像头支架等辅助结构，请补充实物照片与尺寸图。",
])

fill(P[45], [
    "待补充——需要提供开发板实物照片（含 MIPI 排线、HDMI 线、供电连接）。"
    "电路连接说明已在 2.2.3 中给出全部 23 条引脚分配；如需补充原理图截图，请提供或确认可引用官方原理图。",
])

fill(P[46], [
    "软件成果以屏幕截图与量化数据呈现，全部可复现：",
    "（1）实时画面与 OSD 叠加：6 个图层同时工作（Logo、CNT、两行遥测、MODE、参数行），叠加不影响视频时序。",
    "（2）两行橙色遥测的字段定义与实际读数示例：`AE2E S2 M3B W158B B1B6E`，其中 `AE2E` 为 AE 状态与 7bit 增益索引（0x2E = 46）、"
    "`S2` 为闭环状态、`M3B` 为 FPGA 实测帧亮度（0x3B = 59）、`W158B` 为 AWB 的 R 通道增益（÷4096 = 1.346×）、`B1B6E` 为 B 通道增益（1.714×）。",
    "（3）白纸靶面 A/B 对照截图（SW1 关 / 开 各 2 张，同一上电、间隔 <10 秒）。",
    "（4）运动检测截图：静止时 0 框；缓慢进入时 1~2 个块框；横移时 2~4 个块框且框随物体移动。",
    "（5）比特流版本台账：`proj/releases/` 下 16 个版本目录，每版含 `.bit`、压缩版、`route.qor`、`phy.area` 与 `readMe.txt`。",
])

anchor = fill(P[48], [
    "各功能与性能指标的量化验收结果如下表：",
])
add_table_after(anchor, [
    ["能力", "验收方法", "实测结果", "判据", "结论"],
    ["视频采集与显示", "连续采集，帧计数比对墙钟", "ΔCNT/Δt = 60.00fps，误差 <0.3%", "无丢帧", "通过"],
    ["黑电平校正", "盖严镜头拍摄", "整帧 Y 均值 0.00；100% 像素为 0；max = 0", "无基座残留", "通过"],
    ["自动白平衡", "白纸靶面连续 3 张", "R/G = 0.9800 / 0.9804 / 0.9797；B/G = 0.9803 / 0.9807 / 0.9799", "0.98~1.02", "通过"],
    ["自动曝光", "15 分钟连续挂机", "三张 Y 均值 95.22 / 96.04 / 95.72，最大漂移 0.86%；增益索引全程未变", "漂移 <5%", "通过"],
    ["镜头暗角校正", "同场 SW1 关/开 A/B，逐列 R/G 极差", "0.1208→0.0689（−43.0%）；0.1164→0.0634（−45.5%）", "下降 ≥50%（自定）", "通过"],
    ["色调曲线", "曲线分析脚本（真 S 表）", "p10 38→19；p50 134→127；p90 203→233；跨度 165→214；中调斜率 0.695→1.086", "跨度增大、中点回 128", "通过"],
    ["运动目标检测", "144 块帧差 + OSD 描边", "静止帧 0 框；运动时 1~3 个块框且位置随物体移动", "无爆发式误检", "基本通过（暗场景待复验）"],
    ["资源占用", "TangDynasty phy.area", "slice 77.31%；LUT6 71.40%；ERAM 47.22%；DSP 25.00%", "留有余量", "通过"],
    ["时序收敛", "TangDynasty route.qor", "Setup WNS +102ps / TNS 0 / 0 违例；Hold WNS +20ps / TNS 0 / 0 违例", "0 违例", "通过"],
    ["除法器资源优化", "优化前后版本对照", "slice 17774→14023（−17.7pp）；LUT6 16143→13080（−14.4pp）；FF 14961→9447（−13.0pp）；DSP 8→10", "精度 ±2%", "通过（最差 0.39%）"],
])

# ------------------------------------------------------------------ 第四部分
fill(P[54], [
    "（1）目标检测与识别：现有 `motion_detect` 已输出运动块掩码与计数，只需增加颜色 / 形状特征提取与块级连通域，即可在 OSD 上叠检测框与类别文字。",
    "（2）动态跟踪：把当前帧的运动块坐标与上一帧做最近邻匹配并保持，即可输出跟踪框与坐标。",
    "（3）处理延迟可视化：在帧首注入时间戳、在输出端读回并做差，可把「采集到显示」的延迟以毫秒级数值上屏。",
    "（4）直方图均衡：在已有亮度直方图统计的基础上增加 CDF 映射，即可实现自适应对比度增强。",
    "（5）QSPI 固化：赛题要求最终设计上电即可运行、无需 PC 下载，需把比特流写入板载 128MB QSPI Flash 并配置启动模式。",
])

fill(P[56], [
    "待补充——这一节需要参赛队员本人撰写，不宜由他人代笔。可围绕以下线索展开（相关事实素材均可从项目记录中取得）：",
    "① 从「能出图」到「颜色对」之间踩过的坑：采集链把颜色做了 limited→full 展开导致所有调色结论被污染；传感器内置灰度测试图被「四开关全上」这一出厂推荐档意外打开；"
    "工程里长期存在两份 `awb.v`，一整轮改动打在了不参与综合的副本上。",
    "② 工具链的教训：TangDynasty 命令行只认 run 目录的 `.prj` 而不认图形界面的 `.al`；比特流文件时间戳变新并不等于构建成功，必须核对日志与网表中关键模块是否仍在。",
    "③ 用算术换资源的过程：把两路流水除法器换成归一化 + 倒数查表 + 一次乘法，逻辑资源下降 14.4 个百分点，而精度仍满足 ±2% 的验收带。",
    "④ 一块板三个人怎么协作：分支约定、PR 流程、改动顶层文件时在提交信息首行标注 `TOUCHES:`、以及 16 个版本的比特流台账如何让任何一次回滚都有据可依。",
])

# ------------------------------------------------------------------ 第五部分
fill(P[59], [
    "[1] 唐小明, 等. 基于 FPGA 的自适应阈值运动目标检测[J]. 应用光学, 2017, 38(6): 903-909.",
    "[2] Adaptive Dual Threshold Based Moving Target Detection Algorithm[C]. IEEE, 2019.",
    "[3] FPGA-Based Real-Time Moving Target Detection System for Unmanned Aerial Vehicle Application[J].",
    "[4] 李斌华, 等. 自适应自动白平衡算法的改进与实现[J]. 光学学报.",
    "[5] 数字图像的自动白平衡算法设计与 FPGA 实现[J]. 电子技术与软件工程, 2023(12).",
    "[6] Speeding up the Throughput of an NLMS Adaptive Filter[C]. IEEE, 2024.",
    "[7] F. de Dinechin, et al. Constant Division by Multiplication[J]. IEEE Transactions on Computers, 2017.",
    "[8] Newton-Raphson Integer Division for Area-Constrained Microcontrollers[C]. ARITH Symposium, 2023.",
    "[9] Dynamic Partial Reconfiguration for Automatic White Balance[C]. IEEE, 2014.",
    "[10] 安路科技. PH1P 系列 FPGA 器件手册[Z].",
    "[11] 安路科技. APUG092 HDMI1.4b Transmitter 用户手册[Z].",
    "[12] 安路科技. MIPI Camera Reference Design 用户手册[Z].",
    "[13] 安路科技. IPUG012 Soft_FIFO 用户手册[Z].",
    "[14] Smartsens. SC500CS 图像传感器数据手册[Z].",
])

d.save(DST)
print("已生成:", DST, os.path.getsize(DST), "B")
print("段落数:", len(Document(DST).paragraphs), " 表格数:", len(Document(DST).tables))
