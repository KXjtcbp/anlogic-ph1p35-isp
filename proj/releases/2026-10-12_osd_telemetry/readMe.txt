proj/releases/2026-10-12_OSD遥测版/camera_to_dsi_display.bit
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
