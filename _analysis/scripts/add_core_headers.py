# -*- coding: utf-8 -*-
"""给核心链路 9 个手写 HDL 文件补「文件头 + 修改记录」注释块。

规则：
  * 按字节读写，保留原编码与换行。
  * 只插入注释行，不改动任何既有代码字符。
  * 幂等：文件里已含标记 HDR-2026-10-09 就跳过。
  * 修改记录只写有据可查的内容（git log 提交 + 本工程未提交改动），不编造日期。
"""
import os, shutil

BASE = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
BACKUP = r"E:\FPGA\_backup\20261009_comments\core"
MARK = "HDR-2026-10-09"

def hdr(fname, module, func, path, clk, deps, impl, records):
    L = []
    L.append("//=============================================================================")
    L.append(f"// [{MARK}] 文件      : {fname}")
    L.append(f"// 模块      : {module}")
    L.append(f"// 功能      : {func}")
    L.append(f"// 数据通路  : {path}")
    L.append(f"// 时钟/复位 : {clk}")
    L.append(f"// 依赖      : {deps}")
    L.append(f"// 综合/实现 : {impl}")
    L.append("//-----------------------------------------------------------------------------")
    L.append("// 修改记录  :")
    for r in records:
        L.append(f"//   {r}")
    L.append("//-----------------------------------------------------------------------------")
    L.append("// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑，见 E:\\FPGA\\_analysis\\reports\\rename_report.txt）")
    L.append("//=============================================================================")
    L.append("")
    return "\n".join(L).encode()

DTW = hdr(
    "design_top_wrapper.v", "design_top_wrapper",
    "整板顶层：把 MIPI 摄像头 → RAW 解包 → ISP → 视频缓存 → HDMI 输出整条链路接起来，"
    "并管理时钟/复位、按键、摄像头 I2C 配置。",
    "MIPI 差分对 → u_mipi_dphy_rx_* → csi_unpacket_2lane(字节流) → raw10_unpacket_2lane(40bit/4像素 RAW10)"
    " → uial2axis(AXI4-Stream) → isp_top(ISP) → video_in/video_out(DDR2 帧缓存) → hdmi_tx → TMDS 差分对",
    "主输入 I_sys_clk = 50 MHz；摄像头接收域 S_csi_rx_clk；像素/HDMI 域 HDMI_PIXEL_CLK；"
    "按键/配置域 24 MHz。各域间靠单 bit 翻转协议或同步器跨域。复位 I_rst_n 低有效。",
    "isp_top / csi_unpacket_2lane / raw10_unpacket_2lane / uial2axis / video_in / video_out / "
    "hdmi_tx / hdmi_phy_wrapper / uicfgcs500_720p / key_mode_ctrl / u_ph1p35_324_ddr_wrapper 等",
    "■ 本文件是时序约束 camera_to_dsi_display.sdc 的引用对象：约束里按层次路径点名了 "
    "u_PLL/…/u_PH1P_PHY_PLL.clkc[0/1/4/5]、u_mipi_dphy_rx_ph1p_mipiio_wrapper/…/o_fabric_div4_8_clk、"
    "u_ph1p35_324_ddr_wrapper/u_ddr2/{ddr_clk,usr_clk} —— 这些实例名禁止改名。\n"
    "//           ■ 12 个顶层端口被 pin.adc 分派引脚（I_sys_clk/I_rst_n/O_cam_scl/IO_cam_sda/O_cam_24m/"
    "O_cam_rst/I_button[1:0]/O_screen_pwm/O_tmds_ch*_p/O_tmds_clk_p），同样禁止改名。\n"
    "//           ■ (:80-83,:91-94) 8 根观测 wire 带 (*MARK_DEBUG = \"TRUE\"*)，供 TD 的 ChipWatcher 抓波形；"
    "不要删除这些属性。",
    [
        "2026-09-27  [230f479] 导入官方 lab3 基线并把工程路径改为本地路径",
        "2026-09-27  [6440c52] 接入自研 RGB 点运算算法集与按键模式切换（新增 S_algo_mode 跨域链路）",
        "2026-09-27  [c8e7b96] 新增 SHOW_DEBUG 参数，把 DDR 状态直接画进 HDMI 画面",
        "2026-10-03  [043f927] 修复跨时钟域违例（SWNS -4.416ns）与 DSP 用满（40/40）",
        "2026-10-03  [364d1bf] 算法模式改为单 bit 翻转跨域协议，消除残留 0.085ns 违例",
        "2026-10-08  （未提交）给 8 根观测 wire 加 (*MARK_DEBUG = \"TRUE\"*)，以便 ChipWatcher 抓 RAW10/ISP 波形",
        "2026-10-09  （未提交）标识符改名 10 处（S_ae/S_ag/I_ae/I_ag 等），无逻辑改动",
    ])

