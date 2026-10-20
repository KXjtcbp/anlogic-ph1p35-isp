# -*- coding: utf-8 -*-
"""
apply_cartoon.py  --  恢复"卡通化(MODE4)"的一键入口，并修掉 MODE4 的 OSD 显示 bug

背景（m02742）：卡通化是官方评分细则点名要求的功能，不能被移除或弱化。
  选题指南 2.6 评分标准「（一）基础扩展项（1）视频图像风格化处理或视觉增强」
  在《赛题解析二》里点名为「边缘提取与区域填充（卡通化处理）」
  ⇒ my_algo.v 的 MODE 4（f_cart 区域填充 + edg 描边）正是该实现，必须能一键直达。

改动清单：
  A. key_mode_ctrl.v
     A1 文件头"修改记录"追加本次条目
     A2 "作用"说明块：K4 改为 MODE4，长按 = MODE3，并写明评分依据
     A3 新增"长按检测"块（2 级同步 + 25bit 保持计数器 + 长按请求标志）
     A4 S_target 由 2bit 加宽到 3bit（目标模式 0..4）
     A5 S_diff_w 表达式与注释按 3bit 目标重写
     A6 主复位块：S_target 初值 3'd0，新增 S_long_done
     A7 主 always 的 else 开头：全部松手时复位 S_long_done
     A8 IDLE 分支：K4→MODE4；新增"长按→MODE3"分支
  B. hdmi_mixer.v
     B1 字形库函数注释补上 8='4'
     B2 字形库新增 4'd8 数字 '4' 的字形
     B3 OSD 取字形索引由"特例"改为统一的 4+mode（MODE4 显示为 "MODE 4"）
  C. design_top_wrapper.v
     C1/C2 例化处注释同步为新的按键语义

所有替换都要求"恰好命中 1 次"，否则整文件放弃（不写盘）。
"""
import io, os, re, sys, hashlib

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
BACKUP = r"E:\FPGA\_backup\20261010_cartoon"
os.makedirs(BACKUP, exist_ok=True)

F_KEY = os.path.join(ROOT, "my_algo", "key_mode_ctrl.v")
F_MIX = os.path.join(ROOT, "hdmi_mixer.v")
F_TOP = os.path.join(ROOT, "design_top_wrapper.v")


def lines2pat(lines):
    """把若干行拼成一个正则：行间允许 CRLF 或 LF 混用，行内内容全部转义。"""
    return r"\r?\n".join(re.escape(l) for l in lines)


def load(path):
    with open(path, "rb") as f:
        raw = f.read()
    txt = raw.decode("utf-8")
    return raw, txt


def apply(path, patches):
    raw, txt = load(path)
    orig_sha = hashlib.sha256(raw).hexdigest()[:16]
    print("=" * 78)
    print("FILE : %s" % path)
    print("BEFORE: %d bytes  sha16=%s" % (len(raw), orig_sha))
    new = txt
    ok = True
    for name, old_lines, new_text in patches:
        pat = lines2pat(old_lines)
        hits = len(re.findall(pat, new))
        if hits != 1:
            print("  [FAIL] %-6s 命中 %d 次（要求恰好 1 次）-> 整文件放弃" % (name, hits))
            ok = False
            break
        new = re.sub(pat, lambda m: new_text, new, count=1)
        print("  [ OK ] %-6s 替换 1 处" % name)
    if not ok:
        print("  >>> 未写盘")
        return False

    # 备份
    bak = os.path.join(BACKUP, os.path.basename(path) + ".pre_cartoon")
    if not os.path.exists(bak):
        with open(bak, "wb") as f:
            f.write(raw)

    out = new.encode("utf-8")
    # 先编码成功再写盘（教训：open(...,'wb') 会先截断文件）
    with open(path, "wb") as f:
        f.write(out)

    # 回读校验
    with open(path, "rb") as f:
        chk = f.read()
    if chk != out:
        print("  [FAIL] 回读不一致！")
        return False
    print("AFTER : %d bytes  sha16=%s  (backup: %s)"
          % (len(out), hashlib.sha256(out).hexdigest()[:16], bak))
    return True


# ===========================================================================
# A. key_mode_ctrl.v
# ===========================================================================
p_key = []

