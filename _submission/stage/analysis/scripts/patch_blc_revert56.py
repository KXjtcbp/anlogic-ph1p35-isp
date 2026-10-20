# -*- coding: utf-8 -*-
"""2026-10-11e：回退 2026-10-11d 的黑电平改动（模块 A 收口）

回退两处：
 1) isp/demosaic_4x_2_0/mipi_to_raw_converter.v （GBK，按字节替换）
      BLACK_LEVEL 10'd42 -> 10'd56
 2) design_top_wrapper.v （UTF-8）
      wire S_blk_bypass = ~S_sw1_sync1;  ->  wire S_blk_bypass = S_sw1_sync1;
      （撤销 10-11d 的 SW1 语义反相，恢复与 design_top_wrapper.v:750、
        pin.adc:22、captures/README.md 全部历史采集标注一致的定义：
        拨下 = 逻辑 1 = 旁路 = 老行为；拨上 = 0 = 启用扣除）

理由（三条独立证据，见 2026-10-11 那一轮的数据）：
 1) 12:50 盖镜头图实测 Y 均值 40.52 / p50 41。把 40.52 反过 p160_a050 曲线得
    曲线前 10.4 码，再 x4 = raw10 基座 42。但那张图是【黑电平旁路 + 曲线启用】拍的：
    40.52 只有在"旁路"世界才拟合得上（启用扣除 + 基座 42 -> 0；旁路 + 曲线关 -> 10.4）。
    => 42 是"旁路时读到的基座位"，逻辑上推不出"BLACK_LEVEL 应该 = 42"。
 2) 四张盖镜头增益梯（01:59-02:00，黑电平_4.000x/8.000x/15.750x/31.500x）读到
    Y==0 占 99.894% / 99.471% / 93.720% / 76.532% => BL=56 在四档增益都把基座压到 0。
 3) BL=42 对实测基座 42 的余量 = 0；基座漂 2 个 raw10 就出现 1 个 8bit 码，而
    p160_a050 表 mem[1]=13 / mem[2]=18 => 1 码基座立刻放大成 13 码灰。BL=56 有 16 码余量。
    在"基座 = 67~72"的另一个候选世界里，56 同样优于 42。=> 56 在两个世界都更稳。

备份到 E:\\FPGA\\_backup\\20261011e_revert56\\
"""
import os
import shutil

BAK = r"E:\FPGA\_backup\20261011e_revert56"
os.makedirs(BAK, exist_ok=True)

# ---------------------------------------------------------------- 1) GBK 文件
p1 = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\demosaic_4x_2_0\mipi_to_raw_converter.v"
shutil.copyfile(p1, os.path.join(BAK, "mipi_to_raw_converter.v.before"))
b = open(p1, "rb").read()

# 10-11d 插进去的那一整段。★注意换行是混合的★：
#   10-11d 的脚本写的是  10'd42 + CRLF + note，而 note 内部用的是裸 LF。
old_note = ("    parameter [9:0] BLACK_LEVEL = 10'd42\r\n"
            "// [HDR-2026-10-11d] BLACK_LEVEL 56 -> 42: 2026-10-11 12:50 盖镜头实测(SW1下=直通, SW2上=曲线开, "
            "SW3+SW4上=31.500x)曲线前约 10.5 码, 即 raw10 基座约 42;\n"
            "//   原值 56 在启用扣除时会多扣 14 个 raw10 (约 3.5 码 8bit), 会把真实暗部一起钳掉。\n").encode("gbk")
assert b.count(old_note) == 1, ("anchor-note", b.count(old_note))

