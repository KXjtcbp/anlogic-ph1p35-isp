# -*- coding: utf-8 -*-
"""awb.v 三项修复（2026-10-12k）

背景（实测）：
  2026-10-12 21:30~21:49 的 8 张遥测图，把 AWB 算出的增益反推一遍：
      需要的增益 = 1 / (实测输出 R/G ÷ 它给的增益)
      缺口 = 1 - 给 / 需要
  结果 R 恒定差 17.0~17.4%、B 恒定差 8.3~8.9%，与增益大小（1.12x~1.28x）和场景都无关。
  恒定百分比 ⇒ 采样有偏，不是时序/溢出/饱和。

改动：
  1) rgb888_*_d[1:3] / rgb888_*_d0[1:3] 补上赋值 —— 原先 4 元素数组只赋了 [0]，
     其余 3 路是悬空 wire。
  2) rgb_sum 与 sum_* 累加器改成 4 路全累加（原来只累加 96bit 字里的第 0 个像素，
     等于每 4 个像素丢 3 个）。
  3) sum_* 初值 1 -> 0（语义上应为 0）。
  4) in_r_r1 / in_b_r1 的复位条件去掉 I_tuser —— 原来每帧开头被打回 1.000x，
     再靠 done 在整帧里用"运行中的部分和"慢慢爬回来，等于每帧前半段没有白平衡。
"""
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\awb.v"
BAK = r"E:\FPGA\_backup\20261012k_awb_4lane"

raw = open(SRC, "rb").read()
nl = "\r\n" if raw.count(b"\r\n") > raw.count(b"\n") // 2 else "\n"
txt = raw.decode("utf-8", errors="replace").replace("\r\n", "\n")

if os.path.isdir(BAK):
    shutil.rmtree(BAK)
os.makedirs(BAK)
shutil.copy2(SRC, os.path.join(BAK, "awb.v.before"))
print("备份 -> %s\\awb.v.before  (%d B)" % (BAK, os.path.getsize(SRC)))
print("行尾: %s" % ("CRLF" if nl == "\r\n" else "LF"))

REPL = []

# ---- 1) rgb888_*_d 补 3 路（组合路径，来自 I_tdata） ----
old = """assign  rgb888_r_d[0] = I_tdata[16+:8];
assign  rgb888_g_d[0] = I_tdata[8+:8];
assign  rgb888_b_d[0] = I_tdata[0+:8];"""
new = """assign  rgb888_r_d[0] = I_tdata[16+:8];
assign  rgb888_g_d[0] = I_tdata[8+:8];
assign  rgb888_b_d[0] = I_tdata[0+:8];
// [HDR-2026-10-12k] 补上第 1~3 路。原文件这两个 4 元素数组只赋了 [0]，
// 其余三路是悬空 wire；白平衡要按整帧统计，不能只取 1/4 的像素。
assign  rgb888_r_d[1] = I_tdata[40+:8];
assign  rgb888_g_d[1] = I_tdata[32+:8];
assign  rgb888_b_d[1] = I_tdata[24+:8];
assign  rgb888_r_d[2] = I_tdata[64+:8];
assign  rgb888_g_d[2] = I_tdata[56+:8];
assign  rgb888_b_d[2] = I_tdata[48+:8];
assign  rgb888_r_d[3] = I_tdata[88+:8];
assign  rgb888_g_d[3] = I_tdata[80+:8];
assign  rgb888_b_d[3] = I_tdata[72+:8];"""
REPL.append(("rgb888_*_d[1:3]", old, new))

