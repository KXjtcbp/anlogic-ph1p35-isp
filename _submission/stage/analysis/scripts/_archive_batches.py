# -*- coding: utf-8 -*-
"""Archive the capture batches with meaningful names + READMEs.

  A) 2026-10-11 19:06 / 19:14  ->  captures\2026-10-11_链校准后\        (capture chain verified IDENTITY)
  B) 2026-10-11 17:00 / 17:02  ->  captures\2026-10-11_采集链未校准\    (taken before the OBS fix)
"""
import os
import shutil
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = r"E:\FPGA"
CAP = os.path.join(ROOT, "captures")

# ---------------------------------------------------------------- batch A
A_DIR = os.path.join(CAP, "2026-10-11_链校准后")
A_MAP = [
    ("Screenshot 2026-10-11 19-06-05.png", "00_开关未记录_链校准首张_室内常光.png"),
    ("Screenshot 2026-10-11 19-14-05.png", "01_开关未记录_浅色均匀面_CNT495303.png"),
    ("Screenshot 2026-10-11 19-14-12.png", "02_开关未记录_暗部_CNT495725.png"),
    ("Screenshot 2026-10-11 19-14-19.png", "03_开关未记录_室内常光_CNT496171.png"),
    ("Screenshot 2026-10-11 19-14-28.png", "04_开关未记录_直看光源_CNT496791.png"),
]

# ---------------------------------------------------------------- batch B
B_DIR = os.path.join(CAP, "2026-10-11_采集链未校准")
B_MAP = [
    ("Screenshot 2026-10-11 17-00-12.png", "01_MODE0_室内常光_CNT008467.png"),
    ("Screenshot 2026-10-11 17-00-21.png", "02_MODE0_室内常光_CNT009021.png"),
    ("Screenshot 2026-10-11 17-00-30.png", "03_MODE0_室内常光_CNT009582.png"),
    ("Screenshot 2026-10-11 17-00-42.png", "04_MODE0_室内常光_CNT010296.png"),
    ("Screenshot 2026-10-11 17-00-57.png", "05_MODE1_灰度_CNT011178.png"),
    ("Screenshot 2026-10-11 17-01-01.png", "06_MODE2_伪彩_CNT011460.png"),
    ("Screenshot 2026-10-11 17-01-05.png", "07_MODE4_卡通_CNT011682.png"),
    ("Screenshot 2026-10-11 17-01-45.png", "08_MODE0_近黑_CNT014088.png"),
    ("Screenshot 2026-10-11 17-01-49.png", "09_MODE0_均匀灰_CNT014370.png"),
    ("Screenshot 2026-10-11 17-01-58.png", "10_MODE0_全黑_CNT014872.png"),
    ("Screenshot 2026-10-11 17-02-02.png", "11_MODE0_极暗_CNT015157.png"),
    ("Screenshot 2026-10-11 17-02-07.png", "12_MODE1_灰度_CNT015449.png"),
    ("Screenshot 2026-10-11 17-02-14.png", "13_MODE2_伪彩_CNT015869.png"),
    ("Screenshot 2026-10-11 17-02-18.png", "14_MODE4_卡通_CNT016117.png"),
]

A_README = """# 2026-10-11 采集链校准后（★可信基线★）

**采于 OBS 色彩范围修复之后，采集链已验证为 identity。**

## 校准验证（脚本：`_analysis/scripts/_capture_chain_fit.py`、`_osd_reference.py`）

FPGA 里写死的常量 vs 截图实测，残差应 ≤ 3 码：

| 基准（源码常量） | 修复前 | 修复后 |
|---|---|---|
| Logo 主蓝底 `(28,45,78)`（`anlogic_logo_rom.v`） | `(14,33,67)` | **`(27,44,75)`** |
| Logo 红三角 `(237,28,36)` | `(251,16,24)` | **`(235,29,36)`** |
| OSD 帧计数黄字 `COLOR_DYN_TEXT=24'hfff200`（`hdmi_mixer.v:203`） | `(255,255,9)` | **`(252,243,0)`** |

最优模型 = `identity`（RMS 13.54），不再是 `limited->full`（RMS 19.68）。
R 通道最小二乘 `out = +0.9949*in - 0.857, R^2 = 1.00000`。

## 本目录

| 文件 | 场景 | 说明 |
|---|---|---|
| `00_...链校准首张` | 室内常光 | 修复后第一张，用来确认设置生效 |
| `01_...浅色均匀面` | 浅色墙面/纸面，Y≈118 | **★白平衡判据用图★**，见下 |
| `02_...暗部` | 暗色表面，Y≈17 | 低照度通道比 |
| `03_...室内常光` | 书架/桌面，Y≈52 | 与 17:00 机位接近 |
| `04_...直看光源` | 吸顶灯直射，Y≈153 | 高光削顶与去马赛克伪彩（灯周围绿青晕） |

## 实测数据

```
file              Ymean  Ystd  p50 |    R      G      B   R/G     B/G   | 中心区 R/G  B/G
00 链校准首张      52.83 26.00   43 |  ...                       0.9574 0.9466
01 浅色均匀面     118.02 17.82  119 | 116.74 119.78 116.63 0.9746 0.9737 | 0.9522 0.9648
02 暗部            16.72  4.24   17 |  14.45  18.92  15.75 0.7639 0.8324 | 0.7778 0.8326
03 室内常光        51.77 24.90   41 |  51.49  53.26  49.17 0.9669 0.9234 | 0.9400 0.8809
04 直看光源       152.62 66.67  140 | 156.62 150.67 156.28 1.0395 1.0372 | 1.0812 1.0886
```

## 未解决问题（重要）

**白平衡欠校正。** 01 号图是一个近乎均匀的浅色面**占满整个画面**——灰世界 AWB 的设计前提
就是"把整帧均值拉平成 R=G=B"，所以这种画面在 AWB 正常时输出必然是中性，与墙面真实颜色无关。
实测 `R/G = 0.952~0.975`、`B/G = 0.965~0.974`，说明 **AWB 只把传感器原生的 ~0.88 拉到 ~0.96，
没有拉到位**（ChipWatcher 实测 RAW10 原生 R/G=0.856~0.895）。

02 号图 `R/G=0.764` 偏得更多，但那是暗色表面，**不能排除是场景本身的颜色**，不作为 AWB 证据。

## 未记录项

**四张图的 SW1–SW4 拨码位置没有记录。** 这是刻意的：原始截图没有留下拨码证据，
事后不得推断补填。下次采集请把开关状态写进文件名。
"""

