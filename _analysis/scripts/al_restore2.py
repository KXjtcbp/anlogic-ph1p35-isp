# -*- coding: utf-8 -*-
"""从已知good 的 .orig 恢复 camera_to_dsi_display.al，并做逐项复验。
安全要点：
  1) 先算出完整字节变量，再 open(...,'wb').write(...) —— 绝不让 open() 先截断文件。
  2) 只用 ASCII 打印，避免 GBK 控制台 UnicodeEncodeError（本脚本第一版就死在这上面）。
  3) 保留 .orig 的 CRLF 与无 BOM。
"""
import os, re, sys, time, hashlib

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AL   = r"E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display.al"
ORIG = r"E:\FPGA\_backup\20261009_rename\hdl_source\camera_to_dsi_display.al.orig"
BROKEN = r"E:\FPGA\_backup\20261009_al修复\camera_to_dsi_display.al.broken_again_20261009_181746"

def sha(b):
    return hashlib.sha256(b).hexdigest()[:16]

def paths_of(txt):
    """按出现顺序取所有 File 条目的 Path。"""
    return re.findall(r"<File\b[^>]*Path=\"([^\"]+)\"", txt)

def phy_ctx(txt, needle):
    lines = txt.split("\n")
    for i, l in enumerate(lines):
        if needle in l:
            return i, lines[max(0, i - 1):i + 2]
    return -1, []

def dump(tag, path):
    raw = open(path, "rb").read()
    txt = raw.decode("utf-8", "surrogateescape")
    ps = paths_of(txt)
    o = dict(tag=tag, bytes=len(raw), sha16=sha(raw),
             cr=raw.count(b"\r"), lf=raw.count(b"\n"),
             bom=(raw[:3] == b"\xef\xbb\xbf"),
             n_file=len(re.findall(r"<File\b", txt)),
             n_path=len(ps),
             n_new=len(re.findall(r"hdmi_phy_wrapper\.v", txt)),
             n_old=len(re.findall(r"hdmi_phy_warpper\.v", txt)),
             n_auto=len(re.findall(r"AutoExcluded", txt)),
             n_attr=len(re.findall(r"<Attr\b", txt)),
             paths=ps, txt=txt)
    i, ctx = phy_ctx(txt, "hdmi_phy_")
    o["phy_line"] = i
    o["phy_ctx"] = ctx
    return o

print("=" * 78)
print("[1] BEFORE : current .al")
cur = dump("before", AL)
for k in ("bytes","sha16","cr","lf","bom","n_file","n_path","n_new","n_old","n_auto","n_attr"):
    print("    %-10s = %s" % (k, cur[k]))
print("    mtime      = %s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(AL))))
print("    phy entry line = %d" % cur["phy_line"])
for l in cur["phy_ctx"]:
    print("      | " + l.rstrip("\r"))

print("=" * 78)
print("[2] SOURCE : .orig")
src = dump("orig", ORIG)
for k in ("bytes","sha16","cr","lf","bom","n_file","n_path","n_new","n_old","n_auto","n_attr"):
    print("    %-10s = %s" % (k, src[k]))
print("    mtime      = %s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(ORIG))))
print("    phy entry line = %d" % src["phy_line"])
for l in src["phy_ctx"]:
    print("      | " + l.rstrip("\r"))

print("=" * 78)
print("[3] SAFETY CHECKS on .orig")
ok = True
if src["n_auto"] != 0:
    print("    FAIL: .orig contains AutoExcluded"); ok = False
else:
    print("    PASS: AutoExcluded == 0")
if src["n_old"] != 1:
    print("    FAIL: old spelling appears %d times (expect 1)" % src["n_old"]); ok = False
else:
    print("    PASS: old spelling appears exactly once")
if src["n_new"] != 0:
    print("    FAIL: .orig already has new spelling"); ok = False
else:
    print("    PASS: no new spelling yet")
if not ok:
    print("ABORT"); sys.exit(1)

# 当前坏版本与坏版本存档是否逐字节相同（证明它就是 TD 17:31:35 那次写的）
if os.path.exists(BROKEN):
    bb = open(BROKEN, "rb").read()
    print("    broken archive sha=%s ; identical to current .al = %s" % (sha(bb), sha(bb) == cur["sha16"]))
    btxt = bb.decode("utf-8", "surrogateescape")
    bset, sset = set(paths_of(btxt)), set(paths_of(src["txt"]))
    print("    broken paths=%d  orig paths=%d" % (len(bset), len(sset)))
    print("    in ORIG but NOT in broken (should be exactly the phy file):")
    for p in sorted(sset - bset):
        print("        + " + p)
    print("    in BROKEN but NOT in orig (should be empty):")
    for p in sorted(bset - sset):
        print("        - " + p)

# ---- 生成恢复内容：先算好字节 ----
new_txt = src["txt"].replace("hdmi_phy_warpper.v", "hdmi_phy_wrapper.v")
new_bytes = new_txt.encode("utf-8", "surrogateescape")
print("=" * 78)
print("[4] WRITE  %d bytes  (orig %d, delta %+d)" % (len(new_bytes), src["bytes"], len(new_bytes) - src["bytes"]))
open(AL, "wb").write(new_bytes)
print("    done")

print("=" * 78)
print("[5] AFTER : verify")
new = dump("after", AL)
for k in ("bytes","sha16","cr","lf","bom","n_file","n_path","n_new","n_old","n_auto","n_attr"):
    print("    %-10s = %s" % (k, new[k]))
print("    mtime      = %s" % time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(os.path.getmtime(AL))))
print("    phy entry line = %d" % new["phy_line"])
for l in new["phy_ctx"]:
    print("      | " + l.rstrip("\r"))

print("=" * 78)
print("[6] CRITERIA")
checks = [
    ("bytes == 23569",                 new["bytes"] == 23569, new["bytes"]),
    ("<File entries == 55",            new["n_file"] == 55, new["n_file"]),
    ("Path attrs == 55",               new["n_path"] == 55, new["n_path"]),
    ("hdmi_phy_wrapper.v appears == 1",new["n_new"] == 1, new["n_new"]),
    ("old spelling == 0",              new["n_old"] == 0, new["n_old"]),
    ("AutoExcluded == 0",              new["n_auto"] == 0, new["n_auto"]),
    ("no BOM",                         new["bom"] is False, new["bom"]),
    ("CRLF preserved (cr==lf==506)",   new["cr"] == 506 and new["lf"] == 506, "cr=%d lf=%d" % (new["cr"], new["lf"])),
    ("text identical to renamed orig", new["txt"] == new_txt, True),
]
allok = True
for n, good, val in checks:
    print("    [%s] %-34s (%s)" % ("PASS" if good else "FAIL", n, val))
    allok = allok and good

print("=" * 78)
print("[7] RE-READ after 3 s (detect external clobber)")
time.sleep(3)
again = dump("reread", AL)
same = again["sha16"] == new["sha16"]
print("    sha16 = %s ; unchanged = %s ; bytes = %d" % (again["sha16"], same, again["bytes"]))
print()
print("RESULT: " + ("ALL PASS" if (allok and same) else "*** SOME CHECK FAILED ***"))