ISP = hdr(
    "isp_top.v", "isp_top",
    "ISP 顶层：把传感器 RAW10 四像素一拍的数据依次过「去马赛克 → 位宽重切 → 自动白平衡 → 自研算法 → 位宽重切」，"
    "输出 128bit/拍的 RGB888。",
    "I_tdata[39:0](RAW10，4 像素×10bit) → demosaic(128bit) → data128_96(96bit，4 像素×24bit RGB)"
    " → awb(白平衡) → my_algo(算法/MODE) → data_96bit_to_128bit(128bit) → O_tdata",
    "axi4s_video_aclk = S_csi_rx_clk（约 100 MHz）；I_rst_n 低有效。全部子模块同域。",
    "demosaic(BAYER_MODE=\"BGGR\",1280x720) / data128_96 / awb / my_algo(MODE_INIT=3'd2,THRESH=8'd128) / data_96bit_to_128bit",
    "■ (:86-89) 输出接线是本文件的关键：O_tdata 取 128bit 级的 awb_O_tdata_128，而 O_tlast 取 96bit 级的 "
    "awb_O_tlast（与官方 lab_ex1 的 isp_top.v:36-40 逐字一致），O_tuser/O_tvalid 取 awb_*_128。\n"
    "//           ■ 96bit 数据格式 = [23:16]=R [15:8]=G [7:0]=B，一拍 4 个像素。",
    [
        "2026-09-27  [230f479] 导入官方 lab3 基线",
        "2026-09-27  [6440c52] 在 awb 与 data_96bit_to_128bit 之间插入自研算法模块 my_algo",
        "2026-10-06  （未提交）★修复输出悬空：原文件缺失 `assign O_tdata = awb_O_tdata_128;`，"
        "导致 ISP 输出端口无消费者，TD 在 phy 阶段执行 PHY-1001 Remove keep and sweep redundant instances "
        "把整条 ISP 链路优化掉（#RAMs 40→12、#DSPs 9→1），上板全黑只剩 OSD；"
        "本次补齐该行，并把 O_tuser/O_tvalid 由 96bit 级改取 128bit 级，避免与 O_tdata 相位错配",
        "2026-10-09  （未提交）标识符改名 25 处：局部 wire 拼写错误 m_aixs_* → m_axis_*",
    ])

