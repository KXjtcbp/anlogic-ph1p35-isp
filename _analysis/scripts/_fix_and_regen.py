# -*- coding: utf-8 -*-
"""修 _L2.py 的 isp_top.v 代码块（合并重复 + 补 ▸ 解释），然后重新装配生成 docx 并复审。"""
import os, re, sys, importlib.util
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
T = os.environ.get("TEMP", r"C:\Users\KX\AppData\Local\Temp")

# ---------- 1) 修 _L2.py 第 32~36 行 ----------
p2 = os.path.join(T, "_L2.py")
L = open(p2, encoding="utf-8-sig").read().splitlines()
assert L[31].startswith('code("hdl_source\\\\isp\\\\isp_top.v", 187, 187'), "第32行不是预期的 code 调用：%r" % L[31]
assert L[35].startswith('    code("hdl_source\\\\isp\\\\isp_top.v", ln, ln'), "第36行不是预期的循环体：%r" % L[35]

NEW = '''_NOTE_TOP = {
    187: "这一行是 demosaic（BGGR 去马赛克）的例化起点，把 RAW10 的 Bayer 数据还原成 RGB。它后面紧跟 data128_96 把 128bit 转成 96bit。",
    228: "这一行是 lsc（镜头暗角校正）的例化起点。它只校 R/B 相对 G 的比例，G 原样透传，所以下面紧接的 awb 看到的是已经补好暗角的画面。",
    298: "这一行是 awb（自动白平衡）的例化起点，内部包含倒数查表的 wb_recip。它的输入是 lsc 的输出，输出给 isp_gamma。",
    325: "这一行是 isp_gamma（真 S 曲线查表）的例化。它是全链里唯一一个固定 2 拍延迟的模块，旁路时也是 2 拍，所以切换不错帧。",
    349: "这一行是 my_algo（五模式风格化）的例化起点。K1~K4 切换的 mode 就是它里面的 case 选择信号。",
    402: "这一行是 data_96bit_to_128bit，把 96bit 的 4 像素回切成 128bit（3 个 96bit 拼成 2 个 128bit），给后面的 OSD 与 HDMI 用。"
}
_L_TOP = open(os.path.join(ROOT, "hdl_source\\\\isp\\\\isp_top.v"), "rb").read().decode("utf-8").splitlines()
for _ln in (187, 228, 298, 325, 349, 402):
    code("hdl_source\\\\isp\\\\isp_top.v", _ln, _ln, note=_NOTE_TOP[_ln], lines=[_L_TOP[_ln - 1]])'''

L2 = L[:31] + NEW.splitlines() + L[36:]
open(p2, "w", encoding="utf-8").write("\n".join(L2) + "\n")
print("[_L2] 已重写第 32~36 行，文件 %d 行（原 %d 行）" % (len(L2), len(L)))

# ---------- 2) 重新装配 ----------
parts = []
for nm in ("_L0.py", "_L1.py", "_L2.py", "_L3.py", "_L4.py"):
    s = open(os.path.join(T, nm), encoding="utf-8-sig").read().replace("\ufeff", "")
    parts.append(s)
ALL = "\n".join(parts)
pa = os.path.join(T, "_ALL.py")
open(pa, "w", encoding="utf-8").write(ALL)
print("[_ALL] 装配完成 %d chars，U+FEFF 残留 %d" % (len(ALL), ALL.count("\ufeff")))

# ---------- 3) 执行生成 ----------
runpy = importlib.util.spec_from_file_location("gen", pa)
mod = importlib.util.module_from_spec(runpy)
sys.argv = ["gen"]
runpy.loader.exec_module(mod)

OUT = r"E:\FPGA\项目学习清单_20261023.docx"
import hashlib
from docx import Document
d = Document(OUT)
print("\n=== 生成结果 ===")
print("  文件 %d B  md5=%s" % (os.path.getsize(OUT), hashlib.md5(open(OUT, "rb").read()).hexdigest()))
print("  段落 %d  表格 %d" % (len(d.paragraphs), len(d.tables)))

# ---------- 4) 复审 ----------
ps = [p.text for p in d.paragraphs]
print("\n=== 复审 ===")
bad_star = [i for i, t in enumerate(ps) if "**" in t]
bad_tick = [i for i, t in enumerate(ps) if "`" in t and not t.startswith("▎")]
print("  残留 ** 的段落: %s" % (bad_star if bad_star else "无"))
print("  残留 ` 的段落（非代码块）: %s" % (bad_tick if bad_tick else "无"))

srcs = [t for t in ps if t.startswith("▎")]
notes = [t for t in ps if t.startswith("▸")]
print("  代码块来源行 %d 条 / ▸ 解释行 %d 条" % (len(srcs), len(notes)))
dup = {}
for s in srcs:
    dup[s] = dup.get(s, 0) + 1
d2 = {k: v for k, v in dup.items() if v > 1}
print("  重复的代码块: %s" % (d2 if d2 else "无"))
miss = []
for i, t in enumerate(ps):
    if t.startswith("▎"):
        seg = ps[i:i + 40]
        if not any(x.startswith("▸") for x in seg):
            miss.append(t)
print("  缺 ▸ 解释的块: %s" % (miss if miss else "无"))
print("  一级标题 %d 个" % len([t for t in ps if t and t[0] in "第附项" and len(t) < 60 and "章" in t[:4] or t.startswith("这份清单")]))
