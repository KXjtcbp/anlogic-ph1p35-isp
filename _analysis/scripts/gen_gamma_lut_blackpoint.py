# -*- coding: utf-8 -*-
"""
模块 B（S 曲线黑位修正）生成器
==============================
问题：当前生效的 p160_a050 表是「反 S」（降对比），且 y(1)=13 / y(2)=18 / y(3)=22，
      把传感器噪声底从 0 抬成可见灰 -> A/B 实测 <=8 占比 3.082% -> 0.082%，画面发闷。

本脚本以上游真值 `_analysis/lut/gamma_lut_twoseg_p160_a050.hex` 为唯一输入，
叠加一个「黑位恢复」变换，重新生成 `isp_gamma.v` 的内联 mem_b00 表（并复制到 b01..b11）。

两种可选的变换（--mode）：
  soft   (默认) y = old - K * (1 - old/255)^2       阴影加权扣减，中间调/高光基本不动
  affine        y = (old - K) * 255 / (255 - K)     纯仿射：扣黑位 + 整体提对比，画面更暗

用法：
  python gen_gamma_lut_blackpoint.py                 # soft, K=24, 写回 isp_gamma.v
  python gen_gamma_lut_blackpoint.py --mode affine --K 18
  python gen_gamma_lut_blackpoint.py --dry-run       # 只打印，不写文件
"""
import argparse
import os
import re
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HEX_SRC = r"E:\FPGA\_analysis\lut\gamma_lut_twoseg_p160_a050.hex"
GAMMA_V = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
LUT_OUT = r"E:\FPGA\_analysis\lut"
BACKUP = r"E:\FPGA\_backup"


def load_src():
    raw = open(HEX_SRC, "r", encoding="utf-8", errors="replace").read()
    vals = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("//") or ln.startswith("#"):
            continue
        tok = ln.split()[0]
        vals.append(int(tok, 16))
    if len(vals) != 256:
        raise SystemExit("FATAL: %s has %d entries, expected 256" % (HEX_SRC, len(vals)))
    return vals


def transform(old, mode, K):
    out = []
    for x in old:
        if mode == "affine":
            v = (x - K) * 255.0 / (255.0 - K)
        else:                                    # soft
            v = x - K * (1.0 - x / 255.0) ** 2
        out.append(int(round(max(0.0, min(255.0, v)))))
    out[0] = 0
    out[255] = 255
    for i in range(1, 256):                      # 强制单调不减（LUT 必须单调）
        if out[i] < out[i - 1]:
            out[i] = out[i - 1]
    return out


def render(tbl):
    lines = []
    for i in range(0, 256, 4):
        lines.append(" ".join("mem_b00[%3d] = 8'h%02x;" % (j, tbl[j]) for j in range(i, i + 4)))
    return "\n    ".join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["soft", "affine"], default="soft")
    ap.add_argument("--K", type=int, default=24)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    old = load_src()
    new = transform(old, a.mode, a.K)

    print("source : %s" % HEX_SRC)
    print("mode   : %s   K = %d" % (a.mode, a.K))
    print()
    print("  x   old  new")
    for x in [0, 1, 2, 3, 4, 8, 13, 16, 34, 64, 96, 128, 160, 200, 255]:
        print("  %3d  %3d  %3d" % (x, old[x], new[x]))
    reach = len(set(new))
    print()
    print("  distinct output codes: %d / 256   (old table had %d)" % (reach, len(set(old))))
    print("  new[0..12] = %s" % new[0:13])
    print("  new[248..255] = %s" % new[248:256])

    txt = open(GAMMA_V, "r", encoding="utf-8").read()
    hits = list(re.finditer(r"mem_b00\[\s*\d+\]\s*=\s*8'h[0-9a-fA-F]{1,2};", txt))
    if len(hits) != 256:
        raise SystemExit("FATAL: parsed %d mem_b00 entries from isp_gamma.v, expected 256" % len(hits))
    cur = [int(m.group(0).split("'h")[1].rstrip(";"), 16) for m in hits]
    print()
    print("  isp_gamma.v currently holds the p160_a050 table: %s" % ("YES" if cur == old else "NO (!)"))
    if cur == old:
        print("  -> this edit is idempotent: source of truth is the hex, not the .v")
    else:
        print("  -> WARNING: inlined table differs from the hex source; overwriting anyway")

    if a.dry_run:
        print("\n--dry-run: nothing written.")
        return

    # ---- backup ----
    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(BACKUP, "20261011g_bp_%s%d" % (a.mode, a.K))
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(GAMMA_V, os.path.join(bdir, "isp_gamma.v.before"))
    print("\nbackup -> %s\\isp_gamma.v.before" % bdir)

    # ---- write back the inline table ----
    i0, i1 = hits[0].start(), hits[-1].end()
    txt2 = txt[:i0] + render(new) + txt[i1:]
    # 注意：文件里还有一句 mem_b01[k] <= mem_b00[k];（初始块把 b00 复制到 b01..b11），
    #       所以必须按「赋值字面量」计数，不能直接 txt.count("mem_b00[")。
    n_ent = len(re.findall(r"mem_b00\[\s*\d+\]\s*=\s*8'h[0-9a-fA-F]{1,2};", txt2))
    assert n_ent == 256, "table mangled: %d entries" % n_ent
    with open(GAMMA_V, "w", encoding="utf-8", newline="") as f:
        f.write(txt2)
    head = open(GAMMA_V, "rb").read(3)
    assert head != b"\xef\xbb\xbf", "BOM written - ModelSim would choke"
    print("wrote  -> %s  (%d B)" % (GAMMA_V, os.path.getsize(GAMMA_V)))
    print("         no BOM, %d mem_b00 assignments, %d lines" % (n_ent, txt2.count("\n") + 1))

    # ---- hex + vh side artifacts ----
    hx = os.path.join(LUT_OUT, "gamma_lut_bp_%s_k%d.hex" % (a.mode, a.K))
    with open(hx, "w", encoding="ascii", newline="\n") as f:
        for v in new:
            f.write("%02x\n" % v)
    print("wrote  -> %s" % hx)
    csvp = os.path.join(LUT_OUT, "gamma_lut_bp_%s_k%d.csv" % (a.mode, a.K))
    with open(csvp, "w", encoding="ascii", newline="\n") as f:
        f.write("in,old_p160_a050,new\n")
        for i in range(256):
            f.write("%d,%d,%d\n" % (i, old[i], new[i]))
    print("wrote  -> %s" % csvp)

    # ---- Verilog include with the expected table, for the regression TB ----
    # 用 function+case 而不是 $readmemh：TB 的工作目录里 $readmemh 的相对路径
    # 一旦找不到会静默把表读成全 0（本项目已经踩过一次），function 没有路径依赖。
    vh = os.path.join(LUT_OUT, "gamma_lut_bp_%s_k%d.vh" % (a.mode, a.K))
    with open(vh, "w", encoding="ascii", newline="\n") as f:
        f.write("// auto-generated by _analysis/scripts/gen_gamma_lut_blackpoint.py\n")
        f.write("// mode=%s K=%d   (embed with `include, no $readmemh path dependency)\n" % (a.mode, a.K))
        f.write("function [7:0] exp_lut;\n    input [7:0] x;\n    begin\n        case (x)\n")
        for i in range(256):
            f.write("        8'd%3d: exp_lut = 8'h%02x;\n" % (i, new[i]))
        f.write("        default: exp_lut = 8'h00;\n        endcase\n    end\nendfunction\n")
    print("wrote  -> %s" % vh)


if __name__ == "__main__":
    main()
