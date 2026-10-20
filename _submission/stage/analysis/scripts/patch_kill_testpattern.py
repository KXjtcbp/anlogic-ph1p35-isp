# -*- coding: utf-8 -*-
"""修复「传感器灰度测试图被正常开关组合点开」的 bug。

根因链：
  isp/../design_top_wrapper.v:789  assign S_tp_canary = ~(S_sw1_sync1|S_sw2_sync1|S_sw3_sync1|S_sw4_sync1);
      ⇒ 四个开关全"上"（引脚全 0）= 1
  design_top_wrapper.v:618        .I_test_pattern(S_tp_canary)
      ⇒ uicfgcs500_720p → uics500regAE.v:83  7: {16'h4501, I_test_pattern ? 8'hbc : 8'hb4}
      ⇒ 运行时表把 0x4501 写成 0xbc = 传感器内置灰度递增测试图【打开】

  但"出厂推荐工作档"恰恰就是四个开关全上：
      SW1上 = 黑电平扣除【启用】 / SW2上 = S 曲线【启用】
      SW3上 = 数字增益 ×2.000   / SW4上 = 模拟增益 15.750×
  ⇒ 自检钩子会在正常使用中被触发，不是"正常使用绝不会出现的状态"（原注释判断错误）。

  而且重下发只由 SW3/SW4 变化触发（S_gain_applied 只有 2 bit，见 :562/:582/:588/:591），
  拨 SW1/SW2 不会重下发 ⇒ 一旦在"四开关全上"时下发过一次，测试图就【卡住】，再也关不掉。

修复：
  (1) I_test_pattern 硬接 1'b0 —— 永久关闭测试图（运行时 I2C 写通路早已由增益梯与曲线 A/B 证明是通的）；
  (2) S_gain_applied 由 2 bit 扩到 4 bit（含 SW1/SW2）—— 任何开关变化都会重下发，杜绝"寄存器表状态陈旧"这一类 bug。
"""
import io
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"E:\FPGA"
SRC = os.path.join(ROOT, "proj", "baseline", "lab3", "user_source", "hdl_source", "design_top_wrapper.v")
BAK = os.path.join(ROOT, "_backup", "20261011i_kill_testpattern")
DRY = "--dry-run" in sys.argv

t = io.open(SRC, encoding="utf-8", newline="").read()
orig = t
edits = []


def rep(old, new, tag):
    global t
    n = t.count(old)
    assert n == 1, "anchor %r matched %d times (expected 1)" % (tag, n)
    t = t.replace(old, new, 1)
    edits.append(tag)


# (1) 永久关闭测试图
rep(
    ".I_test_pattern(S_tp_canary),      // [HDR-2026-10-10d] \u2605\u81ea\u68c0\u2605 \u56db\u5f00\u5173\u5168\"\u4e0a\"=1 \u21d2 \u8fd0\u884c\u65f6\u8868\u628a 0x4501 \u5199\u6210 0xbc\uff08\u7070\u5ea6\u9012\u589e\u6d4b\u8bd5\u56fe\uff09",
    ".I_test_pattern(1'b0),             // [HDR-2026-10-11i] \u2605\u6c38\u4e45\u5173\u95ed\u6d4b\u8bd5\u56fe\u2605 "
    "\u539f\u6765\u63a5 S_tp_canary\uff08\u56db\u5f00\u5173\u5168\u4e0a = 1\uff09\uff0c\u800c\u56db\u5f00\u5173\u5168\u4e0a\u6b63\u662f\u51fa\u5382\u63a8\u8350\u5de5\u4f5c\u6863 "
    "(SW1\u4e0a=\u9ed1\u7535\u5e73\u5f00\u3001SW2\u4e0a=\u66f2\u7ebf\u5f00\u3001SW3\u4e0a=\u00d72.000\u3001SW4\u4e0a=15.750\u00d7) "
    "\u21d2 \u81ea\u68c0\u94a9\u5b50\u88ab\u6b63\u5e38\u4f7f\u7528\u70b9\u5f00\uff0c\u4e14\u53ea\u6709 SW3/SW4 \u53d8\u5316\u624d\u91cd\u4e0b\u53d1\uff0c\u4e00\u65e6\u70b9\u5f00\u5c31\u5361\u6b7b\u3002"
    "\u8fd0\u884c\u65f6 I2C \u5199\u901a\u8def\u5df2\u7531\u589e\u76ca\u68af\u4e0e\u66f2\u7ebf A/B \u8bc1\u660e\u662f\u901a\u7684\uff0c\u4e0d\u518d\u9700\u8981\u8fd9\u4e2a\u94a9\u5b50\u3002",
    "kill test pattern port",
)