# ---- 1b) rgb888_*_d0 补 3 路（打一拍路径，来自 I_tdata_d0） ----
old = """assign  rgb888_r_d0[0] = I_tdata_d0[16+:8];
assign  rgb888_g_d0[0] = I_tdata_d0[8+:8];
assign  rgb888_b_d0[0] = I_tdata_d0[0+:8];"""
new = """assign  rgb888_r_d0[0] = I_tdata_d0[16+:8];
assign  rgb888_g_d0[0] = I_tdata_d0[8+:8];
assign  rgb888_b_d0[0] = I_tdata_d0[0+:8];
// [HDR-2026-10-12k] 同上，补第 1~3 路（偏移与 data_d1 的拆法一致）
assign  rgb888_r_d0[1] = I_tdata_d0[40+:8];
assign  rgb888_g_d0[1] = I_tdata_d0[32+:8];
assign  rgb888_b_d0[1] = I_tdata_d0[24+:8];
assign  rgb888_r_d0[2] = I_tdata_d0[64+:8];
assign  rgb888_g_d0[2] = I_tdata_d0[56+:8];
assign  rgb888_b_d0[2] = I_tdata_d0[48+:8];
assign  rgb888_r_d0[3] = I_tdata_d0[88+:8];
assign  rgb888_g_d0[3] = I_tdata_d0[80+:8];
assign  rgb888_b_d0[3] = I_tdata_d0[72+:8];"""
REPL.append(("rgb888_*_d0[1:3]", old, new))

# ---- 2) rgb_sum 四路 ----
old = """            if(!I_rst_n) begin
                rgb_sum[0] <= 0;
            end
            else if(I_tvalid)begin
                rgb_sum[0] <= rgb888_r_d[0] + rgb888_g_d[0] + rgb888_b_d[0];
            end"""
new = """            if(!I_rst_n) begin
                rgb_sum[0] <= 0;
                rgb_sum[1] <= 0;
                rgb_sum[2] <= 0;
                rgb_sum[3] <= 0;
            end
            else if(I_tvalid)begin
                // [HDR-2026-10-12k] 四路各自算 R+G+B（白点排除要逐像素判）
                rgb_sum[0] <= rgb888_r_d[0] + rgb888_g_d[0] + rgb888_b_d[0];
                rgb_sum[1] <= rgb888_r_d[1] + rgb888_g_d[1] + rgb888_b_d[1];
                rgb_sum[2] <= rgb888_r_d[2] + rgb888_g_d[2] + rgb888_b_d[2];
                rgb_sum[3] <= rgb888_r_d[3] + rgb888_g_d[3] + rgb888_b_d[3];
            end"""
REPL.append(("rgb_sum 四路", old, new))

# ---- 3) 累加器四路 + 初值 0 ----
old = """            if (!I_rst_n || I_tuser) begin
                // 复位或行开始信号有效时，清零累加器
                sum_r[0] <= 1;
                sum_g[0] <= 1;
                sum_b[0] <= 1;
            end else if (I_tvalid_r0 && (rgb_sum[0] < 720)) begin
                // 当输入有效时，累加RGB分量的值
                sum_r[0] <= sum_r[0] + rgb888_r_d0[0];
                sum_g[0] <= sum_g[0] + rgb888_g_d0[0];
                sum_b[0] <= sum_b[0] + rgb888_b_d0[0];
            end"""
new = """            if (!I_rst_n || I_tuser) begin
                // 复位或帧起始时清零累加器
                // [HDR-2026-10-12k] 初值由 1 改 0：一帧 92 万个样本，初值 1 数值上
                // 可忽略，但语义上应为 0（原值会让空累加器的比值偏成 1.0）。
                sum_r[0] <= 0;
                sum_g[0] <= 0;
                sum_b[0] <= 0;
            end else if (I_tvalid_r0) begin
                // [HDR-2026-10-12k] ★★ 四路全累加 ★★
                //   原写法只累加 rgb888_*_d0[0]（96bit 字里的第 0 个像素），
                //   等于每 4 个像素只统计 1 个。2026-10-12 21:30~21:49 的 8 张
                //   遥测图反推出：AWB 算出的增益恒定比灰世界需要的低
                //   17.0~17.4%(R) / 8.3~8.9%(B)，与增益大小和场景都无关，
                //   是恒定百分比 => 采样有偏。改成 4 路全进。
                //   ★四路必须先加成一个增量再做一次累加★：同一 always 块里对同一
                //   个 reg 多次非阻塞赋值，只有最后一条生效（会丢掉前三路）。
                sum_r[0] <= sum_r[0] + inc_r;
                sum_g[0] <= sum_g[0] + inc_g;
                sum_b[0] <= sum_b[0] + inc_b;
            end"""
