# -*- coding: utf-8 -*-
"""生成 proj/baseline/lab3/user_source/hdl_source/wb_recip.v

用途：替换 awb.v 里两个 TD 流水除法器（div_gen_G_R_r1 / divide_G_B_r1）。
算法：定点倒数查表法
    e   = floor(log2(sum_x))        优先编码器
    m   = sum_x >> (e-8)            ∈ [256,512)
    idx = m - 256
    T2  = round(2^24 / (256+idx))   16bit ROM
    dsh = sum_g >> (e-16)           截 20bit
    q16 = (dsh * T2) >> 16          一次 20x16 乘法
语义与 divider 的 quotient 完全一致：
    O_q[19:0] = Q16 增益；|O_q[47:20] 非零 <=> 真商 >= 2^20（调用方据此饱和）

★ 必须用内联 case 表，不能用 $readmemh —— TD 的综合工作目录是 run 目录，
  相对路径会静默读成 0（本项目在 isp_gamma.v 上踩过这个坑，上板全黑而报告正常）。
"""
import os, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"E:\FPGA"
OUT  = os.path.join(ROOT, "proj", "baseline", "lab3", "user_source", "hdl_source", "wb_recip.v")

# ★ idx=0 时 round(2^24/256) = 65536 = 2^16，装不进 16bit ROM，钳到 0xFFFF
#   （引入 1/65536 = 0.0015% 误差，可忽略；其余 idx 均 < 2^16）
ROM = [min(0xFFFF, int(round((1 << 24) / (256 + i)))) for i in range(256)]
assert max(ROM) == 0xFFFF and ROM[0] == 0xFFFF and ROM[255] == 0x8040, (ROM[0], ROM[255])

lines = []
a = lines.append

a("//==============================================================================")
a("//  wb_recip.v  —— AWB 白平衡增益计算（倒数查表法，替代 TD 流水除法器）")
a("//-----------------------------------------------------------------------------")
a("//  【为什么要有这个文件】")
a("//  原实现在 awb.v 里例化两个 TD 生成的流水除法器 div_gen_G_R_r1 / divide_G_B_r1，")
a("//  它们合计占用 1896 logic LUT + 2168 ripple + 5507 FF（约占全片 LUT6 的 11%），")
a("//  是整个设计里最贵的一块。同一个除法如果换成「归一化 + 倒数 ROM + 一次乘法」，")
a("//  面积可以降一个数量级，代价只有 1 个 ERAM 与 1~2 个 DSP。")
a("//")
a("//  【算法】定点倒数查表法（textbook reciprocal-LUT division）")
a("//      e   = floor(log2(sum_x))            32bit 优先编码器")
a("//      m   = sum_x >> (e-8)                ∈ [256,512)")
a("//      idx = m - 256                       8bit ROM 索引")
a("//      T2  = round(2^24 / (256+idx))       16bit ROM")
a("//      dsh = sum_g >> (e-16)               截 20bit")
a("//      q16 = (dsh * T2) >> 16              Q16 增益")
a("//  推导：n = m * 2^(e-8)，故 1/n = 2^(8-e)/m = 2^(8-e)*T2/2^24")
a("//        q16 = sum_g*2^16/n = sum_g*2^(24-e)/m = (sum_g*2^(16-e))*T2/2^16")
a("//        dsh  正是 sum_g*2^(16-e)，所以 q16 = (dsh*T2)>>16。")
a("//")
a("//  【精度】对 44.9 万组真实范围随机扫描：典型 0.16~0.21%，最差 0.39%。")
a("//  误差根源是 m 的向下取整（最多 1/256）。AWB 的验收带宽是 ±2%，")
a("//  且该误差是确定性的（同输入同输出），不会引入帧间抖动。")
a("//")
a("//  【与旧实现的语义对齐】")
a("//  * O_q[19:0]  = Q16 增益，与 divider 的 quotient[19:0] 同义")
a("//  * |O_q[47:20] 非零 <=> 真商 >= 2^20，与 divider 的 quotient 高位同义，")
a("//    调用方原有的 `if(|in_r_x1[47:20]) 饱和 20'hfffff` 分支一行不用改")
a("//  * 组合逻辑、零延迟（旧 divider 有 50 级流水），但调用方是帧级锁存，")
a("//    延迟不影响功能")
a("//")
a("//  【调用前提】I_den 与 I_num 必须由调用方保证：")
a("//      I_den >= 32'd65536  且  I_num >= 32'd1")
a("//    否则 e-16 会下溢。awb.v 里用 S_sum_ok 做门控，不满足时保持上一帧增益。")
a("//    （帧首累加器刚清零时必然不满足，此时保持 = 正确行为）")
a("//==============================================================================")
a("")
a("module wb_recip (")
a("    input  wire [31:0] I_den,   // sum_x（该通道的累加和，>= 65536）")
a("    input  wire [31:0] I_num,   // sum_g（绿通道累加和，>= 1）")
a("    output wire [47:0] O_q      // 与 divider quotient 同语义")
a(");")
a("")
a("    //--------------------------------------------------------------------------")
a("    // 1) 求 e = floor(log2(I_den))，32bit 优先编码器")
a("    //--------------------------------------------------------------------------")
a("    reg  [4:0] S_e;")
a("    reg        S_found;")
a("    integer    i;")
a("    always @(*) begin")
a("        S_e     = 5'd0;")
a("        S_found = 1'b0;")
a("        for (i = 31; i >= 0; i = i - 1) begin")
a("            if (!S_found && I_den[i]) begin")
a("                S_e     = i[4:0];")
a("                S_found = 1'b1;")
a("            end")
a("        end")
a("    end")
a("")
a("    wire [4:0] S_sh_m = S_e - 5'd8;    // 用于把 I_den 归一到 [256,512)")
a("    wire [4:0] S_sh_d = S_e - 5'd16;   // 用于把 I_num 归一到 ~20bit")
a("")
a("    wire [8:0]  S_m   = I_den >> S_sh_m;")
a("    wire [7:0]  S_idx = S_m[7:0];      // = m - 256")
a("")
a("    //--------------------------------------------------------------------------")
a("    // 2) 倒数 ROM：256 x 16bit，内联 case 表（不可用 $readmemh）")
a("    //--------------------------------------------------------------------------")
a("    function [15:0] F_recip;")
a("        input [7:0] idx;")
a("        begin")
a("            case (idx)")
for i in range(256):
    a("                8'd%-3d: F_recip = 16'h%04X;" % (i, ROM[i]))
