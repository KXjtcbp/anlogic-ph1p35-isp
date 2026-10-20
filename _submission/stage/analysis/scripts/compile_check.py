# -*- coding: utf-8 -*-
"""用 ModelSim 对 .al 里列出的 HDL 源文件做逐文件编译体检。

用法：
    python compile_check.py                  # 仓库根自动从本文件位置推断
    python compile_check.py <仓库根>          # 或显式指定
    set MODELSIM_BIN=<...>\\win32aloem        # 若 ModelSim 不在默认路径，先设这个环境变量

基线：唯一允许失败的是既有问题
    ph1p35_ddr\\ph1p35_324_ddr_wrapper.v(61) Undefined variable: 'dhi_clk'
其余必须全部 exit=0。出现别的失败 = 你的改动引入的。

★路径可移植性★（2026-10-12 改）：原版把 E:\\FPGA 与 E:\\modelsim 写死，
队友克隆到别的目录后脚本跑不了。现在仓库根从 __file__ 上溯三级推断，
ModelSim 路径按 环境变量 → 常见安装位置 → PATH 的顺序查找。
"""
import os, subprocess, glob, sys, shutil

# 本文件在 <REPO>/_analysis/scripts/ 下 ⇒ 上溯三级得到 <REPO>
_HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(sys.argv[1]) if len(sys.argv) > 1 \
       else os.path.dirname(os.path.dirname(_HERE))


def _find_ms(tool):
    """按 环境变量 MODELSIM_BIN → 常见安装位置 → PATH 的顺序找 vlog/vlib。"""
    cands = [os.environ.get("MODELSIM_BIN", ""),
             r"E:\modelsim\modelsim_ase\win32aloem",
             r"C:\modelsim\modelsim_ase\win32aloem",
             r"D:\modelsim\modelsim_ase\win32aloem",
             r"C:\intelFPGA\modelsim_ase\win32aloem"]
    for d in cands:
        if d and os.path.isfile(os.path.join(d, tool + ".exe")):
            return os.path.join(d, tool + ".exe")
    p = shutil.which(tool)
    if p:
        return p
    sys.exit("找不到 %s.exe。请设置环境变量 MODELSIM_BIN 指向 ModelSim 的 win32aloem 目录，"
             "例如：set MODELSIM_BIN=E:\\modelsim\\modelsim_ase\\win32aloem" % tool)


VLOG = _find_ms("vlog")
VLIB = _find_ms("vlib")
WORK = os.path.join(REPO, "_analysis", "hdlbase")
HDL = os.path.join(REPO, "proj", "baseline", "lab3", "user_source", "hdl_source")
FILELIST = os.path.join(REPO, "_analysis", "reports", "hdl_filelist.txt")
LOG = os.path.join(REPO, "_analysis", "reports", "compile_check.txt")

print("REPO     =", REPO)
print("VLOG     =", VLOG)
print("FILELIST =", FILELIST)
if not os.path.isfile(FILELIST):
    sys.exit("文件清单不存在：%s\n（请确认 REPO 推断是否正确，或用 python compile_check.py <仓库根> 显式指定）" % FILELIST)

def _reroot(p):
    """清单里可能写着别的机器上的绝对路径（hdl_filelist.txt 里就是 E:\\FPGA\\...）。
    原路径存在就照用；不存在就按仓库内的相对后缀重新定位到本机仓库根。"""
    if os.path.isfile(p):
        return p
    norm = p.replace("\\", "/")
    for anchor in ("/proj/", "/_analysis/", "/tools/"):
        i = norm.find(anchor)
        if i >= 0:
            cand = os.path.join(REPO, *norm[i + 1:].split("/"))
            if os.path.isfile(cand):
                return cand
    return p


_raw = [l.strip() for l in open(FILELIST, encoding="utf-8-sig")
        if l.strip().endswith((".v", ".sv")) and ".enc." not in l]
files = [_reroot(p) for p in _raw]
_rerooted = [(p, q) for p, q in zip(_raw, files) if p != q]

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
if _rerooted:
    out.append(f"路径重定位 {len(_rerooted)} 个（清单里的绝对路径在本机不存在），"
               f"例如 {_rerooted[0][0]} -> {_rerooted[0][1]}\n")

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
