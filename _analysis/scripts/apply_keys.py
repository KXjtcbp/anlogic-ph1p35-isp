# -*- coding: utf-8 -*-
"""2026-10-10 按键切换算法改造：K1-K4 直选 MODE0..MODE3 + 默认 MODE0。

改动清单（全部在 E:\\FPGA\\proj\\baseline\\lab3\\user_source 下）
  1) hdl_source/my_algo/key_mode_ctrl.v   —— 整文件重写：4 键各自消抖、直选；
     跨域协议不动，仍只走 O_mode_tgl / O_mode_wrap 两根单 bit 线；
     由本模块按「从当前模式前进几步到目标模式」发出对应个数的步进脉冲，
     脉冲间隔 16 拍 @24MHz ≈ 667ns（接收端 3 级同步只需 <42ns，余量 16 倍）。
  2) hdl_source/design_top_wrapper.v      —— I_button 2bit→4bit、.I_key_n 接 4bit、
     .I_btn 固定 4'b1111（禁用原来的手动 AE/AG 键，避免 KEY2/KEY3 被当成增益键）。
  3) constraints_source/pin.adc           —— I_button[0..3] = D5/A9/B9/C7 (KEY1..KEY4)，
     删除原来的 I_button[0]=N2（N2 是 GPIOA_19 扩展口，不是按键）。
  4) hdl_source/hdmi_mixer.v              —— 本地模式计数器复位值 3'd2 → 3'd0（两处）。
  5) hdl_source/my_algo/my_algo.v         —— MODE_INIT 3'd2 → 3'd0。
  6) hdl_source/isp/isp_top.v             —— .MODE_INIT(3'd2) → 3'd0。

安全措施：①先整体备份到 E:\\FPGA\\_backup\\20261010_keys\\；
          ②每处替换都断言命中次数，不符则整文件放弃；
          ③先 encode 成功再 open('wb')（避免 GBK/异常把文件截成 0 字节的历史事故）；
          ④保留原文件 BOM、编码与换行风格（逐行改，行尾的 \\r 原样保留）。
"""
import os
import sys
import shutil
import datetime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"E:\FPGA\proj\baseline\lab3\user_source"
BAK = r"E:\FPGA\_backup\20261010_keys"
REPORT = r"E:\FPGA\_analysis\reports\apply_keys_report.txt"

F_KEY = os.path.join(ROOT, r"hdl_source\my_algo\key_mode_ctrl.v")
F_TOP = os.path.join(ROOT, r"hdl_source\design_top_wrapper.v")
F_PIN = os.path.join(ROOT, r"constraints_source\pin.adc")
F_MIX = os.path.join(ROOT, r"hdl_source\hdmi_mixer.v")
F_ALG = os.path.join(ROOT, r"hdl_source\my_algo\my_algo.v")
F_ISP = os.path.join(ROOT, r"hdl_source\isp\isp_top.v")

log = []


def note(s):
    log.append(s)
    print(s)


# ---------------------------------------------------------------- 读写工具
def load(path):
    raw = open(path, "rb").read()
    bom = raw.startswith(b"\xef\xbb\xbf")
    body = raw[3:] if bom else raw
    enc = None
    text = None
    for e in ("utf-8", "gbk", "latin-1"):
        try:
            text = body.decode(e)
            enc = e
            break
        except Exception:
            pass
    return text, enc, bom, len(raw)


def save(path, text, enc, bom):
    data = text.encode(enc)                 # 先 encode，成功后才动文件
    if bom:
        data = b"\xef\xbb\xbf" + data
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def backup(path):
    os.makedirs(BAK, exist_ok=True)
    dst = os.path.join(BAK, os.path.basename(path))
    shutil.copy2(path, dst)
    return dst


def rep_line(lines, needle, new_line, expect=1):
    """整行替换（保留该行原有的行尾 \\r）"""
    hit = [i for i, l in enumerate(lines) if needle in l]
    assert len(hit) == expect, "行匹配数不符: %r -> %d (期望 %d)" % (needle, len(hit), expect)
    for i in hit:
        eol = "\r" if lines[i].endswith("\r") else ""
        lines[i] = new_line + eol
    return len(hit)


