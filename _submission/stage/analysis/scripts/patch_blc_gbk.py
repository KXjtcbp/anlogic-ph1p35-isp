# -*- coding: utf-8 -*-
"""
patch_blc_gbk.py —— 用「字节级保编码」的方式给 3 个 GBK 编码的 .v 打补丁。

为什么不用编辑器：raw_matrix_3x3_buffer.v / demosaic.v / mipi_to_raw_converter.v
都是 GBK 编码，UTF-8 编辑器读会报 invalid UTF-8。这里用 GBK 读、GBK 写，
文件编码保持不变，中文注释不会乱码。

补丁内容（黑电平参数化 + 旁路透传，见 E:\\FPGA\\_analysis\\黑电平与伽马S曲线实施方案_20261010.md）：
  mipi_to_raw_converter.v : 加 parameter BLACK_LEVEL/ROUND_ADD、加 I_blk_bypass 端口、
                            4 条 S_blk_f* 加旁路选择
  raw_matrix_3x3_buffer.v : 加 I_blk_bypass 端口 + 连到 mipi_to_raw_converter 实例
  demosaic.v              : 加 I_blk_bypass 端口 + 连到 raw_matrix_3x3_buffer 实例
每个替换都要求「原文出现且只出现一次」，否则整脚本不写盘（防止打歪）。
"""
import os
import shutil
import sys

D = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\demosaic_4x_2_0"
F_MPI = os.path.join(D, "mipi_to_raw_converter.v")
F_RMX = os.path.join(D, "raw_matrix_3x3_buffer.v")
F_DEM = os.path.join(D, "demosaic.v")

# ---------------------------------------------------------------- 补丁表
P_MPI = [
    # A. 参数列表 + 旁路端口
    (
        "module mipi_to_raw_converter \n"
        "(\n"
        "    input                          I_clk   ,\n"
        "    input                          I_rst_n ,\n",
        "module mipi_to_raw_converter \n"
        "#(\n"
        "// [HDR-2026-10-10] 参数化：黑电平基座与四舍五入补偿改成参数；\n"
        "//   不传参数时取值与 2026-10-09 版本完全一致，行为逐位不变。\n"
        "    parameter [9:0] BLACK_LEVEL = 10'd56,   // 黑电平基座（10bit RAW 域，实测标定值）\n"
        "    parameter [9:0] ROUND_ADD   = 10'd2     // 取高 8 位前的四舍五入补偿（= 4/2）\n"
        ")\n"
        "(\n"
        "    input                          I_clk   ,\n"
        "    input                          I_rst_n ,\n"
        "    // [HDR-2026-10-10] 旁路开关（板上 SW1，顶层已做同步）：\n"
        "    //   1 = 直通（不做黑电平扣除 = 2026-10-09 之前的原始行为）\n"
        "    //   0 = 启用黑电平扣除\n"
        "    input                          I_blk_bypass,\n",
    ),
    # B. 基座改成引用参数
    (
        "    wire [9:0] S_blk_level = 10'd56;",
        "    wire [9:0] S_blk_level = BLACK_LEVEL;   // [HDR-2026-10-10] 由参数给出（默认 56）",
    ),
    # C. 四条钳位减法加旁路
    (
        "    wire [9:0] S_blk_f0 = ((I_raw_tdata[ 9: 0] > S_blk_level) ? (I_raw_tdata[ 9: 0] - S_blk_level) : 10'd0) + 10'd2;   // 减基座 +2 四舍五入\n"
        "    wire [9:0] S_blk_f1 = ((I_raw_tdata[19:10] > S_blk_level) ? (I_raw_tdata[19:10] - S_blk_level) : 10'd0) + 10'd2;   // 减基座 +2 四舍五入\n"
        "    wire [9:0] S_blk_f2 = ((I_raw_tdata[29:20] > S_blk_level) ? (I_raw_tdata[29:20] - S_blk_level) : 10'd0) + 10'd2;   // 减基座 +2 四舍五入\n"
        "    wire [9:0] S_blk_f3 = ((I_raw_tdata[39:30] > S_blk_level) ? (I_raw_tdata[39:30] - S_blk_level) : 10'd0) + 10'd2;   // 减基座 +2 四舍五入\n",
        "    // [HDR-2026-10-10] 加 I_blk_bypass 选择：1 = 原值直通，0 = 减基座+四舍五入\n"
        "    wire [9:0] S_blk_f0 = I_blk_bypass ? I_raw_tdata[ 9: 0] : (((I_raw_tdata[ 9: 0] > S_blk_level) ? (I_raw_tdata[ 9: 0] - S_blk_level) : 10'd0) + ROUND_ADD);\n"
        "    wire [9:0] S_blk_f1 = I_blk_bypass ? I_raw_tdata[19:10] : (((I_raw_tdata[19:10] > S_blk_level) ? (I_raw_tdata[19:10] - S_blk_level) : 10'd0) + ROUND_ADD);\n"
        "    wire [9:0] S_blk_f2 = I_blk_bypass ? I_raw_tdata[29:20] : (((I_raw_tdata[29:20] > S_blk_level) ? (I_raw_tdata[29:20] - S_blk_level) : 10'd0) + ROUND_ADD);\n"
        "    wire [9:0] S_blk_f3 = I_blk_bypass ? I_raw_tdata[39:30] : (((I_raw_tdata[39:30] > S_blk_level) ? (I_raw_tdata[39:30] - S_blk_level) : 10'd0) + ROUND_ADD);\n",
    ),
]

