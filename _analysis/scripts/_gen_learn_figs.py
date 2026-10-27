# -*- coding: utf-8 -*-
"""为《项目学习清单》生成四张示意图。
输出 E:\\FPGA\\_analysis\\out\\figs\\fig{1..4}_*.png（200 dpi，白底）
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, FancyArrowPatch
import matplotlib.font_manager as fm

OUT = r"E:\FPGA\_analysis\out\figs"
os.makedirs(OUT, exist_ok=True)

# ---- 中文字体：优先用系统里的微软雅黑/宋体/黑体 ----
CAND = ["Microsoft YaHei", "SimHei", "SimSun", "Noto Sans CJK SC", "Source Han Sans SC"]
have = {f.name for f in fm.fontManager.ttflist}
CN = next((c for c in CAND if c in have), None)
if CN:
    plt.rcParams["font.sans-serif"] = [CN]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 9

C_BLUE = "#DCE6F2"; C_GREEN = "#DCEFD8"; C_YELL = "#FFF2CC"; C_PURP = "#E4DCF0"; C_GREY = "#EDEDED"
E_BLUE = "#4472A8"; E_GREEN = "#4E8B3F"; E_YELL = "#BF9000"; E_PURP = "#7030A0"; E_GREY = "#808080"


def box(ax, x, y, w, h, text, fc, ec, fs=8.0, bold=False):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.02",
                       linewidth=1.0, facecolor=fc, edgecolor=ec, zorder=2)
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            fontweight="bold" if bold else "normal", zorder=3, linespacing=1.45)


def arrow(ax, x1, y1, x2, y2, color="#404040", lw=1.1, style="-|>", ls="-"):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style,
                                 mutation_scale=10, linewidth=lw, color=color,
                                 linestyle=ls, zorder=1))


# ============================ 图 1：数据通路 13 级 ============================
def fig1():
    fig, ax = plt.subplots(figsize=(11.0, 4.6))
    ax.set_xlim(0, 11.0); ax.set_ylim(0, 4.6); ax.axis("off")
    ax.text(5.5, 4.30, "图 1　视频数据通路：13 个模块与每一拍的位宽",
            ha="center", va="center", fontsize=12, fontweight="bold")

    # 三行布局：上行 5 个、中行 5 个、下行 3 个
    row_y = [3.10, 1.95, 0.80]
    W, H = 1.92, 0.86
    xs = [0.15, 2.22, 4.29, 6.36, 8.43]
    top = [
        ("① SC500CS\n摄像头", "RAW10 2 lane\n每像素只有一色", C_BLUE, E_BLUE),
        ("② MIPI D-PHY RX\n（硬核）", "串行→字节流\n40bit/拍", C_BLUE, E_BLUE),
        ("③ csi_unpacket\n_2lane", "拆 CSI-2 包头\n还原像素", C_BLUE, E_BLUE),
        ("④ raw10_unpacket\n_2lane", "拆包\n40bit=4×10bit", C_BLUE, E_BLUE),
        ("⑤ demosaic\nBGGR 去马赛克", "单色补成 RGB\n128bit", C_GREEN, E_GREEN),
    ]
    mid = [
        ("⑥ data128_96", "位宽转换\n128bit→96bit", C_GREEN, E_GREEN),
        ("⑦ lsc\n镜头暗角校正", "只调 R/B\n96bit", C_GREEN, E_GREEN),
        ("⑧ awb\n自动白平衡", "内含 wb_recip\n96bit", C_GREEN, E_GREEN),
        ("⑨ isp_gamma\n真 S 曲线", "查表 2 拍\n96bit", C_GREEN, E_GREEN),
        ("⑩ my_algo\n五模式风格化", "K1~K4 切换\n96bit", C_GREEN, E_GREEN),
    ]
    bot = [
        ("11) data_96bit_to\n_128bit", "96bit→128bit\n128bit", C_GREEN, E_GREEN),
        ("12) hdmi_mixer\n八层 OSD", "叠 Logo/CNT/框\n128bit", C_PURP, E_PURP),
        ("13) hdmi_tx\nHDMI 1.4b", "TMDS 差分\n1280×720@60", C_PURP, E_PURP),
    ]
    for i, (t, s, fc, ec) in enumerate(top):
        box(ax, xs[i], row_y[0], W, H, t + "\n" + s, fc, ec, fs=7.6)
        if i < 4:
            arrow(ax, xs[i] + W, row_y[0] + H / 2, xs[i + 1], row_y[0] + H / 2)
    # ⑤ → ⑥ 折行
    arrow(ax, xs[4] + W / 2, row_y[0], xs[0] + W / 2, row_y[1] + H, style="-|>", ls="--")
    for i, (t, s, fc, ec) in enumerate(mid):
        box(ax, xs[i], row_y[1], W, H, t + "\n" + s, fc, ec, fs=7.6)
        if i < 4:
            arrow(ax, xs[i] + W, row_y[1] + H / 2, xs[i + 1], row_y[1] + H / 2)
    arrow(ax, xs[4] + W / 2, row_y[1], xs[0] + W / 2, row_y[2] + H, style="-|>", ls="--")
    for i, (t, s, fc, ec) in enumerate(bot):
        box(ax, xs[i], row_y[2], W, H, t + "\n" + s, fc, ec, fs=7.6)
        if i < 2:
            arrow(ax, xs[i] + W, row_y[2] + H / 2, xs[i + 1], row_y[2] + H / 2)

    ax.text(0.15, 0.28, "绿底 = 自研/改造模块（我们要讲清的）　蓝底 = 官方 IP（硬核或加密）　紫底 = 显示输出",
            fontsize=8, color="#505050")
    fig.savefig(os.path.join(OUT, "fig1_datapath.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================ 图 2：位宽为什么反复变 ============================
def fig2():
    fig, ax = plt.subplots(figsize=(9.6, 2.9))
    ax.set_xlim(0, 96); ax.set_ylim(0, 29); ax.axis("off")
    ax.text(48, 27.4, "图 2　一拍的数据为什么一会儿 40bit、一会儿 128bit、又变成 96bit",
            ha="center", fontsize=11.5, fontweight="bold")

    items = [
        (2, 40, "40 bit", "个像素 × 10 bit\n（RAW10，每像素只有一色）", C_BLUE, E_BLUE),
        (26, 56, "128 bit", "个像素 × 32 bit\n（补齐成 R/G/B 各 8bit，多 8bit 填充）", C_GREEN, E_GREEN),
        (56, 42, "96 bit", "个像素 × 24 bit\n（R/G/B 正好 8+8+8，最省）", C_GREEN, E_GREEN),
        (78, 16, "128 bit", "个 96bit 拼成 2 个 128bit\n给 OSD 与 HDMI 用", C_PURP, E_PURP),
    ]
    for x, w, t, s, fc, ec in items:
        box(ax, x, 12.0, w, 8.0, t, fc, ec, fs=11, bold=True)
        ax.text(x + w / 2, 8.6, s, ha="center", va="top", fontsize=7.8, color="#303030", linespacing=1.5)

    arrow(ax, 42, 16.0, 55, 16.0)
    arrow(ax, 82, 16.0, 97.5, 16.0)
    arrow(ax, 30, 16.0, 25.5, 16.0)

    ax.text(2, 3.2, "＊ 关键：96bit 装不下 5 个 24bit 像素（120 > 96），128bit 也装不下 6 个（144 > 128）。\n"
                    "   所以位宽只能在「4 像素」上做文章，中间必须插两次位宽转换——这两次转换不是多余的。",
            fontsize=8.2, color="#7A4A00", linespacing=1.6)
    fig.savefig(os.path.join(OUT, "fig2_bitwidth.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================ 图 3：ISP 六环节顺序 ============================
def fig3():
    fig, ax = plt.subplots(figsize=(10.4, 3.4))
    ax.set_xlim(0, 104); ax.set_ylim(0, 34); ax.axis("off")
    ax.text(52, 32.6, "图 3　ISP 六个环节：顺序不能随便换", ha="center", fontsize=11.5, fontweight="bold")

    steps = [
        ("① 黑电平\n扣除", "减掉一个常数\n把「黑」拉回 0", "减法\n必须最前", C_BLUE, E_BLUE),
        ("② 去马赛克", "每像素只有一色\n补出 RGB 三通道", "补色\n必须紧接", C_GREEN, E_GREEN),
        ("③ 镜头暗角\n校正", "补四角偏暗偏色\n只调 R/B", "乘法\n可与④换序", C_GREEN, E_GREEN),
        ("④ 自动\n白平衡", "整帧拉成中性\nR/B 各乘一个增益", "乘法\n可与③换序", C_GREEN, E_GREEN),
        ("⑤ 自动曝光", "按亮度调增益\n回到亮度目标", "增益\n影响①②", C_YELL, E_YELL),
        ("⑥ S 曲线", "提对比、压暗部\n最后调观感", "最后\n调观感", C_PURP, E_PURP),
    ]
    W, H = 14.4, 11.0
    for i, (t, s, tag, fc, ec) in enumerate(steps):
        x = 2.0 + i * 16.9
        box(ax, x, 13.0, W, H, t, fc, ec, fs=8.4, bold=True)
        ax.text(x + W / 2, 11.6, s, ha="center", va="top", fontsize=7.2, color="#303030", linespacing=1.5)
        ax.text(x + W / 2, 6.6, tag, ha="center", va="top", fontsize=7.0, color="#7A4A00", linespacing=1.4)
        if i < 5:
            arrow(ax, x + W, 18.5, x + 16.9, 18.5)
    ax.text(2.0, 2.2, "蓝=减法类　绿=去马赛克/乘法类　黄=增益控制（影响进光量）　紫=最后调观感",
            fontsize=7.8, color="#505050")
    fig.savefig(os.path.join(OUT, "fig3_isp.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


# ============================ 图 4：块划分 + OSD 八层 ============================
def fig4():
    fig, axes = plt.subplots(1, 2, figsize=(11.0, 3.9),
                             gridspec_kw={"width_ratios": [16, 12]})
    # 左：16×9 块划分
    ax = axes[0]
    ax.set_xlim(0, 16); ax.set_ylim(0, 9); ax.set_aspect("equal")
    ax.set_xticks(range(17)); ax.set_yticks(range(10))
    ax.tick_params(labelsize=6, labelbottom=False, labelleft=False)
    ax.grid(True, color="#C8C8C8", linewidth=0.6)
    for spine in ax.spines.values():
        spine.set_color("#606060")
    # 举例：标几个运动块
    for (cx, cy) in [(3, 5), (4, 5), (5, 5), (4, 6), (3, 6)]:
        ax.add_patch(Rectangle((cx, cy), 1, 1, facecolor="#F8CBCB", edgecolor="#C00000", linewidth=1.4, zorder=3))
    ax.text(8, 9.9, "16 列 × 9 行 = 144 块，每块 80×80 像素", ha="center", fontsize=8.6, fontweight="bold")
    ax.text(3.5, 4.4, "被判为\n运动的块", ha="center", va="top", fontsize=6.8, color="#C00000", linespacing=1.4)

    # 右：八层 OSD
    ax = axes[1]
    ax.set_xlim(0, 12); ax.set_ylim(0, 12); ax.axis("off")
    ax.text(6, 11.6, "八层 OSD 从下往上叠", ha="center", fontsize=8.6, fontweight="bold")
    layers = [
        ("Logo（安路标识）", "#4472A8"), ("帧计数 CNT（右上角计数）", "#BF9000"), ("模式 MODE", "#4E8B3F"),
        ("遥测行 1", "#C55A11"), ("遥测行 2", "#C55A11"), ("参数行", "#2E9BB5"),
        ("运动框", "#C00000"), ("目标框", "#00A040"),
    ]
    for i, (t, c) in enumerate(layers):
        y = 1.1 + i * 1.25
        ax.add_patch(FancyBboxPatch((1.0, y), 10.0, 1.0,
                                    boxstyle="round,pad=0.01,rounding_size=0.04",
                                    facecolor="white", edgecolor=c, linewidth=1.3, zorder=2))
        ax.add_patch(Rectangle((1.0, y), 0.9, 1.0, facecolor=c, edgecolor=c, zorder=3))
        ax.text(1.45, y + 0.5, str(i + 1), ha="center", va="center", color="white",
                fontsize=8, fontweight="bold", zorder=4)
        ax.text(2.2, y + 0.5, t, ha="left", va="center", fontsize=8, zorder=4)
        ax.annotate("", xy=(11.7, y + 0.15), xytext=(11.7, y + 0.85),
                    arrowprops=dict(arrowstyle="-|>", color="#808080", lw=0.9))
    ax.text(1.0, 0.35, "后写的覆盖先写的 → 第 8 层永远在最上面", fontsize=7.2, color="#505050")

    fig.text(0.5, 0.015, "图 4　块级检测的「块」是怎么切的　｜　八层 OSD 的叠放顺序",
             ha="center", fontsize=11.5, fontweight="bold")
    fig.savefig(os.path.join(OUT, "fig4_blocks_osd.png"), dpi=200, bbox_inches="tight", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4()
    for n in ("fig1_datapath", "fig2_bitwidth", "fig3_isp", "fig4_blocks_osd"):
        p = os.path.join(OUT, n + ".png")
        print("%-24s %8d B" % (n + ".png", os.path.getsize(p)))