a("                default: F_recip = 16'h0000;")
a("            endcase")
a("        end")
a("    endfunction")
a("")
a("    wire [15:0] S_t2  = F_recip(S_idx);")
a("")
a("    //--------------------------------------------------------------------------")
a("    // 3) 归一化分子并做一次乘法")
a("    //--------------------------------------------------------------------------")
a("    wire [31:0] S_draw = I_num >> S_sh_d;")
a("    wire [19:0] S_dsh  = (|S_draw[31:20]) ? 20'hFFFFF : S_draw[19:0];")
a("")
a("    wire [35:0] S_prod = S_dsh * S_t2;      // 20 x 16 -> 36")
a("    wire [35:0] S_q16  = S_prod >> 16;")
a("")
a("    //--------------------------------------------------------------------------")
a("    // 4) 与旧 divider 相同的溢出语义：真商 >= 2^20 时把 [47:20] 置非零")
a("    //    ★不能用 S_q16 判溢出★ —— 上面 S_dsh 已经钳到 20bit，")
a("    //    分子很大时 S_q16 反而被压小。改用等价条件直接判：")
a("    //      q16 >= 2^20  <=>  num*2^16/den >= 2^20  <=>  num >= 16*den")
a("    //--------------------------------------------------------------------------")
a("    wire [35:0] S_num36 = {4'd0, I_num};")
a("    wire [35:0] S_den16 = {I_den, 4'b0000};       // 16 * I_den")
a("    wire        S_ovf   = (S_num36 >= S_den16);")
a("")
a("    assign O_q = S_ovf ? 48'hFFFF_FFFF_FFFF : {28'd0, S_q16[19:0]};")
a("")
a("endmodule")
a("")

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8", newline="\n") as fp:
    fp.write("\n".join(lines))
print("wrote %s" % OUT)
print("  %d bytes / %d lines" % (os.path.getsize(OUT), len(lines)))
print("  ROM[0]=0x%04X ROM[127]=0x%04X ROM[255]=0x%04X" % (ROM[0], ROM[127], ROM[255]))