REG720 = hdr(
    "uics500reg_720p60.v", "uics500reg_720p60",
    "SC500CS 传感器的初始化寄存器表（1280x720@60，24MHz MCLK，2-Lane RAW10，约 480Mbps/lane）："
    "按 REG_INDEX 逐条给出 I2C 要写的 16bit 地址与 8bit 数据。",
    "纯查表（always @(*) case）—— 无数据流；被 uicfgcs500_720p 例化，随 reg_index 递增逐条下发",
    "组合逻辑（无时钟）；复位不适用。参数 TEST_PATTERN 供调试用。",
    "被 uics500_cfg/uicfgcs500_720p.v:118-122 例化（.REG_INDEX / .REG_DATA / .REG_SIZE）",
    "■ REG_SIZE 必须等于表内 case 条目总数（当前 9'd117，索引 0..116）；追加条目只需改 REG_SIZE + 加一条 case。\n"
    "//           ■ 索引 113 的 `{16'h3e09, 8'hXX}` 与索引 112 的 `{16'h3e08, ...}` 合起来是模拟增益："
    "增益 = (3e09/0x20) × 2^(coarse 档位)，其中 3e08 的 0x03/0x07/0x0F/0x1F 分别对应 ×1/×2/×4/×8。\n"
    "//             当前值 0x2d → (0x2d/0x20)×8 = 11.25×；手册表2-4 的上限是 0x3f → 15.750×。\n"
    "//           ■ 索引 116 是传感器内置灰度递增测试图：0x4501 写 0xbc 打开、写 0xb4（该寄存器默认值）关闭。\n"
    "//           ■ 曝光 = {3e00[3:0], 3e01, 3e02[7:4]}，索引 94-96；本表当前 0x07C6 = 1990 = 2×VTS−10，已是硬件上限。",
    [
        "2026-09-27  [230f479] 导入官方 lab3 基线",
        "2026-10-06  （未提交）新增 parameter TEST_PATTERN；新增索引 116 `{16'h4501, TEST_PATTERN ? 8'hbc : 8'hb4}`"
        "（传感器灰度递增测试图，手册表2-10）；REG_SIZE 由 9'd116 改为 9'd117",
        "2026-10-08  （未提交）索引 113 `{16'h3e09, 8'h20}` → `8'h2d`，模拟增益由 8.000× 提高到 11.25×",
    ])

GAINTBL = hdr(
    "SC500GainTbl.v", "SC500GainTbl",
    "把自动曝光/增益算法给出的增益档位索引（0..73）翻译成 SC500CS 的模拟增益寄存器编码（16bit，"
    "高 8bit 写在 0x3e08、低 8bit 写在 0x3e09）。",
    "I_gain_idx(7bit 档位) → 查表 → O_gain_code(16bit 寄存器编码)",
    "I_clk 上升沿同步输出；I_rstn 低有效。",
    "被 uics500_cfg/uicfgcs500_720p.v:124-130 与 uics500_cfg/uicfgcs500.v:154 例化",
    "■ 表内三段阶梯 0x0320 / 0x0720 / 0x0F20 = 粗调 ×1 / ×2 / ×4；每段内低字节 0x20..0x3F 是细调。\n"
    "//           ■ ★表只到索引 73（0x0F29），因此把 RTL 自动增益路径封顶在约 4.28×；"
    "而手册表2-4 允许到 15.750×。想用更高模拟增益只能改 init 表（uics500reg_720p60.v 索引 112/113），按键调不上去。",
    ["2026-09-27  [230f479] 导入官方 lab3 基线",
     "2026-10-09  （未提交）端口改名 I → I_gain_idx、O → O_gain_code（原名无语义），同步更新 2 处例化"])

AESET = hdr(
    "ae_set.v", "ae_set",
    "按键触发的手动曝光/模拟增益调节器：给「曝光 +/−」和「增益 +/−」按键各做一个步进计数器，"
    "输出目标曝光值与目标增益档位。",
    "按键(边沿) → r_exposure_step / r_analog_gain_step 单拍脉冲 → 步进加减 r_exposure_set / r_analog_gain_set"
    " → 与当前值比较后请求下发（O_ae_req）→ 输出 r_exposure / r_analog_gain",
    "24 MHz 按键/配置域；复位低有效。",
    "被 design_top_wrapper.v:462-471 例化（u_ae_set），输出送 uicfgcs500_720p 的曝光/增益接口",
    "■ ★★本模块有三处已知隐患（只标注，本次不改）：\n"
    "//           1. (:73) 复位值 r_exposure_set = 3000 **超过手册最大曝光 1990**；(:88) 的 AE 加上限 2246 同样超限。\n"
    "//           2. (:109-114) 复位后 r_exposure == r_exposure_set 且 r_analog_gain == r_analog_gain_set，"
    "条件 `(r_ae != r_ae_set) || (r_ag != r_ag_set)` 不成立 ⇒ r_ae_req 永不置位 ⇒ AE 寄存器组从不下发。\n"
    "//           3. 一旦按下 AE 键，上述条件成立，会把 2999+ 的非法曝光值写进传感器，"
    "//              并把模拟增益覆盖回 SC500GainTbl 的 0x0F20（4.000×）。\n"
    "//              ⇒ 现场调试期间「只按模式切换键 KEY1(I_button[1]/D5)，不要按 AE/AG 键」。",
    ["2026-09-27  [230f479] 导入官方 lab3 基线（Milianke 参考例程）",
     "2026-10-09  （未提交）标识符改名 56 处：O_ae/O_ag → O_exposure_time/O_analog_gain、"
     "r_ae_set/r_ag_set → r_exposure_set/r_analog_gain_set、r_ae_tick/r_ag_tick/rc_ag_tick → r_exposure_step/"
     "r_analog_gain_step/r_analog_gain_accum，无逻辑改动"])

