#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# compare.py —— FPGA 图像处理前后对比分析工具
# -----------------------------------------------------------------------------
# 用途
#   把「FPGA 当前输出(before)」和「LR(Lightroom) 调整后 / 期望效果(after)」两张图
#   做逐项量化对比，输出：
#     1) 终端报告         —— 6 大节（基础统计/直方图/影调/色彩/差异/反推参数建议）
#     2) report.txt       —— 与终端报告完全相同的文本（UTF-8-BOM，记事本可直接打开）
#     3) diff.png         —— 差异图（原图 / 目标图 / 绝对差放大 / 有符号差热力图）
#     4) histogram.png    —— 直方图与统计图（灰度直方图/RGB 32bin/CDF/通道均值/HSV/差值分布）
#
# 命令行
#   python compare.py before.png after.png
#   python compare.py before.png after.png -o out_dir          # 指定输出目录
#   python compare.py before.png after.png --amp 8             # 差异放大倍数（默认 4）
#   python compare.py before.png after.png --tag 黑电平56       # 报告标题里加一个备注标签
#
# 依赖
#   只用 OpenCV + NumPy + Matplotlib（+ 标准库）。不需要 scikit-image / Pillow / pandas。
#
# 关键实现说明（为什么这样写）
#   * 中文路径：cv2.imread / cv2.imwrite 在 Windows 下遇到中文路径会静默返回 None。
#     本脚本统一用「np.fromfile + cv2.imdecode」读、「cv2.imencode + tofile」写，彻底绕开该问题。
#   * 位深与通道：统一归一化成 8bit BGR。16bit 输入按 >>8 降到 8bit 并在报告里标注；
#     灰度图自动扩成 3 通道；BGRA 丢掉 alpha。
#   * 尺寸不一致：把 after 用 INTER_AREA 缩放到 before 的尺寸，并在报告顶部明确警告。
#   * 灰度（luma）：用 Rec.601 标准权重 0.299R+0.587G+0.114B（= cv2.COLOR_BGR2GRAY）。
#     注意这与本工程 my_algo.v 里的 f_luma 自定义权重不同，报告里会说明。
#   * 色相均值：色相是角度量，直接取算术均值会被 0/360 交界污染，因此同时给「算术均值」和
#     「圆均值(单位圆向量平均)」，并以圆均值为准。
#   * 影调/反推：所有阈值/公式都在代码里写明，报告里给出中间量，便于人工复核。
#
# 作者：AI 助手（为 Anlogic PH1P35 + SC500CS 720p60 工程定制）
# 版本：v1.0
# =============================================================================

from __future__ import annotations

import argparse
import math
import os
import sys
import datetime

import numpy as np
import cv2

# Matplotlib 用无界面后端，才能在脚本/无显示环境下出图
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager


# =============================================================================
# 0. 全局常量与配置
# =============================================================================

# ---- SC500CS 模拟增益寄存器编码（用于「反推参数建议」一节） --------------------
# 手册公式：模拟增益 = (3e09 / 0x20) * 2^k，其中 3e08 的高 5 bit 决定 k：
#   3e08 = 0x03 -> x1 ; 0x07 -> x2 ; 0x0F -> x4 ; 0x1F -> x8
# 3e09 的 6 bit 有效范围 0x20..0x3F = 1.000x..1.969x，因此总增益范围 1.000x..15.750x。
SC500_GAIN_STEPS = ((0x03, 1.0), (0x07, 2.0), (0x0F, 4.0), (0x1F, 8.0))
SC500_GAIN_MAX = 15.75
# 本工程当前写在 uics500reg_720p60.v 里的模拟增益（0x1F2D = 11.25x），仅用于报告对照。
CURRENT_SC500_GAIN_REG = (0x1F, 0x2D)
CURRENT_SC500_GAIN = CURRENT_SC500_GAIN_REG[1] / 32.0 * 8.0

# 本工程当前写在 mipi_to_raw_converter.v 里的黑电平基座（10bit 域）
CURRENT_BLK_LEVEL = 56

# 目标中间调（18% 中性灰在 sRGB 下约 118），AE/影调建议会引用
TARGET_MIDTONE = 118.0

# 判定「有变化」的阈值（8bit 码值）
TH_SMALL = 2.0      # 小于 2 视为噪声级
TH_MID = 8.0        # 8 以上人眼明显可见
TH_LARGE = 32.0     # 32 以上属于大幅改动

# 量化台阶告警阈值：P1..P99 区间内实际用到的灰度级数少于该值就提示断阶
MIN_DISTINCT_LEVELS = 100

# 中文字体候选（Windows 自带微软雅黑/黑体；缺字体时图形上的中文会显示成方框）
CJK_FONT_CANDIDATES = (
    "Microsoft YaHei", "SimHei", "SimSun",
    "Noto Sans CJK SC", "Source Han Sans SC", "WenQuanYi Micro Hei", "Arial Unicode MS",
)


# =============================================================================
# 1. 基础工具函数
# =============================================================================

def setup_matplotlib_cjk() -> str:
    """挑一个系统里存在的中文字体，返回实际使用的字体名（找不到就返回空串）。"""
    available = {f.name for f in font_manager.fontManager.ttflist}
    for name in CJK_FONT_CANDIDATES:
        if name in available:
            plt.rcParams["font.sans-serif"] = [name] + list(plt.rcParams["font.sans-serif"])
            plt.rcParams["axes.unicode_minus"] = False   # 负号用 ASCII，避免缺字形
            return name
    plt.rcParams["axes.unicode_minus"] = False
    return ""


def safe_print(text: str) -> None:
    """把报告打到终端。终端编码不是 UTF-8（例如 cp437）时退化为 replace，避免抛异常。"""
    try:
        print(text)
    except UnicodeEncodeError:
        enc = sys.stdout.encoding or "ascii"
        sys.stdout.write(text.encode(enc, errors="replace").decode(enc, errors="replace") + "\n")


def imread_bgr(path: str) -> np.ndarray:
    """读图并归一化为 8bit BGR。

    用 np.fromfile + cv2.imdecode 而不是 cv2.imread —— 前者支持中文路径，后者在
    Windows 上遇到中文路径会直接返回 None。
    """
    if not os.path.isfile(path):
        raise FileNotFoundError("找不到文件：%s" % path)
    raw = np.fromfile(path, dtype=np.uint8)          # np.fromfile 正常支持中文路径
    if raw.size == 0:
        raise IOError("文件为空或无法读取：%s" % path)
    img = cv2.imdecode(raw, cv2.IMREAD_UNCHANGED)    # UNCHANGED 保留原始位深/通道
    if img is None:
        raise IOError("OpenCV 无法解码该图像（格式不支持？）：%s" % path)
    return normalize_to_bgr8(img, path)


def normalize_to_bgr8(img: np.ndarray, path: str = "") -> np.ndarray:
    """任意输入 -> 8bit 3 通道 BGR。"""
    note = []
    # --- 位深 ---
    if img.dtype == np.uint16:
        img = (img >> 8).astype(np.uint8)            # 16bit -> 8bit 取高 8 位（与 FPGA 链路一致）
        note.append("16bit 输入按 >>8 降到 8bit")
    elif img.dtype == np.float32 or img.dtype == np.float64:
        img = np.clip(img, 0.0, 1.0) * 255.0
        img = img.astype(np.uint8)
        note.append("浮点输入按 [0,1] 归一化到 8bit")
    elif img.dtype != np.uint8:
        img = np.clip(img, 0, 255).astype(np.uint8)
        note.append("非 8bit 输入被截断为 8bit")
    # --- 通道 ---
    if img.ndim == 2:                                 # 单通道灰度
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        note.append("灰度图已扩成 3 通道")
    elif img.ndim == 3 and img.shape[2] == 4:         # BGRA，丢 alpha
        img = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
        note.append("BGRA 已丢弃 alpha 通道")
    elif img.ndim == 3 and img.shape[2] == 1:
        img = cv2.cvtColor(img[:, :, 0], cv2.COLOR_GRAY2BGR)
        note.append("单通道图已扩成 3 通道")
    if note:
        print("[提示] %s：%s" % (os.path.basename(path), "；".join(note)))
    return img


