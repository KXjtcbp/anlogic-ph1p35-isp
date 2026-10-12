# -*- coding: utf-8 -*-
"""
[HDR-2026-10-11b] 把 isp_gamma.v 的内联色调曲线表从「对数型提亮曲线 k=10」
换回本工程既有的「两段幂函数」族，参数 P=160, A=B=0.50（=反 S / 提暗部 + 压高光）。

为什么换掉对数曲线 k=10：
  对数曲线 y=255*ln(1+10x/255)/ln(11) 把 x=236 抬到 248 —— 也就是把光源本身
  【抬得更亮】，与用户诉求「光源过亮」方向相反；它只是靠把中位从 42 提到 103
  让光源"相对不那么突出"。用户诉求是两条：偏暗 + 光源过亮。
  两段幂函数族（P 为拐点，A 为低段幂、B=1-A 的高段幂）可以在【提亮暗部】的同时
  把高光【压到原始值以下】：
      P=160 A=0.50 ： 42->82（+40 码） 236->213（比原来还低 23 码） 255->255
  实拍 31.5x 图上的离线仿真（_analysis/sim_tone3.py）：
      现状线性            Y均值 46.0  中位 42  <=8码 9.91%  >=250 0.036%
      本曲线 P160 A0.50   Y均值 79.8  中位 82  <=8码 0.19%  >=250 0.024%
      （过曝面积 -33%，且 y(236) 213<236 ⇒ 光源本身变暗，而不是"相对不亮"）
安全性：写文件一律「先构造完整 bytes，写临时文件，再 os.replace」。
"""
import os, re, shutil

RTL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
HEX = r"E:\FPGA\_analysis\lut\gamma_lut_twoseg_p160_a050.hex"
BAK = r"E:\FPGA\_backup\20261011_gamma_twoseg"
P = 160
A = 0.50
B = 1.0 - A
ANCHORS = (0, 4, 8, 16, 32, 42, 64, 90, 118, 160, 200, 236, 255)

# ---------- 1. 生成曲线（两段幂函数，与 gen_gamma_lut.py 的族一致）----------
lut = []
for x in range(256):
    if x <= P:
        y = P * ((x / P) ** A)
    else:
        y = P + (255 - P) * (1.0 - ((255 - x) / (255 - P)) ** B)
    lut.append(int(round(y)))
lut[0], lut[255] = 0, 255
assert all(0 <= v <= 255 for v in lut)
assert all(lut[i] <= lut[i + 1] for i in range(255)), "必须单调不减"
# 关键性质断言（写进注释里的数字全部由这里算出来，杜绝手写注释与表不一致）
assert lut[42] > 42 and lut[236] < 236, "必须同时提暗部、压高光"
plateau = max(sum(1 for j in range(i, 256) if lut[j] == lut[i]) for i in range(256))
anchor_txt = "  ".join("%d->%d" % (x, lut[x]) for x in ANCHORS)

os.makedirs(BAK, exist_ok=True)
with open(HEX, "w", encoding="utf-8", newline="\n") as f:
    for v in lut:
        f.write("%02x\n" % v)

# ---------- 2. 内联表（每行 4 条，与现文件风格一致）----------
rows = ["    " + " ".join("mem_b00[%3d] = 8'h%02x;" % (i + j, lut[i + j]) for j in range(4))
        for i in range(0, 256, 4)]
new_table = "\n".join(rows)

# ---------- 3. 头注释「表」段（全部由 lut 自动生成）----------
new_tbl = (
    "// 表        : E:\\FPGA\\_analysis\\lut\\gamma_lut_twoseg_p160_a050.hex\n"
    "//             由 E:\\FPGA\\_analysis\\gen_gamma_lut_twoseg.py 生成，曲线为两段幂函数\n"
    "//               x <= P : y = P*(x/P)^A\n"
    "//               x >  P : y = P + (255-P)*(1 - ((255-x)/(255-P))^B)\n"
    "//               参数 P=%d, A=%.2f, B=%.2f（反 S：提暗部 + 压高光）\n" % (P, A, B) +
    "//             ★选型依据（2026-10-11 用实拍 31.5x 图离线仿真，见 _analysis/sim_tone3.py）★\n"
    "//               现状 31.5x 线性      Y均值 46.0 中位 42  暗部<=8 9.91%%  过曝>=250 0.036%%\n"
    "//               旧 S 曲线 P118 A=1.25 Y均值 39.0 中位 32  暗部<=8 23.69%% 过曝 0.040%%\n"
    "//                                   ^^^ 方向相反：越开越暗、暗部更死 ^^^\n"
    "//               对数曲线 k=10        Y均值 99.0 中位 103 暗部<=8 0.25%%  过曝 0.044%%\n"
    "//                                   ^^^ 提亮够，但 y(236)=248 把光源抬得更亮 ^^^\n"
    "//               本曲线 P=%d A=%.2f   Y均值 79.8 中位 82  暗部<=8 0.19%%  过曝>=250 0.024%%\n" % (P, A) +
    "//                                   ⇒ 暗部提亮 + 光源本身变暗，两条诉求同向解决\n"
    "//             ★锚点（本段数字由生成脚本按表自动打印，已逐条核对）★\n"
    "//               " + anchor_txt + "\n"
    "//             性质：单调不减；最长平台 %d 级；暗部提升（42->%d，+%d 码）；\n" % (plateau, lut[42], lut[42] - 42) +
    "//               高光压缩（236->%d，比原始低 %d 码；200->%d），y(0)=0 保留真黑，y(255)=255 保留白。\n" % (lut[236], 236 - lut[236], lut[200]) +
    "//             ★灰雾风险控制★ 低端斜率 y(4)/4 = %.2f（对数值 k=10 为 4.17），\n" % (lut[4] / 4.0) +
    "//               实测该场景 x<=8 的像素占 9.91%%，提亮后落到 <=%d 码 ⇒ 不会出现大片灰雾。\n" % lut[8]
)

