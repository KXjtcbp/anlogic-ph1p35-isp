# -*- coding: utf-8 -*-
"""核对 isp_gamma.v 内联表 = 目标曲线，并用【RTL 里实际读出的表】预测四档采集图的
   上板效果（这是给用户的"预期现象"，用于回归验证）。"""
import re
import numpy as np
from PIL import Image

RTL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
P, A, B = 160, 0.50, 0.50

lut_ref = []
for x in range(256):
    y = P * ((x / P) ** A) if x <= P else P + (255 - P) * (1.0 - ((255 - x) / (255 - P)) ** B)
    lut_ref.append(int(round(y)))
lut_ref[0], lut_ref[255] = 0, 255

src = open(RTL, "r", encoding="utf-8", newline="").read()
tbl = re.search(r"    mem_b00\[  0\] = .*?mem_b00\[255\] = 8'h[0-9a-f]{2};", src, re.S).group(0)
vals = [int(v, 16) for v in re.findall(r"8'h([0-9a-f]{2})", tbl)]
names = [int(v) for v in re.findall(r"mem_b00\[\s*(\d+)\]", tbl)]
ok = True
print("[1] 表条数 = %d (应为 256)，索引连续 = %s" % (len(vals), names == list(range(256))))
ok &= (len(vals) == 256 and names == list(range(256)))
ok &= (vals == lut_ref)
print("[2] 与目标曲线逐条一致 = %s" % (vals == lut_ref))
if vals != lut_ref:
    bad = [(i, vals[i], lut_ref[i]) for i in range(256) if vals[i] != lut_ref[i]][:8]
    print("    不一致示例(i, 文件, 期望): %s" % bad)
ok &= all(vals[i] <= vals[i+1] for i in range(255))
print("[3] 单调不减 = %s，最长平台 = %d 级" %
      (all(vals[i] <= vals[i+1] for i in range(255)),
       max(sum(1 for j in range(i, 256) if vals[j] == vals[i]) for i in range(256))))
print("[4] y(0)=%d y(255)=%d  y(42)=%d(>42?) y(236)=%d(<236?)" %
      (vals[0], vals[255], vals[42], vals[236]))
ok &= (vals[0] == 0 and vals[255] == 255 and vals[42] > 42 and vals[236] < 236)
anchors = (0, 4, 8, 16, 32, 42, 64, 90, 118, 160, 200, 236, 255)
txt = "  ".join("%d->%d" % (x, vals[x]) for x in anchors)
print("[5] 头注释锚点行存在 = %s" % (txt in src))
ok &= txt in src
print("[6] 残留 log_k10 = %s ; 12 张表复制循环在 = %s" %
      ("log_k10" in src, "mem_b00[" in src and "for" in src))

# ---- 用 RTL 实际表预测四档图的上板效果 ----
lut = np.array(vals, dtype=np.uint8)
files = [(r"E:\FPGA\captures\2026-10-10_增益梯SW34\两个全关.png", "4.000x"), (r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3.png", "8.000x"),
         (r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW4.png", "15.750x"), (r"E:\FPGA\captures\2026-10-10_增益梯SW34\SW3+SW4.png", "31.500x"),
         (r"E:\FPGA\captures\2026-10-10_基线\00.png", "00.png(11.25x)")]

def load(p):
    a = np.asarray(Image.open(p).convert("RGB")).astype(np.int32)
    h, w = a.shape[:2]
    s = w / 1280.0
    m = np.ones((h, w), bool)
    for (x0, y0, x1, y1) in [(0, 0, 180, 180), (360, 110, 600, 150), (165, 165, 270, 195)]:
        m[int(y0*s):min(int(y1*s), h), int(x0*s):min(int(x1*s), w)] = False
    return a, m

def stat(b, m):
    b = b.astype(np.int32)          # ★必须转 int32：uint8 下 77R+150G+29B 会溢出
    Y = (77*b[:, :, 0] + 150*b[:, :, 1] + 29*b[:, :, 2]) >> 8
    Yv = Y[m]
    R, G, Bc = b[:, :, 0][m], b[:, :, 1][m], b[:, :, 2][m]
    return dict(mean=Yv.mean(), p50=np.percentile(Yv, 50), p90=np.percentile(Yv, 90),
                p99=np.percentile(Yv, 99), clip=(Yv >= 250).mean()*100,
                dark=(Yv <= 8).mean()*100, rg=R.mean()/max(G.mean(), 1e-9),
                bg=Bc.mean()/max(G.mean(), 1e-9), mx=int(Yv.max()))

print("\n[7] 用 RTL 表预测上板效果（SW2 拨上 = 启用曲线）")
print("%-16s %-34s %s" % ("模式", "现状(线性)", "加曲线后(预测)"))
for p, tag in files:
    a, m = load(p)
    s0 = stat(a, m)
    s1 = stat(lut[a], m)
    print("%-16s mean %5.1f p50 %3.0f p90 %3.0f clip %.3f%% dark %5.2f%% | "
          "mean %5.1f p50 %3.0f p90 %3.0f clip %.3f%% dark %5.2f%%" %
          (tag, s0["mean"], s0["p50"], s0["p90"], s0["clip"], s0["dark"],
           s1["mean"], s1["p50"], s1["p90"], s1["clip"], s1["dark"]))
print("\n%-16s %-34s %s" % ("", "R/G B/G", "R/G B/G"))
for p, tag in files:
    a, m = load(p)
    s0, s1 = stat(a, m), stat(lut[a], m)
    print("%-16s %.4f %.4f                     %.4f %.4f" % (tag, s0["rg"], s0["bg"], s1["rg"], s1["bg"]))
print("\n结论: 全部自检 %s" % ("PASS" if ok else "FAIL"))