def imwrite_png(path: str, img_bgr: np.ndarray) -> None:
    """写 PNG，支持中文路径（cv2.imencode + tofile）。"""
    ok, buf = cv2.imencode(".png", img_bgr)
    if not ok:
        raise IOError("PNG 编码失败：%s" % path)
    buf.tofile(path)


def split_rgb(bgr: np.ndarray):
    """返回 (R, G, B)，每个都是 HxW 的 uint8 视图。"""
    return bgr[:, :, 2], bgr[:, :, 1], bgr[:, :, 0]


def to_gray(bgr: np.ndarray) -> np.ndarray:
    """Rec.601 luma：0.299R + 0.587G + 0.114B（= cv2.COLOR_BGR2GRAY）。"""
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def hist256(x: np.ndarray) -> np.ndarray:
    """256 bin 直方图（计数）。"""
    return np.bincount(x.ravel().astype(np.int64), minlength=256)[:256].astype(np.int64)


def hist32(x: np.ndarray) -> np.ndarray:
    """32 bin 直方图：把 256 个 bin 每 8 个合并一格，第 i 格对应码值 [8i, 8i+7]。"""
    return hist256(x).reshape(32, 8).sum(axis=1)


def entropy_bits(x: np.ndarray) -> float:
    """灰度直方图香农熵（bit）。越大说明信息量/层次越多，越小说明趋于平坦或二值化。"""
    h = hist256(x).astype(np.float64)
    p = h / max(h.sum(), 1.0)
    p = p[p > 0]
    return float(-(p * np.log2(p)).sum())


def pct(x: np.ndarray, qs=(1, 5, 50, 95, 99)) -> dict:
    """分位数，返回 {q: 值}。"""
    vals = np.percentile(x.astype(np.float64), qs)
    return {q: float(v) for q, v in zip(qs, vals)}


def gain_to_sc500_regs(gain: float):
    """把线性增益倍数换算成 SC500CS 的 {3e08, 3e09} 寄存器字节。

    返回 dict：coarse(3e08 字节) / fine(3e09 字节) / actual(实际倍数) / err(相对误差)
    或 {'overflow': True} / {'underflow': True}。
    选择策略：4 个 coarse 档位各算一个候选，取与目标倍数误差最小的那个。
    """
    if gain is None or not np.isfinite(gain) or gain <= 0:
        return None
    if gain > SC500_GAIN_MAX + 1e-6:
        return {"overflow": True, "gain": gain}
    best = None
    for reg, mult in SC500_GAIN_STEPS:
        fine = int(round(32.0 * gain / mult))
        fine = max(32, min(63, fine))               # 3e09 有效 0x20..0x3F
        actual = mult * fine / 32.0
        err = abs(actual - gain) / gain
        if best is None or err < best[0]:
            best = (err, reg, fine, actual)
    err, reg, fine, actual = best
    if actual < 1.0 - 1e-9:
        return {"underflow": True, "gain": gain}
    return {"coarse": reg, "fine": fine, "actual": actual, "err": err}


def bias_direction(da: float, db: float):
    """由 Lab 的 (a-128, b-128) 均值给出偏色方向文字与角度。

    a>0 偏红、a<0 偏绿；b>0 偏黄、b<0 偏蓝。角度用 atan2(db, da)，0 度=纯红方向。
    """
    ang = math.degrees(math.atan2(db, da)) % 360.0
    sectors = [
        (0, "偏红"), (45, "偏橙/黄红"), (90, "偏黄"), (135, "偏黄绿"),
        (180, "偏绿"), (225, "偏青"), (270, "偏蓝"), (315, "偏品红"),
    ]
    name = min(sectors, key=lambda s: min(abs(ang - s[0]), 360 - abs(ang - s[0])))[1]
    if abs(da) < 1.0 and abs(db) < 1.0:
        name = "基本中性（无明显偏色）"
    return name, ang


def fmt(x, nd=2) -> str:
    """数字格式化：None 原样，其余保留 nd 位小数。"""
    if x is None:
        return "N/A"
    if isinstance(x, (int, np.integer)):
        return str(int(x))
    return ("%." + str(nd) + "f") % float(x)


# =============================================================================
# 2. 各维度分析
# =============================================================================

def analyze_basic(bgr: np.ndarray) -> dict:
    """第 1 节：基础统计（RGB 均值/标准差、灰度均值、HSV 均值）。"""
    r, g, b = split_rgb(bgr)
    gray = to_gray(bgr)
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    h = hsv[:, :, 0].astype(np.float64)   # OpenCV 色相 0..179（对应 0..360 度）
    s = hsv[:, :, 1].astype(np.float64)   # 饱和度 0..255
    v = hsv[:, :, 2].astype(np.float64)   # 明度 0..255

    # 色相圆均值：把 H 映射到单位圆上求平均向量，避免 0/360 交界把均值拉到中间
    ang = h * (2.0 * math.pi / 180.0)     # H 单位是 0.5 度，故 x2 得真实角度
    mx, my = float(np.sin(ang).mean()), float(np.cos(ang).mean())
    h_circ_deg = math.degrees(math.atan2(mx, my)) % 360.0
    # 圆均值的合成向量长度（0..1）：越接近 0 说明色相越分散，此时均值意义不大
    h_r = math.hypot(mx, my)

    return {
        "shape": bgr.shape,
        "pixels": int(bgr.shape[0] * bgr.shape[1]),
        "r_mean": float(r.mean()), "g_mean": float(g.mean()), "b_mean": float(b.mean()),
        "r_std": float(r.std()), "g_std": float(g.std()), "b_std": float(b.std()),
        "rgb_mean_all": float(bgr.mean()),
        "rgb_std_all": float(bgr.astype(np.float64).std()),
        "gray_mean": float(gray.mean()), "gray_std": float(gray.std()),
        "h_mean_arith": float(h.mean()), "h_circ_deg": h_circ_deg, "h_circ_r": h_r,
        "s_mean": float(s.mean()), "s_std": float(s.std()),
        "v_mean": float(v.mean()), "v_std": float(v.std()),
    }


def analyze_hist(bgr: np.ndarray) -> dict:
    """第 2 节：直方图特征（灰度/RGB 各 32bin、1/5/50/95/99 分位数）。"""
    r, g, b = split_rgb(bgr)
    gray = to_gray(bgr)
    hg = hist256(gray)
    total = max(int(hg.sum()), 1)
    return {
        "gray32": hist32(gray), "r32": hist32(r), "g32": hist32(g), "b32": hist32(b),
        "gray256": hg,
        "hist_total": total,
        "pct_gray": pct(gray), "pct_r": pct(r), "pct_g": pct(g), "pct_b": pct(b),
        "zero_frac": float((gray == 0).mean()),        # 纯黑像素占比（黑电平是否压低）
        "full_frac": float((gray == 255).mean()),      # 纯白像素占比（是否过曝截断）
        "entropy": entropy_bits(gray),
        "distinct_levels": int(np.count_nonzero(hg[(hg > 0)])),
        "max_bin_frac": float(hg.max() / total),
    }


def analyze_tone(bgr: np.ndarray, hist: dict) -> dict:
    """第 3 节：影调特征（黑场、白场、动态范围、中间调、对比度、断阶）。"""
    gray = to_gray(bgr)
    p = hist["pct_gray"]
    p1, p5, p50, p95, p99 = p[1], p[5], p[50], p[95], p[99]

    # 黑场/白场用 1%/99% 分位（比 min/max 抗噪，单点坏点不会带偏）
    black_level, white_level = p1, p99
    # 动态范围：P99-P1 是"有效"范围；min..max 是"全部"范围
    dr_p = p99 - p1
    dr_full = float(gray.max()) - float(gray.min())
    # 中间调：取 P10..P90 之间的像素求均值（排除死黑与高光，反映"主体"亮度）
    lo, hi = np.percentile(gray, [10, 90])
    mid_mask = (gray >= lo) & (gray <= hi)
    mid_mean = float(gray[mid_mask].mean()) if mid_mask.any() else float(gray.mean())

    # 对比度估计 3 种口径：
    #   RMS 对比度 = 灰度标准差（最常用）
    #   Michelson  = (白场-黑场)/(白场+黑场)
    #   局部对比度 = 相邻像素梯度幅值均值（反映边缘/细节强度，也能侧面反映锐度）
    rms = float(gray.std())
    michelson = (white_level - black_level) / max(white_level + black_level, 1e-6)
    gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
    grad_mean = float(np.sqrt(gx * gx + gy * gy).mean())

    # 断阶检测：P1..P99 内实际用到的灰度级数
    hg = hist["gray256"]
    lo_i, hi_i = int(round(black_level)), int(round(white_level))
    used = int(np.count_nonzero(hg[lo_i:hi_i + 1])) if hi_i >= lo_i else 0

    return {
        "black": black_level, "white": white_level,
        "min": float(gray.min()), "max": float(gray.max()),
        "dr_p": dr_p, "dr_full": dr_full,
        "mid_mean": mid_mean, "mid_lo": float(lo), "mid_hi": float(hi),
        "mid_frac": float(mid_mask.mean()),
        "rms_contrast": rms, "michelson": michelson, "grad_mean": grad_mean,
        "p": p, "used_levels": used,
    }


