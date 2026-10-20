# -*- coding: utf-8 -*-
"""2026-10-09 向 mipi_to_raw_converter.v 加入「黑电平基座扣除」（实测 64 LSB）。
安全约束（来自当日 0 字节事故的教训）：
  1) 先把新文本 encode 成目标编码并成功，才允许 open(path,'wb')；
  2) 每条替换模式必须 count==1，否则整文件放弃（不写盘）；
  3) GBK 文件里不得出现非 GBK 字符（用 => 代替 ⇒，不用 ★）。
"""
import sys, os, hashlib, shutil
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
P1 = BASE + r"\isp\demosaic_4x_2_0\mipi_to_raw_converter.v"
P2 = BASE + r"\isp\isp_top.v"
BK = r"E:\FPGA\_backup\20261009_blk"

EOL = "\r\n"

INS_AFTER = "    ///此处对于每个RAW10取高8位是因为高位所包含的颜色数据更多。"
BLK = [
    "    //-----------------------------------------------------------------------------",
    "    // 2026-10-09  增加「黑电平基座扣除」（现场实测数据驱动）",
    "    //   实测依据：ChipWatcher 抓取盖住镜头时 ISP 输入端 S_axis_tdata[39:0]（传感器 RAW10）：",
    "    //             1024 个采样内 1432 个有效 10bit 值，值域 = [57..79]、均值 67.02，",
    "    //             四字段均值 [68.11 65.88 68.12 65.97]，光学黑基座约为 64 LSB(10bit)。",
    "    //   不扣除的后果：10bit 的黑在 8bit 链路里变成 64>>2 = 16，相当于整幅画面叠加约 6%",
    "    //             的灰雾（8bit 域 16/255）—— 这是「画面发灰、暗部对比度不足」的来源之一。",
    "    //   做法：每个 10bit 字段先减 S_blk_level（不足者钳到 0，避免无符号下溢回绕成大数），再取高 8 位。",
    "    //   资源代价：每拍 4 个比较器 + 4 个 10bit 减法器；本模块在 csi_rx_clk 域（约 100 MHz），",
    "    //             组合深度约 2 级 LUT，不构成关键路径（本工程关键路径在 HDMI 像素域）。",
    "    //   回退：把 raw_data_r0 的拼接换回 {I_raw_tdata[9:2], I_raw_tdata[19:12], I_raw_tdata[29:22], I_raw_tdata[39:32]}",
    "    //         并删掉 4 条 S_blk_f* 即可；改动前备份 E:\\FPGA\\_backup\\20261009_blk\\mipi_to_raw_converter.v",
    "    //-----------------------------------------------------------------------------",
    "    wire [9:0] S_blk_level = 10'd64;   // 黑电平基座（实测标定值；重新标定只改这一个常数）",
    "    wire [9:0] S_blk_f0 = (I_raw_tdata[ 9: 0] > S_blk_level) ? (I_raw_tdata[ 9: 0] - S_blk_level) : 10'd0;",
    "    wire [9:0] S_blk_f1 = (I_raw_tdata[19:10] > S_blk_level) ? (I_raw_tdata[19:10] - S_blk_level) : 10'd0;",
    "    wire [9:0] S_blk_f2 = (I_raw_tdata[29:20] > S_blk_level) ? (I_raw_tdata[29:20] - S_blk_level) : 10'd0;",
    "    wire [9:0] S_blk_f3 = (I_raw_tdata[39:30] > S_blk_level) ? (I_raw_tdata[39:30] - S_blk_level) : 10'd0;",
]

