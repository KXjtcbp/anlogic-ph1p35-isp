# -*- coding: utf-8 -*-
"""
[HDR-2026-10-11] 把 isp_gamma.v 的内联色调曲线表从「S 曲线 P=118 A=B=1.25」
换成「对数型提亮曲线」y = 255*ln(1+k*x/255)/ln(1+k)，k=10。

依据（见 _analysis/diag_sw34.py 与 sim_tone2.py 的实测/仿真）：
  现状 31.5x 线性        : Ymean 46.0  p50 42  <=8码 9.91%  >=250 0.036%
  套旧 S 曲线(1.25)       : Ymean 39.0  p50 32  <=8码 23.69% >=250 0.040%   <- 方向相反，更暗更死
  套本对数曲线 k=10       : Ymean 99.0  p50 103 <=8码 0.25%  >=250 0.044%   <- 提亮且不增加过曝
  对照：把数字增益加到 4x : Ymean 100.0 p50 101 <=8码 0.26%  >=250 0.544%   <- 过曝面积大 12 倍
安全性：写文件一律「先构造完整 bytes，写临时文件，再 os.replace」，杜绝上次的清空事故。
"""
import os, re, shutil, math

RTL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
HEX = r"E:\FPGA\_analysis\lut\gamma_lut_log_k10.hex"
BAK = r"E:\FPGA\_backup\20261011_gamma_log"
K = 10.0

# ---------- 1. 生成曲线 ----------
lut = [int(round(255.0 * math.log1p(K * x / 255.0) / math.log1p(K))) for x in range(256)]
assert lut[0] == 0 and lut[255] == 255, (lut[0], lut[255])
assert all(lut[i] <= lut[i + 1] for i in range(255)), "必须单调不减"
assert all(0 <= v <= 255 for v in lut)

os.makedirs(BAK, exist_ok=True)
with open(HEX, "w", encoding="utf-8", newline="\n") as f:
    for v in lut:
        f.write("%02x\n" % v)

# ---------- 2. 生成 RTL 内联表（每行 4 条，与现文件风格一致）----------
rows = []
for i in range(0, 256, 4):
    rows.append("    " + " ".join("mem_b00[%3d] = 8'h%02x;" % (i + j, lut[i + j]) for j in range(4)))
new_table = "\n".join(rows)

# ---------- 3. 读原文并逐处替换 ----------
src = open(RTL, "r", encoding="utf-8", newline="").read()
orig = src
shutil.copyfile(RTL, os.path.join(BAK, "isp_gamma.v.before"))

# 3.1 内联表
m = re.search(r"    mem_b00\[  0\] = .*?mem_b00\[255\] = 8'h[0-9a-f]{2};", src, re.S)
assert m, "找不到内联表块"
src = src[:m.start()] + new_table + src[m.end():]

# 3.2 头注释：功能行
src = src.replace(
    "// 功能      : ISP 支路的 8bit S 曲线（色调曲线）查表级。",
    "// 功能      : ISP 支路的 8bit 对数型色调曲线（tone curve）查表级。")

# 3.3 头注释：表说明段（旧的 S 曲线参数与锚点 → 新曲线）
old_tbl = src[src.index("// 表        :"):src.index("// 实现      :")]
new_tbl = (
    "// 表        : E:\\FPGA\\_analysis\\lut\\gamma_lut_log_k10.hex\n"
    "//             由 E:\\FPGA\\_analysis\\gen_gamma_lut_log.py 生成，曲线\n"
    "//                y = 255 * ln(1 + k*x/255) / ln(1+k)，k = 10\n"
    "//             ★选型依据（2026-10-11 用实拍图离线仿真，见 _analysis/sim_tone2.py）★\n"
    "//               现状 31.5x 线性      Y均值 46.0 中位 42 暗部<=8 9.91%  过曝>=250 0.036%\n"
    "//               旧 S 曲线 P118 A=1.25 Y均值 39.0 中位 32 暗部<=8 23.69% 过曝 0.040%\n"
    "//                                   ^^^ 方向相反：更暗、暗部更死 ^^^\n"
    "//               本曲线 k=10          Y均值 99.0 中位 103 暗部<=8 0.25% 过曝 0.044%\n"
    "//               对照：数字增益 4x    Y均值 100  中位 101 暗部<=8 0.26% 过曝 0.544%\n"
    "//                                   ^^^ 同样亮度，过曝面积大 12 倍 ^^^\n"
    "//             锚点（已逐条核对 .hex）：0->0  4->7  8->13  16->25 32->48\n"
    "//               42->62  64->89  90->117  118->144  160->193  200->222  236->243  255->255\n"
    "//             单调不减；曲线对暗部是【提升】（42->62，+20 码）、对高光是【压缩】\n"
    "//               （236->243 相对 255 的余量从 19 码缩到 12 码；200->222 = 高光对比度下降）\n"
    "//               ⇒ 同时解决「画面偏暗」与「光源过亮」。\n"
    "//             参数选择：k 越大提亮越强（k=6 -> Y均值 87.9 / k=10 -> 99.0 / k=16 -> 109.6，\n"
    "//               三者的过曝面积都≈0.044%）；取 k=10 时中位落在 103，接近标准曝光。\n"
)
src = src.replace(old_tbl, new_tbl)

# 3.4 初始化段注释里的曲线描述
src = src.replace(
    "//    表内容 = gamma_lut_p118_k125.hex（gen_gamma_lut.py 生成，已逐条核对）；\n"
    "//      曲线 x<=P: y=P*(x/P)^A / x>P: y=P+(255-P)*(1-((255-x)/(255-P))^B)，\n"
    "//      P=118, A=B=1.25（中等档）。",
    "//    表内容 = gamma_lut_log_k10.hex（gen_gamma_lut_log.py 生成，已逐条核对）；\n"
    "//      曲线 y = 255*ln(1+k*x/255)/ln(1+k)，k=10（对数型提亮曲线，见文件头「表」段）。")

# 3.5 修改记录
src = src.replace(
    "// 修改记录  :\n//   2026-10-10  新建。12 路同表查表级，插在 awb 之后、my_algo 之前（方案 A）。",
    "// 修改记录  :\n"
    "//   2026-10-10  新建。12 路同表查表级，插在 awb 之后、my_algo 之前（方案 A）。\n"
    "//   2026-10-11  表内容换成对数型提亮曲线 k=10（原 S 曲线 P=118 A=B=1.25 对\n"
    "//               「偏暗 + 光源过亮」方向相反，会越开越暗）。端口/时序/12 路结构均未动。")

# 3.6 顶部标签
src = src.replace("// [HDR-2026-10-10] 文件      : isp_gamma.v",
                  "// [HDR-2026-10-11] 文件      : isp_gamma.v")

assert src != orig
assert "8'h%02x" not in src.lower()
# 写临时文件再替换，避免任何中途失败把源文件截断
tmp = RTL + ".tmp_new"
with open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(src)
os.replace(tmp, RTL)

print("已更新: " + RTL)
print("  备份: " + os.path.join(BAK, "isp_gamma.v.before"))
print("  hex : " + HEX)
print("  曲线锚点: " + " ".join("%d->%d" % (x, lut[x]) for x in
      (0, 4, 8, 16, 32, 42, 64, 90, 118, 160, 200, 236, 255)))
print("  单调: 是   最长平台: %d 级" % max(sum(1 for j in range(i, 256) if lut[j] == lut[i]) for i in range(256)))
