# -*- coding: utf-8 -*-
"""
LSC 增益通路修复 + 重新拟合表（最终版）。

## 修的两件事
1) **位宽溢出（真 bug）**：原 `F_mul` 返回 10bit，而 p = v*k 最大 7*255 = 1785 > 1023。
   v > 146 之后 p 回绕，`p[9:6]` 反而变小 ⇒ **亮部的校正被悄悄抹掉**。
   这就是 Y=168 的白纸靶面看不出任何校正、而 Y=83 的诊断图能看见分界的原因。
2) **k 的量化太粗**：`g = 1 + k/64`，原来 k 只能到 7（g<=1.1094），而实测靶面需要的
   增益范围是 m_max/m_min = 1.0509/0.9234 = 1.138，本来就够不着。
   现在把 `F_mul` 扩到支持 k = 0..15（g 到 1.234），同时保持 1/64 的细步长（每级 1.56%），
   这样 13.8% 的量程里有 ~9 级可用，量化误差降到 ±0.8%。

## 用法
    python fix_lsc_gain.py            # 试拟合，只打印
    python fix_lsc_gain.py --write    # 写入 lsc.v
"""
import os, re, sys, glob, shutil
import numpy as np
from PIL import Image

WS = r"E:\FPGA"
LSC = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "isp", "lsc.v")
INBOX = os.path.join(WS, "inbox")
BAK = os.path.join(WS, "_backup", "20261014_lsc_gainfix", "lsc.v.before")
K_MAX, H_NODE, V_NODE = 15, 20, 23
IMG_W, IMG_H, SCALE = 1280, 720, 1.5
SC = 64.0                       # g = 1 + k/SC

OLD_MUL = """    function [9:0] F_mul(input [7:0] v, input [3:0] k);
        reg [9:0] a, b, c;
        begin
            a = {2'b00, v};                 // v * 1
            b = {1'b0, v, 1'b0};            // v * 2
            c = {v, 2'b00};                 // v * 4
            case (k)
                4'd0: F_mul = 10'd0;
                4'd1: F_mul = a;
                4'd2: F_mul = b;
                4'd3: F_mul = a + b;
                4'd4: F_mul = c;
                4'd5: F_mul = a + c;
                4'd6: F_mul = b + c;
                default: F_mul = a + b + c;
            endcase
        end
    endfunction"""

NEW_MUL = """    function [11:0] F_mul(input [7:0] v, input [3:0] k);
        reg [11:0] a, b, c, d, r;
        begin
            // [HDR-2026-10-14] 重写：
            //  a) 位宽 10 -> 12。原写法 p = v*k 最大 7*255 = 1785 > 1023 会回绕，
            //     回绕后 p[9:6] 反而变小 => v > 146 的像素校正被抹掉（真 bug）。
            //  b) 支持 k = 0..15（原来是 case 到 7，>7 全按 7 处理），g 上限从 1.1094 提到 1.234。
            //     k 的每一级仍是 1/64 = 1.56%，量化更细。
            //  4 个移位项按 k 的 4 个位做条件相加，全是 LUT 加法器，不用乘法器/BRAM。
            a = {4'b0000, v};               // v * 1
            b = {3'b000, v, 1'b0};          // v * 2
            c = {2'b00, v, 2'b00};          // v * 4
            d = {1'b0, v, 3'b000};          // v * 8
            r = 12'd0;
            if (k[0]) r = r + a;
            if (k[1]) r = r + b;
            if (k[2]) r = r + c;
            if (k[3]) r = r + d;
            F_mul = r;
        end
    endfunction"""

OLD_APL = """    function [7:0] F_apply(input [7:0] v, input [3:0] k);
        reg [9:0] p;
        reg [8:0] s;
        begin
            p = F_mul(v, k);
            s = {1'b0, v} + {1'b0, p[9:6]};     // v + p/64"""
NEW_APL = """    function [7:0] F_apply(input [7:0] v, input [3:0] k);
        reg [11:0] p;
        reg [8:0] s;
        begin
            p = F_mul(v, k);
            s = {1'b0, v} + {1'b0, p[11:6]};    // v + p/64 => g = 1 + k/64（k 到 15）"""


def load(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    h, w, _ = a.shape
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(0,0,180,180),(360,110,600,150),(165,165,270,195)]:
        s = w/1280.0
        m[int(y0*s):int(y1*s), int(x0*s):int(x1*s)] = False
    m[220:268, 540:1020] = False
    return a, m