p_key.append((
    "A1", [
        "//                - 代价：MODE 4（卡通化）不再有按键入口。",
    ],
    "\n".join([
        "//                - 代价：MODE 4（卡通化）不再有按键入口。",
        "//    2026-10-10  （未提交）★按 m02742 要求恢复卡通化一键入口（评分细则硬要求）★",
        "//                - K4 短按由 MODE 3 改为 ★MODE 4（卡通化）★，一键直达；",
        "//                - 长按任意键 >=1s -> MODE 3（5 段彩条诊断模式，原诊断能力保留）；",
        "//                - 依据：选题指南 2.6 评分标准「（一）基础扩展项（1）视频图像",
        "//                  风格化处理或视觉增强」，在《赛题解析二》里点名为「边缘提取与",
        "//                  区域填充（卡通化处理）」；my_algo.v 的 MODE 4（f_cart 区域",
        "//                  填充 + edg 描边）正是该实现，属于计分功能，不能只藏在长按里。",
        "//                  同时满足 2.5 加分项（1）多算法切换与状态显示。",
        "//                - 同步修掉 hdmi_mixer.v 的 MODE 4 OSD 显示 bug（字形库补 '4'）。",
    ])
))

p_key.append((
    "A2", [
        "//  作用：把开发板上的 4 个按键变成「算法模式直选键」：",
        "//            K1 → MODE 0(原图直通)     K2 → MODE 1(灰度)",
        "//            K3 → MODE 2(伪彩热力图)   K4 → MODE 3(二值化)",
        "//        上电默认 MODE 0。到不了 MODE 4(卡通化) —— 这是刻意的取舍，",
        "//        4 个键正好对应 4 个模式，不需要长按/组合键。",
    ],
    "\n".join([
        "//  作用：把开发板上的 4 个按键变成「算法模式直选键」，5 个模式全部可达：",
        "//            K1 → MODE 0(原图直通)     K2 → MODE 1(灰度)",
        "//            K3 → MODE 2(伪彩热力图)   K4 → MODE 4(★卡通化★)",
        "//            长按任意键 >=1s           → MODE 3(5 段彩条诊断模式)",
        "//        上电默认 MODE 0。",
        "//        ★为什么 MODE 4 必须放在短按上：卡通化是评分细则「基础扩展项（1）",
        "//          视频图像风格化处理」点名的功能（见《赛题解析二》），属于计分项，",
        "//          一键直达比藏在长按里更稳妥；而 MODE 3 彩条在本工程里是诊断工具",
        "//          （my_algo.v 的注释写着「诊断用看得见的直方图」），放长按合适。★",
        "//        ★hdmi_mixer.v 的字形库原来没有数字 '4' 的字形，MODE 4 会被显示成",
        "//          「MODE 0」（与真正的 MODE 0 无法区分，直接违反评分项「状态显示」），",
        "//          本次已补字形并改成统一索引。★",
    ])
))

p_key.append((
    "A3", [
        "    //------------------------------------------------------------------",
        "    // 步进发生器",
        "    //   IDLE : 等按键（同一拍多键同时按下时，键号小的优先）",
        "    //   CALC : 算出「还要前进几步」",
        "    //   STEP : 每隔 GAP_MAX+1 拍发一个步进脉冲，直到 S_steps 归零",
        "    //------------------------------------------------------------------",
    ],
    "\n".join([
        "    //------------------------------------------------------------------",
        "    // ★长按检测：任一按键按住 >= T_HOLD 拍 → 置一次长按请求★",
        "    //   按键 active-low（松开=1，按下=0），先做 2 级同步再判断电平。",
        "    //   注：key_remove_shakes 已经把「按下」变成「按住 4.17ms 后仍按住」的单拍",
        "    //       脉冲（见该文件 :76-79 与 :110-111），所以短按动作在按下后约 4ms",
        "    //       就发生；长按只是在这个基础上再叠一次请求，两者互不干扰。",
        "    //   S_long_req 只在本 always 块里写，主 FSM 只读；主 FSM 用自己拥有的",
        "    //   S_long_done 记住「已经消费过」，避免同一个按住期间反复触发。",
        "    //------------------------------------------------------------------",
        "    localparam [24:0] T_HOLD = 25'd24_000_000;   // 1 s @ 24 MHz（本模块挂在 S_24m_clk）",
        "",
        "    reg  [3:0]  S_key_sync1;",
        "    reg  [3:0]  S_key_sync2;",
        "    reg  [24:0] S_hold_cnt;",
        "    reg         S_long_req;",
        "",
        "    wire S_all_released = &S_key_sync2;     // 4 个键全部松开（active-low ⇒ 全 1）",
        "",
        "    always @(posedge I_clk or negedge I_rst_n) begin",
        "        if(!I_rst_n) begin",
        "            S_key_sync1 <= 4'hF;",
        "            S_key_sync2 <= 4'hF;",
        "            S_hold_cnt  <= 25'd0;",
        "            S_long_req  <= 1'b0;",
        "        end",
        "        else begin",
        "            S_key_sync1 <= I_key_n;",
        "            S_key_sync2 <= S_key_sync1;",
        "",
        "            if(S_all_released) begin",
        "                S_hold_cnt <= 25'd0;        // 全部松开：计时清零，请求作废",
        "                S_long_req <= 1'b0;",
        "            end",
        "            else if(S_hold_cnt < T_HOLD) begin",
        "                S_hold_cnt <= S_hold_cnt + 25'd1;",
        "            end",
        "            else begin",
        "                S_long_req <= 1'b1;         // ★按住满 1s：置一次长按请求★",
        "            end",
        "        end",
        "    end",
        "",
        "    //------------------------------------------------------------------",
        "    // 步进发生器",
        "    //   IDLE : 等按键（同一拍多键同时按下时，键号小的优先）",
        "    //   CALC : 算出「还要前进几步」",
        "    //   STEP : 每隔 GAP_MAX+1 拍发一个步进脉冲，直到 S_steps 归零",
        "    //------------------------------------------------------------------",
    ])
))