def analyze_color(bgr: np.ndarray, basic: dict) -> dict:
    """第 4 节：色彩特征（白平衡估计、饱和度估计、偏色方向）。"""
    r, g, b = split_rgb(bgr)
    gray_mean = basic["gray_mean"]

    # (1) 灰世界假设：如果画面平均应该是灰的，则各通道需要的增益 = 总均值/该通道均值
    gw_gain_r = gray_mean / max(basic["r_mean"], 1e-6)
    gw_gain_g = gray_mean / max(basic["g_mean"], 1e-6)
    gw_gain_b = gray_mean / max(basic["b_mean"], 1e-6)

    # (2) 白点估计（亮部 99% 分位当作"白"）：用于判断偏色方向
    wp_r = float(np.percentile(r, 99))
    wp_g = float(np.percentile(g, 99))
    wp_b = float(np.percentile(b, 99))

    # (3) Lab 偏色：cv2 的 L/a/b 都是 0..255，a/b 以 128 为中性
    lab = cv2.cvtColor(bgr, cv2.COLOR_BGR2LAB)
    da = float(lab[:, :, 1].astype(np.float64).mean()) - 128.0
    db = float(lab[:, :, 2].astype(np.float64).mean()) - 128.0
    direction, angle = bias_direction(da, db)

    # (4) 饱和度 / 彩度：HSV 的 S，以及 max(R,G,B)-min(R,G,B) 的均值（后者不受 HSV 量化影响）
    chroma = (bgr.max(axis=2).astype(np.float64) - bgr.min(axis=2).astype(np.float64))
    s_mean = basic["s_mean"]
    grayish_frac = float((cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)[:, :, 1] < 10).mean())

    # (5) 色温趋势：R/B 均值比，>1 偏暖、<1 偏冷
    rb_ratio = basic["r_mean"] / max(basic["b_mean"], 1e-6)

    return {
        "gw_gain_r": gw_gain_r, "gw_gain_g": gw_gain_g, "gw_gain_b": gw_gain_b,
        "wp_r": wp_r, "wp_g": wp_g, "wp_b": wp_b,
        "da": da, "db": db, "bias_dir": direction, "bias_angle": angle,
        "s_mean": s_mean, "chroma_mean": float(chroma.mean()),
        "grayish_frac": grayish_frac, "rb_ratio": rb_ratio,
    }


def analyze_diff(before: np.ndarray, after: np.ndarray):
    """第 5 节：差异分析（返回 (diff_dict, diff_gray_int16))。"""
    bf = before.astype(np.int16)
    af = after.astype(np.int16)
    d = af - bf                                     # 有符号逐像素差
    dg = to_gray(after).astype(np.int16) - to_gray(before).astype(np.int16)

    mse_rgb = float((d.astype(np.float64) ** 2).mean())
    psnr = 10.0 * math.log10(255.0 ** 2 / mse_rgb) if mse_rgb > 0 else float("inf")

    br, bg_, bb = split_rgb(before)
    ar, ag, ab = split_rgb(after)
    r_ratio = float(ar.mean()) / max(float(br.mean()), 1e-6)
    g_ratio = float(ag.mean()) / max(float(bg_.mean()), 1e-6)
    b_ratio = float(ab.mean()) / max(float(bb.mean()), 1e-6)

    bbasic = analyze_basic(before)
    abasic = analyze_basic(after)
    btone = analyze_tone(before, analyze_hist(before))
    atone = analyze_tone(after, analyze_hist(after))

    res = {
        "same_size": before.shape == after.shape,
        "d": d, "dg": dg,
        "mae_rgb": float(np.abs(d.astype(np.float64)).mean()),
        "mae_gray": float(np.abs(dg.astype(np.float64)).mean()),
        "rms_diff": float(np.sqrt((dg.astype(np.float64) ** 2).mean())),
        "max_abs_diff": int(np.abs(dg).max()),
        "psnr": psnr,
        "frac_gt2": float((np.abs(dg) > TH_SMALL).mean()),
        "frac_gt8": float((np.abs(dg) > TH_MID).mean()),
        "frac_gt32": float((np.abs(dg) > TH_LARGE).mean()),
        "dgray_mean": float(abasic["gray_mean"] - bbasic["gray_mean"]),
        "gray_ratio": float(abasic["gray_mean"]) / max(bbasic["gray_mean"], 1e-6),
        "std_ratio": float(abasic["gray_std"]) / max(bbasic["gray_std"], 1e-6),
        "s_ratio": float(abasic["s_mean"]) / max(bbasic["s_mean"], 1e-6),
        "chroma_ratio": float(analyze_color(after, abasic)["chroma_mean"]) /
                        max(analyze_color(before, bbasic)["chroma_mean"], 1e-6),
        "r_ratio": r_ratio, "g_ratio": g_ratio, "b_ratio": b_ratio,
        # 相对绿通道的白平衡增益变化（R/G 与 B/G）：剔除整体曝光影响后的"色偏"变化
        "wb_rgb_ratio": (r_ratio / max(g_ratio, 1e-6), b_ratio / max(g_ratio, 1e-6)),
        "mae_r": float(np.abs(d[:, :, 2].astype(np.float64)).mean()),
        "mae_g": float(np.abs(d[:, :, 1].astype(np.float64)).mean()),
        "mae_b": float(np.abs(d[:, :, 0].astype(np.float64)).mean()),
        "dmean_r": float(ar.mean() - br.mean()),
        "dmean_g": float(ag.mean() - bg_.mean()),
        "dmean_b": float(ab.mean() - bb.mean()),
        "basic_before": bbasic, "basic_after": abasic,
        "tone_before": btone, "tone_after": atone,
    }
    return res, dg


# =============================================================================
# 3. 第 6 节：给 Agent 的「反推参数建议」
# =============================================================================

