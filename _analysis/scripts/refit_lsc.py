# -*- coding: utf-8 -*-
"""
从干净的白纸靶面测量里重新拟合 LSC 表，并按 lsc.v 的真实坐标口径（20 x 23 节点）生成。

为什么重做：
  1) 旧表注释自称「D = 1-R/G = +0.0164 + 0.0000*u^2 + 0.0000*v^2」——两个二次项系数
     都圆整成 0.0000，说明最小二乘是退化的，等于只拟合出一个常数，形状没进表。
  2) 旧表按「垂直 24 节点 / 每节点 30 行」生成，但 lsc.v 的查表是 S_vidx = S_y[11:5]，
     即每节点 32 行（y/32），只能取到 0..22 ⇒ 表与查表口径不一致，垂直方向整体错位。

本脚本：
  * 输入：inbox 里的三张均匀白纸靶面（未校正的干净数据）
  * 网格：水平 20 节点 x 每节点 1280/20 = 64 像素；垂直 23 节点 x 每节点 720/23 ≈ 31.3 行
          （垂直改用 23 节点，直接对齐 S_y[11:5] 的 y/32 口径）
  * 每格算 R/G，取全网格的 R/G 最大值 m_ref 为「最不绿」的参考点
  * k_total(x,y) = round(64 * (m_ref / m(x,y) - 1))   —— 把最绿的地方抬起来
  * 分离：KH(x) = round(mean_y k_total) - min_x(...)
          KV(y) = round(mean_x k_total) - min_y(...)
          （两者各自非负、各自在某处为 0；常数部分由下游 AWB 全局归一化吃掉）
  * 生成 k = KH + KV 饱和到 K_MAX 的 F_kh / F_kv

用法：python refit_lsc.py [--write]
"""
import os, re, sys, glob, shutil
import numpy as np
from PIL import Image

WS = r"E:\FPGA"
LSC = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "isp", "lsc.v")
INBOX = os.path.join(WS, "inbox")
K_MAX = 7
H_NODE = 20          # 水平节点数
V_NODE = 23          # 垂直节点数（对齐 S_y[11:5]）
IMG_W, IMG_H = 1280, 720   # 内部坐标
SCALE = 1920.0 / 1280.0    # 采集图是 1920x1080


def load(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.float64)
    h, w, _ = a.shape
    m = np.ones((h, w), bool)
    for x0, y0, x1, y1 in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        s = w / 1280.0
        m[int(y0 * s):int(y1 * s), int(x0 * s):int(x1 * s)] = False
    m[220:268, 540:1020] = False          # 两行橙色遥测
    return a, m


def grid_ratio(paths):
    """返回 (V_NODE, H_NODE) 的 R/G 网格（多图平均）"""
    acc = np.zeros((V_NODE, H_NODE))
    cnt = np.zeros((V_NODE, H_NODE))
    for p in paths:
        a, m = load(p)
        H, W, _ = a.shape
        for j in range(V_NODE):
            y0 = int(j * IMG_H / V_NODE * SCALE); y1 = int((j + 1) * IMG_H / V_NODE * SCALE)
            for i in range(H_NODE):
                x0 = int(i * IMG_W / H_NODE * SCALE); x1 = int((i + 1) * IMG_W / H_NODE * SCALE)
                sub = a[y0:y1, x0:x1]
                sm = m[y0:y1, x0:x1]
                if sm.sum() < 500:
                    continue
                R = sub[..., 0][sm].mean(); G = sub[..., 1][sm].mean()
                if G < 20:
                    continue
                acc[j, i] += R / G; cnt[j, i] += 1
        print("   已读", os.path.basename(p))
    return np.where(cnt > 0, acc / np.maximum(cnt, 1), np.nan)


def main():
    write = "--write" in sys.argv
    cands = [p for p in glob.glob(os.path.join(INBOX, "*.png"))]
    # 只取文件名含 23-29 的那三张（干净未校正靶面）
    paths = sorted([p for p in cands if "23-29" in os.path.basename(p)])
    if len(paths) < 1:
        print("inbox 里找不到 23-29 那批靶面图"); return 1
    print("输入 %d 张：" % len(paths))
    g = grid_ratio(paths)

    m_ref = np.nanmax(g)
    print("\nR/G 网格：min=%.4f  max=%.4f" % (np.nanmin(g), m_ref))
    ktot = np.round(64.0 * (m_ref / g - 1.0))
    ktot = np.nan_to_num(ktot, nan=0.0)

    kh = ktot.mean(axis=0)                # 每个水平节点的纵向平均
    kv = ktot.mean(axis=1)                # 每个垂直节点的横向平均
    kh = np.round(kh - kh.min())
    kv = np.round(kv - kv.min())
    kh = np.clip(kh, 0, K_MAX).astype(int)
    kv = np.clip(kv, 0, K_MAX).astype(int)

    print("\nKH(20) =", kh.tolist())
    print("KV(23) =", kv.tolist())
    print("k_max  = %d（饱和上限 %d）" % (int(np.max(kh[:, None] + kv[None, :])), K_MAX))

    # 预测校正后的 R/G 网格（k 相加后 g = 1 + k/64）
    ksum = np.clip(kh[None, :] + kv[:, None], 0, K_MAX)
    pred = g * (1.0 + ksum / 64.0)
    print("校正后 R/G 预测：min=%.4f max=%.4f 极差=%.4f （校正前极差 %.4f）"
          % (np.nanmin(pred), np.nanmax(pred), np.nanmax(pred) - np.nanmin(pred),
             np.nanmax(g) - np.nanmin(g)))

    fh = "    function [2:0] F_kh(input [4:0] i);\n        begin\n            case (i)\n"
    for i in range(H_NODE):
        fh += "                5'd%-2d: F_kh = 3'd%d;\n" % (i, kh[i])
    fh += "                default: F_kh = 3'd0;\n            endcase\n        end\n    endfunction\n"

    fk = "    function [2:0] F_kv(input [4:0] i);\n        begin\n            case (i)\n"
    for j in range(V_NODE):
        fk += "                5'd%-2d: F_kv = 3'd%d;\n" % (j, kv[j])
    fk += "                default: F_kv = 3'd0;\n            endcase\n        end\n    endfunction\n"

    if not write:
        print("\n（未写盘；加 --write 才写入 lsc.v）")
        return 0

    raw = open(LSC, "rb").read()
    txt = raw.decode("utf-8"); nl = "\r\n" if b"\r\n" in raw else "\n"
    t = txt.replace("\r\n", "\n")
    bak = os.path.join(WS, "_backup", "20261014_lsc_refit", "lsc.v.before")
    os.makedirs(os.path.dirname(bak), exist_ok=True)
    if not os.path.exists(bak):
        shutil.copy2(LSC, bak); print("备份 ->", bak)

    t2, n1 = re.subn(r"    function \[2:0\] F_kh\(input \[4:0\] i\);.*?\n    endfunction\n",
                     fh, t, count=1, flags=re.S)
    t3, n2 = re.subn(r"    function \[2:0\] F_kv\(input \[4:0\] i\);.*?\n    endfunction\n",
                     fk, t2, count=1, flags=re.S)
    print("替换 F_kh=%d F_kv=%d（都应为 1）" % (n1, n2))
    if n1 != 1 or n2 != 1:
        print("★命中数不对，放弃★"); return 1
    open(LSC, "wb").write(t3.replace("\n", nl).encode("utf-8"))
    print("写入 ->", LSC, os.path.getsize(LSC), "B")
    return 0


if __name__ == "__main__":
    sys.exit(main())