def main():
    write = "--write" in sys.argv
    paths = sorted(p for p in glob.glob(os.path.join(INBOX, "*.png")) if "23-29" in os.path.basename(p))
    if not paths:
        print("inbox 找不到 23-29 那批干净靶面"); return 1

    acc = np.zeros((V_NODE, H_NODE)); cnt = np.zeros((V_NODE, H_NODE))
    for p in paths:
        a, m = load(p); print("   read", os.path.basename(p))
        for j in range(V_NODE):
            y0 = int(j*IMG_H/V_NODE*SCALE); y1 = int((j+1)*IMG_H/V_NODE*SCALE)
            for i in range(H_NODE):
                x0 = int(i*IMG_W/H_NODE*SCALE); x1 = int((i+1)*IMG_W/H_NODE*SCALE)
                sm = m[y0:y1, x0:x1]
                if sm.sum() < 500: continue
                R = a[y0:y1, x0:x1, 0][sm].mean(); G = a[y0:y1, x0:x1, 1][sm].mean()
                if G < 20: continue
                acc[j, i] += R/G; cnt[j, i] += 1
    g = np.where(cnt > 0, acc/np.maximum(cnt, 1), np.nan)
    m_ref, m_min = np.nanmax(g), np.nanmin(g)
    ktot = np.nan_to_num(np.round(SC*(m_ref/g - 1.0)), nan=0.0)
    print("\nR/G grid min=%.4f max=%.4f  need gain=%.4fx  (= k %.1f)" % (m_min, m_ref, m_ref/m_min, SC*(m_ref/m_min-1)))

    kh = np.round(ktot.mean(axis=0)); kv = np.round(ktot.mean(axis=1))
    kh = np.clip(kh - kh.min(), 0, K_MAX).astype(int)
    kv = np.clip(kv - kv.min(), 0, K_MAX).astype(int)
    print("KH(20) =", kh.tolist())
    print("KV(23) =", kv.tolist())
    ks = np.clip(kh[None, :] + kv[:, None], 0, K_MAX)
    pred = g*(1.0 + ks/SC)
    r0 = np.nanmax(g)-np.nanmin(g); r1 = np.nanmax(pred)-np.nanmin(pred)
    print("k_sum max=%d (cap %d)" % (int(ks.max()), K_MAX))
    print("residual R/G range  %.4f -> %.4f   (-%.0f%%)" % (r0, r1, 100*(1-r1/r0)))
    # 只看画面中央 80% 区域（边缘本来就好，且实际镜头边缘另有暗角）
    c = pred[:, 2:18]
    print("centre-80%% column range %.4f" % (np.nanmax(c)-np.nanmin(c)))

    fh = "    function [2:0] F_kh(input [4:0] i);\n        begin\n            case (i)\n"
    for i in range(H_NODE): fh += "                5'd%-2d: F_kh = 3'd%d;\n" % (i, kh[i])
    fh += "                default: F_kh = 3'd0;\n            endcase\n        end\n    endfunction\n"
    fk = "    function [2:0] F_kv(input [4:0] i);\n        begin\n            case (i)\n"
    for j in range(V_NODE): fk += "                5'd%-2d: F_kv = 3'd%d;\n" % (j, kv[j])
    fk += "                default: F_kv = 3'd0;\n            endcase\n        end\n    endfunction\n"

    if not write:
        print("\n(dry run; add --write)"); return 0

    raw = open(LSC, "rb").read(); nl = "\r\n" if b"\r\n" in raw else "\n"
    t = raw.decode("utf-8").replace("\r\n", "\n")
    os.makedirs(os.path.dirname(BAK), exist_ok=True)
    if not os.path.exists(BAK): shutil.copy2(LSC, BAK); print("backup ->", BAK)

    n = 0
    for old, new, tag in ((OLD_MUL, NEW_MUL, "F_mul"), (OLD_APL, NEW_APL, "F_apply")):
        if old in t: t = t.replace(old, new, 1); n += 1; print("  patch", tag, "OK")
        else: print("  *patch", tag, "NO MATCH*")
    t, n1 = re.subn(r"    function \[2:0\] F_kh\(input \[4:0\] i\);.*?\n    endfunction\n", fh, t, count=1, flags=re.S)
    t, n2 = re.subn(r"    function \[2:0\] F_kv\(input \[4:0\] i\);.*?\n    endfunction\n", fk, t, count=1, flags=re.S)
    print("  table F_kh=%d F_kv=%d" % (n1, n2))
    if n != 2 or n1 != 1 or n2 != 1:
        print("*abort*"); return 1
    open(LSC, "wb").write(t.replace("\n", nl).encode("utf-8"))
    print("write ->", LSC, os.path.getsize(LSC), "B")
    for k in ("[11:0] F_mul", "p[11:6]", "k[3]) r = r + d"):
        print("  check %-20s : %s" % (k, "OK" if k in t else "MISSING"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
