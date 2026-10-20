# -*- coding: utf-8 -*-
"""校验 2026-10-10c 增益改动（模拟增益上限 15.750x + 新增 SW3 数字增益 x2）：

  A. 寄存器表 uics500reg_720p60.v
     A1 索引 0..122 连续、无重复、无缺口
     A2 REG_SIZE == 123 == 条目数
     A3 索引 112/113 = 0x3e08=0x1f / 0x3e09=0x2d（上电先写的中间值，保留）
     A4 索引 118/119 = 0x3e08 = I_gain_high?0x1f:0x0f，0x3e09 = I_gain_high?0x3f:0x20
     A5 索引 121/122 = 0x3e06 = I_gain_digital?0x01:0x00，0x3e07 = 0x80
     A6 索引 116 = 0x4501 且条件里是 `&`（不是 `|`）；索引 120 = 0x4501=0xb4
     A7 索引 117 = 0x3e03=0x0b（AGC 位，本轮保留）
     A8 端口表含 I_gain_digital；模块头含 parameter TEST_PATTERN = 1'b0
  B. uicfgcs500_720p.v：声明 I_gain_digital 且接到 u_init_table
  C. design_top_wrapper.v：S_gain_digital = ~S_sw3_sync1；接到 u_uicfgcs500；O_led 仍在
  D. 曝光仍为 1990（索引 94/95/96）且 VTS=1000（索引 28/29）
"""
import re, sys

BASE = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
TBL  = BASE + r"\uics500_cfg\uics500reg_720p60.v"
CFG  = BASE + r"\uics500_cfg\uicfgcs500_720p.v"
TOP  = BASE + r"\design_top_wrapper.v"

def rd(p):
    for enc in ("utf-8", "utf-8-sig", "gbk", "latin-1"):
        try:
            return open(p, encoding=enc).read()
        except UnicodeDecodeError:
            continue
    raise RuntimeError(p)

tbl, cfg, top = rd(TBL), rd(CFG), rd(TOP)
ok = True
def chk(cond, msg):
    global ok
    print(("[PASS] " if cond else "[FAIL] ") + msg)
    if not cond: ok = False

print("=" * 78); print("A. 寄存器表 uics500reg_720p60.v"); print("=" * 78)
entries = {}
for m in re.finditer(r"(\d+)\s*:\s*REG_DATA\s*=\s*\{([^}]*)\}", tbl):
    entries[int(m.group(1))] = m.group(2).strip()
idx = sorted(entries)
chk(idx == list(range(0, 123)), "A1 索引连续 0..122（实际 %d..%d，共 %d 条）" % (idx[0], idx[-1], len(idx)))
msz = re.search(r"assign\s*REG_SIZE\s*=\s*9'd(\d+)", tbl)
chk(msz and int(msz.group(1)) == 123 == len(entries),
    "A2 REG_SIZE = %s，条目数 = %d" % (msz.group(1) if msz else "?", len(entries)))

def norm(s): return re.sub(r"\s+", "", s)
e = {k: norm(v) for k, v in entries.items()}
print("  112 :", entries.get(112)); print("  113 :", entries.get(113))
print("  116 :", entries.get(116)); print("  117 :", entries.get(117))
print("  118 :", entries.get(118)); print("  119 :", entries.get(119))
print("  120 :", entries.get(120)); print("  121 :", entries.get(121))
print("  122 :", entries.get(122))

chk(e.get(112) == "16'h3e08,8'h1f" and e.get(113) == "16'h3e09,8'h2d",
    "A3 索引 112/113 = 3e08=0x1f / 3e09=0x2d")
chk(e.get(118) == "16'h3e08,I_gain_high?8'h1f:8'h0f", "A4a 索引 118 = 3e08 = gain_high?0x1f:0x0f")
chk(e.get(119) == "16'h3e09,I_gain_high?8'h3f:8'h20", "A4b 索引 119 = 3e09 = gain_high?**0x3f**:0x20（15.750x 上限）")
chk(e.get(121) == "16'h3e06,I_gain_digital?8'h01:8'h00", "A5a 索引 121 = 3e06 = gain_digital?0x01:0x00（x2/x1）")
chk(e.get(122) == "16'h3e07,8'h80", "A5b 索引 122 = 3e07 = 0x80（细档 1.000，显式写）")
cond116 = entries.get(116, "")
chk("16'h4501" in cond116 and "&" in cond116 and "|" not in cond116, "A6a 索引 116 条件用 `&` 且非 `|`")
chk(e.get(120) == "16'h4501,8'hb4", "A6b 索引 120 = 4501=0xb4 兜底")
chk(e.get(117) == "16'h3e03,8'h0b", "A7 索引 117 = 3e03=0x0b（AGC 位保留）")
chk(re.search(r"input\s+I_gain_digital", tbl) is not None, "A8a 表模块端口含 I_gain_digital")
chk(re.search(r"parameter\s+TEST_PATTERN\s*=\s*1'b0", tbl) is not None, "A8b parameter TEST_PATTERN = 1'b0")

print(); print("=" * 78); print("D. 曝光/VTS 未被动过"); print("=" * 78)
chk(e.get(28) == "16'h320e,8'h03" and e.get(29) == "16'h320f,8'he8", "D1 VTS = 0x03E8 = 1000")
chk(e.get(94) == "16'h3e00,8'h00" and e.get(95) == "16'h3e01,8'h7c" and e.get(96) == "16'h3e02,8'h60",
    "D2 曝光 = {0,0x7c,0x6} = 0x07C6 = 1990 = 2*1000-10（硬件上限）")

print(); print("=" * 78); print("B. uicfgcs500_720p.v"); print("=" * 78)
chk(re.search(r"input\s+wire\s+I_gain_digital", cfg) is not None, "B1 声明 input wire I_gain_digital")
chk(re.search(r"\.I_gain_digital\s*\(\s*I_gain_digital\s*\)", cfg) is not None,
    "B2 接到 uics500reg_720p60 u_init_table")
chk(re.search(r"reg_index\s*==\s*9'd115", cfg) is not None, "B3 延时触发点仍是索引 115（表尾追加未破坏它）")

print(); print("=" * 78); print("C. design_top_wrapper.v"); print("=" * 78)
chk(re.search(r"wire\s+S_gain_digital\s*=\s*~\s*S_sw3_sync1", top) is not None,
    "C1 S_gain_digital = ~S_sw3_sync1（拨上=1=高档）")
chk(re.search(r"\.I_gain_digital\s*\(\s*S_gain_digital\s*\)", top) is not None, "C2 接到 u_uicfgcs500")
chk(re.search(r"\.I_test_pattern\s*\(\s*1'b0\s*\)", top) is not None, "C3 I_test_pattern 仍硬接 1'b0")
chk(re.search(r"\.I_gain_high\s*\(\s*S_gain_high\s*\)", top) is not None, "C4 I_gain_high 仍接着")
chk(re.search(r"assign\s+O_led\s*=", top) is not None, "C5 O_led 实时指示仍在")

print(); print("=" * 78)
print("总结：%s" % ("全部 PASS" if ok else "存在 FAIL"))
sys.exit(0 if ok else 1)
