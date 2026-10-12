# -*- coding: utf-8 -*-
"""把 mipi_to_raw_converter.v 的黑电平标定值由 64 改为 56，并加四舍五入补偿。
安全约束：
  1) 先把全部替换在内存里做完并 encode 成目标编码，成功后才 open('wb')；
  2) 每个 old 模式必须在本文件中出现且仅出现 1 次，否则整体放弃、不写盘；
  3) 任何一步异常都不写盘。
"""
import sys, os, shutil, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PATH = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\demosaic_4x_2_0\mipi_to_raw_converter.v"
BAK = r"E:\FPGA\_backup\20261009_blk\mipi_to_raw_converter.v.blk64"
EOL = "\r\n"

NEW_DECL = (
    "    wire [9:0] S_blk_level = 10'd56;   // 黑电平基座（2026-10-09 实测标定：盖镜头时 RAW10 值域 [57..79]、均值 66~67）" + EOL +
    "    //   取 56 而不是实测均值 66 的理由（m02552「绝不影响效果」的硬保证）：" + EOL +
    "    //     56 小于观测到的最低 RAW10 值 57，所以对现有全部采集数据都不会钳掉任何一个像素，" + EOL +
    "    //     即黑电平扣除在数学上不可能损失任何真实暗部细节；" + EOL +
    "    //     同时仍扣掉 56/66 约 85% 的基座，8bit 域残留 10>>2 约 2 个码值（0.8%），肉眼不可见。" + EOL +
    "    //   将来若改增益/曝光，重新标定只需改这一个常数（建议取值 = 新实测最小值 减 1）。" + EOL +
    "    //   下面 4 条同时做「钳位减法」与「四舍五入补偿 +2」：随后取 [9:2] 等价于 (x-56+2)/4 四舍五入，" + EOL +
    "    //   最大值 (1023-56)+2 = 969 仍在 10bit 内，不会溢出；8bit 输出上限为 969>>2 = 242。" + EOL
)

PAIRS = [
    ("    wire [9:0] S_blk_level = 10'd64;   // 黑电平基座（实测标定值；重新标定只改这一个常数）" + EOL, NEW_DECL),
    ("    wire [9:0] S_blk_f0 = (I_raw_tdata[ 9: 0] > S_blk_level) ? (I_raw_tdata[ 9: 0] - S_blk_level) : 10'd0;" + EOL,
     "    wire [9:0] S_blk_f0 = ((I_raw_tdata[ 9: 0] > S_blk_level) ? (I_raw_tdata[ 9: 0] - S_blk_level) : 10'd0) + 10'd2;   // 减基座 +2 四舍五入" + EOL),
    ("    wire [9:0] S_blk_f1 = (I_raw_tdata[19:10] > S_blk_level) ? (I_raw_tdata[19:10] - S_blk_level) : 10'd0;" + EOL,
     "    wire [9:0] S_blk_f1 = ((I_raw_tdata[19:10] > S_blk_level) ? (I_raw_tdata[19:10] - S_blk_level) : 10'd0) + 10'd2;   // 减基座 +2 四舍五入" + EOL),
    ("    wire [9:0] S_blk_f2 = (I_raw_tdata[29:20] > S_blk_level) ? (I_raw_tdata[29:20] - S_blk_level) : 10'd0;" + EOL,
     "    wire [9:0] S_blk_f2 = ((I_raw_tdata[29:20] > S_blk_level) ? (I_raw_tdata[29:20] - S_blk_level) : 10'd0) + 10'd2;   // 减基座 +2 四舍五入" + EOL),
    ("    wire [9:0] S_blk_f3 = (I_raw_tdata[39:30] > S_blk_level) ? (I_raw_tdata[39:30] - S_blk_level) : 10'd0;" + EOL,
     "    wire [9:0] S_blk_f3 = ((I_raw_tdata[39:30] > S_blk_level) ? (I_raw_tdata[39:30] - S_blk_level) : 10'd0) + 10'd2;   // 减基座 +2 四舍五入" + EOL),
    ("            // 2026-10-09 改动：由直接截断 I_raw_tdata[x:y] 改为截断 (I_raw_tdata[x:y] - 64)" + EOL,
     "            // 2026-10-09 改动：由直接截断 I_raw_tdata[x:y] 改为截断 (I_raw_tdata[x:y] - 56 + 2)" + EOL),
    ("    //             四字段均值 [68.11 65.88 68.12 65.97]，光学黑基座约为 64 LSB(10bit)。" + EOL,
     "    //             四字段均值 [68.11 65.88 68.12 65.97]，光学黑基座实测约 66 LSB(10bit)，本实现取 56。" + EOL),
    ("    //   不扣除的后果：10bit 的黑在 8bit 链路里变成 64>>2 = 16，相当于整幅画面叠加约 6%" + EOL,
     "    //   不扣除的后果：10bit 的黑在 8bit 链路里变成 66>>2 = 16，相当于整幅画面叠加约 6%" + EOL),
]

raw = open(PATH, "rb").read()
orig_sha = hashlib.sha256(raw).hexdigest()[:16]
enc = "gbk"
try:
    t = raw.decode("gbk")
except UnicodeDecodeError:
    t = raw.decode("utf-8"); enc = "utf-8"
print("原文件 %d B, sha16 %s, 编码 %s" % (len(raw), orig_sha, enc))

for i, (o, n) in enumerate(PAIRS):
    c = t.count(o)
    print("  模式%02d 命中 %d 次 : %s" % (i, c, o.strip()[:72]))
    if c != 1:
        print("!! 命中次数不为 1，整体放弃，未写盘")
        sys.exit(2)

for o, n in PAIRS:
    t = t.replace(o, n, 1)

# 先编码，成功后才开文件（避免 0 字节事故）
try:
    data = t.encode(enc)
except UnicodeEncodeError as e:
    print("!! 编码失败，未写盘:", e)
    sys.exit(3)

if not os.path.exists(BAK):
    shutil.copy2(PATH, BAK)
    print("已备份 -> " + BAK)
else:
    print("备份已存在，跳过 -> " + BAK)

open(PATH, "wb").write(data)
chk = open(PATH, "rb").read()
print("新文件 %d B, sha16 %s, LF %d, CRLF %d" % (len(chk), hashlib.sha256(chk).hexdigest()[:16],
      chk.decode(enc).count("\n"), chk.decode(enc).count("\r\n")))
print("写盘后回读校验: %s" % ("OK" if chk == data else "!! 不一致"))
for kw in ("10'd56", "+ 10'd2", "10'd64"):
    print("  关键词 %-10s 出现 %d 次" % (kw, chk.decode(enc).count(kw)))