OLD_ASSIGN = "            raw_data_r0 <= {I_raw_tdata[9:2], I_raw_tdata[19:12], I_raw_tdata[29:22], I_raw_tdata[39:32]};  // 位拼接顺序：I_raw_tdata[9:2]->[31:24]、[19:12]->[23:16]、[29:22]->[15:8]、[39:32]->[7:0]，即 10bit 字段自低位起依次落到 MSB 侧；哪个字段对应图像左侧未能从本文件确认"
NEW_ASSIGN = [
    "            // 位拼接顺序与改动前完全一致（字段次序未动）：字段0(减黑后)->[31:24]、字段1->[23:16]、字段2->[15:8]、字段3->[7:0]",
    "            // 哪个字段对应图像左侧仍未能从本文件确认",
    "            // 2026-10-09 改动：由直接截断 I_raw_tdata[x:y] 改为截断 (I_raw_tdata[x:y] - 64)",
    "            raw_data_r0 <= {S_blk_f0[9:2], S_blk_f1[9:2], S_blk_f2[9:2], S_blk_f3[9:2]};",
]

OLD_HDR = "//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改"
NEW_HDR = [
    OLD_HDR,
    "//   2026-10-09  增加黑电平基座扣除（实测 64 LSB）：每个 10bit 字段先减 64（带钳位）再取高 8 位。",
    "//               依据：盖住镜头时 RAW10 实测值域 [57..79]、均值 67.02。备份 E:\\FPGA\\_backup\\20261009_blk\\",
]


def safe_write(path, text, enc, tag):
    """先编码成功再开文件；任何一步失败都不碰盘。"""
    try:
        data = text.encode(enc)
    except UnicodeEncodeError as e:
        bad = text[e.start:e.end]
        print("[FAIL] %s encode(%s) 失败于 %r (U+%04X)，未写盘" % (tag, enc, bad, ord(bad[0])))
        return False
    with open(path, "wb") as f:
        f.write(data)
    print("[OK]   %-26s 已写入 %d B (%s)" % (tag, len(data), enc))
    return True


def apply(path, enc, edits, tag):
    t = open(path, "rb").read().decode(enc)
    eol = EOL if EOL in t else "\n"
    for i, (old, new) in enumerate(edits):
        n = t.count(old)
        if n != 1:
            print("[FAIL] %s 第 %d 条模式 count=%d，放弃整文件（未写盘）" % (tag, i + 1, n))
            return False
        t = t.replace(old, new, 1)
    return safe_write(path, t, enc, tag)


def sha16(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]


# ---- 0. 先确认当前状态与备份 ----
ok = True
for p, b in ((P1, BK + r"\mipi_to_raw_converter.v"), (P2, BK + r"\isp_top.v")):
    print("before: %-26s %6d B sha16=%s | backup %6d B sha16=%s"
          % (os.path.basename(p), os.path.getsize(p), sha16(p), os.path.getsize(b), sha16(b)))

# ---- 1. mipi_to_raw_converter.v：黑电平扣除 ----
ok &= apply(P1, "gbk", [
    (INS_AFTER, EOL.join([INS_AFTER] + BLK)),
    (OLD_ASSIGN, EOL.join(NEW_ASSIGN)),
    (OLD_HDR, EOL.join(NEW_HDR)),
], "mipi_to_raw_converter.v")

# ---- 2. isp_top.v：头部说明串同步为 MODE_INIT=3'd0 ----
ok &= apply(P2, "utf-8", [
    ("my_algo(MODE_INIT=3'd2,THRESH=8'd128)", "my_algo(MODE_INIT=3'd0,THRESH=8'd128)"),
], "isp_top.v(header)")

# ---- 3. 复核 ----
print()
print("AFTER ------------------------------------------------------------")
for p in (P1, P2):
    print("%-26s %6d B sha16=%s" % (os.path.basename(p), os.path.getsize(p), sha16(p)))
t = open(P1, "rb").read().decode("gbk")
print("S_blk_level 定义 %d 处, S_blk_f0/f1/f2/f3 各 %d/%d/%d/%d 处, 旧拼接残留 %d 处"
      % (t.count("wire [9:0] S_blk_level"), t.count("S_blk_f0"), t.count("S_blk_f1"),
         t.count("S_blk_f2"), t.count("S_blk_f3"), t.count("raw_data_r0 <= {I_raw_tdata[9:2]")))
print("旧文件仍可回退：备份在 " + BK)
sys.exit(0 if ok else 1)