# (2) 重下发监视全部四个开关 → 2 bit 扩到 4 bit
rep("reg  [1:0]  S_gain_applied;", "reg  [3:0]  S_gain_applied;", "decl 4bit")
rep("S_gain_applied  <= 2'b11;", "S_gain_applied  <= 4'b1111;", "reset 4bit")
rep(
    "S_gain_applied  <= {S_sw3_sync1, S_sw4_sync1};",
    "S_gain_applied  <= {S_sw1_sync1, S_sw2_sync1, S_sw3_sync1, S_sw4_sync1};",
    "latch 4bit (boot)",
)
rep(
    "else if (S_gain_applied != {S_sw3_sync1, S_sw4_sync1}) begin",
    "else if (S_gain_applied != {S_sw1_sync1, S_sw2_sync1, S_sw3_sync1, S_sw4_sync1}) begin",
    "compare 4bit",
)
rep(
    "S_gain_applied <= {S_sw3_sync1, S_sw4_sync1};",
    "S_gain_applied <= {S_sw1_sync1, S_sw2_sync1, S_sw3_sync1, S_sw4_sync1};",
    "latch 4bit (sw)",
)

# (3) canary 本体停用（保留声明与注释，仅强制为 0，供 LED/调试备用）
rep(
    "assign S_tp_canary = ~(S_sw1_sync1 | S_sw2_sync1 | S_sw3_sync1 | S_sw4_sync1);",
    "assign S_tp_canary = 1'b0;  // [HDR-2026-10-11i] \u505c\u7528\uff1a\u539f\u4e3a ~(\u56db\u5f00\u5173)\uff0c"
    "\u4f46\u201c\u56db\u5f00\u5173\u5168\u4e0a\u201d\u6b63\u662f\u63a8\u8350\u5de5\u4f5c\u6863\uff0c\u4f1a\u628a\u4f20\u611f\u5668\u7070\u5ea6\u6d4b\u8bd5\u56fe\u70b9\u5f00\u3002"
    "\u4fdd\u7559\u4fe1\u53f7\u540d\u4f9b LED/\u8c03\u8bd5\u5907\u7528\u3002",
    "canary disabled",
)

if DRY:
    print("DRY RUN, would apply %d edits:" % len(edits))
    for e in edits:
        print("   ", e)
    sys.exit(0)

os.makedirs(BAK, exist_ok=True)
shutil.copy2(SRC, os.path.join(BAK, "design_top_wrapper.v.before"))
io.open(SRC, "w", encoding="utf-8", newline="").write(t)

raw = open(SRC, "rb").read()
print("applied %d edits:" % len(edits))
for e in edits:
    print("   ", e)
print("backup -> %s" % os.path.join(BAK, "design_top_wrapper.v.before"))
print("size %d -> %d B, BOM=%s" % (len(orig.encode("utf-8")), len(raw), raw[:3] == b"\xef\xbb\xbf"))

# post-conditions
chk = io.open(SRC, encoding="utf-8").read()
assert ".I_test_pattern(1'b0)" in chk, "port not tied off"
assert chk.count("S_sw1_sync1, S_sw2_sync1, S_sw3_sync1, S_sw4_sync1") == 3, "4-bit latch count"
assert "S_gain_applied  <= 2'b11" not in chk
assert "S_sw3_sync1, S_sw4_sync1}" not in chk
assert "assign S_tp_canary = 1'b0;" in chk
print("post-conditions OK")
