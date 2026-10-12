# -*- coding: utf-8 -*-
"""★权威映射：全树每个 module 名 -> 哪些文件定义了它；以及 .al 实际编的是哪一份。
   目的：杜绝"我分析的副本不是工程在编的那一份"这类错误。"""
import os, re

ROOT = r"E:\FPGA\proj\baseline\lab3"
AL   = os.path.join(ROOT, "td_project", "camera_to_dsi_display.al")
SRC  = os.path.join(ROOT, "user_source", "hdl_source")

al = open(AL, "rb").read().decode("utf-8", "replace")
al_files = re.findall(r'<File\s+Path="([^"]+)"', al)
print(f".al 共 {len(al_files)} 个 File 条目\n")

def norm(p):
    p = p.replace("\\", "/")
    if p.startswith("../"):
        return os.path.normpath(os.path.join(ROOT, "td_project", p))
    return p

compiled = [norm(p) for p in al_files]
compiled_hdl = [p for p in compiled if p.lower().endswith((".v", ".sv"))]
print(f"其中 HDL 源文件 {len(compiled_hdl)} 个，出现两次以上（重复）的：")
from collections import Counter
for p, c in Counter(compiled_hdl).items():
    if c > 1:
        print("   x%d %s" % (c, p))

# 全树扫 module 定义
defs = {}
for dirpath, _, files in os.walk(SRC):
    for f in files:
        if not f.lower().endswith((".v", ".sv")):
            continue
        p = os.path.join(dirpath, f)
        try:
            txt = open(p, "rb").read().decode("utf-8", "replace")
        except Exception:
            continue
        # 去掉块注释再找 module，避免命中注释里的 module
        txt2 = re.sub(r"/\*.*?\*/", "", txt, flags=re.S)
        txt2 = re.sub(r"//[^\n]*", "", txt2)
        for m in re.finditer(r"^\s*module\s+([A-Za-z_]\w*)", txt2, re.M):
            defs.setdefault(m.group(1), []).append(p)

print("\n=== ★重名 module（同一名字有多份实现）===")
for name in sorted(defs):
    if len(defs[name]) > 1:
        print(f"\n  module {name}  （{len(defs[name])} 份）")
        for p in defs[name]:
            inc = "★在 .al 中【编译】" if p in compiled_hdl else "  未在 .al（不编译）"
            print(f"     {inc}  {p.replace(SRC, '...hdl_source')}")

print("\n=== 关键名字：工程实际在编哪一份 ===")
for name in ("awb", "signal_delay", "raw10_unpacket_2lane", "csi_unpacket_2lane",
             "raw10_unpacket", "csi_unpacket", "data_96bit_to_128bit",
             "uics500reg", "uicfgcs500", "uicfgcs500_720p", "uics500reg_720p60"):
    hits = [p for p in defs.get(name, []) if p in compiled_hdl]
    print(f"  {name:<24} 编译中: {[h.replace(SRC, '...') for h in hits] if hits else '（无，未编译）'}")

print("\n=== .al 里的 HDL 清单 ===")
for p in compiled_hdl:
    print("   ", p.replace(SRC, "...hdl_source"))
