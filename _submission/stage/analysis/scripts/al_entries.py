# -*- coding: utf-8 -*-
"""解析新旧 .al 的 File 条目（路径+属性），精确指出差异；并检查两个疑似同名模块。"""
import re, os

OLD = r"E:\FPGA\_backup\20261009_rename\hdl_source\camera_to_dsi_display.al.orig"
NEW = r"E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display.al"
ROOT = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"

out = []


def parse(p):
    txt = open(p, "rb").read().decode("utf-8", "replace")
    entries = {}
    for m in re.finditer(r'<File\s+Path="([^"]+)">(.*?)</File>', txt, re.S):
        path, body = m.group(1), m.group(2)
        attrs = dict(re.findall(r'<Attr\s+Name="([^"]+)"\s+Val="([^"]*)"\s*/>', body))
        entries[path] = attrs
    return entries


o = parse(OLD)
n = parse(NEW)
# 旧文件里带 typo，统一成新名再比
o = {(k.replace("hdmi_phy_warpper", "hdmi_phy_wrapper")): v for k, v in o.items()}

out.append("旧 .al 条目 %d 个 / 新 .al 条目 %d 个" % (len(o), len(n)))
out.append("")
out.append("=== 只在旧 .al 里（新 .al 丢了）===")
for k in sorted(set(o) - set(n)):
    out.append("  " + k + "   attrs=" + str(o[k]))
out.append("=== 只在新 .al 里（新增）===")
for k in sorted(set(n) - set(o)):
    out.append("  " + k + "   attrs=" + str(n[k]))
out.append("")
out.append("=== 属性发生变化的条目 ===")
for k in sorted(set(o) & set(n)):
    if o[k] != n[k]:
        added = {a: v for a, v in n[k].items() if o[k].get(a) != v}
        removed = {a: v for a, v in o[k].items() if n[k].get(a) != v}
        out.append("  %s" % k)
        out.append("      旧: %s" % o[k])
        out.append("      新: %s" % n[k])
        out.append("      新增/改动: %s   丢失/改动: %s" % (added, removed))
out.append("")
out.append("=== 旧 .al 里所有 AutoExcluded=true 的条目 ===")
for k, v in sorted(o.items()):
    if v.get("AutoExcluded") == "true":
        out.append("  " + k)
out.append("=== 新 .al 里所有 AutoExcluded=true 的条目 ===")
for k, v in sorted(n.items()):
    if v.get("AutoExcluded") == "true":
        out.append("  " + k)

out.append("")
out.append("=== 两个疑似同族文件定义的 module ===")
for rel in ("hdmi_phy_wrapper.v", "lane_lvds_10_1.v", "hdmi_tx.v"):
    p = os.path.join(ROOT, rel)
    if not os.path.exists(p):
        out.append("  %s  不存在" % rel)
        continue
    txt = open(p, "rb").read().decode("utf-8", "replace")
    mods = re.findall(r"^\s*module\s+([\w$]+)", txt, re.M)
    out.append("  %-24s %d B  module: %s" % (rel, os.path.getsize(p), mods))

out.append("")
out.append("=== 谁例化了 hdmi_phy_wrapper / lane_lvds_10_1 ===")
for dp, _d, fns in os.walk(ROOT):
    for fn in fns:
        if not fn.endswith((".v", ".sv")):
            continue
        p = os.path.join(dp, fn)
        try:
            txt = open(p, "rb").read().decode("utf-8", "replace")
        except Exception:
            continue
        for kw in ("hdmi_phy_wrapper", "lane_lvds_10_1"):
            for m in re.finditer(r"\b" + kw + r"\b", txt):
                line = txt[:m.start()].count("\n") + 1
                ctx = txt.splitlines()[line - 1].strip()
                if ctx.startswith("//"):
                    continue
                out.append("  %-46s :%-4d %s" % (os.path.relpath(p, ROOT), line, ctx[:110]))

open(r"E:\FPGA\_analysis\reports\al_entries.txt", "w", encoding="utf-8").write("\n".join(out))
print("done", len(out))