def rep_sub(lines, needle, new_text, expect=1):
    """行内子串替换（保留行尾）"""
    hit = [i for i, l in enumerate(lines) if needle in l]
    assert len(hit) == expect, "子串匹配数不符: %r -> %d (期望 %d)" % (needle, len(hit), expect)
    for i in hit:
        lines[i] = lines[i].replace(needle, new_text)
    return len(hit)


print("=" * 78)
print("apply_keys.py  —— K1-K4 直选模式改造")
print("=" * 78)

# =====================================================================
# 1) key_mode_ctrl.v 整文件重写
# =====================================================================
NEW_KEY = '''//-----------------------------------------------------------------------------
//  修改记录 :
//    2026-09-27  [6440c52] 新建本模块（按键切换算法模式）
//    2026-10-03  [364d1bf] 模式值改为单 bit 翻转跨域协议，修掉残留 0.085ns 时序违例
//    2026-10-06  （未提交）模式数由 4 改为 5，增加第二根翻转线 O_mode_wrap，
//                循环改为 0→1→2→3→4→0；复位默认模式 = MODE 2（伪彩热力图）
//    2026-10-09  （未提交）标识符改名，无逻辑改动
//    2026-10-10  （未提交）★按键语义改成 K1-K4 直选 MODE0-MODE3★
//                - 端口 I_key_n 由 1 bit 扩成 4 bit（bit0=K1/D5, bit1=K2/A9,
//                  bit2=K3/B9, bit3=K4/C7），四个键各自消抖；
//                - K1/K2/K3/K4 → MODE 0/1/2/3，不再循环切换；
//                - 复位默认模式由 MODE 2 改为 MODE 0（原图直通）；
//                - ★跨域协议一个字没改★：仍只走 O_mode_tgl / O_mode_wrap 两根
//                  单 bit 翻转线。本模块按「从当前模式前进几步能到目标模式」
//                  发出对应个数的步进脉冲（0~4 个），接收端照旧"数脉冲"即可，
//                  所以 hdmi_mixer.v 的接收逻辑完全不用动（只改了它的复位值）。
//                - 脉冲间隔 16 拍 @24MHz ≈ 667ns，而接收端 3 级同步只需要
//                  <42ns 就能看到稳定电平，余量 16 倍，绝不会漏计数。
//                - 代价：MODE 4（卡通化）不再有按键入口。
//-----------------------------------------------------------------------------
//===========================================================================
//  key_mode_ctrl.v  --  按键算法模式切换控制器（K1-K4 直选版）
//
//  项目：2026 全国大学生嵌入式芯片与系统设计竞赛 选题二
//
//  作用：把开发板上的 4 个按键变成「算法模式直选键」：
//            K1 → MODE 0(原图直通)     K2 → MODE 1(灰度)
//            K3 → MODE 2(伪彩热力图)   K4 → MODE 3(二值化)
//        上电默认 MODE 0。到不了 MODE 4(卡通化) —— 这是刻意的取舍，
//        4 个键正好对应 4 个模式，不需要长按/组合键。
//
//  ---------------------------------------------------------------------
//  按键硬件事实（来自 user_source/constraints_source/pin.adc 与开发板手册
//  《HX1P35B 开发板引脚分配汇总》"十三、4 组按键"）
//  ---------------------------------------------------------------------
//    KEY1 = D5  → I_button[0]      KEY2 = A9 → I_button[1]
//    KEY3 = B9  → I_button[2]      KEY4 = C7 → I_button[3]
//    均带内部上拉、按下为低电平（active-low）。
//    （改版前 I_button[0] 被约束到 N2，那是 GPIOA_19 扩展口第 22 脚，
//      不是按键，所以当时实际只有 KEY1 可用。）
//
//  ---------------------------------------------------------------------
//  为什么单独例化 4 份消抖而不是复用现成的
//  ---------------------------------------------------------------------
//   工程里 key_remove_shakes 只被 hdmi_tx.v 内部使用（它的 I_key_in 在
//   design_top_wrapper.v 被接成 1'b0，等于没用）。本模块自己例化 4 份，
//   互不干扰，不会改变 hdmi_tx 的任何既有行为。单份约 14 LUT / 24 FF。
//
//  ---------------------------------------------------------------------
//  时钟域
//  ---------------------------------------------------------------------
//   必须用 24 MHz（S_24m_clk）等慢时钟：key_remove_shakes 内部固定计数到
//   100000，在 24 MHz 下约 4.2ms（正常消抖），在 100MHz 下只有 1ms（偏短）。
//
//  资源消耗估计：4 份消抖 + 一个步进发生器 ≈ 60 LUT / 120 FF（可忽略）
//===========================================================================

//  ---------------------------------------------------------------------
//  跨时钟域协议（重要，别改回 2 bit 直连）
//  ---------------------------------------------------------------------
//   本模块跑在 24 MHz 慢时钟域；算法模式要送给 hdmi_mixer（74.25MHz 像素域）
//   和 my_algo（csi_rx_clk 域）。**只把 2 bit 模式值直接送过去会被时序工具
//   当成跨域组合路径**，实测代价：
//     - 直连进 hdmi_mixer 组合云：Setup WNS 由 +0.103ns 掉到 -4.416ns（29 个违例端点）
//     - 只加同步器送电平：      仍有 -0.085ns / 2 个违例端点
//   因此改为标准做法：**只跨 1 bit 的"翻转"信号**。
//   两个接收域各自维护 3 bit 计数器：
//     收到 tgl  边沿 → mode = (mode == 4) ? 0 : mode + 1
//     收到 wrap 边沿 → mode = 0
//   本模块发出步进脉冲时必须与自己的 O_mode 严格同步地翻转 tgl；
//   只有当这一步恰好是 4→0 时，才同时翻转 wrap（并把 O_mode 置 0）。
//   注意：O_mode / O_mode_chg 只供同域使用；算法模式值由各目标域各自计数得到
//         （my_algo 走的是 3 bit 直连 + 2 级同步，见 my_algo.v 的 I_mode）。
//===========================================================================

module key_mode_ctrl (
    input  wire       I_clk     ,   // 24 MHz 慢时钟
    input  wire       I_rst_n   ,
    input  wire [3:0] I_key_n   ,   // K1..K4 按键输入，active-low；bit0=K1/D5 … bit3=K4/C7
    output reg  [2:0] O_mode    ,   // 本域当前算法模式（同域使用）
    output reg        O_mode_chg,   // 模式每前进一步给出 1 个时钟周期的高脉冲（同域使用）
    output reg        O_mode_tgl,   // ★跨域用★：每前进一步翻转 1 次（单 bit）
    output reg        O_mode_wrap   // ★跨域用★：模式由 4 回到 0 时翻转 1 次（单 bit）
);

    //------------------------------------------------------------------
    // 4 份独立消抖：每次有效按下产生 1 个时钟周期的高脉冲
    //------------------------------------------------------------------
    wire [3:0] S_key_trig;

    key_remove_shakes u_key_remove_shakes_mode0 (
        .I_clk          ( I_clk        ),
        .I_rst_n        ( I_rst_n      ),
        .I_key_in       ( I_key_n[0]   ),
        .O_key_trig_out ( S_key_trig[0])
    );

    key_remove_shakes u_key_remove_shakes_mode1 (
        .I_clk          ( I_clk        ),
        .I_rst_n        ( I_rst_n      ),
        .I_key_in       ( I_key_n[1]   ),
        .O_key_trig_out ( S_key_trig[1])
    );

    key_remove_shakes u_key_remove_shakes_mode2 (
        .I_clk          ( I_clk        ),
        .I_rst_n        ( I_rst_n      ),
        .I_key_in       ( I_key_n[2]   ),
        .O_key_trig_out ( S_key_trig[2])
    );

    key_remove_shakes u_key_remove_shakes_mode3 (
        .I_clk          ( I_clk        ),
        .I_rst_n        ( I_rst_n      ),
        .I_key_in       ( I_key_n[3]   ),
        .O_key_trig_out ( S_key_trig[3])
    );

    //------------------------------------------------------------------
    // 步进发生器
    //   IDLE : 等按键（同一拍多键同时按下时，键号小的优先）
    //   CALC : 算出「还要前进几步」
    //   STEP : 每隔 GAP_MAX+1 拍发一个步进脉冲，直到 S_steps 归零
    //------------------------------------------------------------------
    localparam [1:0] IDLE = 2'd0;
    localparam [1:0] CALC = 2'd1;
    localparam [1:0] STEP = 2'd2;

    localparam [4:0] GAP_MAX = 5'd15;   // 步进脉冲间隔 = 16 拍 @24MHz ≈ 667ns

    reg [1:0] S_state;
    reg [1:0] S_target;                 // 目标模式 0..3
    reg [4:0] S_gap;                    // 步进间隔计数器
    reg [2:0] S_steps;                  // 剩余步进次数

    // 前进步数 = (目标 - 当前) mod 5。用「先加 5 再按需减 5」实现，
    // 避免 Verilog 取模运算；输入范围 S_target∈0..3、O_mode∈0..4，
    // 故 S_diff_w ∈ 1..8，减 5 后 ∈ 0..3，不减则 ∈ 1..4，合计 0..4 正确。
    wire [3:0] S_diff_w = {2'b00, S_target} + 4'd5 - {1'b0, O_mode};

    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            O_mode      <= 3'd0;        // ★上电默认 MODE 0（原图直通）★
            O_mode_chg  <= 1'b0;
            O_mode_tgl  <= 1'b0;
            O_mode_wrap <= 1'b0;
            S_state     <= IDLE;
            S_target    <= 2'd0;
            S_gap       <= 5'd0;
            S_steps     <= 3'd0;
        end
        else begin
            O_mode_chg <= 1'b0;         // 默认拉低，只在步进那一拍抬高

            case(S_state)
                IDLE: begin
                    if(S_key_trig != 4'd0) begin
                        // 多键同时按下：键号小的优先，保证行为确定
                        if(S_key_trig[0])      S_target <= 2'd0;
                        else if(S_key_trig[1]) S_target <= 2'd1;
                        else if(S_key_trig[2]) S_target <= 2'd2;
                        else                   S_target <= 2'd3;
                        S_state <= CALC;
                    end
                end

                CALC: begin
                    // 算出步数后就进入发脉冲状态（步数 0 表示已经在该模式，直接回 IDLE）
                    S_steps <= (S_diff_w >= 4'd5) ? (S_diff_w - 4'd5) : S_diff_w[2:0];
                    S_gap   <= 5'd0;
                    S_state <= STEP;
                end

                STEP: begin
                    if(S_steps == 3'd0)
                        S_state <= IDLE;
                    else if(S_gap != GAP_MAX)
                        S_gap <= S_gap + 5'd1;
                    else begin
                        S_gap <= 5'd0;
                        // ---- 发出一步：翻转 tgl；若这一步是 4→0，同时翻转 wrap ----
                        O_mode_tgl <= ~O_mode_tgl;
                        O_mode_chg <= 1'b1;
                        if(O_mode == 3'd4) begin
                            O_mode      <= 3'd0;
                            O_mode_wrap <= ~O_mode_wrap;   // ★只在回卷那一次翻第二根线★
                        end
                        else begin
                            O_mode <= O_mode + 3'd1;
                        end
                        S_steps <= S_steps - 3'd1;
                    end
                end

                default: S_state <= IDLE;
            endcase
        end
    end

endmodule
'''

