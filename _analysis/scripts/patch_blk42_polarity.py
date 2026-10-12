# -*- coding: utf-8 -*-
"""2026-10-11d：按三张新采集的分析改两处
1) `E:\\FPGA\\proj\\baseline\\lab3\\user_source\\hdl_source\\isp\\demosaic_4x_2_0\\mipi_to_raw_converter.v`
   `BLACK_LEVEL` 10'd56 → 10'd42（GBK 文件，按字节替换；盖镜头实测曲线前 ≈10.5 码 ⇒ raw10 基座 ≈42）
2) `E:\\FPGA\\proj\\baseline\\lab3\\user_source\\hdl_source\\design_top_wrapper.v`
   `wire S_blk_bypass = S_sw1_sync1;` → `~S_sw1_sync1`（**反相**）：让"SW1 拨下（默认安全位）= 启用扣除"，
   拨上 = 直通。理由：基座必须默认扣掉，否则黑底被曲线抬到 ≈41 码（16% 灰）⇒ 画面发灰。
备份到 `E:\\FPGA\\_backup\\20261011d_blk42\\`。
"""
import os
import shutil

BAK = r"E:\FPGA\_backup\20261011d_blk42"
os.makedirs(BAK, exist_ok=True)

# ---------- 1) GBK 文件：BLACK_LEVEL 56 -> 42 ----------
p1 = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\demosaic_4x_2_0\mipi_to_raw_converter.v"
shutil.copyfile(p1, os.path.join(BAK, "mipi_to_raw_converter.v.before"))
b = open(p1, "rb").read()
old = b"BLACK_LEVEL = 10'd56"
assert b.count(old) == 1, ("anchor", b.count(old))
note = ("// [HDR-2026-10-11d] BLACK_LEVEL 56 -> 42: 2026-10-11 12:50 盖镜头实测(SW1下=直通, SW2上=曲线开, "
        "SW3+SW4上=31.500x)曲线前约 10.5 码, 即 raw10 基座约 42;\n"
        "//   原值 56 在启用扣除时会多扣 14 个 raw10 (约 3.5 码 8bit), 会把真实暗部一起钳掉。\n").encode("gbk")
b2 = b.replace(old, b"BLACK_LEVEL = 10'd42" + b"\r\n" + note, 1)
assert b2 != b
tmp = p1 + ".tmp_new"
open(tmp, "wb").write(b2)
os.replace(tmp, p1)

# ---------- 2) UTF-8 文件：SW1 语义反相 ----------
p2 = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\design_top_wrapper.v"
shutil.copyfile(p2, os.path.join(BAK, "design_top_wrapper.v.before"))
t = open(p2, "r", encoding="utf-8", newline="").read()
old2 = "wire S_blk_bypass   = S_sw1_sync1;   // 1 = 黑电平扣除直通"
assert t.count(old2) == 1, ("anchor2", t.count(old2))
new2 = ("wire S_blk_bypass   = ~S_sw1_sync1;  // ★2026-10-11d 反相★ 1 = 黑电平扣除【直通】(SW1 拨上)；"
        "0 = 启用扣除（**SW1 拨下＝默认即扣除**，因为基座必须默认扣掉，否则曲线把黑底抬到 ≈41 码灰）")
t2 = t.replace(old2, new2, 1)
assert t2 != t
tmp2 = p2 + ".tmp_new"
open(tmp2, "w", encoding="utf-8", newline="").write(t2)
os.replace(tmp2, p2)

print("改完：")
print("  1) mipi_to_raw_converter.v  BLACK_LEVEL 56 -> 42")
print("  2) design_top_wrapper.v     S_blk_bypass = ~S_sw1_sync1（SW1 下＝启用扣除）")
print("  备份: " + BAK)
