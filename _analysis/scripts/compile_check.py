# -*- coding: utf-8 -*-
"""用 ModelSim 对 .al 里列出的 HDL 源文件做逐文件编译体检。

基线（改名之前）：参与编译 39 个，38 个 exit=0；
唯一失败是既有问题 ph1p35_ddr\ph1p35_324_ddr_wrapper.v(61) Undefined variable: 'dhi_clk'。
判据：改名之后其余 38 个必须仍然 exit=0。
"""
import os, subprocess, glob, sys

VLOG = r"E:\modelsim\modelsim_ase\win32aloem\vlog.exe"
VLIB = r"E:\modelsim\modelsim_ase\win32aloem\vlib.exe"
WORK = r"E:\FPGA\_analysis\hdlbase"
HDL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
FILELIST = r"E:\FPGA\_analysis\reports\hdl_filelist.txt"
LOG = r"E:\FPGA\_analysis\reports\compile_check.txt"

files = [l.strip() for l in open(FILELIST, encoding="utf-8-sig")
         if l.strip().endswith((".v", ".sv")) and ".enc." not in l]

incdirs = sorted({os.path.dirname(p) for p in
                  glob.glob(os.path.join(HDL, "**", "blk_mem_gen_*", "RTL", "include"),
                            recursive=True)})

if not os.path.isdir(WORK):
    os.makedirs(WORK)
# work 库必须先建，否则 vlog 报 vlog-19 Failed to access library 'work'
if not os.path.isdir(os.path.join(WORK, "work")):
    subprocess.run([VLIB, "work"], cwd=WORK, capture_output=True)

inc_args = []
for d in incdirs:
    inc_args += ["+incdir+" + d]

out, fails, ok = [], [], 0
out.append("include dirs: " + repr(incdirs))
out.append(f"待编译文件数: {len(files)}\n")

for f in files:
    r = subprocess.run([VLOG, "-quiet", "-sv", *inc_args, "-work", "work", f],
                       cwd=WORK, capture_output=True, text=True, errors="replace")
    tag = "OK  " if r.returncode == 0 else f"FAIL({r.returncode})"
    if r.returncode == 0:
        ok += 1
    else:
        fails.append((f, r.stdout + r.stderr))
    out.append(f"[{tag}] {os.path.relpath(f, HDL)}")

out.append(f"\n==== 汇总: exit=0 的 {ok} 个 / 失败 {len(fails)} 个 ====")
for f, msg in fails:
    out.append(f"\n---- {os.path.relpath(f, HDL)} ----")
    out.append("\n".join(msg.strip().splitlines()[:12]))

open(LOG, "w", encoding="utf-8").write("\n".join(out))
print(f"exit=0: {ok} / {len(files)}   失败: {len(fails)}")
for f, _ in fails:
    print("  FAIL", os.path.relpath(f, HDL))
print("日志:", LOG)
