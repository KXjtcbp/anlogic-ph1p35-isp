# -*- coding: utf-8 -*-
"""补两版 readMe.txt，然后把两个新 releases 目录 + 本轮 RTL 改动提交。"""
import os, sys, subprocess
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
REL = os.path.join(WS, "proj", "releases")

K45 = """proj/releases/2026-10-12_K45基线/camera_to_dsi_display.bit
============================================================
md5    f4f9ce5ec969a7524bb0d5e609ca60d1
大小   1789539 B
产出   2026-10-12 01:49（td_run_direct.ps1 命令行综合）

这一版是什么
------------
无 AE。ISP 链 = demosaic -> data128_96 -> awb -> isp_gamma -> my_algo -> data96_128。
isp_gamma 的表是"黑位软压缩 K=45"版：
    new(x) = round( p160_a050(x) - 45 * (1 - p160_a050(x)/255)^2 )
锚点 0/1/2/3/4/8/13/16/34/64/96/128/160/200/255 = 0,0,0,0,0,3,16,22,51,85,112,134,154,179,255
共 185 个不同输出码。
BLACK_LEVEL = 10'd56（已用"盖严镜头"验证：整帧 Y 均值 0.00、max 0、100% 为 0）。

这一版没有 AE：曝光硬写 16'h07C6 = 1990，模拟增益只有 SW3/SW4 两档组合。

用途
----
AWB 诊断的对照基线（不含 AE 变量）。要复现 2026-10-12 02:30 那张
"均匀面 CNT106211 / R-G = -3.157" 的基准，用它 + 四开关全上。

注意
----
所有 PH1P35MDG324 的 .bit 都是 1789539 B，大小相同不代表内容相同，只能比 md5。
"""

OSD = """proj/releases/2026-10-12_OSD遥测版/camera_to_dsi_display.bit
============================================================
md5    af25c9b559898eb677241f729a997614
大小   1789539 B
产出   2026-10-12 21:19（td_run_direct.ps1 命令行综合，exit=0）

这一版是什么
------------
AE 修正版 + 一行橙色的"遥测 OSD"。除了原来三行（青色安路 Logo、黄色安路 CNT、
亮绿 MODE n），左上角多出第 4 行，用来把 ISP 内部状态直接画到屏幕上：

    AE<g><g>S<s>M<m><m>W<rrrr>B<bbbb>        共 19 字符，橙色，位置 x=376..679 y=152..161

    AE + 两位十六进制  AE 当前模拟增益索引，00=1.000x，40=4.000x，7F=15.750x
    S  + 一位          AE 状态：0=等配置表/表下载中 1=稳定计时中 2=闭环运行 3=冻结
    M  + 两位十六进制  本帧实测画面均值（0x46 = 70 十进制 = 目标）
    W  + 四位十六进制  AWB 实际在用的 R 通道增益（0x1000 = 1.000x，0x1240 = 1.140x）
    B  + 四位十六进制  AWB 实际在用的 B 通道增益

作用：不用 ChipWatcher、不用重综合抓波形，烧上去就能读 AWB 增益与 AE 状态。
同时它本身就是赛题"扩展要求：实时参数调节与 OSD 信息叠加"与"进阶要求 1：
多算法切换与状态显示"的直接实现。

改了什么（4 个文件，不动任何功能逻辑）
--------------------------------------
1. hdl_source/awb.v              加 2 个输出端口 O_gain_r / O_gain_b + 2 行 assign
2. hdl_source/isp/isp_top.v      加 2 个输出端口 O_wb_gain_r / O_wb_gain_b
3. hdl_source/design_top_wrapper.v  加 49bit 准静态总线 S_osd_dbg 并接到 hdmi_mixer
4. hdl_source/hdmi_mixer.v       加输入端口 + 2FF 同步 + 第 4 层 OSD + 19 字 5x7 字形库

AE 逻辑本身（ae_ctrl.v / ae_stat.v）未改动。

QoR（phy_1/route.qor，2026-10-12 21:19）
----------------------------------------
Setup WNS  +27 ps  TNS 0  违例 0
Hold  WNS  +20 ps  TNS 0  违例 0
#slices 18448 (86.95%)   #lut6 16155 (76.15%)   #reg 19400
#RAMs 60   #DSPs 8   #eram 60/108   wire 5028912
对比上一版（AE修正版）：WNS +95 -> +27 ps，#slices 18111 -> 18448。
字形库与取字形逻辑是主要开销，诊断做完删掉可退回。

上板怎么看
----------
烧上去、四开关全拨上，画面左上角应有四行 OSD。若橙色第 4 行不出现，
说明该层没生效，回报即可。
回滚：proj/releases/2026-10-12_AE修正版/camera_to_dsi_display.bit
      （md5 4c75078a4c31b091a3e015dde4854b59，无遥测行，其余功能相同）
"""

for sub, txt in (("2026-10-12_K45基线", K45), ("2026-10-12_OSD遥测版", OSD)):
    p = os.path.join(REL, sub, "readMe.txt")
    open(p, "w", encoding="utf-8", newline="\r\n").write(txt)
    print("wrote %s (%d B)" % (os.path.relpath(p, WS), os.path.getsize(p)))

print("\n=== git add / commit / push ===")
cmds = [
    ["git", "add", "-A"],
    ["git", "status", "--porcelain"],
]
for c in cmds:
    r = subprocess.run(c, cwd=WS, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print("$ " + " ".join(c))
    print((r.stdout or "") + (r.stderr or ""))
