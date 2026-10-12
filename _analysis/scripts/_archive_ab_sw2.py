# -*- coding: utf-8 -*-
"""归档 SW2 A/B 两张 + 写 README。"""
import os, shutil, hashlib, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

DST = r"E:\FPGA\captures\2026-10-11_S曲线AB验证"
os.makedirs(DST, exist_ok=True)

PAIRS = [
    (r"E:\FPGA\10_SW1上SW2下SW3上SW4上.png.png", "10_SW1上_SW2下_曲线旁路_CNT574558.png"),
    (r"E:\FPGA\11_SW1上SW2上SW3上SW4上.png.png", "11_SW1上_SW2上_曲线启用_CNT574725.png"),
]

for src, dst in PAIRS:
    if not os.path.exists(src):
        print("MISSING", src); continue
    if os.path.exists(os.path.join(DST, dst)):
        print("already there:", dst); continue
    shutil.move(src, os.path.join(DST, dst))
    h = hashlib.sha256(open(os.path.join(DST, dst), "rb").read()).hexdigest()[:16]
    print("moved -> %s  (%d B, sha256 %s)" % (dst, os.path.getsize(os.path.join(DST, dst)), h))

README = """# 2026-10-11 S 曲线 A/B 验证（SW2）

## 目的
验证 `isp_gamma.v` 里的 S 曲线（LUT `p160_a050`）到底有没有真正进入 ISP 通路。
此前 `p118_k125` -> `p160_a050` 换过两次曲线、两次重综合上板，画面看不出变化，
怀疑曲线被旁路。

## 开关状态（本批**有记录**，与前几批不同）

| 文件 | SW1 | SW2 | SW3 | SW4 | 含义 |
|---|---|---|---|---|---|
| `10_..._CNT574558.png` | 上 | **下** | 上 | 上 | 黑电平扣除开 / **曲线旁路** / 增益 31.500x |
| `11_..._CNT574725.png` | 上 | **上** | 上 | 上 | 黑电平扣除开 / **曲线启用** / 增益 31.500x |

- 拨码极性（实测）：**拨上 = 逻辑 0 = 启用**；拨下 = 逻辑 1 = 旁路。
- `design_top_wrapper.v:773` `wire S_gamma_bypass = S_sw2_sync1;`（1 = 直通）
  ⇒ **SW2 拨上 = 曲线启用**。
- 两张之间只拨了 SW2，机位/朝向/光照未动。

## 采集一致性
- CNT 574558 -> 574725，差 **167 帧 = 2.78 s**，与墙钟 19:35:53 -> 19:35:56 = 3 s 吻合。
- 同一批 MODE 0。
- 上一批（19:14，CNT 496791）之后板子又连续跑了 77767 帧 = 21.6 min，与墙钟 21.4 min 吻合
  ⇒ **全程无断电、无复位**。
- 采集链 identity 已校准并复核通过（见同目录上一批 README）。

## ★决定性证据：曲线确实在通路上★

把 10 号（曲线旁路，线性域）的每个 percentile 过一遍 `isp_gamma.v` 的 `mem_b00` 真值表，
应当预测出 11 号（曲线启用）的 percentile：

| percentile | #10 旁路 | LUT(#10) 预测 | #11 实测 | 差 |
|---|---|---|---|---|
| p0.1 | 3 | 22 | 27 | +5 |
| p1 | 7 | 33 | 34 | +1 |
| p5 | 10 | 40 | 42 | +2 |
| p10 | 13 | 46 | 48 | +2 |
| p25 | 25 | 63 | 65 | +2 |
| p50 | 34 | 74 | 74 | **0** |
| p75 | 42 | 82 | 82 | **0** |
| p90 | 55 | 94 | 94 | **0** |
| p95 | 70 | 106 | 106 | **0** |
| p99 | 90 | 120 | 119 | -1 |
| p99.9 | 127 | 143 | 142 | -1 |
| **mean** | 34.92 | 72.48 | 73.52 | +1.04 |
| **std** | 17.33 | 18.47 | 17.78 | -0.69 |

**±2 码以内，中位数/四分位完全一致。** 逐像素套 LUT 的预测均值 72.48 vs 实测 73.52。

⇒ **S 曲线（p160_a050）确认已进入通路，并且逐码按设计工作。这是本项目第一次端到端验证曲线上板生效。**

LUT 真值锚点：`x -> y` = `0->0, 1->13, 2->18, 3->22, 4->25, 8->36, 16->51, 32->72, 64->101, 96->124, 128->143, 160->160, 200->183, 255->255`。

## 同时暴露的三个问题

### D1 这条 LUT 是"反 S"（降对比），不是赛题要求的 S 曲线
- 160 以下 `y = 160*(x/160)^0.5`：凹函数 -> **抬暗部**
- 160 以上 `y = 160+95*(1-((255-x)/95)^0.5)`：也是凹的 -> **压高光**
- 两侧都压缩 ⇒ **对比度下降**，画面发灰发闷（"糊成一团"的主因）。
- 用户最初的需求（m00002）是"**压暗部、提高光、保留中间调**"，即真正的 S 曲线。
  更早的 `p118_k125`（指数 1.25）才是真 S 曲线，被 `p160_a050` 取代后方向反了。

### D2 黑场丢失
- `<=8` 的像素占比：10 号 **3.082%** -> 11 号 **0.082%**（后者只剩真正的 0）。
- 曲线底部 `y(1)=13, y(2)=18, y(3)=22` 把传感器噪声底抬成可见灰。
- 视觉证据：10 号右侧近黑区域在 11 号变成一片平灰。

### D3 白平衡残差 11%（线性域）
- 10 号是**唯一一张开关状态已知的曲线旁路图**，所以它的通道比就是 AWB 之后的线性域真值：
  - `R=32.88 G=36.87 B=34.65`  ⇒ **R/G = 0.8919, B/G = 0.9399**
- 灰世界 AWB 的目标是 1.0000（已由 `tb_awb_means.v` 仿真证明该模块算法本身精确正确）。
- 待验证假设：`awb.v` 的增益是**逐行递推**的（`sum_*` 在 `I_tuser` 清零，`done` 每拍更新），
  所以第 N 行用的是第 0..N 行的累计比 —— **运行中的非稳态增益无法归一化整帧均值**。
  定量上：上半帧偏暖（R/G=1.2）、下半帧偏冷（R/G=0.8）的场景，
  帧锁存增益给出 1.00，逐行递推增益给出 0.90 —— 与实测 0.89 同量级。
- 检验 TB：`E:\\FPGA\\_analysis\\sim\\awb\\tb_awb_zones.v`（分区分帧测试）。

## 复现命令
```
py = C:\\Users\\KX\\.dsh\\dsh-runtimes\\dsh-primary-runtime\\dependencies\\python\\python.exe
%py% E:\\FPGA\\_analysis\\scripts\\_ab_sw2.py          % 不可达码统计
%py% E:\\FPGA\\_analysis\\scripts\\_ab_curve_predict.py % percentile 预测比对
```
产物：`_analysis\\out\\_ab_sw2.txt`、`_ab_curve_predict.txt`、`osd_ab_sw2.png`、`ab_sw2_scene.png`。

## OSD 读数
- 10 号 `安路 CNT:574558` / `MODE 0`
- 11 号 `安路 CNT:574725` / `MODE 0`
"""

p = os.path.join(DST, "README.md")
open(p, "w", encoding="utf-8").write(README)
print("wrote", p, os.path.getsize(p), "B")
print()
print("=== dir ===")
for f in sorted(os.listdir(DST)):
    print("  %-52s %9d" % (f, os.path.getsize(os.path.join(DST, f))))
print()
print("=== root Screenshot*.png left ===")
import glob
left = glob.glob(r"E:\FPGA\Screenshot*.png") + glob.glob(r"E:\FPGA\*.png.png")
print("  ", left if left else "(none)")