B_README = """# 2026-10-11 采集链未校准（⚠️ 颜色数据不可用）

**全部采于 OBS 色彩范围修复之前。** 采集链当时做的是 limited→full 展开
`out = clip((in-16) * 255/219)`，实测证据：

| 基准（FPGA 写死的常量） | 截图实测 | 残差 |
|---|---|---|
| Logo 主蓝底 `(28,45,78)` | `(14,33,67)` | `(-14,-12,-11)` |
| Logo 红三角 `(237,28,36)` | `(251,16,24)` | `(+14,-12,-12)` |
| OSD 黄字 `COLOR_DYN_TEXT=24'hfff200` | `(255,255,9)` | 精确命中 0 像素 |

## ⚠️ 使用限制

- **R/G、B/G 等颜色比值一律不可用。** 该展开每通道强制 −12 码偏置再乘 1.1644，
  在暗部会把偏色**放大**（两通道 20 vs 21 → 4.7 vs 5.8，比值从 0.952 掉到 0.800），
  所以"越暗越绿"有一部分是采集链自己造的。
- 唯一可用的是：**构图、亮度分布（Y 统计）、OSD 读数、MODE 行为**。
- 若要复用颜色结论，必须先套逆变换 `fpga = png/1.1644 + 16`，且只对中层亮度可信。

## 内容

两轮 K1–K4 的 MODE 扫描（用户现场按键）：

| 文件 | MODE | 内容 |
|---|---|---|
| 01–04 | 0 | 室内常光 ×4 |
| 05 | 1 | 灰度（BT.601）|
| 06 | 2 | 伪彩热力图 |
| 07 | 4 | 卡通化 |
| 08–11 | 0 | 近黑 / 均匀灰 / 全黑 / 极暗 |
| 12 | 1 | 灰度 |
| 13 | 2 | 伪彩 |
| 14 | 4 | 卡通化 |

CNT 从 008467 到 016117 单调递增、与墙钟逐段吻合 ⇒ **一次连续上电、无复位**。
"""


def do(dest_dir, readme, mapping, title):
    os.makedirs(dest_dir, exist_ok=True)
    print("=" * 96)
    print(title)
    print(dest_dir)
    moved = 0
    for src_name, dst_name in mapping:
        src = os.path.join(ROOT, src_name)
        dst = os.path.join(dest_dir, dst_name)
        if not os.path.exists(src):
            print("  MISSING  %s" % src_name)
            continue
        if os.path.exists(dst):
            print("  exists   %s" % dst_name)
            continue
        shutil.move(src, dst)
        print("  moved    %-40s -> %s" % (src_name, dst_name))
        moved += 1
    rp = os.path.join(dest_dir, "README.md")
    with open(rp, "w", encoding="utf-8") as f:
        f.write(readme)
    print("  README   %s" % rp)
    print("  moved %d file(s)" % moved)


do(A_DIR, A_README, A_MAP, "BATCH A - capture chain calibrated (trustworthy)")
do(B_DIR, B_README, B_MAP, "BATCH B - capture chain NOT calibrated (colour unusable)")

print()
print("remaining Screenshot*.png at %s :" % ROOT)
left = sorted(f for f in os.listdir(ROOT) if f.startswith("Screenshot") and f.lower().endswith(".png"))
for f in left:
    print("   ", f)
if not left:
    print("    (none - good)")
