# -*- coding: utf-8 -*-
"""校验 2026-10-10b 加固版（测试图永久关闭 + 四个开关状态上 LED）的改动是否完整。

检查项：
 A. uics500reg_720p60.v
    A1. 表内索引必须是 0..120 连续无缺口，且 REG_SIZE == 索引数
    A2. 索引 116 必须是 `(TEST_PATTERN & I_test_pattern) ? 8'hbc : 8'hb4`（& 不是 |）
    A3. 索引 117 = {3e03, 0x0b}；118/119 = 3e08/3e09 由 I_gain_high 选择
    A4. 索引 120 = {4501, 0xb4}（兜底）
    A5. parameter TEST_PATTERN == 1'b0
 B. design_top_wrapper.v
    B1. 端口表新增 `output wire [3:0] O_led`
    B2. `.I_test_pattern(1'b0)`（不再接 S_test_pattern）
    B3. 全文件不再出现 `S_test_pattern`
    B4. `assign O_led = {S_sw4_sync1, S_sw3_sync1, S_sw2_sync1, S_sw1_sync1};`
    B5. S_sw1_sync1 / S_sw2_sync1 / S_sw3_sync1 / S_sw4_sync1 均有声明
 C. pin.adc
    C1. O_led[0..3] 四条，LOCATION 依次为 D10/E10/C6/D6，带 DRIVESTRENGTH
    C2. I_switch[0..3] 四条仍在，LOCATION 依次为 A4/B4/E11/D11
    C3. 无 `//` 注释（TD 的 .adc 不接受），全部是 `#`
"""
import re, sys, io

ROOT = r"E:\FPGA\proj\baseline\lab3\user_source"
REG = ROOT + r"\hdl_source\uics500_cfg\uics500reg_720p60.v"
TOP = ROOT + r"\hdl_source\design_top_wrapper.v"
ADC = ROOT + r"\constraints_source\pin.adc"

res = []
def ck(ok, name, detail=""):
    res.append((bool(ok), name, detail))

def read(p):
    for enc in ("utf-8-sig", "gbk", "latin-1"):
        try:
            return open(p, encoding=enc).read()
        except UnicodeDecodeError:
            continue
    return open(p, encoding="latin-1").read()

# ---------------- A ----------------
reg = read(REG)
entries = {}
dups = []
for m in re.finditer(r"(\d+)\s*:\s*REG_DATA\s*=\s*\{([^}]*)\}", reg):
    k = int(m.group(1))
    if k in entries:
        dups.append(k)
    entries[k] = m.group(2).strip()
idx = sorted(entries)
ck(not dups, "A1a0 无重复索引", "重复: %s" % dups)
ck(idx == list(range(0, len(idx))), "A1a 索引 0..%d 连续无缺口" % (len(idx) - 1),
   "实际 %d 条，范围 %s..%s" % (len(idx), idx[0], idx[-1]))
msz = re.search(r"assign\s+REG_SIZE\s*=\s*9'd(\d+)", reg)
size = int(msz.group(1)) if msz else -1
ck(size == len(idx), "A1b REG_SIZE == 条目数", "REG_SIZE=%d 条目数=%d" % (size, len(idx)))

e116 = entries.get(116, "")
ck("TEST_PATTERN & I_test_pattern" in e116.replace("  ", " "), "A2 索引116 用 & 而非 |", e116)
ck("|" not in e116, "A2b 索引116 里没有裸 |", e116)
e117 = entries.get(117, "")
ck("3e03" in e117 and "8'h0b" in e117, "A3 索引117 = 0x3e03 <- 0x0b", e117)
e118, e119 = entries.get(118, ""), entries.get(119, "")
ck("3e08" in e118 and "I_gain_high" in e118 and "8'h1f" in e118 and "8'h0f" in e118,
   "A4 索引118 = 3e08 由 I_gain_high 选 0x1f/0x0f", e118)
ck("3e09" in e119 and "I_gain_high" in e119 and "8'h2d" in e119 and "8'h20" in e119,
   "A5 索引119 = 3e09 由 I_gain_high 选 0x2d/0x20", e119)
e120 = entries.get(120, "")
ck("4501" in e120 and "8'hb4" in e120, "A6 索引120 = 0x4501 <- 0xb4 (兜底)", e120)
ck(re.search(r"parameter\s+TEST_PATTERN\s*=\s*1'b0", reg) is not None,
   "A7 parameter TEST_PATTERN == 1'b0")

# ---------------- B ----------------
top = read(TOP)
ck(re.search(r"output\s+wire\s*\[3:0\]\s*O_led\s*,", top) is not None, "B1 端口表有 output wire [3:0] O_led")
ck(".I_test_pattern(1'b0)" in top.replace(" ", ""), "B2 .I_test_pattern 硬接 1'b0")
ck("S_test_pattern" not in top, "B3 全文件已无 S_test_pattern")
mled = re.search(r"assign\s+O_led\s*=\s*\{([^}]*)\}", top)
ck(mled is not None and
   [s.strip() for s in mled.group(1).split(",")] ==
   ["S_sw4_sync1", "S_sw3_sync1", "S_sw2_sync1", "S_sw1_sync1"],
   "B4 assign O_led = {SW4,SW3,SW2,SW1}", mled.group(1).strip() if mled else "未找到")
for n in (1, 2, 3, 4):
    ck(re.search(r"reg\s+S_sw%d_sync0\s*,\s*S_sw%d_sync1\s*;" % (n, n), top) is not None,
       "B5 SW%d 同步寄存器已声明" % n)

# ---------------- C ----------------
adc = read(ADC)
for i, loc in enumerate(["D10", "E10", "C6", "D6"]):
    m = re.search(r"set_pin_assignment\s*\{\s*O_led\[%d\]\s*\}\s*\{([^}]*)\}" % i, adc)
    ck(m is not None and ("LOCATION = " + loc) in m.group(1) and "DRIVESTRENGTH" in m.group(1),
       "C1 O_led[%d] -> %s (+DRIVESTRENGTH)" % (i, loc), m.group(1).strip() if m else "未找到")
for i, loc in enumerate(["A4", "B4", "E11", "D11"]):
    m = re.search(r"set_pin_assignment\s*\{\s*I_switch\[%d\]\s*\}\s*\{([^}]*)\}" % i, adc)
    ck(m is not None and ("LOCATION = " + loc) in m.group(1),
       "C2 I_switch[%d] -> %s" % (i, loc), m.group(1).strip() if m else "未找到")
ck("//" not in adc, "C3 .adc 内没有 // 注释")
ck(sum(1 for l in adc.splitlines() if l.strip().startswith("set_pin_assignment")) == 23,
   "C4 set_pin_assignment 共 23 条（原 19 + LED 4）", "实际 %d" % sum(1 for l in adc.splitlines() if l.strip().startswith("set_pin_assignment")))

# ---------------- 输出 ----------------
buf = io.StringIO()
bad = 0
for ok, name, detail in res:
    if not ok:
        bad += 1
    buf.write(("[PASS] " if ok else "[FAIL] ") + name + (("   <-- " + detail) if (detail and not ok) else "") + "\n")
buf.write("\n==== %d 项检查，失败 %d 项 ====\n" % (len(res), bad))
txt = buf.getvalue()
open(r"E:\FPGA\_analysis\reports\verify_v1_hardening.txt", "w", encoding="utf-8").write(txt)
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
print(txt)
sys.exit(1 if bad else 0)