def suggest_params(before_bgr, after_bgr, dstat: dict) -> list:
    """根据 before/after 的测量结果，反推「要让 FPGA 输出变成 after，应该在 ISP 里改什么」。

    全部是"测量值 -> 公式 -> 具体寄存器/常数"的推导，报告里同时打印中间量以便人工复核。
    本工程的链路假设（与实际 RTL 一致）：
        RAW10 --(减黑电平 S_blk_level, 再 >>2)--> RAW8 --demosaic--> AWB --my_algo--> HDMI
    """
    out = []
    bb, ba = dstat["basic_before"], dstat["basic_after"]
    tb, ta = dstat["tone_before"], dstat["tone_after"]

    d_black = tb["black"] - ta["black"]                 # 8bit 黑场差
    d_white = ta["white"] - tb["white"]                 # 8bit 白场差
    sig_ratio = (ta["white"] - ta["black"]) / max(tb["white"] - tb["black"], 1e-6)

    # ---- (1) 黑电平 -----------------------------------------------------------
    out.append("【1. 黑电平（Black Level）】")
    out.append("  before 黑场(P1)=%s，after 黑场(P1)=%s，差 %s 码值(8bit)"
               % (fmt(tb["black"], 1), fmt(ta["black"], 1), fmt(d_black, 1)))
    out.append("  before 纯黑像素占比=%.2f%%，after=%.2f%%"
               % (_zero_frac_hack(before_bgr) * 100.0, _zero_frac_hack(after_bgr) * 100.0))
    if abs(d_black) < TH_SMALL:
        out.append("  -> 黑电平无需改动（差值在噪声级以内，< %d 码值）。" % int(TH_SMALL))
    else:
        # 本工程 raw8 = (raw10 - S_blk + 2) >> 2，所以 8bit 域的黑场差 d_black(=before-after)
        # 等价于 10bit 基座要反向改 4*d_black。
        need8 = -d_black                 # after 相对 before 需要的 8bit 黑场变化量
        delta10 = d_black * 4.0          # 对应的 10bit 基座增量（符号相反）
        new_blk = CURRENT_BLK_LEVEL + delta10
        out.append("  要让 8bit 黑场%+.1f 码值，10bit 域 S_blk_level 需 %+.1f -> %s"
                   % (need8, delta10, fmt(new_blk, 0)))
        if new_blk < 0:
            out.append("  -> ★ S_blk_level 会变成 %s（< 0，物理上不可实现）⇒ 这部分黑场差【不可能】"
                       "靠黑电平实现。" % fmt(new_blk, 0))
            out.append("     它更像是 after 做了「暗部抬升 / 加曲线」：请改走第 2 节的 gamma 或"
                       "第 6 节的线性映射 out = a*in + b（b 项即黑场平移量），而不是动黑电平。")
        elif new_blk > 200:
            out.append("  -> ★ S_blk_level 会变成 %s（过大）：剩余信号 (1023 - %s) 太窄，"
                       "暗部会被大片钳成 0，不建议这样改。" % (fmt(new_blk, 0), fmt(new_blk, 0)))
        else:
            out.append("  -> 即 mipi_to_raw_converter.v 里 S_blk_level: %d -> %s"
                       % (CURRENT_BLK_LEVEL, fmt(new_blk, 0)))
            out.append("     约束：(1023 - S_blk) + 2 < 1024（即 S_blk >= 2）；改完请重测黑帧，"
                       "确认低码值没有被钳成 0。")

    # ---- (2) Gamma / 中间调 ---------------------------------------------------
    out.append("")
    out.append("【2. Gamma / 中间调（Tone Curve）】")
    xs, ys = [], []
    for q in (5, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95):
        x = float(np.percentile(_gray_of(before_bgr), q))
        y = float(np.percentile(_gray_of(after_bgr), q))
        xs.append(x)
        ys.append(y)
    xs = np.array(xs, dtype=np.float64) / 255.0
    ys = np.array(ys, dtype=np.float64) / 255.0
    mask = (xs > 0.01) & (ys > 0.01)
    if mask.sum() >= 4:
        # 在 log-log 空间最小二乘拟合 y = x^g，等价于对每个分位点求 g 后取加权平均
        lx = np.log(xs[mask])
        ly = np.log(ys[mask])
        g = float((lx * ly).sum() / max((lx * lx).sum(), 1e-9))
        out.append("  按 11 个分位点(x=before 灰度, y=after 灰度)在 log-log 空间拟合 y = x^gamma：")
        out.append("     等效 gamma = %s" % fmt(g, 3))
        if abs(g - 1.0) < 0.03:
            out.append("  -> 曲线基本是线性的，不需要加 gamma LUT（差异主要来自增益/黑电平）。")
        else:
            direction = "提亮中间调" if g < 1.0 else "压暗中间调"
            out.append("  -> 需要 %s：按 out = 255*(in/255)^%s 实现（%s）"
                       % (direction, fmt(g, 3), "gamma<1 提亮" if g < 1.0 else "gamma>1 压暗"))
            for code in (32, 64, 96, 128, 160, 192, 224):
                v = 255.0 * (code / 255.0) ** g
                out.append("       LUT[%3d] = %3d" % (code, int(round(min(255.0, max(0.0, v))))))
    else:
        out.append("  分位点样本不足，无法可靠拟合 gamma。")

    mid_b, mid_a = tb["mid_mean"], ta["mid_mean"]
    out.append("  中间调均值：before=%s -> after=%s（目标中性灰约 %s）"
               % (fmt(mid_b, 1), fmt(mid_a, 1), fmt(TARGET_MIDTONE, 0)))
    if abs(mid_b - TARGET_MIDTONE) > 6:
        # 近似线性关系：需要的亮度增益 ~= 目标/当前（非线性曲线下只作迭代起点）
        need = TARGET_MIDTONE / max(mid_b, 1e-6)
        out.append("  -> before 中间调偏离目标，若要以「标准曝光」为准，亮度需 x%s（或反向 x%s）"
                   % (fmt(need, 3), fmt(1.0 / need, 3)))

    # ---- (3) 曝光 vs 增益 的判别 ---------------------------------------------
    out.append("")
    out.append("【3. 该加曝光还是该加增益（AE/AGC 方向判别）】")
    out.append("  有效信号比 (after 的 P99-P1)/(before 的 P99-P1) = %s" % fmt(sig_ratio, 3))
    out.append("  黑场变化 = %s 码值；白场变化 = %s 码值" % (fmt(d_black, 1), fmt(d_white, 1)))
    if abs(d_black) < TH_SMALL and abs(sig_ratio - 1.0) > 0.03:
        out.append("  -> 黑场几乎不动、信号按比例变化 => 这是【曝光/积分时间】的作用，"
                   "应改 3e00/3e01/3e02（曝光）而不是增益。")
        exp_now = 1990
        exp_new = int(round(exp_now * sig_ratio))
        out.append("     当前曝光 1990（=手册最大 2*VTS-10，已顶满）=> 目标 %d" % exp_new)
        if exp_new > 1990:
            out.append("     ★ 曝光已到手册上限 1990，无法再加：只能加增益或提高帧长(VTS)/降帧率。")
    elif abs(d_black) >= TH_SMALL and abs(sig_ratio - 1.0) <= 0.05:
        out.append("  -> 信号幅度基本不变而黑场整体平移 => 这属于【偏置/暗部曲线】类改动，"
                   "既不是曝光也不是增益。实现方式二选一：")
        out.append("     (a) 改 S_blk_level —— 仅当第 1 节算出的新值落在 2..200 的有效区间内；")
        out.append("     (b) 在 my_algo 的像素级流程里加线性映射 out = a*in + b（见第 6 节），"
                   "b 项就是这里的黑场平移量（暗部抬升通常只能这样实现）。")
    elif abs(sig_ratio - 1.0) > 0.03 and abs(d_black) > TH_SMALL:
        out.append("  -> 黑场与信号同时按比例变化 => 这是【模拟增益】的作用（增益会把黑电平一起放大）。")
    else:
        out.append("  -> 两者变化都在噪声级，无需调整曝光/增益。")

    # ---- (4) 增益换算成 SC500 寄存器 ----------------------------------------
    out.append("")
    out.append("【4. 增益寄存器换算（SC500CS）】")
    if sig_ratio > 1.001:
        regs = gain_to_sc500_regs(CURRENT_SC500_GAIN * sig_ratio)
        out.append("  若用增益实现同样的亮度提升：%s x %s = %s 倍"
                   % (fmt(CURRENT_SC500_GAIN, 3), fmt(sig_ratio, 3), fmt(CURRENT_SC500_GAIN * sig_ratio, 3)))
        if regs is None:
            out.append("  换算失败（输入异常）。")
        elif regs.get("overflow"):
            out.append("  -> 超出模拟增益上限 %s 倍，必须先加曝光或降帧率/提高 VTS。" % fmt(SC500_GAIN_MAX, 3))
        elif regs.get("underflow"):
            out.append("  -> 低于最小模拟增益 1.000 倍，请改用减小曝光或数字增益。")
        else:
            out.append("  -> 最接近的寄存器组合：{3e08, 8'h%02X}, {3e09, 8'h%02X} = %s 倍（误差 %s%%）"
                       % (regs["coarse"], regs["fine"], fmt(regs["actual"], 3), fmt(regs["err"] * 100, 2)))
            out.append("     本工程当前为 {3e08, 8'h%02X}, {3e09, 8'h%02X} = %s 倍"
                       % (CURRENT_SC500_GAIN_REG[0], CURRENT_SC500_GAIN_REG[1], fmt(CURRENT_SC500_GAIN, 3)))
    else:
        out.append("  不需要提高增益（信号比 %s，未见变亮需求）。" % fmt(sig_ratio, 3))

    # ---- (5) 白平衡 ----------------------------------------------------------
    out.append("")
    out.append("【5. 白平衡（AWB）】")
    cb = analyze_color(before_bgr, bb)
    ca = analyze_color(after_bgr, ba)
    out.append("  灰世界增益估计：before  R/G/B = %s / %s / %s"
               % (fmt(cb["gw_gain_r"], 3), fmt(cb["gw_gain_g"], 3), fmt(cb["gw_gain_b"], 3)))
    out.append("                    after   R/G/B = %s / %s / %s"
               % (fmt(ca["gw_gain_r"], 3), fmt(ca["gw_gain_g"], 3), fmt(ca["gw_gain_b"], 3)))
    out.append("  Lab 偏色：before Δa*=%s Δb*=%s (%s)；after Δa*=%s Δb*=%s (%s)"
               % (fmt(cb["da"], 2), fmt(cb["db"], 2), cb["bias_dir"],
                  fmt(ca["da"], 2), fmt(ca["db"], 2), ca["bias_dir"]))
    wb_r, wb_b = dstat["wb_rgb_ratio"]
    out.append("  相对绿通道的通道比变化：R/G x%s，B/G x%s（=1 表示只变亮度不变色）"
               % (fmt(wb_r, 3), fmt(wb_b, 3)))
    # 目标(after)自身的 WB 需求（相对绿通道），以及本次调整带来的纯色偏变化
    ta_r = ca["gw_gain_r"] / max(ca["gw_gain_g"], 1e-6)
    ta_b = ca["gw_gain_b"] / max(ca["gw_gain_g"], 1e-6)
    gmax = max(ca["gw_gain_r"], ca["gw_gain_g"], ca["gw_gain_b"])
    out.append("  -> 目标(after)自身需要的灰世界 AWB 增益（相对绿通道）：R x%s, B x%s"
               % (fmt(ta_r, 3), fmt(ta_b, 3)))
    if gmax > 4.0:
        out.append("     ★ 其中某通道的绝对增益已达 x%s，超过建议上限 4.0x：应检查光源/黑电平，"
                   "否则 AWB 会把噪声一起放大。" % fmt(gmax, 2))
    out.append("     复现 after 需要的纯色偏变化（相对绿）：R/G x%s，B/G x%s ⇒ 在现有 AWB 基础上"
               "把 R 通道再乘 %s、B 通道再乘 %s"
               % (fmt(wb_r, 3), fmt(wb_b, 3), fmt(wb_r, 3), fmt(wb_b, 3)))

    # ---- (6) 饱和度 / 对比度 -------------------------------------------------
    out.append("")
    out.append("【6. 饱和度与对比度】")
    out.append("  饱和度(HSV S 均值)：before=%s -> after=%s，比 x%s"
               % (fmt(bb["s_mean"], 2), fmt(ba["s_mean"], 2), fmt(dstat["s_ratio"], 3)))
    out.append("  彩度(max-min 均值)：比 x%s" % fmt(dstat["chroma_ratio"], 3))
    out.append("  灰色像素占比(HSV S<10)：before=%.2f%% -> after=%.2f%%"
               % (cb["grayish_frac"] * 100.0, ca["grayish_frac"] * 100.0))
    if abs(dstat["s_ratio"] - 1.0) > 0.03:
        out.append("  -> 饱和度乘数 k = %s：建议在 ISP 里做 S' = clamp(128 + (S-128)*k) 或 UV 增益 x%s"
                   % (fmt(dstat["s_ratio"], 3), fmt(dstat["s_ratio"], 3)))
    else:
        out.append("  -> 饱和度无需调整（变化 < 3%%）。")
    out.append("  RMS 对比度(灰度标准差)：before=%s -> after=%s，比 x%s"
               % (fmt(tb["rms_contrast"], 2), fmt(ta["rms_contrast"], 2), fmt(dstat["std_ratio"], 3)))
    out.append("  局部对比度(梯度均值)：before=%s -> after=%s，比 x%s"
               % (fmt(tb["grad_mean"], 2), fmt(ta["grad_mean"], 2),
                  fmt(ta["grad_mean"] / max(tb["grad_mean"], 1e-6), 3)))
    # 用 before 的黑/白场去对齐 after 的黑/白场 => 线性拉伸 out = a*in + b
    a = (ta["white"] - ta["black"]) / max(tb["white"] - tb["black"], 1e-6)
    bo = ta["black"] - a * tb["black"]
    if abs(a - 1.0) > 0.02 or abs(bo) > 2.0:
        out.append("  -> 影调线性映射：out = %s * in + %s（即把 P1/P99 从 %s/%s 拉到 %s/%s）"
                   % (fmt(a, 4), fmt(bo, 2), fmt(tb["black"], 0), fmt(tb["white"], 0),
                      fmt(ta["black"], 0), fmt(ta["white"], 0)))
        out.append("     若要做逐帧自动拉伸：在统计模块里求本帧 P1/P99 -> 目标 P1/P99，"
                   "按上式算 a/b 后对像素做 clamp。")
    else:
        out.append("  -> 影调范围基本一致，无需线性拉伸。")

    # ---- (7) 量化/断阶与链路健康度 -------------------------------------------
    out.append("")
    out.append("【7. 链路健康度提示（8bit 量化/断阶/截断）】")
    out.append("  before：纯黑占比 %.2f%%，纯白(255)占比 %.2f%%，P1..P99 内灰度级数 %d，熵 %s bit"
               % (_zero_frac_hack(before_bgr) * 100.0, _full_frac_hack(before_bgr) * 100.0,
                  tb["used_levels"], fmt(_entropy_hack(before_bgr), 3)))
    out.append("  after ：纯黑占比 %.2f%%，纯白(255)占比 %.2f%%，P1..P99 内灰度级数 %d，熵 %s bit"
               % (_zero_frac_hack(after_bgr) * 100.0, _full_frac_hack(after_bgr) * 100.0,
                  ta["used_levels"], fmt(_entropy_hack(after_bgr), 3)))
    if tb["used_levels"] < MIN_DISTINCT_LEVELS:
        out.append("  -> ★ before 的可用灰度级数只有 %d 级（< %d）：说明已经出现明显量化台阶。"
                   "常见原因：8bit 链路 + 黑电平扣除 + 增益过大（放大后台阶被拉开）、"
                   "或中间某级做了过多整数运算/右移。建议检查 f_luma / 增益链路的位宽。"
                   % (tb["used_levels"], MIN_DISTINCT_LEVELS))
    if _full_frac_hack(before_bgr) > 0.02:
        out.append("  -> ★ before 有 %.2f%% 的像素顶在 255：高光已截断，"
                   "应降低增益/曝光或加高光压缩。" % (_full_frac_hack(before_bgr) * 100.0))
    if _zero_frac_hack(before_bgr) > 0.10:
        out.append("  -> ★ before 有 %.2f%% 的像素为 0：暗部可能被黑电平扣除钳死，"
                   "建议减小 S_blk_level 或改用带符号的减法。" % (_zero_frac_hack(before_bgr) * 100.0))

    # ---- (8) 差异总览 --------------------------------------------------------
    out.append("")
    out.append("【8. 差异总览】")
    out.append("  平均绝对差(灰度)=%s，RMS=%s，最大=%s；PSNR=%s dB"
               % (fmt(dstat["mae_gray"], 2), fmt(dstat["rms_diff"], 2),
                  dstat["max_abs_diff"], fmt(dstat["psnr"], 2)))
    out.append("  差异>2 的像素 %.2f%%，>8 的 %.2f%%，>32 的 %.2f%%"
               % (dstat["frac_gt2"] * 100, dstat["frac_gt8"] * 100, dstat["frac_gt32"] * 100))
    out.append("  各通道增益比 R/G/B = %s / %s / %s；均值差 = %+.1f / %+.1f / %+.1f"
               % (fmt(dstat["r_ratio"], 3), fmt(dstat["g_ratio"], 3), fmt(dstat["b_ratio"], 3),
                  dstat["dmean_r"], dstat["dmean_g"], dstat["dmean_b"]))
    return out