note("[1] key_mode_ctrl.v 整文件重写")
t, enc, bom, n0 = load(F_KEY)
note("    备份 -> %s" % backup(F_KEY))
note("    原: %d B / enc=%s / bom=%s / %d 行" % (n0, enc, bom, t.count("\n")))
n1 = save(F_KEY, NEW_KEY, enc, bom)
note("    新: %d B / enc=%s / bom=%s" % (n1, enc, bom))

# =====================================================================
# 2) design_top_wrapper.v
# =====================================================================
note("[2] design_top_wrapper.v")
t, enc, bom, n0 = load(F_TOP)
note("    备份 -> %s" % backup(F_TOP))
lines = t.split("\n")

rep_sub(lines, "inout wire [1:0]  I_button,", "inout wire [3:0]  I_button,")

# 端口连接行：保留原缩进
i = [k for k, l in enumerate(lines) if ".I_key_n" in l]
assert len(i) == 1, "I_key_n 连接行数 = %d" % len(i)
k = i[0]
indent = lines[k][: lines[k].index(".I_key_n")]
eol = "\r" if lines[k].endswith("\r") else ""
lines[k] = indent + ".I_key_n    ( I_button        ),   // K1-K4 四键直选（bit0=K1/D5, bit1=K2/A9, bit2=K3/B9, bit3=K4/C7）" + eol