CFG720 = hdr(
    "uicfgcs500_720p.v", "uicfgcs500_720p",
    "SC500CS 的 I2C 配置状态机：上电后按 init 表逐条写寄存器，配置完成后转为按 AE 表下发曝光/增益，"
    "并产生 O_cfg_done / O_ae_cfg_done 握手信号。",
    "init 表(上电) 或 ae 表(运行时) → I2C 时序(uii2c) → O_cam_scl / IO_cam_sda 两条线到传感器",
    "I_clk（24MHz 域）；I_rst_n 低有效。I2C 分频由 parameter CLK_DIV 决定（16'd239）。",
    "uics500reg_720p60（init 表）/ SC500GainTbl（增益编码）/ uics500regAE（AE 表）/ uii2c（I2C 主机）",
    "■ (:56) 延时分支只按 `reg_index == 9'd115` 触发（stream on 之后延时 POST_STREAM_DELAY=240000 拍 ≈ 10ms @24MHz）；"
    "因此往 init 表**追加索引**只需改 REG_SIZE 与 case，不必改状态机。\n"
    "//           ■ (:32-33) 用 O_cfg_done 选择当前下发的是 init 表还是 ae 表。",
    ["2026-09-27  [230f479] 导入官方 lab3 基线",
     "2026-10-09  （未提交）标识符改名 8 处：I_ae/I_ag → I_exposure_time/I_analog_gain，"
     "SC500GainTbl 例化的 .I/.O → .I_gain_idx/.O_gain_code"])

REGAE = hdr(
    "uics500regAE.v", "uics500regAE",
    "运行时的曝光/增益寄存器表：把 16bit 曝光时间与 16bit 模拟增益编码拆成 5 条 I2C 写操作"
    "（3e00/3e01/3e02 装曝光，3e08/3e09 装增益）。",
    "I_exposure_time / I_analog_gain → 按 REG_INDEX 拆位 → REG_DATA",
    "组合逻辑（always @(*) case）；无时钟。",
    "被 uicfgcs500_720p.v:132-138 例化（.I_AG / .I_AE）",
    "■ 曝光 16bit 拆成 3e00[3:0]/3e01[7:0]/3e02[7:4]；增益 16bit 拆成 3e08[7:0]/3e09[7:0]。\n"
    "//           ■ 注意：自动增益路径的输入来自 SC500GainTbl，该表只到索引 73（约 4.28×）。",
    ["2026-09-27  [230f479] 导入官方 lab3 基线（Milianke 参考例程）",
     "2026-10-09  （未提交）标识符改名 7 处：I_AE/I_AG → I_exposure_time/I_analog_gain"])

# (相对路径, 模式, 行号(1 基), 内容)
SPECS = [
    ("design_top_wrapper.v", "prepend", None, DTW),
    ("isp/isp_top.v", "prepend", None, ISP),
    ("uics500_cfg/uics500reg_720p60.v", "prepend", None, REG720),
    ("uics500_cfg/SC500GainTbl.v", "prepend", None, GAINTBL),
    ("uiisp_beta/ae_set.v", "prepend", None, AESET),
    ("uics500_cfg/uicfgcs500_720p.v", "prepend", None, CFG720),
    ("uics500_cfg/uics500regAE.v", "prepend", None, REGAE),
]

