# -*- coding: utf-8 -*-
"""
模块 A（黑电平校正 BLC）配套生成 / 核对脚本
=============================================
用法：
    python gen_blc_module_a.py            # 生成 + 核对 + 出图
    python gen_blc_module_a.py --check    # 只核对，不写文件

产出（全部落在 _analysis/lut/blc/ 与 _analysis/out/）：
  1. blc_levels.hex        16 档黑电平的 ROM 初值（10bit，$readmemh 格式）
                            —— 供「模块 A 的动态黑电平」预留接口使用
  2. blc_levels_pkg.vh     Verilog include：localparam + 选择常量
  3. blc_gamma_composite.csv  BLC -> S 曲线的合成响应（用于纸面验证）
  4. blc_module_a.png      合成曲线图（四条：两世界 x 旁路/启用）

核对（--check 也会跑）：
  ★ 断言 isp_gamma.v 的内联表 == gamma_lut_twoseg_p160_a050.hex ★
    这是「综合上板结果 == 仿真结果 == Python 纸面结果」的唯一保证。
    一旦内联表和 hex 不一致，纸面推演就全部失效（历史上踩过一次：
    相对路径 $readmemh 读不到 -> 表全 0 -> 上板全黑而报告全绿）。
"""
import os
import re
import sys
import math

ROOT = r"E:\FPGA"
GAMMA_HEX = os.path.join(ROOT, "_analysis", "lut", "gamma_lut_twoseg_p160_a050.hex")
ISP_GAMMA = os.path.join(ROOT, "proj", "baseline", "lab3", "user_source",
                         "hdl_source", "isp", "isp_gamma.v")
OUT_DIR = os.path.join(ROOT, "_analysis", "lut", "blc")
OUT_PNG = os.path.join(ROOT, "_analysis", "out", "blc_module_a.png")

# ---------------------------------------------------------------- 模块 A 参数
# 黑电平 16 档：level = 40 + 2*i，i = 0..15  =>  40,42,...,70
# 默认 index = 8  ->  56（= 2026-10-09 ChipWatcher 实测基座下限 57 减 1）
BLC_BASE = 40
BLC_STEP = 2
BLC_N = 16
BLC_DEFAULT_IDX = 8
assert BLC_BASE + BLC_STEP * BLC_DEFAULT_IDX == 56

ROUND_ADD = 2          # mipi_to_raw_converter.v 的四舍五入补偿


def load_gamma_hex(path):
    v = []
    for line in open(path, encoding="utf-8"):
        s = line.strip()
        if not s or s.startswith(("#", "//", ";")):
            continue
        v.append(int(s, 16))
    assert len(v) == 256, ("gamma hex 行数不是 256", len(v))
    return v


def load_gamma_inline(path):
    """从 isp_gamma.v 里抠出 mem_b00 的 256 个初值。"""
    txt = open(path, encoding="utf-8").read()
    hits = re.findall(r"mem_b00\[\s*(\d+)\]\s*=\s*8'h([0-9a-fA-F]{1,2})", txt)
    d = {}
    for idx, val in hits:
        d[int(idx)] = int(val, 16)
    missing = [i for i in range(256) if i not in d]
    assert not missing, ("isp_gamma.v 内联表缺条目", missing[:10])
    return [d[i] for i in range(256)]


def check_inline_vs_hex():
    hex_t = load_gamma_hex(GAMMA_HEX)
    inl_t = load_gamma_inline(ISP_GAMMA)
    bad = [i for i in range(256) if hex_t[i] != inl_t[i]]
    print("[核对 1] isp_gamma.v 内联表 vs gamma_lut_twoseg_p160_a050.hex")
    print("         hex  :", " ".join("%02x" % v for v in hex_t[:8]), "...")
    print("         inline:", " ".join("%02x" % v for v in inl_t[:8]), "...")
    if bad:
        print("         ★ 不一致 %d 处，前 10 个：%s" % (len(bad), bad[:10]))
        for i in bad[:10]:
            print("           mem[%3d] hex=%02x inline=%02x" % (i, hex_t[i], inl_t[i]))
        raise SystemExit("内联表与 hex 不一致 —— 纸面推演不可信，先修表")
    print("         => 完全一致（256/256），纸面推演可用%s" % "")
    return hex_t


