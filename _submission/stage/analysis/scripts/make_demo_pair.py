#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""make_demo_pair.py —— 用工作区里的真实照片造一对 before/after，供 compare.py 演示。

为什么要造：
    用户要求的 compare.py 需要 before.png（FPGA 当前输出）与 after.png（LR 调整后）。
    但工程现在没有导出过 PNG（ChipWatcher 采的是 CSV，屏摄是手机 jpg），
    为了能给出「真实跑通的示例输出」，本脚本用工作区的真实照片
        E:\\FPGA\\captures\\2026-10-08_首轮\\mode0室内常光.jpg
    生成一对图：
        before.png = 照片原样（当作"FPGA 当前输出"）
        after.png  = 模拟一次 Lightroom 式调整（当作"期望效果"）
                    - 曝光 +0.15 EV（线性 x1.10）
                    - 暗部抬升：+6 码值（提高黑场，拉开暗部）
                    - gamma 0.92（提亮中间调）
                    - 白平衡微调：R x1.06、B x0.96（更暖）
                    - 饱和度 x1.25
    这样 compare.py 的 6 节报告与"反推参数建议"都能拿到有意义的非零数值。

注意：这一步生成的 after.png 只是**演示用**，不代表真实需要对 FPGA 做的改动。
真实使用时，请把 LR 导出的 after.png 与 FPGA 导出的 before.png 直接喂给 compare.py。

用法：
    python make_demo_pair.py [源图] [输出目录]
"""
import os
import sys

import numpy as np
from PIL import Image


def simulate_lr_adjust(bgr: np.ndarray) -> np.ndarray:
    """在 8bit 域模拟一次 LR 调整（顺序：白平衡 -> 曝光 -> 黑场抬升 -> gamma -> 饱和度）。"""
    x = bgr.astype(np.float32)

    # 1) 白平衡（更暖：R 提、B 压）
    x[:, :, 2] *= 1.06   # R（OpenCV/PIL 拼接顺序：BGR 里 index2 是 R）
    x[:, :, 0] *= 0.96   # B

    # 2) 曝光 +0.15 EV
    x *= 1.10

    # 3) 黑场抬升：暗部整体 +6，高光不动（用软过渡，避免硬拐点）
    x = x + 6.0 * np.clip(1.0 - x / 255.0, 0.0, 1.0)

    # 4) gamma 0.92（提亮中间调）：在 [0,255] 归一化后做幂运算
    x = np.clip(x, 0.0, 255.0) / 255.0
    x = np.power(x, 0.92) * 255.0

    # 5) 饱和度 x1.25（围绕亮度做缩放）
    gray = (0.299 * x[:, :, 2] + 0.587 * x[:, :, 1] + 0.114 * x[:, :, 0])[:, :, None]
    x = gray + (x - gray) * 1.25

    return np.clip(x, 0.0, 255.0).astype(np.uint8)


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else r"E:\FPGA\captures\2026-10-08_首轮\mode0室内常光.jpg"
    outdir = sys.argv[2] if len(sys.argv) > 2 else r"E:\FPGA\tools\compare\demo"
    os.makedirs(outdir, exist_ok=True)

    if not os.path.isfile(src):
        print("找不到源图：%s" % src)
        return 2

    im = Image.open(src).convert("RGB")
    # 手机照片 4000x3000 太大，缩到宽 1280 便于快速演示（compare.py 支持任意尺寸）
    if im.width > 1280:
        im = im.resize((1280, int(round(im.height * 1280.0 / im.width))), Image.LANCZOS)
    rgb = np.asarray(im)
    bgr = rgb[:, :, ::-1].copy()          # RGB -> BGR

    before_path = os.path.join(outdir, "before.png")
    after_path = os.path.join(outdir, "after.png")

    Image.fromarray(bgr[:, :, ::-1]).save(before_path)           # 原样
    Image.fromarray(simulate_lr_adjust(bgr)[:, :, ::-1]).save(after_path)  # 模拟 LR

    print("源图  : %s (%dx%d)" % (src, im.width, im.height))
    print("before: %s" % before_path)
    print("after : %s" % after_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
