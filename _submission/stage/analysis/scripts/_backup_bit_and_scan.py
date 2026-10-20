# -*- coding: utf-8 -*-
"""备份当前在板比特流 + 扫描最新图片。python _backup_bit_and_scan.py"""
import os, sys, time, shutil, hashlib
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
R_ = r"E:\FPGA"
RUN = os.path.join(R_, r"proj\baseline\lab3\td_project\camera_to_dsi_display_Runs")

print("=== all .bit / .bid / .qor / .area under _Runs ===")
rows = []
for dp, dn, fn in os.walk(RUN):
    for f in fn:
        if f.lower().endswith((".bit", ".bid", ".qor", ".area", ".ts")):
            p = os.path.join(dp, f)
            rows.append((os.path.getmtime(p), os.path.getsize(p), p))
rows.sort(reverse=True)
for t, s, p in rows[:14]:
    print("  %s %10d  %s" % (time.strftime("%m-%d %H:%M:%S", time.localtime(t)), s, p.replace(R_ + "\\", "")))

print("\n=== newest images under E:\\FPGA ===")
im = []
for dp, dn, fn in os.walk(R_):
    if any(s in dp for s in ("\\.git", "\\_backup", "\\anlogic_example", "\\\u5b98\u65b9\u8d44\u6599", "\\.extract", "\\_analysis\\out")):
        continue
    for f in fn:
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".bmp")):
            p = os.path.join(dp, f)
            try:
                im.append((os.path.getmtime(p), os.path.getsize(p), p))
            except OSError:
                pass
im.sort(reverse=True)
for t, s, p in im[:10]:
    print("  %s %9d  %s" % (time.strftime("%m-%d %H:%M:%S", time.localtime(t)), s, p.replace(R_ + "\\", "")))

src = os.path.join(RUN, "phy_1", "camera_to_dsi_display.bit")
if not os.path.exists(src):
    print("\n!! bit not found:", src); sys.exit(1)
dst = os.path.join(R_, "_backup", "20261012_bit_K45_0149")
os.makedirs(dst, exist_ok=True)
for name in ("camera_to_dsi_display.bit", "camera_to_dsi_display_compress.bit"):
    s = os.path.join(RUN, "phy_1", name)
    if os.path.exists(s):
        d = os.path.join(dst, name)
        shutil.copy2(s, d)
        md5 = hashlib.md5(open(d, "rb").read()).hexdigest()
        print("\nBACKUP %s  %d B  md5=%s" % (name, os.path.getsize(d), md5))

note = """# 2026-10-12 01:49 版比特流（K=45 黑位 + AWB 改动 B + 传感器测试图关闭）

这是 **2026-10-12 02:01 起在板子上运行的那一版**，由用户实测确认：
- 02:02 批（CNT 002994 / 003374）与 02:18 批（CNT 062894 / 063033 / 063663）
  属于同一次上电（帧差与墙钟逐段吻合），中途未重新烧录。
- 该版含三项改动：
  - 改动 A：`isp_gamma.v` 黑位恢复 K=45（`gen_gamma_lut_blackpoint.py --K 45`）
  - 改动 B：`awb.v` 增益帧锁存 + 阻尼 + 钳位（awb.v:279-347）
  - 改动 C：`design_top_wrapper.v` 关掉传感器内置测试图（7 处改动，`S_tp_canary` 恒 0）
- 来源路径：`proj\\baseline\\lab3\\td_project\\camera_to_dsi_display_Runs\\phy_1\\`
- 构建 QoR：Setup WNS +84 ps / TNS 0 / 违例 S-EP 0；Hold WNS +20 ps / TNS 0 / 违例 H-EP 0；
  `#slices 17687 (83.37%)`、`#RAMs 60`、`#DSPs 8`、`#eram 60/108`。

## 回滚方法
把本目录下的两个 .bit 覆盖回 `..._Runs\\phy_1\\`，再用 TD 的下载工具烧录即可。
源码级回滚见 `_backup\\20261011g_bp_soft45\\`（isp_gamma.v.before）
与 `_backup\\20261011i_kill_testpattern\\`（design_top_wrapper.v.before）。
"""
open(os.path.join(dst, "NOTE.md"), "w", encoding="utf-8").write(note)
print("wrote NOTE.md")