P_RMX = [
    (
        "    input           I_rst_n ,   // 复位信号，低有效\n",
        "    input           I_rst_n ,   // 复位信号，低有效\n"
        "    input           I_blk_bypass,   // [HDR-2026-10-10] 黑电平扣除旁路（1=直通，0=扣除）\n",
    ),
    (
        "    .I_rst_n     (I_rst_n),              // 复位信号，低有效\n",
        "    .I_rst_n     (I_rst_n),              // 复位信号，低有效\n"
        "    .I_blk_bypass(I_blk_bypass),         // [HDR-2026-10-10] 黑电平扣除旁路透传\n",
    ),
]

P_DEM = [
    (
        "    input           I_rst_n ,   // 复位信号，低有效\n",
        "    input           I_rst_n ,   // 复位信号，低有效\n"
        "    input           I_blk_bypass,   // [HDR-2026-10-10] 黑电平扣除旁路（1=直通，0=扣除）\n",
    ),
    (
        "    /*input           */.I_rst_n  (I_rst_n ),   // 复位信号，低有效\n",
        "    /*input           */.I_rst_n  (I_rst_n ),   // 复位信号，低有效\n"
        "    /*input           */.I_blk_bypass(I_blk_bypass),  // [HDR-2026-10-10] 黑电平扣除旁路透传\n",
    ),
]


def patch(path, pairs, dry=False):
    raw = open(path, "rb").read()
    try:
        txt = raw.decode("gbk")
        enc = "gbk"
    except UnicodeDecodeError:
        txt = raw.decode("utf-8-sig")
        enc = "utf-8-sig"
    # ★源文件是 CRLF 行尾，而补丁表里写的是 \n；先统一成文件自己的行尾再匹配
    nl = "\r\n" if "\r\n" in txt else "\n"
    print("--- %s  (编码 %s, %d 字节, 行尾 %s)" % (os.path.basename(path), enc, len(raw),
                                              "CRLF" if nl == "\r\n" else "LF"))
    ok = True
    new = txt
    for old, rep in pairs:
        if nl != "\n":
            old = old.replace("\n", nl)
            rep = rep.replace("\n", nl)
        c = new.count(old)
        tag = "OK " if c == 1 else "★★"
        print("    %s 命中 %d 次 : %s" % (tag, c, old.strip().splitlines()[0][:64]))
        if c != 1:
            ok = False
            continue
        new = new.replace(old, rep, 1)
    if not ok:
        print("    ⇒ 本文件有替换未唯一命中，未写盘")
        return False
    if dry:
        print("    ⇒ dry-run 通过（未写盘）")
        return True
    with open(path + ".bak_20261010", "wb") as f:
        f.write(raw)
    with open(path, "wb") as f:
        f.write(new.encode("gbk" if enc == "gbk" else "utf-8-sig"))
    print("    ⇒ 已写盘（备份 .bak_20261010）")
    return True


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    a = patch(F_MPI, P_MPI, dry)
    b = patch(F_RMX, P_RMX, dry)
    c = patch(F_DEM, P_DEM, dry)
    print("\n结果: mipi=%s raw_matrix=%s demosaic=%s" % (a, b, c))