p_key.append((
    "A4", [
        "    reg [1:0] S_target;                 // 目标模式 0..3",
    ],
    "    reg [2:0] S_target;                 // 目标模式 0..4（4 = 卡通化）"
))

p_key.append((
    "A5", [
        "    // 前进步数 = (目标 - 当前) mod 5。用「先加 5 再按需减 5」实现，",
        "    // 避免 Verilog 取模运算；输入范围 S_target∈0..3、O_mode∈0..4，",
        "    // 故 S_diff_w ∈ 1..8，减 5 后 ∈ 0..3，不减则 ∈ 1..4，合计 0..4 正确。",
        "    wire [3:0] S_diff_w = {2'b00, S_target} + 4'd5 - {1'b0, O_mode};",
    ],
    "\n".join([
        "    // 前进步数 = (目标 - 当前) mod 5。用「先加 5 再按需减 5」实现，",
        "    // 避免 Verilog 取模运算；输入范围 S_target∈0..4、O_mode∈0..4，",
        "    // 故 S_diff_w ∈ 0..9（4 bit 足够），减 5 后 ∈ 0..4，不减则 ∈ 1..4。",
        "    // 例：目标 4、当前 0 -> 4+5-0=9 -> 9-5=4 步（0→1→2→3→4）正确。",
        "    wire [3:0] S_diff_w = {1'b0, S_target} + 4'd5 - {1'b0, O_mode};",
    ])
))

p_key.append((
    "A6", [
        "            S_state     <= IDLE;",
        "            S_target    <= 2'd0;",
        "            S_gap       <= 5'd0;",
        "            S_steps     <= 3'd0;",
    ],
    "\n".join([
        "            S_state     <= IDLE;",
        "            S_target    <= 3'd0;",
        "            S_gap       <= 5'd0;",
        "            S_steps     <= 3'd0;",
        "            S_long_done <= 1'b0;",
    ])
))

p_key.append((
    "A7", [
        "        else begin",
        "            O_mode_chg <= 1'b0;         // 默认拉低，只在步进那一拍抬高",
        "",
        "            case(S_state)",
    ],
    "\n".join([
        "        else begin",
        "            O_mode_chg <= 1'b0;         // 默认拉低，只在步进那一拍抬高",
        "",
        "            // 全部松手：清掉「本次长按已消费」标志，下一次按住才能再触发一次",
        "            if(S_all_released)",
        "                S_long_done <= 1'b0;",
        "",
        "            case(S_state)",
    ])
))

