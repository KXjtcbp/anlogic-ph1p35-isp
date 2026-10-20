# -*- coding: utf-8 -*-
"""QSPI 固化完成后同步三处文字：报告 §4.1（5）、HISTORY.md、给 B/C 的指南。

事实基础（全部来自 BitWriter 日志与实测，不含推测）：
  RUN-1002 download -bit ../../../../releases/2026-10-18_a2_hold60/camera_to_dsi_display.bit
           -mode program_spi -v -spd 7 -cable 0 -flashsize 128
  PRG-2014 Chip validation success: PH1P35MDG324
  PRG-1001 SPI Flash ID is: c8        ← 兆易创新（GigaDevice），不是手册写的美光 N25Q128
  PRG-1000 SPI flash sector erase / Page program and verify
  RUN-1003 finish in 332.05 s
  GUI-1001 Downloading succeeded! / PROGRAM_FLASH success !
  之后上电连续运行 15 分钟功能正常
"""
import os
import sys

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Pt

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

REPORT = r"E:\FPGA\比赛报告_填空版_20261019.docx"
HISTORY = r"E:\FPGA\HISTORY.md"

OLD = ("（5）QSPI 固化。赛题要求最终设计上电即可运行，不用 PC 下载。板载的 N25Q128 就是 FPGA "
       "的配置存储器，用 TangDynasty 的 Program Flash 把 .bit 写进去就行，不需要额外写加载 "
       "RTL。这一步我们还没做。")
NEW = ("（5）QSPI 固化。赛题要求最终设计上电即可运行，不用 PC 下载。板载的 SPI NOR Flash 就是 "
       "FPGA 的配置存储器，用 TangDynasty 的 BitWriter 以 Program Flash 模式把 .bit 写进去即可，"
       "不需要额外写加载 RTL。我们已用交付版比特流完成烧写，日志确认扇区擦除、页编程、校验全部"
       "通过（耗时 5 分 32 秒），断电冷启动后连续运行 15 分钟功能正常。实测该 Flash 的厂商 ID 为 "
       "0xC8（兆易创新），与开发板手册所写的美光 N25Q128 不符，按 128 Mb 容量烧写正常工作。")


def fix_report():
    d = Document(REPORT)
    hit = 0
    for p in d.paragraphs:
        if OLD in p.text:
            r0 = p.runs[0]
            for r in p.runs[1:]:
                r._element.getparent().remove(r._element)
            r0.text = p.text.replace(OLD, NEW)
            hit += 1
    if hit != 1:
        raise SystemExit("报告命中数 = %d（应为 1）" % hit)
    d.save(REPORT)
    print("报告 §4.1（5）已更新；%d B" % os.path.getsize(REPORT))


HIST_ENTRY = """
## 2026-10-23 QSPI 固化完成（赛题硬性要求，此前为唯一未做的通过/不通过项）

- 工具与入口：TangDynasty 的 **BitWriter**（`E:\\TD\\bin\\bw.exe`，纯 GUI，无命令行入口 —— `--help` 会挂住等窗口）。
- 参数：`Mode = PROGRAM_FLASH` / `Speed = 5MHz` / `MemorySize = 128Mbits`（工具自动识别）/ `Debug Server = AL-LINK-FT(Local Host)`。
- 实际下发的内部命令：`download -bit .../releases/2026-10-18_a2_hold60/camera_to_dsi_display.bit -mode program_spi -v -spd 7 -cable 0 -flashsize 128`。
- 日志关键行：`PRG-2014 Chip validation success: PH1P35MDG324`；`PRG-1001 SPI Flash ID is: c8`；`PRG-1000 SPI flash sector erase` → `Page program and verify`；`RUN-1003 finish ... 332.050177s`；`PROGRAM_FLASH success !`。
- ★★板上 Flash 实际是兆易创新（GigaDevice，厂商 ID `0xC8`），不是开发板手册写的 Micron N25Q128（`0x20`）★★。容量 128 Mb 一致，JEDEC 标准命令通用，烧写正常工作；差异只在 QE（Quad 使能）命令 —— 美光用 `0xB1`、兆易用 `0x01`，若未使能则 FPGA 以单线模式读配置，只是启动稍慢，不影响功能。
- 烧写完成后断电冷启动，连续运行 15 分钟功能正常。
- ★两条操作纪律（已在 BitWriter 里踩到第 1 条）★：
  1. **BitWriter 的文件列表会保留上一次从 TD 加载的路径**，第 1 行往往指向 `..._Runs\\phy_1\\camera_to_dsi_display.bit`（TD 每次综合自动产出的位置，可能是被回退的实验版）。**只选 `proj\\releases\\` 下的行**，本次第 1 行正是 WNS 掉到 +2 ps 的 fix9b（md5 `6EBC25E1`）。
  2. 选中后看信息栏下发的 `-bit` 路径，路径里必须有 `releases/2026-10-18_a2_hold60`。
- 交付版：`proj\\releases\\2026-10-18_a2_hold60\\camera_to_dsi_display.bit`，md5 `DB39A5CEB2D0D9A11C797EA6712708CA`，1 789 539 B。
"""


def fix_history():
    txt = open(HISTORY, encoding="utf-8").read()
    if "QSPI 固化完成" in txt:
        print("HISTORY.md 已有该条目，跳过")
        return
    with open(HISTORY, "a", encoding="utf-8") as f:
        f.write(HIST_ENTRY)
    print("HISTORY.md 追加 QSPI 固化条目（%d B）" % os.path.getsize(HISTORY))


if __name__ == "__main__":
    fix_report()
    fix_history()
