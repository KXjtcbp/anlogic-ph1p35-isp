# -*- coding: utf-8 -*-
"""恢复被截断的 my_algo.v，并安全补入「修改记录」块。

教训：不要写 `open(p,"wb").write(可能抛异常的表达式)` —— open 会先截断文件，
异常在参数求值阶段抛出，于是文件被清空。本脚本一律「先算好完整字节，再开文件写」。
"""
import os, shutil

BASE = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
BACKUP = r"E:\FPGA\_backup\20261009_comments\core"

# ---- 1. 恢复 ----
p_my = os.path.join(BASE, "my_algo", "my_algo.v")
bak = os.path.join(BACKUP, "my_algo__my_algo.v.bak")
if os.path.getsize(p_my) == 0:
    shutil.copy2(bak, p_my)
    print(f"RESTORE my_algo.v <- {os.path.basename(bak)}  ({os.path.getsize(p_my)} B)")
else:
    print(f"my_algo.v 无需恢复（{os.path.getsize(p_my)} B）")

REC_MYALGO = b"""//-----------------------------------------------------------------------------
//  \u4fee\u6539\u8bb0\u5f55 :
//    2026-09-27  [6440c52] \u65b0\u5efa\u672c\u6a21\u5757\uff08\u81ea\u7814 RGB \u70b9\u8fd0\u7b97\u7b97\u6cd5\u96c6\uff0c5 \u79cd\u6a21\u5f0f\uff09\u5e76\u63a5\u5165 isp_top
//    2026-10-03  [043f927] \u4fee\u590d\u8de8\u65f6\u949f\u57df\u8fdd\u4f8b\u4e0e DSP \u7528\u6ee1\uff08\u53bb\u6389 `a * \u5e38\u6570` \u5199\u6cd5\uff09
//    2026-10-03  [e562752] \u4fee\u590d f_heat \u672a\u521d\u59cb\u5316\u8bfb\u53d6\u5bfc\u81f4\u7684\u7efc\u5408\u81f4\u547d\u9519\u8bef HDL-8007
//    2026-10-06  \uff08\u672a\u63d0\u4ea4\uff09MODE 3 \u7531\u300c\u4e8c\u503c\u5316\u300d\u6539\u4e3a\u300c\u4eae\u5ea6\u4e94\u6863\u5f69\u6761\u300d\uff1a
//                \u9608\u503c 8'd32/64/128/192 \u6620\u5c04 \u9ed1/\u84dd/\u7eff/\u9ec4/\u7ea2\uff1b
//                \u4fee\u6b63 f_luma \u7684 B \u901a\u9053\u7cfb\u6570\uff0821B \u2192 29B\uff0c\u5373 R+2G+B \u6539\u4e3a\u771f\u6b63\u7684 BT.601\uff09
//    2026-10-06  \uff08\u672a\u63d0\u4ea4\uff09MODE 4 \u5361\u901a\u5316\uff1a\u6bb5\u8fb9\u754c\u4e0e\u63cf\u8fb9\u95e8\u9650\u8c03\u6574
//    2026-10-09  \uff08\u672a\u63d0\u4ea4\uff09\u6807\u8bc6\u7b26\u6539\u540d\uff08S_phase_cnt \u7b49\uff09\uff0c\u65e0\u903b\u8f91\u6539\u52a8
//-----------------------------------------------------------------------------
"""

REC_KEY = b"""//-----------------------------------------------------------------------------
//  \u4fee\u6539\u8bb0\u5f55 :
//    2026-09-27  [6440c52] \u65b0\u5efa\u672c\u6a21\u5757\uff08\u6309\u952e\u5207\u6362\u7b97\u6cd5\u6a21\u5f0f\uff09
//    2026-10-03  [364d1bf] \u6a21\u5f0f\u503c\u6539\u4e3a\u5355 bit \u7ffb\u8f6c\u8de8\u57df\u534f\u8bae\uff0c\u4fee\u6389\u6b8b\u7559 0.085ns \u65f6\u5e8f\u8fdd\u4f8b
//    2026-10-06  \uff08\u672a\u63d0\u4ea4\uff09\u6a21\u5f0f\u6570\u7531 4 \u6539\u4e3a 5\uff0c\u589e\u52a0\u7b2c\u4e8c\u6839\u7ffb\u8f6c\u7ebf O_mode_wrap\uff0c
//                \u5faa\u73af\u6539\u4e3a 0\u21921\u21922\u21923\u21924\u21920\uff1b\u590d\u4f4d\u9ed8\u8ba4\u6a21\u5f0f = MODE 2\uff08\u4f2a\u5f69\u70ed\u529b\u56fe\uff09
//    2026-10-09  \uff08\u672a\u63d0\u4ea4\uff09\u6807\u8bc6\u7b26\u6539\u540d\uff0c\u65e0\u903b\u8f91\u6539\u52a8\uff1b
//                \u4fee\u6b63\u6587\u4ef6\u5934\u91cc\u4e0e pin.adc \u4e0d\u7b26\u7684\u4e00\u5904\uff1aI_button[1] \u5f15\u811a J14 \u2192 D5
//-----------------------------------------------------------------------------
"""

for rel, lineno, blob in [("my_algo/my_algo.v", 59, REC_MYALGO),
                          ("my_algo/key_mode_ctrl.v", 33, REC_KEY)]:
    p = os.path.join(BASE, rel.replace("/", os.sep))
    raw = open(p, "rb").read()
    if b"HDR-2026-10-09" in raw:
        print("skip (already marked):", rel)
        continue
    lines = raw.split(b"\n")
    idx = lineno - 1
    assert lines[idx].startswith(b"//==="), (rel, lineno, lines[idx][:40])
    bl = blob.split(b"\n")
    if bl and bl[-1] == b"":
        bl = bl[:-1]
    new = b"\n".join(lines[:idx] + bl + lines[idx:])   # 先算好
    open(p, "wb").write(new)                            # 再落盘
    print(f"record +{len(bl)} \u884c -> {rel}  ({len(raw)} \u2192 {len(new)} B)")

# ---- 修正与 pin.adc 不符的注释 ----
p = os.path.join(BASE, "my_algo", "key_mode_ctrl.v")
raw = open(p, "rb").read()
bad = b"I_button[1] } { LOCATION = J14;"
good = b"I_button[1] } { LOCATION = D5; "
if bad in raw:
    new = raw.replace(bad, good)
    open(p, "wb").write(new)
    print("fix comment: key_mode_ctrl.v  I_button[1] J14 -> D5（与 pin.adc:11 一致）")
else:
    print("note: key_mode_ctrl.v 未找到 J14 注释")
