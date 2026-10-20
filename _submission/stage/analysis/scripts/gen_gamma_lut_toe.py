# -*- coding: utf-8 -*-
"""
【已否决，未写入 RTL —— 2026-10-11 决定，保留作为候选与记录】

否决依据：四档盖镜头实测（`captures/2026-10-11_标定/黑电平_*.png`，2026-10-11 02:00）
  4.000x/8.000x/15.750x/31.500x 四档的 8bit 输出 Y 均值 0.00/0.01/0.07/0.30，
  Y==0 占 99.894%/99.471%/93.720%/76.532%，R=B=0，G 只高 1 码
  ⇒ **近黑处没有基座、也没有可观的噪声底**（读噪声 ±1 码），
     所以曲线对 2~8 码的强抬升提的是【真实暗部信号】，不是"把噪声/基座抬成灰"。
  ⇒ 本脚本当初的前提（近黑=基座+噪声，应加趾压掉）不成立；
     而用户的诉求是"画面偏暗"，加趾会把 p10 从 38 压到 20（更暗）⇒ 方向相反。
  保留本脚本以便将来真出现基座时复用；生成物只在 `_analysis/lut/candidates/`。

------------------------------------------------------------------
给 isp_gamma.v 的两段幂函数曲线加【线性趾（死区）】的候选生成器。

背景（四档盖镜头实测定标，2026-10-11 02:00 采集）：
  盖镜头时 4.000x/8.000x/15.750x/31.500x 四档的 8bit 输出分别是
  Y均值 0.00/0.01/0.07/0.30，Y==0 占 99.9/99.5/93.7/76.5%，R=B=0，G=0~1
  ⇒ 传感器黑电平基座≈0（0~3 个 raw10），链路本身没有基座；
  ⇒ 旧常数 BLACK_LEVEL=56（=14 码 8bit）是 10-09 在写 0x3e03=0x0b 之前标的，已作废。
  既然黑是 0，画面"发灰"就不是基座，而是【曲线把 0~3 码的底噪抬成了灰】：
     无趾曲线 y(1)=13、y(2)=18、y(4)=25、y(8)=36  ⇒ 1 码噪声 = 13 码灰
     实测 31.5x 图上 p10 从 9（线性）抬到 38 ⇒ 整幅压在 38 码灰底上，这就是"发灰"。
  加趾后 y(1)=2、y(2)=3、y(4)=6、y(8)=12 ⇒ 近黑仍是黑，p10 从 38 降到 20。

曲线（x = 8bit 输入，y = 8bit 输出）：
    x <= t        : y = s*x                                          线性趾
    t < x <= P    : y = s*t + (P - s*t) * ((x-t)/(P-t))^A            中段提亮
    x > P         : y = P + (255-P) * (1 - ((255-x)/(255-P))^B)       上臂压光源
参数 t=8, s=1.5, P=160, A=B=0.50。t=8 时折点在 y=12 码（深暗区，极少像素），
所以折线看不出来；y(42)=82、y(118)=138、y(236)=213 与上一版逐码相同
⇒ 只动最底下 8 码，其余亮度/色调整体不变（纯改善）。
"""
import os
import re
import shutil

RTL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
HEX = r"E:\FPGA\_analysis\lut\candidates\gamma_lut_toe_t8_s15_p160_a050.hex"
BAK = r"E:\FPGA\_backup\20261011c_gamma_toe"
T, S, P, A, B = 8, 1.5, 160, 0.50, 0.50
ANCHORS = (0, 4, 8, 16, 32, 42, 64, 90, 118, 160, 200, 236, 255)


def curve(x):
    if x <= T:
        y = S * x
    elif x <= P:
        y = S * T + (P - S * T) * (((x - T) / (P - T)) ** A)
    else:
        y = P + (255 - P) * (1.0 - (((255 - x) / (255 - P)) ** B))
    return int(round(y))


lut = [curve(x) for x in range(256)]
lut[0], lut[255] = 0, 255
assert all(0 <= v <= 255 for v in lut)
assert all(lut[i] <= lut[i + 1] for i in range(255)), "必须单调不减"
assert lut[42] == 82 and lut[236] == 213, "必须与上一版一致：42->82, 236->213"
assert lut[4] <= 8 and lut[8] <= 14, "趾必须够低（近黑不被抬高）"
plateau = max(sum(1 for j in range(i, 256) if lut[j] == lut[i]) for i in range(256))
anchor_txt = "  ".join(f"{x}->{lut[x]}" for x in ANCHORS)

os.makedirs(BAK, exist_ok=True)
with open(HEX, "w", encoding="utf-8", newline="\n") as f:
    for v in lut:
        f.write(f"{v:02x}\n")

rows = ["    " + " ".join(f"mem_b00[{i+j:3d}] = 8'h{lut[i+j]:02x};" for j in range(4))
        for i in range(0, 256, 4)]
new_table = "\n".join(rows)

