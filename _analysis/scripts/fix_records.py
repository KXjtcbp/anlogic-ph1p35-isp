# -*- coding: utf-8 -*-
"""修掉上一步的转义事故：bytes 字面量里的 \\uXXXX 不会被解释，被原样写进了文件。

做法：定位插入块的起止行（前后各一条 //---- 横线），整段替换为正确 UTF-8 文本。
"""
import os

BASE = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"

REC_MYALGO = """//-----------------------------------------------------------------------------
//  修改记录 :
//    2026-09-27  [6440c52] 新建本模块（自研 RGB 点运算算法集，5 种模式）并接入 isp_top
//    2026-10-03  [043f927] 修复跨时钟域违例与 DSP 用满（去掉 `a * 常数` 写法）
//    2026-10-03  [e562752] 修复 f_heat 未初始化读取导致的综合致命错误 HDL-8007
//    2026-10-06  （未提交）MODE 3 由「二值化」改为「亮度五档彩条」：阈值 8'd32/64/128/192
//                映射 黑/蓝/绿/黄/红；修正 f_luma 的 B 通道系数（21B → 29B）
//    2026-10-06  （未提交）MODE 4 卡通化：段边界与描边门限调整
//    2026-10-09  （未提交）标识符改名（S_phase_cnt 等），无逻辑改动
//-----------------------------------------------------------------------------"""

REC_KEY = """//-----------------------------------------------------------------------------
//  修改记录 :
//    2026-09-27  [6440c52] 新建本模块（按键切换算法模式）
//    2026-10-03  [364d1bf] 模式值改为单 bit 翻转跨域协议，修掉残留 0.085ns 时序违例
//    2026-10-06  （未提交）模式数由 4 改为 5，增加第二根翻转线 O_mode_wrap，
//                循环改为 0→1→2→3→4→0；复位默认模式 = MODE 2（伪彩热力图）
//    2026-10-09  （未提交）标识符改名，无逻辑改动；
//                修正文件头里与 pin.adc 不符的一处：I_button[1] 引脚 J14 → D5
//-----------------------------------------------------------------------------"""

for rel, rec in [("my_algo/my_algo.v", REC_MYALGO),
                 ("my_algo/key_mode_ctrl.v", REC_KEY)]:
    p = os.path.join(BASE, rel.replace("/", os.sep))
    lines = open(p, "rb").read().split(b"\n")

    # 找被写坏的 \uXXXX 行
    bad_idx = [i for i, l in enumerate(lines) if b"\\u4fee" in l or b"\\uff08" in l or b"\\u2192" in l]
    if not bad_idx:
        print(f"{rel}: 没有坏行，跳过（可能已修好）")
        continue
    lo, hi = min(bad_idx), max(bad_idx)
    # 向前找最近的 //---- 横线，向后找最近的 //---- 横线
    start = lo
    while start > 0 and not lines[start].startswith(b"//---"):
        start -= 1
    end = hi
    while end < len(lines) - 1 and not lines[end].startswith(b"//---"):
        end += 1
    print(f"{rel}: 坏块位于第 {start+1}~{end+1} 行，共 {end-start+1} 行，整段替换")
    new = b"\n".join(lines[:start] + rec.split("\n") and
                     [l.encode() for l in rec.split("\n")] + lines[end + 1:])
    open(p, "wb").write(new)
    print(f"   -> {len(b'\\n'.join(lines))} B 变为 {len(new)} B")

# 复核
for rel in ("my_algo/my_algo.v", "my_algo/key_mode_ctrl.v"):
    p = os.path.join(BASE, rel.replace("/", os.sep))
    raw = open(p, "rb").read()
    print(f"{rel}: {len(raw)} B, 残留 \\u 坏行 = {raw.count(b'\\\\u4fee')}")