os.makedirs(BACKUP, exist_ok=True)
for rel, mode, lineno, blob in SPECS:
    p = os.path.join(BASE, rel.replace("/", os.sep))
    raw = open(p, "rb").read()
    if MARK.encode() in raw:
        print("skip (already marked):", rel)
        continue
    shutil.copy2(p, os.path.join(BACKUP, rel.replace("/", "__") + ".bak"))
    open(p, "wb").write(blob + raw)
    print(f"prepend {len(blob):>5} B -> {rel}")

# ---- my_algo.v / key_mode_ctrl.v：已有详细中文文件头，只在结尾补「修改记录」----
REC_MYALGO = """//-----------------------------------------------------------------------------
//  修改记录 :
//    2026-09-27  [6440c52] 新建本模块（自研 RGB 点运算算法集，5 种模式）并接入 isp_top
//    2026-10-03  [043f927] 修复跨时钟域违例与 DSP 用满（去掉 `a * 常数` 写法）
//    2026-10-03  [e562752] 修复 f_heat 未初始化读取导致的综合致命错误 HDL-8007
//    2026-10-06  （未提交）MODE 3 由「二值化」改为「亮度五档彩条」：阈值 8'd32/64/128/192
//                映射黑/蓝/绿/黄/红；修正 f_luma 的 B 通道系数（21B → 29B）；
//    2026-10-06  （未提交）MODE 4 卡通化：段边界与描边门限调整
//    2026-10-09  （未提交）标识符改名（S_phase_cnt 等），无逻辑改动
//-----------------------------------------------------------------------------
""".encode()

REC_KEY = """//-----------------------------------------------------------------------------
//  修改记录 :
//    2026-09-27  [6440c52] 新建本模块（按键切换算法模式）
//    2026-10-03  [364d1bf] 模式值改为单 bit 翻转跨域协议，修掉残留 0.085ns 时序违例
//    2026-10-06  （未提交）模式数由 4 改为 5，增加第二根翻转线 O_mode_wrap，
//                循环改为 0→1→2→3→4→0；复位默认模式 = MODE 2（伪彩热力图）
//    2026-10-09  （未提交）标识符改名（S_phase_cnt 等），无逻辑改动
//-----------------------------------------------------------------------------
""".encode()

for rel, lineno, blob, assert_prefix in [
        ("my_algo/my_algo.v", 59, REC_MYALGO, b"//==="),
        ("my_algo/key_mode_ctrl.v", 33, REC_KEY, b"//===")]:
    p = os.path.join(BASE, rel.replace("/", os.sep))
    raw = open(p, "rb").read()
    if MARK.encode() in raw:
        print("skip (already marked):", rel)
        continue
    lines = raw.split(b"\n")
    idx = lineno - 1
    assert lines[idx].startswith(assert_prefix), (rel, lines[idx][:40])
    shutil.copy2(p, os.path.join(BACKUP, rel.replace("/", "__") + ".bak"))
    bl = blob.split(b"\n")
    if bl and bl[-1] == b"":
        bl = bl[:-1]
    lines[idx:idx] = bl
    open(p, "wb").write(b"\n".join(lines))
    print(f"record  {len(blob):>5} B -> {rel} (插在第 {lineno} 行前)")

# ---- 顺手改正 key_mode_ctrl.v 里一处与 pin.adc 不符的注释（J14 -> D5）----
p = os.path.join(BASE, "my_algo", "key_mode_ctrl.v")
raw = open(p, "rb").read()
bad = b"I_button[1] } { LOCATION = J14;"
good = b"I_button[1] } { LOCATION = D5; "
if bad in raw:
    open(p, "wb").write(raw.replace(bad, good))
    print("fix comment: key_mode_ctrl.v  I_button[1] J14 -> D5（与 constraints_source/pin.adc:11 一致）")
else:
    print("note: key_mode_ctrl.v 未找到 J14 注释（可能已改过）")