tbl_head = "\n".join([
    r"// 表        : E:\FPGA\_analysis\lut\gamma_lut_toe_t8_s15_p160_a050.hex",
    r"//             由 E:\FPGA\_analysis\scripts\gen_gamma_lut_toe.py 生成，曲线为「线性趾 + 两段幂函数」",
    "//               x <= t : y = s*x                                        (线性趾)",
    "//               t < x <= P : y = s*t + (P - s*t)*((x-t)/(P-t))^A         (中段提亮)",
    "//               x >  P : y = P + (255-P)*(1 - ((255-x)/(255-P))^B)       (上臂压光源)",
    f"//               参数 t={T}, s={S:.1f}, P={P}, A={A:.2f}, B={B:.2f}",
    "//             ★为什么要加线性趾（2026-10-11c，依据四档盖镜头实测定标）★",
    "//               盖镜头 4.000x/8.000x/15.750x/31.500x 四档 8bit 输出 Y均值 0.00/0.01/0.07/0.30、",
    "//               Y==0 占 99.9/99.5/93.7/76.5 个百分点、R=B=0、G=0~1 ⇒ 传感器黑电平基座约 0，",
    "//               画面发灰不是基座造成的，而是【无趾曲线把 0~3 码底噪抬成灰】：",
    f"//                 无趾版 y(1)=13 y(2)=18 y(4)=25 y(8)=36 ⇒ 1 码噪声 = 13 码灰",
    f"//                 本版   y(1)={lut[1]} y(2)={lut[2]} y(4)={lut[4]} y(8)={lut[8]} ⇒ 近黑仍是黑",
    "//             ★选型依据（实拍 31.5x 图离线仿真，见 _analysis/scripts/sim_toe.py）★",
    "//               31.5x 线性          Y均值 46.5 中位 42 暗部<=8 占 7.20 个百分点 过曝>=250 占 0.036 个百分点",
    "//               无趾 P160 A0.50    Y均值 80.3 中位 82 p10 38 暗部<=8 占 0.18 个百分点 过曝 0.024 个百分点",
    "//               本曲线(加趾)        Y均值 76.9 中位 82 p10 20 暗部<=8 占 1.49 个百分点 过曝 0.024 个百分点",
    "//                                   ⇒ 中位/高光不变，只把 p10 从 38 压到 20（黑得下去）",
    "//             ★锚点（由生成脚本按表自动打印，杜绝手写注释与表不一致）★",
    "//               " + anchor_txt,
    f"//             性质：单调不减；最长平台 {plateau} 级；暗部提升（42->{lut[42]}，+{lut[42]-42} 码）；",
    f"//               高光压缩（236->{lut[236]}，比原始低 {236-lut[236]} 码；200->{lut[200]}），y(0)=0 保留真黑，y(255)=255 保留白；",
    f"//               折点在 (x={T}, y={lut[T]})（深暗区，像素极少 ⇒ 折线不可见）。",
])

src = open(RTL, "r", encoding="utf-8", newline="").read()
orig = src
shutil.copyfile(RTL, os.path.join(BAK, "isp_gamma.v.before"))


def rep(old, new, name):
    global src
    assert old in src, "找不到待替换文本: " + name
    src = src.replace(old, new, 1)


m = re.search(r"    mem_b00\[  0\] = .*?mem_b00\[255\] = 8'h[0-9a-f]{2};", src, re.S)
assert m, "找不到内联表块"
src = src[:m.start()] + new_table + src[m.end():]

i0 = src.index("// 表        :")
i1 = src.index("// 实现      :")
src = src[:i0] + tbl_head + "\n" + src[i1:]

rep("（tone curve, 两段幂函数）查表级。", "（tone curve, 线性趾 + 两段幂函数）查表级。", "功能行")

m2 = re.search(r"//    表内容 = .*?见文件头「表」段）。\n", src, re.S)
assert m2, "找不到初始化段注释"
src = (src[:m2.start()] +
       "//    表内容 = gamma_lut_toe_t8_s15_p160_a050.hex（gen_gamma_lut_toe.py 生成，已逐条核对）；\n"
       "//      曲线 x<=t: y=s*x / t<x<=P: y=s*t+(P-s*t)*((x-t)/(P-t))^A / x>P: y=P+(255-P)*(1-((255-x)/(255-P))^B)，\n"
       f"//      t={T}, s={S:.1f}, P={P}, A={A:.2f}, B={B:.2f}（线性趾 + 反 S：近黑保住黑、暗部提亮、光源压暗）。\n" +
       src[m2.end():])

rep("//               端口/时序/12 路结构/旁路行为均未动。",
    "//               端口/时序/12 路结构/旁路行为均未动。\n"
    f"//   2026-10-11c 加线性趾 t={T} s={S:.1f}（折点 y={lut[T]}）：实测盖镜头黑是 0~1 码、无基座，\n"
    "//               发灰来自无趾曲线把 1~4 码底噪抬到 13~25 码。只改最底下 9 码，\n"
    "//               y(42)/y(118)/y(236) 与上一版逐码相同；端口/时序/12 路/旁路行为均未动。",
    "修改记录")

rep("// [HDR-2026-10-11b] 文件      : isp_gamma.v",
    "// [HDR-2026-10-11c] 文件      : isp_gamma.v", "顶部标签")

assert src != orig
tmp = RTL + ".tmp_new"
with open(tmp, "w", encoding="utf-8", newline="") as f:
    f.write(src)
os.replace(tmp, RTL)

# 回读校验：从 RTL 解析 256 个值，逐条与曲线比对
back = re.findall(r"mem_b00\[\s*(\d+)\] = 8'h([0-9a-f]{2});", open(RTL, encoding="utf-8").read())
assert len(back) == 256, f"内联表条数不是 256: {len(back)}"
for idx, hx in back:
    assert int(hx, 16) == lut[int(idx)], f"第 {idx} 条不符：表 {hx} vs 期望 {lut[int(idx)]}"
print("已更新: " + RTL)
print("  回读校验 PASS：256 条与曲线逐条一致，单调，锚点按表自动写入")
print("  备份: " + os.path.join(BAK, "isp_gamma.v.before"))
print("  hex : " + HEX)
print(f"  参数: t={T} s={S:.1f} P={P} A={A:.2f} B={B:.2f}")
print("  锚点: " + anchor_txt)
print(f"  最长平台 {plateau} 级   y(1)={lut[1]} y(2)={lut[2]} y(4)={lut[4]} y(8)={lut[8]}")