# --- 给 suggest_params 用的小工具（避免重复计算整图统计） ----------------------
def _gray_of(bgr):
    return to_gray(bgr)

def _zero_frac_hack(bgr):
    return float((to_gray(bgr) == 0).mean())

def _full_frac_hack(bgr):
    return float((to_gray(bgr) == 255).mean())

def _entropy_hack(bgr):
    return entropy_bits(to_gray(bgr))


# =============================================================================
# 4. 报告文本
# =============================================================================

def hist32_lines(name: str, h32: np.ndarray, total: int) -> list:
    """把 32 bin 直方图排成 4 列一行的紧凑表格。"""
    lines = []
    lines.append("  %s（32 bin，每 bin 宽 8 码值；括号内为占比%%）" % name)
    cells = []
    for i, c in enumerate(h32):
        cells.append("[%3d-%3d] %8d (%5.2f%%)" % (i * 8, i * 8 + 7, c, 100.0 * c / max(total, 1)))
    for i in range(0, 32, 2):
        lines.append("    " + "   ".join(cells[i:i + 2]))
    return lines


def build_report(path_before, path_after, before, after, hist_b, hist_a, basic_b, basic_a,
                 tone_b, tone_a, color_b, color_a, dstat, amp) -> str:
    """拼出完整报告文本（6 大节）。"""
    L = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def head(title):
        L.append("")
        L.append("=" * 78)
        L.append(title)
        L.append("=" * 78)

    head("FPGA 图像对比分析报告（before = FPGA 当前输出 / after = LR 调整后目标）")
    L.append("  生成时间    : %s" % now)
    L.append("  before 文件 : %s" % path_before)
    L.append("  after  文件 : %s" % path_after)
    L.append("  before 尺寸 : %dx%d" % (before.shape[1], before.shape[0]))
    L.append("  after  尺寸 : %dx%d" % (after.shape[1], after.shape[0]))
    if not dstat["same_size"]:
        L.append("  ★ 警告：两图尺寸不同，after 已用 INTER_AREA 缩放到 before 的尺寸后再比较；")
        L.append("     缩放本身会引入额外模糊，差异分析的可信度下降。")
    L.append("  差异放大倍数: x%d（diff.png 中使用）" % amp)
    L.append("  灰度口径    : Rec.601 (0.299R+0.587G+0.114B)；注意本工程 my_algo.v 的 f_luma")
    L.append("                使用自定义权重，数值会有系统性差异。")

    # ---------------- 1. 基础统计 ----------------
    head("1. 基础统计")
    L.append("  指标                 before            after            变化")
    L.append("  " + "-" * 74)
    rows = [
        ("R 均值", "r_mean", 2), ("G 均值", "g_mean", 2), ("B 均值", "b_mean", 2),
        ("R 标准差", "r_std", 2), ("G 标准差", "g_std", 2), ("B 标准差", "b_std", 2),
        ("RGB 总均值", "rgb_mean_all", 2), ("RGB 总标准差", "rgb_std_all", 2),
        ("灰度均值", "gray_mean", 2), ("灰度标准差", "gray_std", 2),
        ("HSV S 均值", "s_mean", 2), ("HSV V 均值", "v_mean", 2),
    ]
    for label, key, nd in rows:
        vb, va = basic_b[key], basic_a[key]
        L.append("  %-16s %-16s %-16s %+.2f" % (label, fmt(vb, nd), fmt(va, nd), va - vb))
    L.append("  %-16s %-16s %-16s %+.2f"
             % ("色相(H)算术均值", fmt(basic_b["h_mean_arith"], 2), fmt(basic_a["h_mean_arith"], 2),
                basic_a["h_mean_arith"] - basic_b["h_mean_arith"]))
    L.append("  %-16s %-16s %-16s %+.2f"
             % ("色相(H)圆均值(度)", fmt(basic_b["h_circ_deg"], 1), fmt(basic_a["h_circ_deg"], 1),
                basic_a["h_circ_deg"] - basic_b["h_circ_deg"]))
    L.append("    （圆均值合成向量长度 before=%s / after=%s；越接近 0 说明色相越分散，"
             "均值参考价值越低）" % (fmt(basic_b["h_circ_r"], 3), fmt(basic_a["h_circ_r"], 3)))

    # ---------------- 2. 直方图 ----------------
    head("2. 直方图特征")
    L += hist32_lines("before 灰度", hist_b["gray32"], hist_b["hist_total"])
    L += hist32_lines("after  灰度", hist_a["gray32"], hist_a["hist_total"])
    L.append("")
    for ch, kb, ka in (("R", "r32", "r32"), ("G", "g32", "g32"), ("B", "b32", "b32")):
        L += hist32_lines("before %s 通道" % ch, hist_b[kb], hist_b["hist_total"])
    for ch, kb, ka in (("R", "r32", "r32"), ("G", "g32", "g32"), ("B", "b32", "b32")):
        L += hist32_lines("after  %s 通道" % ch, hist_a[ka], hist_a["hist_total"])
    L.append("")
    L.append("  分位数（码值 0..255）")
    L.append("  %-10s %8s %8s %8s %8s %8s" % ("通道", "P1", "P5", "P50", "P95", "P99"))
    L.append("  " + "-" * 58)
    for label, key in (("before 灰度", "pct_gray"), ("after  灰度", "pct_gray")):
        hb = hist_b if label.startswith("before") else hist_a
        p = hb[key]
        L.append("  %-10s %8.1f %8.1f %8.1f %8.1f %8.1f"
                 % (label, p[1], p[5], p[50], p[95], p[99]))
    for ch in ("r", "g", "b"):
        pb = hist_b["pct_" + ch]
        pa = hist_a["pct_" + ch]
        L.append("  %-10s %8.1f %8.1f %8.1f %8.1f %8.1f"
                 % ("before " + ch.upper(), pb[1], pb[5], pb[50], pb[95], pb[99]))
        L.append("  %-10s %8.1f %8.1f %8.1f %8.1f %8.1f"
                 % ("after  " + ch.upper(), pa[1], pa[5], pa[50], pa[95], pa[99]))
    L.append("")
    L.append("  灰度熵 / 纯黑占比 / 纯白占比：before %s bit / %.2f%% / %.2f%%    after %s bit / %.2f%% / %.2f%%"
             % (fmt(hist_b["entropy"], 3), hist_b["zero_frac"] * 100, hist_b["full_frac"] * 100,
                fmt(hist_a["entropy"], 3), hist_a["zero_frac"] * 100, hist_a["full_frac"] * 100))

    # ---------------- 3. 影调 ----------------
    head("3. 影调特征")
    L.append("  指标                 before            after            变化")
    L.append("  " + "-" * 74)
    tone_rows = [
        ("黑场 P1", "black", 1), ("白场 P99", "white", 1),
        ("最小值", "min", 0), ("最大值", "max", 0),
        ("动态范围 P99-P1", "dr_p", 1), ("动态范围 max-min", "dr_full", 0),
        ("中间调均值", "mid_mean", 2),
        ("RMS 对比度(σ)", "rms_contrast", 3),
        ("Michelson 对比度", "michelson", 4),
        ("局部对比度(梯度)", "grad_mean", 3),
        ("P1..P99 灰度级数", "used_levels", 0),
    ]
    for label, key, nd in tone_rows:
        vb, va = tone_b[key], tone_a[key]
        L.append("  %-16s %-16s %-16s %+.3f" % (label, fmt(vb, nd), fmt(va, nd), va - vb))
    L.append("  中间调定义：灰度位于 P10..P90 之间的像素（before 区间 %s..%s，占 %s%%）"
             % (fmt(tone_b["mid_lo"], 0), fmt(tone_b["mid_hi"], 0), fmt(tone_b["mid_frac"] * 100, 1)))
    L.append("  断阶判据：P1..P99 内实际出现过的灰度级数，少于 %d 视为有明显台阶。" % MIN_DISTINCT_LEVELS)

    # ---------------- 4. 色彩 ----------------
    head("4. 色彩特征")
    L.append("  指标                       before            after")
    L.append("  " + "-" * 60)
    L.append("  灰世界增益 R              %-16s %-16s" % (fmt(color_b["gw_gain_r"], 3), fmt(color_a["gw_gain_r"], 3)))
    L.append("  灰世界增益 G              %-16s %-16s" % (fmt(color_b["gw_gain_g"], 3), fmt(color_a["gw_gain_g"], 3)))
    L.append("  灰世界增益 B              %-16s %-16s" % (fmt(color_b["gw_gain_b"], 3), fmt(color_a["gw_gain_b"], 3)))
    L.append("  白点(P99) R/G/B           %s/%s/%s   %s/%s/%s"
             % (fmt(color_b["wp_r"], 0), fmt(color_b["wp_g"], 0), fmt(color_b["wp_b"], 0),
                fmt(color_a["wp_r"], 0), fmt(color_a["wp_g"], 0), fmt(color_a["wp_b"], 0)))
    L.append("  Lab Δa* / Δb*             %s / %s        %s / %s"
             % (fmt(color_b["da"], 2), fmt(color_b["db"], 2), fmt(color_a["da"], 2), fmt(color_a["db"], 2)))
    L.append("  偏色方向                  %-16s %-16s" % (color_b["bias_dir"], color_a["bias_dir"]))
    L.append("  偏色角(度,0=红,90=黄)     %-16s %-16s"
             % (fmt(color_b["bias_angle"], 1), fmt(color_a["bias_angle"], 1)))
    L.append("  HSV S 均值                %-16s %-16s" % (fmt(color_b["s_mean"], 2), fmt(color_a["s_mean"], 2)))
    L.append("  彩度(max-min)均值         %-16s %-16s" % (fmt(color_b["chroma_mean"], 2), fmt(color_a["chroma_mean"], 2)))
    L.append("  灰色像素占比(S<10)        %-16s %-16s"
             % (fmt(color_b["grayish_frac"] * 100, 2) + "%", fmt(color_a["grayish_frac"] * 100, 2) + "%"))
    L.append("  R/B 均值比(色温趋势)      %-16s %-16s"
             % (fmt(color_b["rb_ratio"], 3), fmt(color_a["rb_ratio"], 3)))
    L.append("  说明：灰世界增益 = 灰度均值/该通道均值，=1 表示该通道已平衡；")
    L.append("        Δa*>0 偏红、Δa*<0 偏绿；Δb*>0 偏黄、Δb*<0 偏蓝。")

    # ---------------- 5. 差异分析 ----------------
    head("5. 差异分析（逐像素 after - before）")
    L.append("  平均绝对差 MAE(灰度)      %s" % fmt(dstat["mae_gray"], 3))
    L.append("  平均绝对差 MAE(R/G/B)     %s / %s / %s"
             % (fmt(dstat["mae_r"], 3), fmt(dstat["mae_g"], 3), fmt(dstat["mae_b"], 3)))
    L.append("  均方根差 RMS(灰度)        %s" % fmt(dstat["rms_diff"], 3))
    L.append("  最大绝对差                %d 码值" % dstat["max_abs_diff"])
    L.append("  PSNR(RGB)                 %s dB" % fmt(dstat["psnr"], 2))
    L.append("  差异像素占比  >2 : %.2f%%    >8 : %.2f%%    >32 : %.2f%%"
             % (dstat["frac_gt2"] * 100, dstat["frac_gt8"] * 100, dstat["frac_gt32"] * 100))
    L.append("  通道均值差  ΔR=%+.2f  ΔG=%+.2f  ΔB=%+.2f"
             % (dstat["dmean_r"], dstat["dmean_g"], dstat["dmean_b"]))
    L.append("  各通道增益比 R/G/B = %s / %s / %s"
             % (fmt(dstat["r_ratio"], 4), fmt(dstat["g_ratio"], 4), fmt(dstat["b_ratio"], 4)))
    L.append("  相对绿通道的通道比变化 R/G x%s，B/G x%s"
             % (fmt(dstat["wb_rgb_ratio"][0], 4), fmt(dstat["wb_rgb_ratio"][1], 4)))
    L.append("")
    L.append("  变化方向判定：")
    L.append("    亮度   : %s（灰度均值 %+.2f，x%s）"
             % (_dir_word(dstat["gray_ratio"]), dstat["dgray_mean"], fmt(dstat["gray_ratio"], 3)))
    L.append("    对比度 : %s（σ 比 x%s）" % (_dir_word(dstat["std_ratio"]), fmt(dstat["std_ratio"], 3)))
    L.append("    饱和度 : %s（S 比 x%s，彩度比 x%s）"
             % (_dir_word(dstat["s_ratio"]), fmt(dstat["s_ratio"], 3), fmt(dstat["chroma_ratio"], 3)))
    L.append("    色偏   : %s（R/G x%s, B/G x%s）"
             % (_wb_word(dstat["wb_rgb_ratio"][0], dstat["wb_rgb_ratio"][1]),
                fmt(dstat["wb_rgb_ratio"][0], 3), fmt(dstat["wb_rgb_ratio"][1], 3)))

    # ---------------- 6. 反推参数建议 ----------------
    head("6. 反推参数建议（给 Agent：如何让 FPGA 从 before 逼近 after）")
    L.append("  以下每一条都是「测量值 -> 公式 -> 目标常数/寄存器」的推导；")
    L.append("  本工程链路假设：RAW10 -(减 S_blk_level, >>2)-> RAW8 -> demosaic -> AWB -> my_algo -> HDMI。")
    L += suggest_params(before, after, dstat)

    head("附：本次实际使用的参考常数")
    L.append("  当前模拟增益寄存器   : {3e08,8'h%02X}, {3e09,8'h%02X} = %s 倍（上限 %s 倍）"
             % (CURRENT_SC500_GAIN_REG[0], CURRENT_SC500_GAIN_REG[1],
                fmt(CURRENT_SC500_GAIN, 3), fmt(SC500_GAIN_MAX, 3)))
    L.append("  当前黑电平基座       : S_blk_level = %d（10bit 域；raw10->raw8 为 (raw10-S_blk)>>2）"
             % CURRENT_BLK_LEVEL)
    L.append("  曝光寄存器           : {3e00,3e01,3e02} 当前 0x07C6 = 1990（手册最大 = 2*VTS-10）")
    L.append("  输出文件             : report.txt / diff.png / histogram.png（与 after 同目录或 -o 指定目录）")
    L.append("")
    return "\n".join(L)