def blc_levels():
    return [BLC_BASE + BLC_STEP * i for i in range(BLC_N)]


def blc_to_8bit(raw10, level, bypass):
    """与 mipi_to_raw_converter.v:104 逐位等价的定点模型。"""
    if bypass:
        return (raw10 >> 2) & 0xFF
    d = (raw10 - level) if raw10 > level else 0
    return ((d + ROUND_ADD) >> 2) & 0xFF


def composite(raw10, level, bypass_bl, gamma_tbl):
    return gamma_tbl[blc_to_8bit(raw10, level, bypass_bl)]


def fmt_table_check(gamma_tbl):
    print()
    print("[核对 2] 三种模型对同一 raw10 基座的合成输出（= 盖镜头时屏幕上会看到的 Y）")
    print("         基座 raw10 | 旁路+曲线关 | 旁路+曲线开 | BL=56+曲线开 | BL=42+曲线开")
    for raw in (13, 20, 28, 42, 56, 67, 72, 80):
        a = raw >> 2
        b = composite(raw, 56, True, gamma_tbl)
        c = composite(raw, 56, False, gamma_tbl)
        d = composite(raw, 42, False, gamma_tbl)
        print("         %10d | %11d | %11d | %12d | %12d" % (raw, a, b, c, d))
    print("         （raw10 基座 = 8bit 读数 x4；旁路+曲线关那列就是 raw/4）")


def gen_levels_files():
    lv = blc_levels()
    os.makedirs(OUT_DIR, exist_ok=True)
    p_hex = os.path.join(OUT_DIR, "blc_levels.hex")
    # ★ .hex 保持纯十六进制，不带注释行 ★
    #   $readmemh 对注释的支持各家实现不一致；要读得进就得干净。
    #   档位规则写在 blc_levels_pkg.vh 和本脚本头部。
    with open(p_hex, "w", encoding="ascii", newline="\n") as f:
        for v in lv:
            f.write("%03x\n" % v)

    p_vh = os.path.join(OUT_DIR, "blc_levels_pkg.vh")
    with open(p_vh, "w", encoding="utf-8", newline="\n") as f:
        f.write("// ===================================================================\n")
        f.write("// blc_levels_pkg.vh —— 模块 A（黑电平校正）参数包\n")
        f.write("// 由 _analysis/scripts/gen_blc_module_a.py 生成，请勿手改\n")
        f.write("// 生成规则：level = %d + %d * index  （index 0..%d）\n" % (BLC_BASE, BLC_STEP, BLC_N - 1))
        f.write("// 默认 index = %d -> level = %d （10-09 ChipWatcher 实测基座下限 57 减 1）\n"
                % (BLC_DEFAULT_IDX, lv[BLC_DEFAULT_IDX]))
        f.write("// ===================================================================\n")
        f.write("`ifndef BLC_LEVELS_PKG_VH\n`define BLC_LEVELS_PKG_VH\n\n")
        for i, v in enumerate(lv):
            mark = "  // <= 默认" if i == BLC_DEFAULT_IDX else ""
            f.write("localparam [9:0] BLC_LEVEL_%02d = 10'd%-3d;%s\n" % (i, v, mark))
        f.write("\nlocalparam [3:0] BLC_DEFAULT_IDX = 4'd%d;\n" % BLC_DEFAULT_IDX)
        f.write("localparam [9:0] BLC_DEFAULT_LEVEL = BLC_LEVEL_%02d;\n\n" % BLC_DEFAULT_IDX)
        f.write("// 4bit index -> 10bit level\n")
        f.write("function [9:0] blc_level_of;\n    input [3:0] idx;\n    begin\n        case (idx)\n")
        for i, v in enumerate(lv):
            f.write("            4'd%-2d : blc_level_of = 10'd%d;\n" % (i, v))
        f.write("            default: blc_level_of = BLC_DEFAULT_LEVEL;\n")
        f.write("        endcase\n    end\nendfunction\n\n`endif\n")
    print()
    print("[生成] %s  (%d 档: %s)" % (p_hex, len(lv), ", ".join(map(str, lv))))
    print("[生成] %s" % p_vh)
    return lv