i = [k for k, l in enumerate(lines) if ".I_btn(" in l]
assert len(i) == 1, "I_btn 连接行数 = %d" % len(i)
k = i[0]
indent = lines[k][: lines[k].index(".I_btn(")]
eol = "\r" if lines[k].endswith("\r") else ""
lines[k] = indent + ".I_btn(4'b1111),   // ★AE/AG 手动键全部禁用★ 改 4 键后不能再接 I_button" + eol

rep_sub(lines, "//   I_button[1] = D5 (KEY1)，带内部上拉，按下为低电平",
        "//   K1..K4 = I_button[0..3] = D5 / A9 / B9 / C7（带内部上拉，按下为低电平）")
rep_sub(lines, "//   每按一次：MODE0 原图 → MODE1 灰度 → MODE2 伪彩热力图 → MODE3 二值化 → MODE4 卡通化 → 循环",
        "//   K1/K2/K3/K4 分别直选 MODE0 原图 / MODE1 灰度 / MODE2 伪彩热力图 / MODE3 二值化"
        "（不再循环；MODE4 卡通化因此没有按键入口）")
rep_sub(lines, "（inout wire [1:0] I_button）", "（inout wire [3:0] I_button）")

t = "\n".join(lines)
n1 = save(F_TOP, t, enc, bom)
note("    %d B -> %d B / enc=%s" % (n0, n1, enc))