# ---------- 4. 读原文并逐处替换 ----------
src = open(RTL, "r", encoding="utf-8", newline="").read()
orig = src
shutil.copyfile(RTL, os.path.join(BAK, "isp_gamma.v.before"))

def rep(old, new, name):
    global src
    assert old in src, "找不到待替换文本: " + name
    src = src.replace(old, new, 1)

# 4.1 内联表
m = re.search(r"    mem_b00\[  0\] = .*?mem_b00\[255\] = 8'h[0-9a-f]{2};", src, re.S)
assert m, "找不到内联表块"
src = src[:m.start()] + new_table + src[m.end():]

# 4.2 文件头「表」段（按标记切片，内容整体重写）
i0 = src.index("// 表        :")
i1 = src.index("// 实现      :")
src = src[:i0] + new_tbl + src[i1:]
assert "gamma_lut_log_k10" not in src.split("// 实现")[0]

# 4.3 功能行
rep("// 功能      : ISP 支路的 8bit 对数型色调曲线（tone curve）查表级。",
    "// 功能      : ISP 支路的 8bit 色调曲线（tone curve, 两段幂函数）查表级。", "功能行")

# 4.4 初始化段注释
rep("//    表内容 = gamma_lut_log_k10.hex（gen_gamma_lut_log.py 生成，已逐条核对）；\n"
    "//      曲线 y = 255*ln(1+k*x/255)/ln(1+k)，k=10（对数型提亮曲线，见文件头「表」段）。",
    "//    表内容 = gamma_lut_twoseg_p160_a050.hex（gen_gamma_lut_twoseg.py 生成，已逐条核对）；\n"
    "//      曲线 x<=P: y=P*(x/P)^A / x>P: y=P+(255-P)*(1-((255-x)/(255-P))^B)，\n"
    "//      P=%d, A=%.2f, B=%.2f（反 S：提暗部 + 压高光，见文件头「表」段）。" % (P, A, B), "初始化段注释")

# 4.5 端口注释
rep("input               I_gamma_bypass  ,   // 1 = 直通（表不生效）；0 = 启用 S 曲线",
    "input               I_gamma_bypass  ,   // 1 = 直通（表不生效）；0 = 启用色调曲线", "端口注释")

# 4.6 修改记录（追加一行）
rep("//   2026-10-11  表内容换成对数型提亮曲线 k=10（原 S 曲线 P=118 A=B=1.25 对\n"
    "//               「偏暗 + 光源过亮」方向相反，会越开越暗）。端口/时序/12 路结构均未动。",
    "//   2026-10-11  表内容换成对数型提亮曲线 k=10（原 S 曲线 P=118 A=B=1.25 对\n"
    "//               「偏暗 + 光源过亮」方向相反，会越开越暗）。端口/时序/12 路结构均未动。\n"
    "//   2026-10-11b 表内容换成两段幂函数曲线 P=%d A=B=%.2f：对数曲线把 y(236) 抬到 248，\n" % (P, A) +
    "//               与「光源过亮」相反；本曲线 42->%d 且 236->%d（低于原始），两条诉求同向。\n" % (lut[42], lut[236]) +
    "//               端口/时序/12 路结构/旁路行为均未动。", "修改记录")

# 4.7 顶部标签
rep("// [HDR-2026-10-11] 文件      : isp_gamma.v",
    "// [HDR-2026-10-11b] 文件      : isp_gamma.v", "顶部标签")

assert src != orig
assert "log_k10" not in src, "还有残留的 log_k10 字样"
tmp = RTL + ".tmp_new"
with open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(src)
os.replace(tmp, RTL)

print("已更新: " + RTL)
print("  备份: " + os.path.join(BAK, "isp_gamma.v.before"))
print("  hex : " + HEX)
print("  曲线: P=%d A=%.2f B=%.2f" % (P, A, B))
print("  锚点: " + anchor_txt)
print("  最长平台: %d 级   低端斜率 y(4)/4 = %.2f" % (plateau, lut[4] / 4.0))
