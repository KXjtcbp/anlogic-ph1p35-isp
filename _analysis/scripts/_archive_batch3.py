# -*- coding: utf-8 -*-
"""把 inbox 里本批 8 张图重命名并归档，同时补全 采集记录.csv。

重命名规则：序号_场景_AE状态_gi_S_CNT.png
- gi = 橙色第 1 行的 AE 增益索引（十六进制），7F = 最大档
- S  = 橙色第 1 行的 AE 状态位（2 = 闭环运行，3 = 冻结）
- CNT 从黄色 OSD 行读出
"""
import os, shutil, sys, datetime
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = r"E:\FPGA"
SRC = os.path.join(WS, "inbox")
DST = os.path.join(WS, "captures", "2026-10-12_AE遥测两行验证")
os.makedirs(DST, exist_ok=True)

# (原文件名, 新文件名, 场景, 光照, SW1, SW2, SW3, SW4, CNT, MODE, gi, S, 备注)
PLAN = [
    ("SW4\u4e0b.png", "01_SW4\u4e0b_AE\u51bb\u7ed3_gi7F_Sp3_CNT001274.png",
     "\u5bbf\u820d\u684c\u9762", "\u53ea\u5f00\u663e\u793a\u5668", "\u4e0a", "\u4e0a", "\u4e0a", "\u4e0b",
     "001274", "0", "7F", "3", "SW4 \u62e8\u4e0b\uff0cAE \u51bb\u7ed3\uff08\u6b64\u65f6\u5df2\u5728\u6700\u5927\u6863 15.750x\uff09"),
    ("SW4\u4e0a1.png", "02_SW4\u4e0a_AE\u8fd0\u884c1_gi7F_Sp2_CNT001831.png",
     "\u5bbf\u820d\u684c\u9762", "\u53ea\u5f00\u663e\u793a\u5668", "\u4e0a", "\u4e0a", "\u4e0a", "\u4e0a",
     "001831", "0", "7F", "2", "\u62e8 SW4 \u4e0a +9s\uff0cS \u53d8\u4e3a 2 \u4f46 gi \u4ecd\u5728\u6700\u5927\u6863"),
    ("SW4\u4e0a2.png", "03_SW4\u4e0a_AE\u8fd0\u884c2_gi7F_Sp2_CNT002538.png",
     "\u5bbf\u820d\u684c\u9762", "\u53ea\u5f00\u663e\u793a\u5668", "\u4e0a", "\u4e0a", "\u4e0a", "\u4e0a",
     "002538", "0", "7F", "2", "\u518d +11s\uff0cgi \u4ecd\u9876\u683c\u21d2\u623f\u95f4\u592a\u6697"),
    ("Screenshot 2026-10-12 22-56-52.png", "04_\u5ba4\u5185\u684c\u9762_gi7F_Sp3_CNT078815.png",
     "\u5ba4\u5185\u684c\u9762\uff08\u7a97\u8fb9\u5851\u6599\u888b\uff09", "\u5f00\u706f", "\u4e0a", "\u4e0a", "\u4e0a", "\u4e0b",
     "078815", "0", "7F", "3", "SW4 \u4e0b\uff0cAE \u51bb\u7ed3"),
    ("Screenshot 2026-10-12 22-57-02.png", "05_\u5ba4\u5185\u684c\u9762\u7565\u6697_gi7F_Sp3_CNT079413.png",
     "\u5ba4\u5185\u684c\u9762\uff08\u7a97\u8fb9\u5851\u6599\u888b\uff09", "\u5f00\u706f", "\u4e0a", "\u4e0a", "\u4e0a", "\u4e0b",
     "079413", "0", "7F", "3", "SW4 \u4e0b\uff0cAE \u51bb\u7ed3\uff1b\u573a\u666f\u6bd4\u4e0a\u4e00\u5f20\u6697"),
    ("Screenshot 2026-10-12 22-57-13.png", "06_\u5ba4\u5185\u8fd1\u666f_gi7F_Sp2_CNT080103.png",
     "\u5ba4\u5185\u8fd1\u666f\uff08\u624b\u5165\u753b\uff09", "\u5f00\u706f", "\u4e0a", "\u4e0a", "\u4e0a", "\u4e0a",
     "080103", "0", "7F", "2", "\u62e8 SW4 \u4e0a\u540e S=2"),
    ("Screenshot 2026-10-12 22-57-40.png", "07_\u53f0\u706f\u76f4\u7167_gi2E_Sp2_CNT081743.png",
     "\u53f0\u706f/\u53d1\u5149\u9762\u76f4\u7167", "\u5f3a\u5149", "\u4e0a", "\u4e0a", "\u4e0a", "\u4e0a",
     "081743", "0", "2E", "2", "\u2605\u51b3\u5b9a\u6027\u4e00\u5f20\u2605 \u573a\u666f\u53d8\u4eae\u540e AE \u628a gi \u4ece 7F \u964d\u5230 2E\uff08\u6a21\u62df 2.875x\uff09\uff0cM=0x43=67 \u63a5\u8fd1\u76ee\u6807 70"),
    ("Screenshot 2026-10-12 22-57-58.png", "08_\u5747\u5300\u5899\u9762_gi7F_Sp2_CNT082810.png",
     "\u5747\u5300\u5899\u9762\uff08\u6d45\u7070\uff09", "\u5f00\u706f", "\u4e0a", "\u4e0a", "\u4e0a", "\u4e0a",
     "082810", "0", "7F", "2", "\u8fd1\u4f3c\u767d\u5899\u9762\uff0cR/G=0.9605"),
]