# =====================================================================
# 3) pin.adc
# =====================================================================
note("[3] pin.adc")
t, enc, bom, n0 = load(F_PIN)
note("    备份 -> %s" % backup(F_PIN))
lines = t.split("\n")
eol = "\r" if lines[9].endswith("\r") else ""
new4 = [
    "set_pin_assignment\t{ I_button[0] }\t\t\t{ LOCATION = D5;  IOSTANDARD = LVCMOS33; DRIVESTRENGTH = 8; PULLTYPE = PULLUP; }",
    "set_pin_assignment\t{ I_button[1] }\t\t\t{ LOCATION = A9;  IOSTANDARD = LVCMOS33; DRIVESTRENGTH = 8; PULLTYPE = PULLUP; }",
    "set_pin_assignment\t{ I_button[2] }\t\t\t{ LOCATION = B9;  IOSTANDARD = LVCMOS33; DRIVESTRENGTH = 8; PULLTYPE = PULLUP; }",
    "set_pin_assignment\t{ I_button[3] }\t\t\t{ LOCATION = C7;  IOSTANDARD = LVCMOS33; DRIVESTRENGTH = 8; PULLTYPE = PULLUP; }",
]
assert "I_button[0]" in lines[9] and "N2" in lines[9], "pin.adc 第 10 行不是预期内容: %r" % lines[9]
assert "I_button[1]" in lines[10] and "D5" in lines[10], "pin.adc 第 11 行不是预期内容: %r" % lines[10]
lines[9:11] = [x + eol for x in new4]
t = "\n".join(lines)
n1 = save(F_PIN, t, enc, bom)
note("    %d B -> %d B / enc=%s" % (n0, n1, enc))

