# -*- coding: utf-8 -*-
"""
把 lsc.v 的表换成「诊断图案」，用来一次性判断 LSC 到底有没有落到像素上、
以及 x 坐标计数对不对。

诊断图案：
  * 水平：hidx 0..9（像素 0..639）  k = 0      -> 不校正
          hidx 10..19（像素 640..1279）k = 7  -> 满校正
          => 屏幕正中应该出现一条硬竖直分界，右半边明显偏品红
  * 垂直：F_kv 全部 0（不让 y 参与，先单独验 x）
  * 增益强度临时从 g = 1 + k/64 提到 g = 1 + k/16（k=7 -> 1.4375x）
    这样即使只有 10% 的校正也看得见，避免再猜一轮

用法：python gen_lsc_diag.py            写入诊断表
      python gen_lsc_diag.py --restore  从 .before 还原成正式表
"""
import os, re, sys, shutil

LSC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\lsc.v"
BAK = r"E:\FPGA\_backup\20261014_lsc_diag\lsc.v.before"

FH_NEW = """    function [2:0] F_kh(input [4:0] i);
        begin
            // [DIAG] 左半 0..9 -> k=0 ，右半 10..19 -> k=7（硬竖直分界在像素 640）
            if (i < 5'd10) F_kh = 3'd0;
            else           F_kh = 3'd7;
        end
    endfunction
"""

FK_NEW = """    function [2:0] F_kv(input [4:0] i);
        begin
            F_kv = 3'd0;   // [DIAG] 先不让 y 参与
        end
    endfunction
"""


def main():
    restore = "--restore" in sys.argv
    raw = open(LSC, "rb").read()
    txt = raw.decode("utf-8")
    nl = "\r\n" if b"\r\n" in raw else "\n"
    t = txt.replace("\r\n", "\n")

    if restore:
        if not os.path.exists(BAK):
            print("找不到备份", BAK); return 1
        shutil.copy2(BAK, LSC)
        print("已还原 ->", LSC, os.path.getsize(LSC), "B")
        return 0

    os.makedirs(os.path.dirname(BAK), exist_ok=True)
    if not os.path.exists(BAK):
        shutil.copy2(LSC, BAK)
        print("备份 ->", BAK, os.path.getsize(BAK), "B")

    n = 0
    t2 = re.sub(r"    function \[2:0\] F_kh\(input \[4:0\] i\);.*?\n    endfunction\n",
                FH_NEW, t, count=1, flags=re.S)
    if t2 != t: n += 1; t = t2
    t2 = re.sub(r"    function \[2:0\] F_kv\(input \[4:0\] i\);.*?\n    endfunction\n",
                FK_NEW, t, count=1, flags=re.S)
    if t2 != t: n += 1; t = t2
    # 强度 x4： g = 1 + k/64  ->  g = 1 + k/16
    t2 = t.replace("s = {1'b0, v} + {1'b0, p[9:6]};     // v + p/64",
                   "s = {1'b0, v} + {1'b0, p[9:4]};     // [DIAG] v + p/16（临时 x4）")
    if t2 != t: n += 1; t = t2
    print("替换命中 %d 处（应为 3）" % n)
    if n != 3:
        print("★命中数不对，已放弃写入★"); return 1

    out = t.replace("\n", nl)
    open(LSC, "wb").write(out.encode("utf-8"))
    print("写入 ->", LSC, os.path.getsize(LSC), "B")
    for k in ("if (i < 5'd10) F_kh", "F_kv = 3'd0;   // [DIAG]", "p[9:4]"):
        print("  校验 %-34s : %s" % (k, "OK" if k in t else "缺失"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