print("=== 重命名并归档 ===")
for old, new, *_ in PLAN:
    sp = os.path.join(SRC, old)
    dp = os.path.join(DST, new)
    if not os.path.exists(sp):
        print("  MISSING %s" % old); continue
    shutil.move(sp, dp)
    print("  %-40s -> %-58s %d B" % (old, new, os.path.getsize(dp)))

# ---------- 写 README ----------
readme = """# 2026-10-12 AE 两行遥测验证（8 张）

板子：`proj/releases/2026-10-12_两行遥测版/camera_to_dsi_display.bit`
      md5 `79c6832556dda860814e4b5a94514215`

## 一次上电贯穿全程
CNT 从 001274 单调递增到 082810（76277 帧 / 1258 s 墙钟 = 60.6 fps）
⇒ 无复位、无重烧。

## 橙色遥测两行的格式
- 第 1 行（屏幕 1920 空间 y[228..241]，内部 y=152..161）：
  `AE<gi>S<st>M<ml>W<gr>B<gb>`，全部十六进制。
  `gi` = AE 模拟增益索引（00=1.000x，40=4.000x，7F=15.750x）
  `st` = AE 状态（0=等配置 1=稳定计时 2=闭环 3=冻结）
  `ml` = AE 测到的**曲线前**帧均值（目标 70 = 0x46）
  `gr`/`gb` = AWB 给 R / B 的增益，**要 ÷4096 才是倍率**（0x1000 = 1.000x）
- 第 2 行（内部 y=164..173）：
  `F<can><rame><req><aec><cam>T<settle2>N<next2>D<dec2>U<inc2>`
  位含义依次为 can_act / rame_ok / req_pend / ae_cfg_done / cam_cfg_done

## 八张读数
| # | 文件 | 场景 | SW4 | gi | S | M(=曲线前均值) | gr | gb | 实测(曲线后)Ymean | R/G | B/G | CNT |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 01_..._gi7F_Sp3_CNT001274 | 宿舍桌面 | 下 | 7F | 3 | 0x19=25 | 0x1236=1.138 | 0x1BA6=1.727 | 37.04 | 0.8770 | 0.9263 | 001274 |
| 2 | 02_..._gi7F_Sp2_CNT001831 | 宿舍桌面 | 上 | 7F | 2 | 0x19=25 | 0x12B6=1.170 | 0x1B28=1.698 | 36.90 | 0.8762 | 0.9264 | 001831 |
| 3 | 03_..._gi7F_Sp2_CNT002538 | 宿舍桌面 | 上 | 7F | 2 | 0x19=25 | 0x107B=1.030 | 0x1AFC=1.687 | 36.76 | 0.8763 | 0.9253 | 002538 |
| 4 | 04_..._gi7F_Sp3_CNT078815 | 室内桌面 | 下 | 7F | 3 | 0x1E=30 | 0x174A=1.456 | 0x19E7=1.619 | 47.51 | 0.9407 | 0.9374 | 078815 |
| 5 | 05_..._gi7F_Sp3_CNT079413 | 室内略暗 | 下 | 7F | 3 | 0x1A=26 | 0x160A=1.377 | 0x1958=1.584 | 29.17 | 0.9055 | 0.9212 | 079413 |
| 6 | 06_..._gi7F_Sp2_CNT080103 | 室内近景 | 上 | 7F | 2 | 0x23=35 | 0x15D4=1.363 | 0x1B5E=1.711 | 53.00 | 0.9399 | 0.9545 | 080103 |
| 7 | **07_..._gi2E_Sp2_CNT081743** | **台灯直照** | 上 | **2E** | 2 | **0x43=67** | 0x1480=1.282 | 0x1BAC=1.726 | 83.49 | **0.9904** | 0.9498 | 081743 |
| 8 | 08_..._gi7F_Sp2_CNT082810 | 均匀墙面 | 上 | 7F | 2 | 0x40=64 | 0x1605=1.376 | 0x1B26=1.694 | 92.56 | 0.9605 | 0.9630 | 082810 |

## 三条结论
1. **AE 闭环正常，而且第一次被直接观测到**：第 7 张场景变亮后，gi 从 7F（15.750x）自动降到 2E（2.875x），
   `M` 稳定在 0x43=67 —— 距目标 70 只差 3 码、已在 ±4.76% 死区内。第 2 行 `can=1 rame=1 req=0 aec=1 cam=1`
   说明配置握手全程健康。
2. **`M` 只有我测到的 Ymean 的 0.7~0.8 倍，不是 bug**：`ae_stat` 挂在 `isp_gamma` **之前**，
   `M` 是**曲线前**均值；我从 PNG 测的是**曲线后**均值。用 LUT 换算完全对得上：
   `LUT(25)=38` vs 实测 37.0；`LUT(30)=45` vs 47.5；`LUT(35)=52` vs 53.0；`LUT(64)=85` vs 92.6。
   ⇒ 此前「ae_stat 口径偏低 0.7 倍」的判断作废。
3. **AWB 在亮度足够时能拉平**：第 7 张 R/G = 0.9904、B/G = 0.9498，是目前最好的一次。
   但第 1~3 张（Y≈37）R/G 仍只有 0.876 ⇒ 残差与亮度强相关，符合「固定加性偏置」的特征。

## 采集链校验
八张的 Logo 主色恒为 `(27,44,75)`（蓝）与 `(235,29,36)`（红），
对应 `anlogic_logo_rom.v` 的 `(28,45,78)` / `(237,28,36)` ⇒ 采集链 identity 通过。
"""
open(os.path.join(DST, "README.md"), "w", encoding="utf-8").write(readme)
print("\nREADME.md %d B" % os.path.getsize(os.path.join(DST, "README.md")))

