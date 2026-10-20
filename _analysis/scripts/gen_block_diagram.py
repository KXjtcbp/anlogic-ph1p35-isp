# -*- coding: utf-8 -*-
"""生成报告用「系统整体框图」（图 1）——第 2 版，修正色带标题与图形重叠。

布局依据（逐条可核对）：
  - ISP 链顺序取自 isp_top.v 的例化行号：
      demosaic(187) → data128_96(211) → lsc(228) → awb(298) → isp_gamma(325)
      → my_algo(349) → data_96bit_to_128bit(402)
  - 旁路观察者（只收不发，无 tready）：
      ae_stat(253)    取数 lsc_tdata_96    （isp_top.v:258）
      obj_detect(274)  取数 m_axis_tdata_96 （isp_top.v:286，即 lsc 之前）
      motion_detect(375) 取数 algo_O_tdata  （isp_top.v:391，即 my_algo 之后）
  - 显示通路：isp O_tdata(128bit) → DDR2 帧缓存 → uivtc → hdmi_mixer(7 层 OSD) → hdmi_tx
  - 控制通路（24MHz 域）：key_mode_ctrl / ae_ctrl / uicfgcs500_720p(含 I2C) / 拨码同步
输出：E:\\FPGA\\系统框图_FPGA数据通路.png（300 dpi）
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

matplotlib.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
matplotlib.rcParams["axes.unicode_minus"] = False

W, H = 104.0, 64.0
fig, ax = plt.subplots(figsize=(16.0, 9.85), dpi=300)
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis("off")

C_IN, C_ISP, C_OBS, C_DISP, C_CTL = "#dbeafe", "#dcfce7", "#fef3c7", "#ede9fe", "#fee2e2"
C_EDGE = "#334155"


def box(x, y, w, h, text, fc, fs=8.2, bold=False, ls="-", lw=1.1):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.32,rounding_size=1.0",
                                fc=fc, ec=C_EDGE, lw=lw, ls=ls, zorder=3))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", zorder=4, linespacing=1.32)


def arrow(x1, y1, x2, y2, ls="-", lw=1.3, color=C_EDGE, rad=0.0):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", ls=ls, lw=lw,
                                 color=color, mutation_scale=12, zorder=2,
                                 connectionstyle="arc3,rad=%s" % rad))


def band(y0, y1, label, color):
    ax.add_patch(FancyBboxPatch((1.0, y0), W - 2.0, y1 - y0,
                                boxstyle="round,pad=0.2,rounding_size=0.8",
                                fc=color, ec="none", alpha=0.32, zorder=0))
    ax.text(2.6, y1 - 0.9, label, fontsize=8.6, fontweight="bold",
            color="#334155", va="top", zorder=1)


# ================= ① 视频输入通路 =================
band(51.0, 60.2, "① 视频输入通路（MIPI RX 字节时钟域）", "#93c5fd")
box(5, 52.0, 13, 5.6, "SC500CS\nRAW10 2-lane", C_IN, 8.0, True)
box(21, 52.0, 12, 5.6, "MIPI D-PHY RX\n（硬核）", C_IN, 7.6)
box(36, 52.0, 12, 5.6, "csi_unpacket\n_2lane", C_IN, 7.6)
box(51, 52.0, 13, 5.6, "raw10_unpacket\n_2lane", C_IN, 7.6)
for x1, x2 in ((18.2, 20.8), (33.2, 35.8), (48.2, 50.8)):
    arrow(x1, 54.8, x2, 54.8)
ax.text(66.0, 54.8, "40bit / 4 像素（RAW10）", fontsize=7.2, va="center", color="#475569")

# ================= ② 图像处理通路 =================
band(23.0, 50.0, "② 图像处理通路（ISP 域 60MHz，每拍 4 像素，AXI4-Stream 逐拍握手，无帧级缓存）", "#86efac")
box(5, 38.6, 12, 6.8, "demosaic\nBGGR 去马赛克", C_ISP, 7.6, True)
box(19.5, 38.6, 11, 6.8, "data128_96\n128→96bit", C_ISP, 7.4)
box(33, 38.6, 11, 6.8, "lsc\n镜头暗角校正", C_ISP, 7.6, True)
box(46.5, 38.6, 11, 6.8, "awb\n（内含 wb_recip）", C_ISP, 7.4, True)
box(60, 38.6, 11, 6.8, "isp_gamma\n真 S 曲线 LUT", C_ISP, 7.4, True)
box(73.5, 38.6, 11, 6.8, "my_algo\n五模式风格化", C_ISP, 7.4, True)
box(87, 38.6, 9, 6.8, "data96\n_128", C_ISP, 7.2)
for x1, x2 in ((17.2, 19.3), (30.7, 32.8), (44.2, 46.3), (57.7, 59.8), (71.2, 73.3), (84.7, 86.8)):
    arrow(x1, 42.0, x2, 42.0)

# 旁路观察者
box(33, 26.6, 11, 5.6, "ae_stat\n帧亮度和统计", C_OBS, 7.2)
box(46.5, 26.6, 11, 5.6, "obj_detect\n颜色目标检测", C_OBS, 7.2)
box(73.5, 26.6, 11, 5.6, "motion_detect\n块级帧差", C_OBS, 7.2)
arrow(38.5, 38.2, 38.5, 32.6, ls="--", lw=1.0, color="#b45309")
arrow(52.0, 38.2, 52.0, 32.6, ls="--", lw=1.0, color="#b45309")
arrow(79.0, 38.2, 79.0, 32.6, ls="--", lw=1.0, color="#b45309")
ax.text(58.2, 29.4, "旁路观察者：只收不发、无 tready，\n不占用主流水线节拍", fontsize=7.2,
        color="#92400e", va="center", ha="left")

# ================= ③ 显示通路 =================
band(11.0, 21.8, "③ 显示通路（HDMI 像素域 75MHz / 串行域 375MHz）", "#c4b5fd")
box(5, 12.2, 13, 6.2, "DDR2 帧缓存\nph1p35_324", C_DISP, 7.6, True)
box(21, 12.2, 12, 6.2, "uivtc\n1280×720@60", C_DISP, 7.4)
box(36, 12.2, 14, 6.2, "hdmi_mixer\n8 层 OSD 叠加", C_DISP, 7.6, True)
box(53, 12.2, 12, 6.2, "hdmi_tx\nHDMI 1.4b", C_DISP, 7.4, True)
box(68, 12.2, 9, 6.2, "显示器\n1280×720", C_DISP, 7.4)
for x1, x2 in ((18.2, 20.8), (33.2, 35.8), (50.2, 52.8), (65.2, 67.8)):
    arrow(x1, 15.3, x2, 15.3)
arrow(91.5, 38.6, 91.5, 18.6)
ax.text(92.4, 28.6, "128bit\n像素流", fontsize=6.9, va="center", color="#475569")
ax.text(80.0, 13.4, "OSD 8 层：\nLogo｜CNT｜\n两行遥测｜MODE\n参数行｜运动框｜目标框", fontsize=6.6,
        color="#4c1d95", ha="left", va="center", linespacing=1.4)

# ================= ④ 控制通路 =================
band(0.8, 10.0, "④ 控制通路（24MHz 域）", "#fca5a5")
box(5, 2.2, 14, 4.6, "key_mode_ctrl\nK1~K4 去抖 → 模式", C_CTL, 7.2)
box(21, 2.2, 13, 4.6, "ae_ctrl\nAE 闭环状态机", C_CTL, 7.2)
box(36, 2.2, 16, 4.6, "uicfgcs500_720p\n（I2C 配置 SC500CS）", C_CTL, 7.2)
box(54, 2.2, 17, 4.6, "拨码同步 + 亚稳消除\nSW1~SW4 → 全局使能", C_CTL, 7.2)
arrow(53.8, 4.5, 44.2, 4.5, lw=1.0)

ax.text(73.0, 4.6, "SW1→LSC ｜ SW2→S 曲线\nSW3→运动检测 ｜ SW4→检测灵敏度\n（控制输出：模式→my_algo；曝光/增益→I2C）",
        fontsize=6.4, color="#7f1d1d", va="center", linespacing=1.4)

# 标题与注
ax.text(W / 2, H - 1.5, "图 1  基于安路 PH1P35 的实时数字图像处理系统 —— 系统整体框图",
        ha="center", va="center", fontsize=11.5, fontweight="bold")
ax.text(W / 2, 0.15, "注：绿色块为自研/改造模块，蓝色块为官方 IP 与例化，黄色块为旁路观察者（不参与握手）。"
                     "全链路无帧级缓存，处理延迟为固定流水线级数。",
        ha="center", va="center", fontsize=6.9, color="#475569")

OUT = r"E:\FPGA\系统框图_FPGA数据通路.png"
fig.savefig(OUT, dpi=300, bbox_inches="tight", facecolor="white")
plt.close(fig)
print("saved:", OUT, os.path.getsize(OUT), "B")
from PIL import Image
print("尺寸:", Image.open(OUT).size, "px")
