# -*- coding: utf-8 -*-
"""安全还原 my_algo.v / key_mode_ctrl.v 并补入「修改记录」。

铁律（前两次踩雷换来的）：
  1) 不要 `open(p,"wb").write(<可能抛异常的表达式>)` —— open 先截断文件。
     一律先算好完整 bytes，再 open+write。
  2) 列表拼接不要和 and/or 混写：`a + b and c + d` 里 `+` 比 `and` 紧，
     结果会把 a+b 整段丢掉。分步写清楚。
"""
import os, shutil, sys

HDL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\my_algo"
RTL = r"E:\FPGA\proj\rtl\my_algo"
BAK = r"E:\FPGA\_backup\20261009_comments\core"

PAIRS = [
    # (还原源, 目标, 期望大小, 必须在文件里出现的特征串)
    (os.path.join(BAK, "my_algo__my_algo.v.bak"), os.path.join(HDL, "my_algo.v"),
     19571, [b"module my_algo", b"MODE_INIT", b"f_heat", b"f_luma"]),
    (os.path.join(RTL, "key_mode_ctrl.v"), os.path.join(HDL, "key_mode_ctrl.v"),
     6085, [b"module key_mode_ctrl", b"O_mode_wrap", b"3'd4"]),
]

# ---- 1. 还原 ----
for src, dst, want, feats in PAIRS:
    raw = open(src, "rb").read()
    assert len(raw) == want, f"{src}: {len(raw)} != {want}"
    for f in feats:
        assert f in raw, f"{src}: 缺少特征 {f!r}"
    if os.path.getsize(dst) != want:
        shutil.copy2(src, dst)
        print(f"RESTORE {os.path.basename(dst):<18} <- {src}   {len(raw)} B  (特征串全部命中)")
    else:
        print(f"OK      {os.path.basename(dst):<18} 已是 {want} B")

# ---- 2. 补修改记录 ----
REC = {
 "my_algo.v": """//-----------------------------------------------------------------------------
//  修改记录 :
//    2026-09-27  [6440c52] 新建本模块（自研 RGB 点运算算法集，5 种模式）并接入 isp_top
//    2026-10-03  [043f927] 修复跨时钟域违例与 DSP 用满（去掉 `a * 常数` 写法）
//    2026-10-03  [e562752] 修复 f_heat 未初始化读取导致的综合致命错误 HDL-8007
//    2026-10-06  （未提交）MODE 3 由「二值化」改为「亮度五档彩条」：阈值 8'd32/64/128/192
//                映射 黑/蓝/绿/黄/红；修正 f_luma 的 B 通道系数（21B → 29B）
//    2026-10-06  （未提交）MODE 4 卡通化：段边界与描边门限调整
//    2026-10-09  （未提交）标识符改名（S_phase_cnt 等），无逻辑改动
//-----------------------------------------------------------------------------""",
 "key_mode_ctrl.v": """//-----------------------------------------------------------------------------
//  修改记录 :
//    2026-09-27  [6440c52] 新建本模块（按键切换算法模式）
//    2026-10-03  [364d1bf] 模式值改为单 bit 翻转跨域协议，修掉残留 0.085ns 时序违例
//    2026-10-06  （未提交）模式数由 4 改为 5，增加第二根翻转线 O_mode_wrap，
//                循环改为 0→1→2→3→4→0；复位默认模式 = MODE 2（伪彩热力图）
//    2026-10-09  （未提交）标识符改名，无逻辑改动；
//                修正文件头里与 pin.adc 不符的一处：I_button[1] 引脚 J14 → D5
//-----------------------------------------------------------------------------""",
}

for name, rec in REC.items():
    p = os.path.join(HDL, name)
    raw = open(p, "rb").read()
    if b"\\u4fee" in raw:
        sys.exit(f"致命：{name} 里还有未解释的 \\uXXXX 转义，停止")
    lines = raw.split(b"\n")
    anchor = [i for i, l in enumerate(lines) if l.startswith(b"//===")]
    if not anchor:
        sys.exit(f"致命：{name} 找不到文件头结束线 //===")
    idx = anchor[0]
    if b"HDR-2026-10-09" in raw:
        print(f"skip（已有记录）: {name}")
        continue
    head = lines[:idx]                       # 分步，绝不和 and/or 混写
    tail = lines[idx:]
    blk = [l.encode("utf-8") for l in rec.split("\n")]
    new = b"\n".join(head + blk + tail)
    open(p, "wb").write(new)                 # 此时 new 已算好，不会抛
    print(f"RECORD  {name:<18} 在第 {idx+1} 行前插入 {len(blk)} 行   {len(raw)} -> {len(new)} B")

# ---- 3. 修正与 pin.adc 不符的注释 ----
p = os.path.join(HDL, "key_mode_ctrl.v")
raw = open(p, "rb").read()
for bad, good in [(b"J14", b"D5"), (b"j14", b"D5")]:
    if bad in raw:
        open(p, "wb").write(raw.replace(bad, good))
        print(f"FIX     key_mode_ctrl.v  {bad.decode()} -> D5（与 pin.adc:11 一致）")
        break
else:
    print("FIX     key_mode_ctrl.v  未发现 J14，跳过")

# ---- 4. 复核 ----
print()
for name in ("my_algo.v", "key_mode_ctrl.v"):
    p = os.path.join(HDL, name)
    raw = open(p, "rb").read()
    print(f"{name}: {len(raw)} B, {raw.count(b'\\n')} 行, 残留\\\\u={raw.count(b'\\\\u4fee')}, HDR={b'HDR-2026-10-09' in raw}")
