# -*- coding: utf-8 -*-
"""fit_lsc_2d.py —— LSC 完整二维表拟合（20 x 12 网格，R/B 各自一张 4bit 表）

与 fit_lsc.py（可分离 1D 版）的区别：
  旧: k(x,y) = KH[x] + KV[y]          -> 43 个 3bit 常数，但只能吃掉 20% 的碗
  新: k(x,y) = TABLE2D[y][x]          -> 240 个 8bit 常数（kR[7:4] | kB[3:0]）

物理模型
  R/G 在均匀靶面上随位置变化 = 镜头的色彩暗角。
  要把它拉平，就让同一位置乘上  g = 1 + k/64：
      (R/G) * g = target        =>   k = round( 64 * (target/(R/G) - 1) )
  target 取所有节点里最大的 R/G（= 最中性的边缘），k 夹到 0..15。

网格
  水平：1280 像素 / 4 = 320 beat，取 S_bx[8:4] -> 20 节点，每节点 64 像素
  垂直：720 行，取 S_y[11:6]                 -> 12 节点，每节点 64 行
  地址 = { S_y[11:6] (4bit), S_bx[8:4] (5bit) } = 9bit

用法
  python fit_lsc_2d.py            # 拟合 + 回写 lsc.v
  python fit_lsc_2d.py --dry-run  # 只打印，不写文件
"""
import os
import re
import sys
import glob
import argparse

import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LSC_V = os.path.join(REPO, "proj", "baseline", "lab3", "user_source",
                     "hdl_source", "isp", "lsc.v")

# ---- 干净靶面：白纸铺满 + 台灯直照，无 LSC 的那一批 -------------------------
DEFAULT_SRCS = [
    os.path.join(REPO, "captures", "2026-10-13_白纸靶面_无LSC对照", "N1_232908.png"),
    os.path.join(REPO, "captures", "2026-10-13_白纸靶面_无LSC对照", "N2_232918.png"),
    os.path.join(REPO, "captures", "2026-10-13_白纸靶面_无LSC对照", "N3_232923.png"),
]

# 遮掉的区域（1920x1080 采集图坐标）：logo / CNT 黄字 / 橙色遥测两行 / MODE 绿字
MASK_BOXES = [
    (0, 0, 400, 320),        # 安路 logo
    (500, 150, 1620, 290),   # CNT + 两行橙色遥测（都在这一带）
    (240, 380, 620, 440),    # MODE 绿字（1280 空间 y=264..278 -> 1920 空间 y=396..417）
]

NX, NY = 20, 12          # 横向 20 节点、纵向 12 节点
KQ_MAX = 1023            # g = 1 + kq/1024，kq 取 0..1023；实测色碗最深 ~12%，只用到 ~128
KQ_BITS = 10             # ★2026-10-14 从 4bit(1/64) 提到 10bit(1/1024)★
G_MIN = 40               # 只统计足够亮的像素，避免噪声主导比值
IMG_W, IMG_H = 1920, 1080

BEGIN = "// ==== LSC_TABLE_BEGIN ===="
END = "// ==== LSC_TABLE_END ===="


def load_ratio(paths):
    """返回 (2D rhoR, 2D rhoB, 2D valid) 的累加器（按像素原始分辨率）。"""
    acc_r = np.zeros((IMG_H, IMG_W), np.float64)
    acc_b = np.zeros((IMG_H, IMG_W), np.float64)
    cnt = np.zeros((IMG_H, IMG_W), np.float64)
    valid = np.ones((IMG_H, IMG_W), bool)
    for x0, y0, x1, y1 in MASK_BOXES:
        valid[y0:y1, x0:x1] = False
    for p in paths:
        if not os.path.isfile(p):
            print("  [跳过] 找不到 %s" % p)
            continue
        a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
        if a.shape[:2] != (IMG_H, IMG_W):
            print("  [跳过] %s 尺寸不是 %dx%d" % (os.path.basename(p), IMG_W, IMG_H))
            continue
        R, G, B = a[..., 0], a[..., 1], a[..., 2]
        ok = valid & (G > G_MIN)
        acc_r[ok] += R[ok] / G[ok]
        acc_b[ok] += B[ok] / G[ok]
        cnt[ok] += 1.0
        print("  [读入] %s  有效像素 %d" % (os.path.basename(p), int(ok.sum())))
    ok = cnt > 0
    rho_r = np.where(ok, acc_r / np.maximum(cnt, 1), np.nan)
    rho_b = np.where(ok, acc_b / np.maximum(cnt, 1), np.nan)
    return rho_r, rho_b, ok


