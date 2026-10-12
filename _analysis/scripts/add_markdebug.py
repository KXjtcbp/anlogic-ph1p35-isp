# -*- coding: utf-8 -*-
"""给 design_top_wrapper.v 的 8 根 ISP 周边 wire 加 MARK_DEBUG 标记，并顺手把模拟增益改成 11.25×。
保留原文件的 BOM / 换行风格（按 \n 切分再 \n 拼回，\r 作为行尾内容原样保留）。"""
import re

H = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"

# ---------- 1) design_top_wrapper.v：加 MARK_DEBUG ----------
p = H + r"\design_top_wrapper.v"
raw = open(p, "rb").read()
bom = raw.startswith(b"\xef\xbb\xbf")
crlf = raw.count(b"\r\n")
lf = raw.count(b"\n")
print(f"[wrapper] BOM={bom}  CRLF={crlf}  LF={lf}  size={len(raw)}")

txt = raw.decode("utf-8-sig")
targets = [
    "S_axis_tdata", "S_axis_tvalid", "S_axis_tuser", "S_axis_tlast",
    "S_ISP_O_tdata", "S_ISP_O_tvalid", "S_ISP_O_tuser", "S_ISP_O_tlast",
]
lines = txt.split("\n")
hits = []
for i, ln in enumerate(lines):
    m = re.match(r"^(\s*)wire\b", ln)
    if not m:
        continue
    if "MARK_DEBUG" in ln:
        continue
    for t in targets:
        # 该行必须正好声明这个信号（后面紧跟可选的空白和分号）
        if re.search(r"(?<![\w$])" + re.escape(t) + r"\s*;", ln):
            indent = m.group(1)
            lines[i] = indent + '(*MARK_DEBUG = "TRUE"*) ' + ln[len(indent):]
            hits.append((i + 1, t))
            break
out = "\n".join(lines)
open(p, "w", encoding="utf-8-sig" if bom else "utf-8", newline="").write(out)
print(f"[wrapper] 加了 {len(hits)} 处 MARK_DEBUG:")
for n, t in hits:
    print(f"   :{n}  {t}")

# ---------- 2) uics500reg_720p60.v：模拟增益 8.000x -> 11.25x ----------
q = H + r"\uics500_cfg\uics500reg_720p60.v"
rawq = open(q, "rb").read()
bomq = rawq.startswith(b"\xef\xbb\xbf")
print(f"[reg] BOM={bomq}  CRLF={rawq.count(b'\r\n')}  LF={rawq.count(b'\n')}  size={len(rawq)}")
tq = rawq.decode("utf-8-sig")
old = "16'h3e09,8'h20"
new = "16'h3e09,8'h2d"
cnt = tq.count(old)
if cnt == 1:
    tq = tq.replace(old, new)
    open(q, "w", encoding="utf-8-sig" if bomq else "utf-8", newline="").write(tq)
    print(f"[reg] 3e09: 8'h20 -> 8'h2d  ({cnt} 处)")
else:
    print(f"[reg] ！！命中 {cnt} 处，未修改，需人工确认")