# ---------- 补全 CSV ----------
lines = ["\u6587\u4ef6\u540d,\u6279\u6b21,\u62cd\u6444\u65f6\u523b,\u573a\u666f\u5185\u5bb9,\u5149\u7167\u6761\u4ef6,SW1,SW2,SW3,SW4,OSD_CNT,OSD_MODE,gi,S,\u5907\u6ce8"]
for old, new, scene, light, sw1, sw2, sw3, sw4, cnt, mode, gi, s, note in PLAN:
    ts = datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(DST, new))).strftime("%m-%d %H:%M:%S")
    lines.append(",".join([new, "AE\u9065\u6d4b\u4e24\u884c", ts, scene, light,
                           sw1, sw2, sw3, sw4, cnt, mode, gi, s, note]))
lines.append("")
lines.append("# \u4ee5\u4e0b\u4e3a\u5386\u53f2\u6279\u6b21\uff0c\u5f53\u65f6\u672a\u8bb0\u5f55 CNT\uff0c\u5df2\u5f52\u6863\u5230 captures/ \u5bf9\u5e94\u76ee\u5f55")
for d, note in ((u"2026-10-12_AE\u9996\u7248\u4e0a\u677f\u9a8c\u8bc1", u"A1-E5 \u5171 21 \u5f20\uff08AE \u9996\u7248\uff0c\u65b9\u5411\u53cd\uff0c\u5df2\u4f5c\u5e9f\uff09"),
                (u"2026-10-12_AE\u4fee\u6b63\u7248\u4e0a\u677f\u9a8c\u8bc1", u"A1-E5 \u7b2c\u4e8c\u6279 21 \u5f20"),
                (u"2026-10-12_\u9065\u6d4b\u8bca\u65ad", u"T1-T3 / S1-S5 / G1-G2 / W1")):
    idx = os.path.join(WS, "captures", d)
    if os.path.isdir(idx):
        n = len([f for f in os.listdir(idx) if f.lower().endswith(".png")])
        lines.append(u"#   %s\uff08%d \u5f20\uff09\uff1a%s" % (d, n, note))
    else:
        lines.append(u"#   %s\uff1a%s" % (d, note))
open(os.path.join(SRC, "\u91c7\u96c6\u8bb0\u5f55.csv"), "w", encoding="utf-8").write("\n".join(lines) + "\n")
print("CSV %d B" % os.path.getsize(os.path.join(SRC, "\u91c7\u96c6\u8bb0\u5f55.csv")))
print("\ninbox \u5269\u4f59:", os.listdir(SRC))