# =====================================================================
# 4) hdmi_mixer.v —— 本地模式计数器复位值 3'd2 → 3'd0
# =====================================================================
note("[4] hdmi_mixer.v")
t, enc, bom, n0 = load(F_MIX)
note("    备份 -> %s" % backup(F_MIX))
lines = t.split("\n")
rep_sub(lines, "S_algo_mode <= 3'd2;",
        "S_algo_mode <= 3'd0;              ")
rep_sub(lines, "// 与 my_algo.MODE_INIT 保持一致",
        "// 上电默认 MODE0，与 key_mode_ctrl / my_algo.MODE_INIT 保持一致")
rep_sub(lines, "S_algo_mode_2d <= 3'd2;", "S_algo_mode_2d <= 3'd0;")
t = "\n".join(lines)
n1 = save(F_MIX, t, enc, bom)
note("    %d B -> %d B / enc=%s" % (n0, n1, enc))

# =====================================================================
# 5) my_algo.v —— MODE_INIT 3'd2 → 3'd0
# =====================================================================
note("[5] my_algo.v")
t, enc, bom, n0 = load(F_ALG)
note("    备份 -> %s" % backup(F_ALG))
lines = t.split("\n")
rep_sub(lines, "parameter [2:0] MODE_INIT = 3'd2,", "parameter [2:0] MODE_INIT = 3'd0,")
rep_sub(lines, "// 上电默认模式（2 = 伪彩热力图）", "// 上电默认模式（0 = 原图直通；2026-10-10 由 2 改为 0）")
t = "\n".join(lines)
n1 = save(F_ALG, t, enc, bom)
note("    %d B -> %d B / enc=%s" % (n0, n1, enc))

# =====================================================================
# 6) isp_top.v —— .MODE_INIT(3'd2) → 3'd0
# =====================================================================
note("[6] isp_top.v")
t, enc, bom, n0 = load(F_ISP)
note("    备份 -> %s" % backup(F_ISP))
lines = t.split("\n")
rep_sub(lines, ".MODE_INIT  ( 3'd2   )", ".MODE_INIT  ( 3'd0   )")
t = "\n".join(lines)
n1 = save(F_ISP, t, enc, bom)
note("    %d B -> %d B / enc=%s" % (n0, n1, enc))

# =====================================================================
# 回读校验
# =====================================================================
note("")
note("=" * 78)
note("回读校验")
note("=" * 78)
chk = [
    (F_KEY, ["I_key_n   ,", "input  wire [3:0] I_key_n", "O_mode      <= 3'd0;", "GAP_MAX = 5'd15",
             "u_key_remove_shakes_mode3", "S_diff_w", "MODE 4（卡通化）不再有按键入口"]),
    (F_TOP, ["inout wire [3:0]  I_button,", ".I_key_n    ( I_button        ),", ".I_btn(4'b1111),"]),
    (F_PIN, ["LOCATION = D5;", "LOCATION = A9;", "LOCATION = B9;", "LOCATION = C7;"]),
    (F_MIX, ["S_algo_mode <= 3'd0;", "S_algo_mode_2d <= 3'd0;"]),
    (F_ALG, ["MODE_INIT = 3'd0,"]),
    (F_ISP, [".MODE_INIT  ( 3'd0   )"]),
]
bad = 0
for path, keys in chk:
    t2, _, _, n2 = load(path)
    for k in keys:
        c = t2.count(k)
        flag = "OK " if c >= 1 else "!! "
        if c < 1:
            bad += 1
        note("  %s %-46s x%d   %s" % (flag, k, c, os.path.basename(path)))
    note("      %s  %d B" % (os.path.basename(path), n2))

# 旧值必须已消失（仅报告，不计入 bad）
neg = [(F_PIN, "N2"), (F_TOP, "{I_button,2'b11}"), (F_ALG, "MODE_INIT = 3'd2,")]
for path, k in neg:
    t2, _, _, _ = load(path)
    c = t2.count(k)
    note("  %s 旧值已清除? %-24s x%d   %s" % ("OK " if c == 0 else "!! ", k, c, os.path.basename(path)))

note("")
note("异常项: %d" % bad)

with open(REPORT, "w", encoding="utf-8") as f:
    f.write("\n".join(log) + "\n")
print("report -> %s" % REPORT)