p_key.append((
    "A8", [
        "                IDLE: begin",
        "                    if(S_key_trig != 4'd0) begin",
        "                        // 多键同时按下：键号小的优先，保证行为确定",
        "                        if(S_key_trig[0])      S_target <= 2'd0;",
        "                        else if(S_key_trig[1]) S_target <= 2'd1;",
        "                        else if(S_key_trig[2]) S_target <= 2'd2;",
        "                        else                   S_target <= 2'd3;",
        "                        S_state <= CALC;",
        "                    end",
        "                end",
    ],
    "\n".join([
        "                IDLE: begin",
        "                    if(S_key_trig != 4'd0) begin",
        "                        // 多键同时按下：键号小的优先，保证行为确定",
        "                        if(S_key_trig[0])      S_target <= 3'd0;   // K1 -> MODE 0 原图直通",
        "                        else if(S_key_trig[1]) S_target <= 3'd1;   // K2 -> MODE 1 灰度",
        "                        else if(S_key_trig[2]) S_target <= 3'd2;   // K3 -> MODE 2 伪彩热力图",
        "                        else                   S_target <= 3'd4;   // ★K4 -> MODE 4 卡通化★（评分细则点名的计分功能，一键直达）",
        "                        S_state <= CALC;",
        "                    end",
        "                    else if(S_long_req && !S_long_done) begin",
        "                        // ★长按任意键 >=1s -> MODE 3（5 段彩条诊断模式，原诊断能力保留）★",
        "                        S_long_done <= 1'b1;",
        "                        S_target    <= 3'd3;",
        "                        S_state     <= CALC;",
        "                    end",
        "                end",
    ])
))

p_key.append((
    "A9", [
        "    output reg  [2:0] O_mode    ,   // 本域当前算法模式（同域使用）",
    ],
    "    output reg  [2:0] O_mode    ,   // 本域当前算法模式 0..4（同域使用）"
))

# 补一个 S_long_done 的声明（放在 S_steps 声明之后）
p_key.append((
    "A10", [
        "    reg [4:0] S_gap;                    // 步进间隔计数器",
        "    reg [2:0] S_steps;                  // 剩余步进次数",
    ],
    "\n".join([
        "    reg [4:0] S_gap;                    // 步进间隔计数器",
        "    reg [2:0] S_steps;                  // 剩余步进次数",
        "    reg       S_long_done;              // 本次按住的长按请求是否已被消费",
    ])
))

# ===========================================================================
# B. hdmi_mixer.v
# ===========================================================================
p_mix = []

p_mix.append((
    "B1", [
        "    //   idx 0='M' 1='O' 2='D' 3='E' 4='0' 5='1' 6='2' 7='3'",
    ],
    "    //   idx 0='M' 1='O' 2='D' 3='E' 4='0' 5='1' 6='2' 7='3' 8='4'"
))

p_mix.append((
    "B2", [
        "    function [4:0] F_alg_char_bits;  // I_char: 0='M' 1='O' 2='D' 3='E' 4='0' 5='1' 6='2' 7='3'（注意：没有数字 '4' 的字形）",
    ],
    "    function [4:0] F_alg_char_bits;  // I_char: 0='M' 1='O' 2='D' 3='E' 4='0' 5='1' 6='2' 7='3' 8='4'（'4' 是 2026-10-10 补的）"
))

p_mix.append((
    "B3", [
        "                4'd7: begin // 3",
        "                    case(I_row)",
        "                        4'd0: F_alg_char_bits = 5'b11110;",
        "                        4'd1: F_alg_char_bits = 5'b00001;",
        "                        4'd2: F_alg_char_bits = 5'b00001;",
        "                        4'd3: F_alg_char_bits = 5'b01110;",
        "                        4'd4: F_alg_char_bits = 5'b00001;",
        "                        4'd5: F_alg_char_bits = 5'b00001;",
        "                        4'd6: F_alg_char_bits = 5'b11110;",
        "                        default: F_alg_char_bits = 5'b00000;",
        "                    endcase",
        "                end",
        "                default: F_alg_char_bits = 5'b00000;",
    ],
    "\n".join([
        "                4'd7: begin // 3",
        "                    case(I_row)",
        "                        4'd0: F_alg_char_bits = 5'b11110;",
        "                        4'd1: F_alg_char_bits = 5'b00001;",
        "                        4'd2: F_alg_char_bits = 5'b00001;",
        "                        4'd3: F_alg_char_bits = 5'b01110;",
        "                        4'd4: F_alg_char_bits = 5'b00001;",
        "                        4'd5: F_alg_char_bits = 5'b00001;",
        "                        4'd6: F_alg_char_bits = 5'b11110;",
        "                        default: F_alg_char_bits = 5'b00000;",
        "                    endcase",
        "                end",
        "                4'd8: begin // 4   （2026-10-10 新增：MODE 4 的状态显示需要）",
        "                    case(I_row)",
        "                        4'd0: F_alg_char_bits = 5'b10001;   // 左竖 + 右竖",
        "                        4'd1: F_alg_char_bits = 5'b10001;",
        "                        4'd2: F_alg_char_bits = 5'b10001;",
        "                        4'd3: F_alg_char_bits = 5'b01111;   // 横杠（含右竖交点）",
        "                        4'd4: F_alg_char_bits = 5'b00001;   // 只留右竖",
        "                        4'd5: F_alg_char_bits = 5'b00001;",
        "                        4'd6: F_alg_char_bits = 5'b00001;",
        "                        default: F_alg_char_bits = 5'b00000;",
        "                    endcase",
        "                end",
        "                default: F_alg_char_bits = 5'b00000;",
    ])
))