def _dir_word(ratio: float) -> str:
    if ratio > 1.02:
        return "增强/变亮 x%s" % fmt(ratio, 3)
    if ratio < 0.98:
        return "减弱/变暗 x%s" % fmt(ratio, 3)
    return "基本不变 x%s" % fmt(ratio, 3)


def _wb_word(rg: float, bg: float) -> str:
    if abs(rg - 1) < 0.02 and abs(bg - 1) < 0.02:
        return "基本不变"
    parts = []
    if rg > 1.02:
        parts.append("更偏红/更暖")
    elif rg < 0.98:
        parts.append("更偏青（红减）")
    if bg > 1.02:
        parts.append("更偏蓝/更冷")
    elif bg < 0.98:
        parts.append("更偏黄（蓝减）")
    return "、".join(parts) if parts else "基本不变"


# =============================================================================
# 5. 出图
# =============================================================================

def plot_diff(before, after, dg, out_path, amp, cjk_name):
    """diff.png：原图 / 目标图 / 绝对差放大 / 有符号差热力图。"""
    fig, axes = plt.subplots(2, 2, figsize=(12, 8.5))
    ax = axes.ravel()
    ax[0].imshow(cv2.cvtColor(before, cv2.COLOR_BGR2RGB)); ax[0].set_title("before (FPGA 当前输出)")
    ax[1].imshow(cv2.cvtColor(after, cv2.COLOR_BGR2RGB));  ax[1].set_title("after (LR 调整后 / 目标)")
    # 绝对差放大：|after-before| * amp，便于肉眼看清哪里被改了
    absd = np.clip(np.abs(dg.astype(np.float32)) * amp, 0, 255).astype(np.uint8)
    ax[2].imshow(absd, cmap="gray", vmin=0, vmax=255)
    ax[2].set_title("|diff| x%d（越白改动越大）" % amp)
    # 有符号差热力图：seismic 以 0 为中心，蓝=变暗、红=变亮
    im = ax[3].imshow(dg, cmap="seismic", vmin=-32, vmax=32)
    ax[3].set_title("signed diff（红=变亮, 蓝=变暗, 范围 +/-32）")
    fig.colorbar(im, ax=ax[3], fraction=0.046, pad=0.04)
    for a in ax:
        a.set_xticks([]); a.set_yticks([])
    fig.suptitle("差异图（灰度域，放大 x%d）" % amp, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


def plot_hist(before, after, hist_b, hist_a, basic_b, basic_a, dg, out_path):
    """histogram.png：灰度直方图 / RGB 32bin / CDF / 通道均值 / HSV 对比 / 差值分布。"""
    fig, axes = plt.subplots(2, 3, figsize=(16, 8.5))
    ax = axes.ravel()

    # (1) 灰度 256bin 直方图（用对数纵轴，暗部小峰也看得见）
    x = np.arange(256)
    ax[0].plot(x, hist_b["gray256"], label="before", color="tab:blue", lw=1.2)
    ax[0].plot(x, hist_a["gray256"], label="after", color="tab:red", lw=1.2, alpha=0.85)
    ax[0].set_yscale("log")
    ax[0].set_title("灰度直方图（256 bin，纵轴对数）")
    ax[0].set_xlabel("码值"); ax[0].set_ylabel("像素数(log)"); ax[0].legend()

    # (2) RGB 各 32bin 分组柱状对比
    w = 0.2
    idx = np.arange(32)
    ax[1].bar(idx - 1.5 * w, hist_b["r32"], width=w, label="before R", color="r", alpha=0.75)
    ax[1].bar(idx - 0.5 * w, hist_b["g32"], width=w, label="before G", color="g", alpha=0.75)
    ax[1].bar(idx + 0.5 * w, hist_b["b32"], width=w, label="before B", color="b", alpha=0.75)
    ax[1].bar(idx + 1.5 * w, hist_a["g32"], width=w, label="after G", color="k", alpha=0.45)
    ax[1].set_title("RGB 32 bin（黑=after G 作对照）")
    ax[1].set_xlabel("bin 序号(每格 8 码值)"); ax[1].legend(fontsize=8)

    # (3) 灰度 CDF
    cb_ = np.cumsum(hist_b["gray256"]) / max(hist_b["gray256"].sum(), 1)
    ca_ = np.cumsum(hist_a["gray256"]) / max(hist_a["gray256"].sum(), 1)
    ax[2].plot(x, cb_, label="before", color="tab:blue")
    ax[2].plot(x, ca_, label="after", color="tab:red")
    ax[2].grid(alpha=0.3)
    ax[2].set_title("灰度累计分布 CDF（抖得更陡=对比度更高）")
    ax[2].set_xlabel("码值"); ax[2].set_ylabel("累计占比"); ax[2].legend()

    # (4) 通道均值柱状 + 白平衡增益标注
    labels = ["R", "G", "B"]
    mb = [basic_b["r_mean"], basic_b["g_mean"], basic_b["b_mean"]]
    ma = [basic_a["r_mean"], basic_a["g_mean"], basic_a["b_mean"]]
    p1 = np.arange(3)
    ax[3].bar(p1 - 0.2, mb, width=0.4, label="before", color="tab:blue")
    ax[3].bar(p1 + 0.2, ma, width=0.4, label="after", color="tab:red")
    for i in range(3):
        ax[3].text(i - 0.2, mb[i] + 2, "%.1f" % mb[i], ha="center", fontsize=8)
        ax[3].text(i + 0.2, ma[i] + 2, "%.1f" % ma[i], ha="center", fontsize=8)
    ax[3].set_xticks(p1); ax[3].set_xticklabels(labels)
    ax[3].set_title("RGB 通道均值（通道间差异=白平衡）"); ax[3].legend()

    # (5) HSV 均值对比
    hsv_b = [basic_b["s_mean"], basic_b["v_mean"], basic_b["h_circ_deg"] * 255.0 / 360.0]
    hsv_a = [basic_a["s_mean"], basic_a["v_mean"], basic_a["h_circ_deg"] * 255.0 / 360.0]
    p2 = np.arange(3)
    ax[4].bar(p2 - 0.2, hsv_b, width=0.4, label="before", color="tab:blue")
    ax[4].bar(p2 + 0.2, hsv_a, width=0.4, label="after", color="tab:red")
    ax[4].set_xticks(p2); ax[4].set_xticklabels(["S", "V", "H(折算)"])
    ax[4].set_title("HSV 均值对比（H 折算到 0..255）"); ax[4].legend()

    # (6) 差值分布（灰度有符号差）
    ax[5].hist(dg.ravel(), bins=np.arange(-64, 65, 2), color="tab:purple", alpha=0.85)
    ax[5].axvline(0, color="k", lw=0.8)
    ax[5].set_yscale("log")
    ax[5].set_title("灰度差值分布 after-before（纵轴对数）")
    ax[5].set_xlabel("差值(码值)"); ax[5].set_ylabel("像素数(log)")

    fig.suptitle("直方图与统计对比", fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(out_path, dpi=110)
    plt.close(fig)


# =============================================================================
# 6. 主流程
# =============================================================================

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="FPGA 图像处理前后对比分析（before=FPGA 输出, after=LR 调整后目标）",
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("before", help="before.png（FPGA 当前输出）")
    ap.add_argument("after", help="after.png（LR 调整后 / 目标效果）")
    ap.add_argument("-o", "--outdir", default=None, help="输出目录（默认与 after 同目录）")
    ap.add_argument("--amp", type=float, default=4.0, help="diff.png 里绝对差的放大倍数（默认 4）")
    ap.add_argument("--tag", default="", help="额外的报告标签，例如 --tag 黑电平56")
    args = ap.parse_args(argv)

    cjk = setup_matplotlib_cjk()
    if not cjk:
        print("[警告] 未找到中文字体，图形上的中文可能显示为方框（报告文本不受影响）。")

    before = imread_bgr(args.before)
    after = imread_bgr(args.after)

    # 尺寸不一致：把 after 缩放到 before，并记录（报告里会警告）
    if before.shape != after.shape:
        after = cv2.resize(after, (before.shape[1], before.shape[0]), interpolation=cv2.INTER_AREA)
        print("[提示] after 尺寸与 before 不同，已按 INTER_AREA 缩放到 %dx%d"
              % (before.shape[1], before.shape[0]))

    outdir = args.outdir or os.path.dirname(os.path.abspath(args.after)) or "."
    os.makedirs(outdir, exist_ok=True)

    # ---- 逐项分析 ----
    basic_b, basic_a = analyze_basic(before), analyze_basic(after)
    hist_b, hist_a = analyze_hist(before), analyze_hist(after)
    tone_b = analyze_tone(before, hist_b)
    tone_a = analyze_tone(after, hist_a)
    color_b = analyze_color(before, basic_b)
    color_a = analyze_color(after, basic_a)
    dstat, dg = analyze_diff(before, after)
    # dstat 里已经缓存了 basic/tone，避免重复计算
    basic_b, basic_a = dstat["basic_before"], dstat["basic_after"]
    tone_b, tone_a = dstat["tone_before"], dstat["tone_after"]

    # ---- 报告 ----
    text = build_report(args.before, args.after, before, after, hist_b, hist_a,
                        basic_b, basic_a, tone_b, tone_a, color_b, color_a, dstat, args.amp)
    if args.tag:
        text = text.replace("FPGA 图像对比分析报告",
                            "FPGA 图像对比分析报告 [%s]" % args.tag, 1)
    safe_print(text)

    rpt = os.path.join(outdir, "report.txt")
    with open(rpt, "w", encoding="utf-8-sig") as f:      # BOM 便于 Windows 记事本
        f.write(text)

    # ---- 出图 ----
    diff_png = os.path.join(outdir, "diff.png")
    hist_png = os.path.join(outdir, "histogram.png")
    plot_diff(before, after, dg, diff_png, args.amp, cjk)
    plot_hist(before, after, hist_b, hist_a, basic_b, basic_a, dg, hist_png)

    print("")
    print("已输出：")
    print("  报告      : %s" % rpt)
    print("  差异图    : %s" % diff_png)
    print("  直方图    : %s" % hist_png)
    return 0


if __name__ == "__main__":
    sys.exit(main())