new_note = ("    parameter [9:0] BLACK_LEVEL = 10'd56\r\n"
            "// [HDR-2026-10-11e] 回退 2026-10-11d 的 56 -> 42 改动。三条独立证据见\r\n"
            "//   _analysis/黑电平校正_模块A方案与验收_20261011.md 第 2 节：\r\n"
            "//   (1) 12:50 那张盖镜头图（实测 Y 均值 40.52、p50 41）是【黑电平旁路 + 曲线启用】拍的，\r\n"
            "//       40.52 反过 p160_a050 曲线得曲线前 10.4 码，再乘 4 = raw10 基座 42。\r\n"
            "//       42 是「旁路时读到的基座值」，逻辑上不能反推「BLACK_LEVEL 应该等于 42」。\r\n"
            "//   (2) 四张盖镜头增益梯（01:59-02:00，SW1 上=启用扣除）读到 Y==0 占\r\n"
            "//       99.894% / 99.471% / 93.720% / 76.532%，证明 BL=56 在 4.000x / 8.000x /\r\n"
            "//       15.750x / 31.500x 四档增益都把基座压到 0，是够用的。\r\n"
            "//   (3) BL=42 对实测基座 42 的余量 = 0 码：基座只要漂 2 个 raw10 就出现 1 个 8bit 码，\r\n"
            "//       而 p160_a050 表 mem[1]=8'h0d=13、mem[2]=8'h12=18，1 码基座立刻放大成 13 码灰。\r\n"
            "//       BL=56 有 16 码余量；在「基座 = 67~72」的另一个候选世界里 56 同样优于 42。\r\n"
            "//   => 56 在两个候选世界都更稳，且代价 <1.5% 的 8bit 暗部（raw10 44..57 被钳到 0）。\r\n").encode("gbk")

b2 = b.replace(old_note, new_note, 1)
assert b2 != b, "no change 1"
assert b2.count(b"10'd42") == 0, ("leftover 42", b2.count(b"10'd42"))
tmp = p1 + ".tmp_new"
open(tmp, "wb").write(b2)
os.replace(tmp, p1)

# -------------------------------------------------------------- 2) UTF-8 文件
p2 = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\design_top_wrapper.v"
shutil.copyfile(p2, os.path.join(BAK, "design_top_wrapper.v.before"))
t = open(p2, "r", encoding="utf-8", newline="").read()

old2 = ("wire S_blk_bypass   = ~S_sw1_sync1;  // ★2026-10-11d 反相★ 1 = 黑电平扣除【直通】(SW1 拨上)；"
        "0 = 启用扣除（**SW1 拨下＝默认即扣除**，因为基座必须默认扣掉，否则曲线把黑底抬到 ≈41 码灰）")
assert t.count(old2) == 1, ("anchor2", t.count(old2))

new2 = ("wire S_blk_bypass   = S_sw1_sync1;   // 1 = 黑电平扣除【直通】；0 = 启用扣除\n"
        "//   ★2026-10-11e 回退 10-11d 的反相★ 恢复与本文件 :750、pin.adc:22、\n"
        "//   captures/README.md 全部历史采集标注一致的定义：**拨下 = 逻辑 1 = 旁路 = 老行为**。\n"
        "//   反相版会把「拨下」变成「启用扣除」，与 :750 的注释自相矛盾，也让 V1-V5 验收矩阵失效；\n"
        "//   而且 PULLUP 悬空读到 1，原版语义下悬空 = 旁路 = 老行为，是唯一安全的默认。")
t2 = t.replace(old2, new2, 1)
assert t2 != t, "no change 2"
assert "~S_sw1_sync1" not in t2, "leftover inversion"
tmp2 = p2 + ".tmp_new"
open(tmp2, "w", encoding="utf-8", newline="").write(t2)
os.replace(tmp2, p2)

# ------------------------------------------------------------------ 自检
assert open(p1, "rb").read()[:3] != b"\xef\xbb\xbf", "GBK 文件被写入了 BOM！"
assert open(p2, "rb").read()[:3] != b"\xef\xbb\xbf", "UTF-8 文件被写入了 BOM！"

print("回退完成：")
print("  1) mipi_to_raw_converter.v  BLACK_LEVEL 10'd42 -> 10'd56")
print("  2) design_top_wrapper.v     S_blk_bypass = S_sw1_sync1（撤销反相）")
print("备份: " + BAK)