p_mix.append((
    "B4", [
        "                        // BUG(待修): 状态行最后一个字符位取字形时，MODE 4 走的是索引 4'd4，",
        "                        //   而 F_alg_char_bits 的索引 4 是数字 '0'（见 :517），于是 MODE 4 在屏上",
        "                        //   显示成 \"MODE 0\"，与真正的 MODE 0 完全无法区分。",
        "                        //   正确修法：往字符库补一个数字 '4' 的字形（新索引 8），并把取索引统一",
        "                        //   改成 4+mode（即 ({1'b0,S_algo_mode_2d} + 4'd4)），之后删掉这里的特例。",
        "                        //   本次只标注，不改代码。",
        "                        3'd5: S_alg_bits = F_alg_char_bits((S_algo_mode_2d == 3'd4) ? 4'd4 :  // 数字 4",
        "                                                         ({1'b0, S_algo_mode_2d} + 4'd4),",
        "                                                          {1'b0,S_alg_ly[2:0]});          // 数字 0..3",
    ],
    "\n".join([
        "                        // [2026-10-10 已修] 原来 MODE 4 走的是索引 4'd4，而 F_alg_char_bits 的",
        "                        //   索引 4 是数字 '0'，导致 MODE 4 在屏上显示成 \"MODE 0\"，与真正的",
        "                        //   MODE 0 无法区分 —— 这直接违反评分项「多算法切换与★状态显示★」,",
        "                        //   也会让评委以为卡通化没生效。",
        "                        //   修法：字形库补了数字 '4'（新索引 4'd8），这里统一用 4+mode 取索引，",
        "                        //   MODE 0..4 -> 字形 '0'..'4' 全部正确。",
        "                        3'd5: S_alg_bits = F_alg_char_bits({1'b0, S_algo_mode_2d} + 4'd4,",
        "                                                          {1'b0,S_alg_ly[2:0]});  // 数字 0..4",
    ])
))

# ===========================================================================
# C. design_top_wrapper.v
# ===========================================================================
p_top = []

p_top.append((
    "C1", [
        "\t//   K1/K2/K3/K4 分别直选 MODE0 原图 / MODE1 灰度 / MODE2 伪彩热力图 / MODE3 二值化（不再循环；MODE4 卡通化因此没有按键入口）",
    ],
    "\t//   K1/K2/K3/K4 分别直选 MODE0 原图 / MODE1 灰度 / MODE2 伪彩热力图 / MODE4 卡通化（不再循环）；"
    "\n\t//   长按任意键 >=1s -> MODE3（5 段彩条诊断模式）。"
    "\n\t//   ★MODE4 卡通化是评分细则点名的功能（基础扩展项(1) 视频图像风格化处理），必须一键直达。★"
))

p_top.append((
    "C2", [
        "\t\t.I_key_n    ( I_button        ),   // K1-K4 四键直选（bit0=K1/D5, bit1=K2/A9, bit2=K3/B9, bit3=K4/C7）",
    ],
    "\t\t.I_key_n    ( I_button        ),   // K1-K4 四键直选 + 长按（bit0=K1/D5, bit1=K2/A9, bit2=K3/B9, bit3=K4/C7）"
))

# ===========================================================================
if __name__ == "__main__":
    r1 = apply(F_KEY, p_key)
    r2 = apply(F_MIX, p_mix)
    r3 = apply(F_TOP, p_top)
    print("=" * 78)
    print("RESULT: key_mode_ctrl=%s  hdmi_mixer=%s  design_top_wrapper=%s"
          % (r1, r2, r3))