REPL.append(("累加器四路+初值0", old, new))

# 增量组合逻辑（放在累加 always 之前）
old = """        // 对每个通道的值进行累加，用于计算平均值
        always @(posedge I_clk or negedge I_rst_n) begin"""
new = """        // [HDR-2026-10-12k] 四路增量（白点排除逐像素判：该像素 R+G+B < 720 才计入）
        wire [31:0] inc_r = ((rgb_sum[0] < 720) ? {24'd0, rgb888_r_d0[0]} : 32'd0)
                          + ((rgb_sum[1] < 720) ? {24'd0, rgb888_r_d0[1]} : 32'd0)
                          + ((rgb_sum[2] < 720) ? {24'd0, rgb888_r_d0[2]} : 32'd0)
                          + ((rgb_sum[3] < 720) ? {24'd0, rgb888_r_d0[3]} : 32'd0);
        wire [31:0] inc_g = ((rgb_sum[0] < 720) ? {24'd0, rgb888_g_d0[0]} : 32'd0)
                          + ((rgb_sum[1] < 720) ? {24'd0, rgb888_g_d0[1]} : 32'd0)
                          + ((rgb_sum[2] < 720) ? {24'd0, rgb888_g_d0[2]} : 32'd0)
                          + ((rgb_sum[3] < 720) ? {24'd0, rgb888_g_d0[3]} : 32'd0);
        wire [31:0] inc_b = ((rgb_sum[0] < 720) ? {24'd0, rgb888_b_d0[0]} : 32'd0)
                          + ((rgb_sum[1] < 720) ? {24'd0, rgb888_b_d0[1]} : 32'd0)
                          + ((rgb_sum[2] < 720) ? {24'd0, rgb888_b_d0[2]} : 32'd0)
                          + ((rgb_sum[3] < 720) ? {24'd0, rgb888_b_d0[3]} : 32'd0);

        // 对每个通道的值进行累加，用于计算平均值
        always @(posedge I_clk or negedge I_rst_n) begin"""
REPL.append(("四路增量 wire", old, new))

# ---- 4) 增益复位去掉 I_tuser ----
old = """        if(!I_rst_n || I_tuser)begin
            in_r_r1 <= 20'h10000;
            in_b_r1 <= 20'h10000;
        end"""
new = """        // [HDR-2026-10-12k] ★★ 复位条件去掉 I_tuser ★★
        //   原写法每帧帧首把 R/B 增益打回 1.000x，再靠 done[0] 用"运行中的部分和"
        //   在整帧里慢慢爬回来 => 每帧前半段等于没有白平衡，画面出现纵向色偏，
        //   且帧平均的实际校正量小于除法器算出来的值。白平衡是帧间慢变量，
        //   应当跨帧保持并收敛，只在真复位时回 1.000x。
        if(!I_rst_n)begin
            in_r_r1 <= 20'h10000;
            in_b_r1 <= 20'h10000;
        end"""
REPL.append(("增益复位去 I_tuser", old, new))

for name, o, n in REPL:
    cnt = txt.count(o)
    if cnt != 1:
        print("!! 失败 [%s]: 精确匹配到 %d 处（应为 1）" % (name, cnt))
        sys.exit(1)
    txt = txt.replace(o, n)
    print("OK  [%s]" % name)

out = txt.replace("\n", nl).encode("utf-8")
open(SRC, "wb").write(out)
print("\n写回 %s  %d B -> %d B  行尾 %s  首3字节 %s" %
      (SRC, len(raw), len(out), nl.replace("\r", "\\r").replace("\n", "\\n"), out[:3].hex()))
for probe in ("rgb888_r_d0[3]", "rgb_sum[3]", "sum_r[0] <= 0;", "if(!I_rst_n)begin"):
    print("  含 %-22s : %s" % (probe, probe in txt))