def gen_csv_and_plot(gamma_tbl):
    os.makedirs(OUT_DIR, exist_ok=True)
    p_csv = os.path.join(OUT_DIR, "blc_gamma_composite.csv")
    with open(p_csv, "w", encoding="utf-8", newline="\n") as f:
        f.write("raw10,bypass_gammaoff,bypass_gammaon,bl56_gammaon,bl42_gammaon\n")
        for raw in range(0, 1024, 1):
            f.write("%d,%d,%d,%d,%d\n" % (
                raw, raw >> 2,
                composite(raw, 56, True, gamma_tbl),
                composite(raw, 56, False, gamma_tbl),
                composite(raw, 42, False, gamma_tbl)))
    print("[生成] %s" % p_csv)

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception as e:                                   # pragma: no cover
        print("[跳过] 出图失败（%s）—— CSV 仍然可用" % e)
        return

    x = list(range(1024))
    fig, ax = plt.subplots(1, 2, figsize=(13, 5.2), dpi=110)

    ax[0].plot(x, [v >> 2 for v in x], "--", lw=1.2, color="#888888", label="BLC bypass, gamma off (= raw/4)")
    ax[0].plot(x, [composite(v, 56, True, gamma_tbl) for v in x], lw=1.8, color="#2b7bba", label="BLC bypass, gamma ON")
    ax[0].plot(x, [composite(v, 56, False, gamma_tbl) for v in x], lw=1.8, color="#d94b3b", label="BL=56 ON, gamma ON")
    ax[0].plot(x, [composite(v, 42, False, gamma_tbl) for v in x], lw=1.8, color="#e8a13a", label="BL=42 ON, gamma ON")
    ax[0].set_title("BLC + S-curve composite (full range)")
    ax[0].set_xlabel("sensor raw10 code"); ax[0].set_ylabel("8-bit output Y")
    ax[0].grid(alpha=.3); ax[0].legend(fontsize=8)

    zx = list(range(0, 120))
    for lab, byp, lvl, col in (("BLC bypass, gamma ON", True, 56, "#2b7bba"),
                               ("BL=56 ON, gamma ON", False, 56, "#d94b3b"),
                               ("BL=42 ON, gamma ON", False, 42, "#e8a13a")):
        ax[1].plot(zx, [composite(v, lvl, byp, gamma_tbl) for v in zx], lw=1.8, color=col, label=lab)
    ax[1].plot(zx, [v >> 2 for v in zx], "--", lw=1.2, color="#888888", label="linear raw/4")
    for raw, txt, col in ((41, "12:50 shot: raw~41", "#2b7bba"),
                          (57, "ChipWatcher low 57", "#444444"),
                          (67, "ChipWatcher mean 67", "#444444"),
                          (72, "01:37 back-calc 72", "#444444")):
        ax[1].axvline(raw, color=col, ls=":", lw=1.2)
        ax[1].text(raw + 0.8, 116, txt, rotation=90, fontsize=7, color=col, va="top")
    ax[1].set_xlim(0, 120); ax[1].set_ylim(0, 120)
    ax[1].set_title("Zoom: dark end (where the foot of the curve lives)")
    ax[1].set_xlabel("sensor raw10 code"); ax[1].set_ylabel("8-bit output Y")
    ax[1].grid(alpha=.3); ax[1].legend(fontsize=8, loc="lower right")

    fig.tight_layout()
    fig.savefig(OUT_PNG)
    print("[生成] %s" % OUT_PNG)


def main():
    check_only = "--check" in sys.argv
    gamma_tbl = check_inline_vs_hex()
    fmt_table_check(gamma_tbl)
    if check_only:
        return
    gen_levels_files()
    gen_csv_and_plot(gamma_tbl)
    print()
    print("完成。")


if __name__ == "__main__":
    main()