def bin_median(rho, ok):
    """把整幅 rho 按 20x12 节点取中位数。返回 (NY, NX) 数组。"""
    out = np.full((NY, NX), np.nan)
    xs = [i * IMG_W // NX for i in range(NX + 1)]
    ys = [j * IMG_H // NY for j in range(NY + 1)]
    for j in range(NY):
        for i in range(NX):
            blk = rho[ys[j]:ys[j + 1], xs[i]:xs[i + 1]]
            m = ok[ys[j]:ys[j + 1], xs[i]:xs[i + 1]]
            v = blk[m]
            if v.size >= 200:
                out[j, i] = np.median(v)
    # 极少数节点样本不足时用邻居补
    for j in range(NY):
        for i in range(NX):
            if np.isnan(out[j, i]):
                js = [max(0, j - 1), min(NY - 1, j + 1)]
                iis = [max(0, i - 1), min(NX - 1, i + 1)]
                nb = [out[a, b] for a in js for b in iis if not np.isnan(out[a, b])]
                if nb:
                    out[j, i] = float(np.mean(nb))
    return out


def to_k(rho):
    """rho(=R/G 或 B/G) -> kq = round(1024*(target/rho - 1))，夹 0..KQ_MAX。

    ★为什么把量化从 1/64 改成 1/1024★
      1/64 = 1.5625% 的系数台阶会在均匀靶面上画出肉眼可见的方块（2026-10-14
      首验 L2 实测块边界跳变 2.2%~5.3%）。1/1024 = 0.098%，比人眼在平滑面上
      的辨别阈值低一个量级，不需要再做双线性插值。
    """
    target = np.nanmax(rho)
    g_need = target / rho
    k = np.round(1024.0 * (g_need - 1.0))
    k = np.clip(np.nan_to_num(k, nan=0.0), 0, KQ_MAX).astype(int)
    return k, target


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--src", nargs="*", default=None)
    args = ap.parse_args()

    paths = args.src if args.src else DEFAULT_SRCS
    print("=== 输入靶面 ===")
    rho_r, rho_b, ok = load_ratio(paths)
    print("  有效像素合计 %d" % int(ok.sum()))
    if ok.sum() < 100000:
        print("!! 有效像素太少，停止")
        return 1

    R2 = bin_median(rho_r, ok)
    B2 = bin_median(rho_b, ok)
    kR, tR = to_k(R2)
    kB, tB = to_k(B2)

    prof_r = np.nanmean(R2, axis=0)   # 每个 x 节点的 R/G
    prof_b = np.nanmean(B2, axis=0)
    print("\n=== 逐 x 节点 R/G 均值（旧，未校正）===")
    print("  " + " ".join("%.4f" % v for v in prof_r))
    print("=== 逐 x 节点 B/G 均值（旧，未校正）===")
    print("  " + " ".join("%.4f" % v for v in prof_b))
    print("\n  R: target(max R/G)=%.4f  极差=%.4f" % (tR, np.nanmax(prof_r) - np.nanmin(prof_r)))
    print("  B: target(max B/G)=%.4f  极差=%.4f" % (tB, np.nanmax(prof_b) - np.nanmin(prof_b)))

    print("\n=== 拟合出的 kR（行=y 节点 0..%d，列=x 节点 0..%d）===" % (NY - 1, NX - 1))
    for j in range(NY):
        print("  y%02d  " % j + " ".join("%2d" % kR[j, i] for i in range(NX)))
    print("=== 拟合出的 kB ===")
    for j in range(NY):
        print("  y%02d  " % j + " ".join("%2d" % kB[j, i] for i in range(NX)))

    # 预测校正后的效果（节点级）
    corr_r = R2 * (1.0 + kR / 1024.0)
    corr_b = B2 * (1.0 + kB / 1024.0)
    pr = np.nanmean(corr_r, axis=0)
    pb = np.nanmean(corr_b, axis=0)
    print("\n=== 预测校正后逐 x 节点 R/G 均值 ===")
    print("  " + " ".join("%.4f" % v for v in pr))
    print("  极差 %.4f -> %.4f" % (np.nanmax(prof_r) - np.nanmin(prof_r),
                                   np.nanmax(pr) - np.nanmin(pr)))
    print("=== 预测校正后逐 x 节点 B/G 均值 ===")
    print("  " + " ".join("%.4f" % v for v in pb))
    print("  极差 %.4f -> %.4f" % (np.nanmax(prof_b) - np.nanmin(prof_b),
                                   np.nanmax(pb) - np.nanmin(pb)))

    # ---- 生成 Verilog ----
    lines = []
    lines.append(BEGIN)
    lines.append("    // 由 fit_lsc_2d.py 自动生成，请勿手改；改表请重跑脚本")
    lines.append("    // 输入：%s" % ", ".join(os.path.basename(p) for p in paths if os.path.isfile(p)))
    lines.append("    // 网格：水平 %d 节点（S_bx[8:4]，每节点 64 像素）；垂直 %d 节点（S_y[11:6]，每节点 64 行）" % (NX, NY))
    lines.append("    // 返回 {kR[9:0], kB[9:0]}，g = 1 + kq/1024，kq=0 -> 1.0000x，kq=%d -> %.4fx" % (KQ_MAX, 1.0 + KQ_MAX / 1024.0))
    lines.append("    // 实测：未校正逐列 R/G 极差 %.4f / B/G 极差 %.4f；节点级预测校正后 %.4f / %.4f"
                 % (np.nanmax(prof_r) - np.nanmin(prof_r), np.nanmax(prof_b) - np.nanmin(prof_b),
                    np.nanmax(pr) - np.nanmin(pr), np.nanmax(pb) - np.nanmin(pb)))
    lines.append("    // ★系数分辨率 1/1024 = 0.098%%，单节点台阶远低于人眼阈值，无须插值★")
    lines.append("    function [19:0] F_k2d(input [3:0] iy, input [4:0] ix);")
    lines.append("        reg [8:0] a;")
    lines.append("        begin")
    lines.append("            a = {iy, ix};")
    lines.append("            case (a)")
    for j in range(NY):
        for i in range(NX):
            val = (int(kR[j, i]) << 10) | int(kB[j, i])
            lines.append("                9'd%d : F_k2d = 20'h%05x;   // y=%02d x=%02d  kR=%4d kB=%4d"
                         % (j * 32 + i, val, j, i, kR[j, i], kB[j, i]))
    lines.append("                default: F_k2d = 20'h00000;")
    lines.append("            endcase")
    lines.append("        end")
    lines.append("    endfunction")
    lines.append(END)
    new_block = "\n".join(lines)

    if args.dry_run:
        print("\n=== dry-run：不写文件。新表区共 %d 行 ===" % len(lines))
        return 0

    raw = open(LSC_V, "rb").read()
    txt = raw.decode("utf-8", errors="replace")
    crlf = "\r\n" in txt
    text = txt.replace("\r\n", "\n")
    b = text.find(BEGIN)
    e = text.find(END)
    if b < 0 or e < 0:
        print("!! 在 lsc.v 里找不到表区标记")
        return 1
    e += len(END)
    out = text[:b] + new_block + text[e:]
    open(LSC_V, "wb").write(out.replace("\n", "\r\n").encode("utf-8") if crlf
                            else out.encode("utf-8"))
    print("\n=== 已回写 %s ===" % LSC_V)
    print("  表区 %d 行 -> %d 行，文件 %d B -> %d B，CRLF=%s"
          % (text[b:e].count("\n") + 1, len(lines),
             len(raw), os.path.getsize(LSC_V), crlf))
    return 0


if __name__ == "__main__":
    sys.exit(main())
