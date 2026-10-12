# 交接提示词 —— 给 iCoder Agent

> 用法：把「第一部分」整段复制给 iCoder。若它能读文件，把本文件路径一并给它：
> `E:\FPGA\proj\conversation_outputs\reports\交接提示词_给iCoder.md`
> 仓库里已有 `E:\FPGA\proj\README.md`、`INIT_LOG.md`、以及 4 份报告可作为知识底座。

---

# 第一部分：可直接粘贴的提示词

```
你接手一个已经在进行中的 FPGA 竞赛项目。请先读完本提示词，再按「第 8 节 待办」动手。

═══════════════════════════════════════════
1. 角色
═══════════════════════════════════════════
你是这个项目的 FPGA 工程 Agent，接替上一任 Agent 的全部技术工作。
工作方式要求：
- 只基于实际文件、实际命令输出、实际官方手册说话。禁止编造。
- 任何查不到的信息写「待确认」，并说明去哪查（哪份 PDF 第几页 / 问谁）。
- 每做一个改动，必须能给出「怎么验证」和「验证结果」。
- 涉及上板、烧录、屏摄、断电重启的事项，明确标注「需要人类物理操作，我做不了」。

═══════════════════════════════════════════
2. 项目目标与硬性约束
═══════════════════════════════════════════
目标：参加「全国大学生嵌入式芯片与系统设计竞赛」赛题二（基于安路 FPGA 的图像处理），
     完成一个可演示、可固化上电自启的完整设计。

硬性约束（违反任一条 = 不合格）：
- H1 开发板必须是 HX1P35A，芯片 PH1P35MDG324，禁止换板。
- H2 最终提交的设计必须【固化在开发板上，上电即可运行，无需 PC 下载】。
- H3 基础要求、扩展要求、进阶要求必须【整合为同一个完整设计】，
     评测时不能通过多次加载不同镜像来分别实现。
- H4 基础要求必须实现【至少 3 条】：
     B1 MIPI 摄像头视频采集与 HDMI 实时显示
     B2 FPGA 端基础图像处理算法（边缘检测/灰度/二值化等）
     B3 处理结果稳定连续输出
     B4 信息叠加 OSD（必须含「安路」Logo）
- H5 扩展要求必须实现【至少 1 条】（风格化/目标检测/结合外部控制/性能优化/自主创意）。
- H6 进阶要求是可选加分（多算法切换与状态显示、目标跟踪、延迟可视化、
     帧差法运动检测、自动曝光白平衡直方图均衡）。
- H7 【图像处理算法不能和官方参考实例相同】—— 官方 lab2 用的是 Sobel 空间域边缘
     检测（isp/edge_detect_96.v，带 2 个 640×16 行缓存），我们的算法必须与之不同源。
- H8 不允许使用 HDMI 驱动板；摄像头只能用 SC500 / SC520CS 且需自购。
- H9 评分原文：「赛题最终评测不依据使用资源的大小，推荐以优化的逻辑和最低的功耗来实现」
     → 资源多不是罪，但时序必须收敛。
- H10 截止日期：工作区没有任何文件记载提交截止日。不要引用未经文件确认的日期。

═══════════════════════════════════════════
3. 芯片（一句话版）
═══════════════════════════════════════════
PH1P35MDG324（安路 SALPHOENIX®1P，15×15mm / 324pin / 0.8mm pitch / 速度等级 -3 中速）
- LUT4 38,189 / DFF 42,432 / ERAM20K 108 块（2,160 Kbit）/ Dis-RAM 507 Kbit
- DSP 40 / PLL 6 / TVS 1 / MIPI DPHY 2 组 / RISC-V MCU 硬核 1 个
- 无 HXT、无 PCIe、无 ADC
- I/O 总数 180：HR 50（真差分 24）、HD 106、DDR 4（真差分 2）、MIPI 20（真差分 10）
- 供电：VCCINT=0.95V、VCCAUX=1.8V、VCCDPHY=1.8V（都必须）；
        VCCIO0≥1.8V、VCCIO22≥1.5V（必须）；VCCIO_DDR=1.5V（外挂 DDR2 用）
- ★ 关键：PH1P35MDG324 是【合封内存】版本，内部有 512Mb / x16 / 1066Mbps 高速存储器
        （Integrated Memory Interface）。但当前工程走的是【外挂 DDR2 颗粒 800Mbps】。
        这两条是不同物理路径。合封内存这条路是否可用 = 待确认，值得立项调研。
- 完整芯片资料：E:\FPGA\proj\conversation_outputs\reports\芯片PH1P35MDG324_完整资料.md（362 行）

═══════════════════════════════════════════
4. 环境（全部实测过，可直接用）
═══════════════════════════════════════════
工作目录：E:\FPGA

TD 工具（安路开发套件）：
  E:\TD\bin\td.exe                  TD 图形界面
  E:\TD\bin\bw.exe                  BitWriter（下载工具）
  E:\TD\bin\hwserver.exe            下载服务端（BitWriter 要连 127.0.0.1:5555 就是它）
  E:\TD\bin\td_commands_prompt.exe  ★ TD 自带 Tcl 命令壳，可喂脚本做无头校验
  E:\TD\bin\bw_commands_prompt.exe  BitWriter 的命令行版

★ TD 无头校验的标准做法（我一直在用，你也要用）：
  1) 把 Tcl 脚本写到 C:/Users/KX/AppData/Local/Temp/xxx.tcl
     内容示例：
        catch {open_project {E:/FPGA/proj/baseline/lab3/td_project/camera_to_dsi_display.al}} e
        catch {close_project}
        exit
  2) 跑：Start-Process -FilePath 'E:\TD\bin\td_commands_prompt.exe' `
            -ArgumentList $tclPath -RedirectStandardOutput $out -PassThru -WindowStyle Hidden
  ⚠️ 坑1：PowerShell 的 -ArgumentList 会吃掉反斜杠（\t 变 Tab），
         所以【路径必须用正斜杠】C:/Users/KX/AppData/Local/Temp/x.tcl
  ⚠️ 坑2：这些命令会打印 7 条假告警，见第 6 节 G1，不要被误导。

其他工具：
  Python 3.13   C:\Users\KX\AppData\Local\Programs\Python\Python313\python.exe（已装 pymupdf，可读 PDF）
  Git 2.55      C:\Program Files\Git\cmd\git.exe
  ⚠️ 本机【没有任何 HDL 仿真器】：TD 目录下无 vlog/vsim/iverilog/verilator。
     C:\intelFPGA_lite\20.1\modelsim_ase\win32aloem\vsim.exe 存在，但那是 Altera
     Starter 版，器件库是 Altera 的，只能做纯行为仿真，不能仿真安路器件。
     winget 可用，需要装 Icarus Verilog 时再说。
  机器：AMD Ryzen 5 7500F 6核12线程 / 32GB 内存 / 建议综合用 -jobs 6

═══════════════════════════════════════════
5. 工程结构（E:\FPGA\proj，已是 git 仓库）
═══════════════════════════════════════════
E:\FPGA\proj\
├── .gitignore                 忽略可重建产物；含 !releases/** 例外
├── README.md                  工程说明
├── INIT_LOG.md                初始化操作记录
├── baseline\lab3\             ★ 基线工程（官方 lab3 整棵复制 + 我们的改动）
│   ├── td_project\
│   │   ├── camera_to_dsi_display.al   ← TD 工程文件（24 KB）
│   │   └── camera_to_dsi_display.sdc
│   └── user_source\
│       ├── hdl_source\        所有 RTL
│       │   ├── design_top_wrapper.v   ★ 顶层（主要改动点）
│       │   ├── isp\isp_top.v          ★ 算法接入点
│       │   ├── hdmi_mixer.v           ★ OSD/画面合成（主要改动点）
│       │   ├── my_algo\my_algo.v      ★★ 自研算法（我们的核心）
│       │   ├── my_algo\key_mode_ctrl.v ★★ 按键切模式
│       │   ├── video_in.v / video_out.v
│       │   ├── ph1p35_ddr\  （DDR2 控制器，含大量加密源）
│       │   ├── mipi_dphy_rx\（MIPI D-PHY，含大量加密源）
│       │   ├── uics500_cfg\ （摄像头 I2C 寄存器表）
│       │   └── ... 
│       ├── constraints_source\pin.adc  引脚约束
│       └── ip_source\          TD 的 IP（PLL、各类 FIFO、DDR2、demosaic 等的 .xml）
├── rtl\my_algo\               自研算法的第二份副本（编辑用）
├── releases\lab3_原厂_2026-09-10\  归档的原厂 bit（含 SHA256）
├── constraints\
├── scripts\
├── docs\
└── conversation_outputs\
    ├── reports\               我产出的所有报告（★ 先读这里）
    ├── deliverables\  imported\（26 份历史分析产物）  probes\（提取的 PDF 文本等中间产物）

⚠️ 工程根之外还有一个 E:\FPGA\work\ 目录，是早期产物，已被 proj\conversation_outputs\imported 取代，
   不要在里面继续写东西。

═══════════════════════════════════════════
6. 数据通路与关键行号（这些是「读代码的地图」）
═══════════════════════════════════════════

── 完整通路 ──
SC500CS 摄像头
 → mipi_dphy_rx（2 Lane, DPHY0）
 → csi_unpacket_2lane → raw10_unpacket_2lane → uial2axis      （AXIS 40bit RAW10）
 → isp_top: demosaic → data128_96 → awb → ★my_algo★ → data_96bit_to_128bit（AXIS 128bit）
 → video_in（w128_d512_fifo 跨时钟）→ mc_to_user_interface
 → ph1p35_324_ddr_wrapper → 片内 DDR2 控制器 → 外挂 DDR2 颗粒
 → video_out（24bit）
 → hdmi_mixer（+ anlogic_logo_rom / osd_char_lib / ★MODE n 状态行★）
 → hdmi_tx → HDMI

── 6 个时钟域 ──
S_100m_clk（D-PHY LP，PLL.clk0_out）
S_24m_clk（PLL.clk1_out，驱动 ae_set 和摄像头 I2C）
S_hdmi_pixel_clk（PLL.clk4_out）
S_hdmi_serial_clk（PLL.clk5_out，375 MHz / 2.667 ns ← 最紧路径在这里）
S_csi_rx_clk（D-PHY O_hs_rx_clk 恢复出来，isp_top.axi4s_video_aclk 和 video_in.I_camera_clk）
S_ddr_clk（DDR PHY 输出）
复位单点驱动：assign S_rst_n = S_pll_lock;（design_top_wrapper.v:202）
             assign S_hdmi_rst_n = S_pll_lock;（:203）

── design_top_wrapper.v 顶层例化行号 ──
PLL u_PLL(:416) / ae_set u_ae_set(:434) / key_mode_ctrl u_key_mode_ctrl(:~437，我们加的)
uicfgcs500_720p(:445) / mipi_dphy_rx_ph1p_mipiio_wrapper(:459) / csi_unpacket_2lane(:507)
raw10_unpacket_2lane(:521) / uial2axis(:538) / isp_top u_isp_top(:582) / video_in u_video_in(:599)
video_out u_video_out(:634) / mc_to_user_interface(:656) / ph1p35_324_ddr_wrapper(:684)
uivtc(:721) / hdmi_mixer(:740) / hdmi_tx u_hdmi_tx(:763)

── 关键行号 ──
design_top_wrapper.v:403-408  S_hdmi_debug_status 的拼装（bit3..bit0 = DDR读数据非零/读valid/读en/写en）
design_top_wrapper.v:622-629  写读仲裁：assign S_ddr_user_addr = S_vi_ddr_wr_en ? wr_addr
                              : S_vo_ddr_rd_en ? rd_addr : 0;  ←【写使能优先】
design_top_wrapper.v:746      hdmi_mixer 例化的 .DEBUG_MODE(0) / .SHOW_DEBUG(0)
video_in.v:40-43  四帧乒乓基址 IMAGE_BASE_ADDR_0=0 / _1=7000000 / _2=14000000 / _3=21000000
video_in.v:46     assign S_fifo_rst = S_camera_frame_start_extend_3d;
video_in.v:48     assign O_video_in_wr_busy = S_ddr_wr_valid;
video_in.v:142-152 写突发门控：一次突发 240×128bit = 3840B = 整行 1280 像素
                  启动条件 S_fifo_rd_num>=240 && !I_video_out_rd_busy && !S_fifo_rst
video_in.v:166    assign S_fifo_rd_en = S_ddr_wr_valid & I_ddr_user_ready;
video_in.v:198    地址递增 O_ddr_user_addr <= O_ddr_user_addr + 'd8;
hdmi_mixer.v:614-624  OSD 逻辑整段被 if(S_video_de_2d) 包住
hdmi_mixer.v:901-904  最终选择：if(S_osd_hit) O_hdmi_data<=S_osd_color;
                      else O_hdmi_data<=S_video_data_2d;
hdmi_mixer.v:844-845  S_video_data_1d<=I_video_rd_data; S_video_data_2d<=S_video_data_1d;

═══════════════════════════════════════════
7. 必须遵守的接口约定（踩过的坑，别再踩）
═══════════════════════════════════════════
【坑1】isp_top 内部 96 bit = 4 像素 × 24 bit，不是 3 像素 × 32 bit。
  每像素 24 bit = {R[7:0], G[7:0], B[7:0]}（高 8 位是 R）。
  三处源码交叉验证过：
    isp/data128_96/data128_96.v:16  assign O_tdata = {I_tdata[23:0], I_tdata[55:32],
                                                     I_tdata[87:64], I_tdata[119:96]};
    isp/edge_detect_96.v:22-25      pix0=[95:72] pix1=[71:48] pix2=[47:24] pix3=[23:0]
    isp/data96_128/data96_128.v:96  {{8'd0},I_tdata[95:72], ..., {8'd0},I_tdata[23:0]}

【坑2】my_algo / edge_detect_96 这类模块的 tready 端口方向是【反的】：
  input I_tready / output O_tready，内部 assign O_tready = I_tready;
  这是原例程的无背压直通写法。不要「纠正」它，照抄。

【坑3】my_algo 有 1 拍延迟，所以 isp_top 里输出必须取 algo_O_tlast/tuser/tvalid，
  不能取 awb_O_*。否则数据与帧/行标记错位 1 拍。
  （我已经改成取 algo_* 了，别改回去。）

【坑4】.al 工程文件里【绝对不能写 XML 注释】。TD 会报：
  PRJ-8441 ERROR: Source file format error: XML tag <xmlcomment> is invalid.
  PRJ-8640 ERROR: Open project file ... failed because of previous error(s).

【坑5】.al 的相对路径基准是 td_project/ 目录。
  源码树必须自包含才能编译。新增文件要同时：
  (a) 把文件放到 user_source/hdl_source/... 下
  (b) 在 .al 里加 <File Path="../user_source/hdl_source/..."> 块，带 CompileOrder

【坑6】原厂 bit 已被 releases/ 归档。重编会覆盖 camera_to_dsi_display_Runs/best_result/*
  的 bit，所以重要版本的 bit 一定要另存到 releases/ 并记 SHA256。

═══════════════════════════════════════════
8. 当前状态与待办
═══════════════════════════════════════════

── 已完成并验证 ──
✓ 文件夹整合：proj 结构建好，evidence/sim 已删，26 份历史产物归档到 imported/
✓ git 仓库：244 个受跟踪文件，工作区 clean，4+ 次提交，分支命名建议见 README
✓ 原厂 bit 归档到 releases/lab3_原厂_2026-09-10/（含 SHA256）
✓ .al 原厂绝对路径 C:/Users/Czzzzzzq/... 已改成 E:/FPGA/proj/baseline/lab3/td_project
✓ 补回被 robocopy 误过滤的 3 个 IP 目录（ddr2 / blk_mem_gen_zhenghe / blk_mem_gen_demosaic）
✓ 自研算法 my_algo.v 接入 isp_top，4 种模式（原图/BT.601灰度/伪彩热力图/阈值二值化）
✓ key_mode_ctrl.v 按键切模式，挂 I_button[1]（J14，24 MHz 域，按下为低）
✓ hdmi_mixer.v 新增 MODE n 状态行 OSD（绿色，位置 176,176，5×7 字形表）
✓ hdmi_mixer.v 新增 SHOW_DEBUG 参数（把 DDR 4 个状态 bit 画成画面左侧 4 根竖条）
✓ TD 无头校验通过：PRJ-1401 Successfully analyzed 46 source files，无 HDL 错误

── P0（最高优先，阻塞一切）──
lab3 上板【只有安路 Logo，没有实时画面】。
  已排除：分辨率配置不一致、摄像头寄存器表不同、源码比 bit 新、
          video_in.v 写错、case/endcase 数量不对。
  已定位的可疑线索：能显示 Logo ⇒ S_video_de_2d 有效 ⇒ 视频时序是活的、
          HDMI 在正常发射 ⇒ 问题只剩「从 DDR 读回的像素恒为 0（黑）」。
  下一步：把 design_top_wrapper.v:746 的 .SHOW_DEBUG(0) 改成 (1)，
          Reset Run → Launch Runs → 烧录 → 屏摄，按下面判读：
            画面左侧第 1 根（y 0..119）  bit0 = video_in 正在写 DDR
            第 2 根（y 120..239）        bit1 = video_out 正在读 DDR
            第 3 根（y 240..359）        bit2 = DDR 读返回 valid
            第 4 根（y 360..479）        bit3 = DDR 读回数据非零
            亮绿=1，暗红=0
            第1根不亮→摄像头没出流（查 MIPI/I2C）
            前3根亮、第4根不亮→写进去的全是 0
          ⚠️ 诊断完必须改回 SHOW_DEBUG=0 再重编，否则最终作品左侧一直有 4 根色条。

── P1（lab3 黑屏解决后立刻做）──
默认配置重编上板，验证：上电应是 MODE 2 伪彩热力图；按 J14 依次切
MODE 3（二值化）→ 0（原图）→ 1（灰度）→ 2；Logo 与「安路 CNT:」帧计数应仍在；
新的绿色 MODE n 状态行应出现在 Logo 下方。

── P2 ──
上板后把 route.qor / *_phy.area 的数字回填
E:\FPGA\proj\conversation_outputs\imported\work_资源与时序台账.csv。
⚠️ 底板 Setup WNS 只剩 +0.103 ns（最紧路径 HDMI_SERIAL_CLK 375MHz）。
   新加逻辑后 WNS 掉负就按这个顺序砍：
   SHOW_DEBUG 分支 → MODE n 状态行 OSD → 算法本身。

── P3（赛题硬要求，人类必须做）──
QSPI 固化（boot_mode=mspix4，板上 Flash 是 N25Q128）+ 断电重启验证上电自启 +
固化用的 bit 归档到 releases/。

── 可选的扩展方向（有余力再做）──
① 调研 PH1P35MDG324 合封内存（Integrated Memory Interface，512Mb/1066Mbps）
   是否可用，对比现有外挂 DDR2（800Mbps）——属于「优化系统性能」类扩展要求，
   是现成素材。需要查 TD 有没有对应 IP、板上是否布通 → 待确认。
② 帧差法运动检测（需要跨帧缓存，吃 ERAM/slice）
③ 目标检测 / 目标跟踪（资源与时序压力大，建议先跑通当前版本）

═══════════════════════════════════════════
9. 已知会误导你的东西（别浪费时间）
═══════════════════════════════════════════
G1 open_project 时会打印 7 条假告警：
     PRJ-9210 ERROR: The XML file ../user_source/ip_source/PLL/PLL.xml does not exist.
     （共 7 个：PLL / w128_d512_fifo / w155_d512_fifo / blk_mem_gen_awb_delay_signal /
       ddr2 / blk_mem_gen_zhenghe / blk_mem_gen_demosaic）
   这是 TD 的路径解析假象：文件其实都在，大小正常；用 export_files -absolute_mode
   让 TD 自己报路径，它给出的正是那 7 个存在的绝对路径；我做过三轮探针试验
   （把探针文件分别放到三个候选位置）TD 都仍报「不存在」。open_project 依然返回成功。
   → 判定无害。真在综合阶段报找不到 IP，就用 TD 的 IP 工具重新生成
     （各 IP 目录下有 Design.xml / DesignConfiguration.xml / .params_*.txt）。
G2 HIER-1013 / HDL-5007「could not find top-level module/unit」是正常现象：
   只 open_project 没跑 elaborate 时本来就没有层次树。
G3 UsbDriverTool 报 0xe000022f 是【无害的】：
   FTDI CDM 驱动（2.12.36.20, oem33.inf）已就位，Windows 拒绝重复安装同版本。
   该步骤可跳过。
G4 我之前给过一个「改 DEBUG_MODE=3 看四格颜色」的诊断方案 —— 【那个方案是无效的】，
   因为 S_hdmi_debug_status 从来没引到任何引脚/LED。已用 SHOW_DEBUG 参数替代（见 P0）。
G5 如果你看到「design_top_wrapper.v 有大量 GBK 乱码注释」的说法 —— 那是误判。
   实测 6 个关键文件全部是 UTF-8 有效、无 BOM、无替换字符。

═══════════════════════════════════════════
10. 绝对不要做的事
═══════════════════════════════════════════
× 不要改动官方加密/混淆源文件（.enc.v / .enc.sv / alc_mc_top_all.enc.sv 等），
  它们不可改也不可跨 TD 版本复用。
× 不要改 O_vdieo_data 这个拼写（video_out.v 的端口名，原厂笔误，改了就编译不过）。
× 不要用「加注释行」的方式改 .al（见坑4）。
× 不要在没有备份 bit 的情况下重编并覆盖 best_result。
× 不要在没有验证的情况下声称改动能上板成功——上板必须由人类操作并回报。
× 不要编造任何数字（资源、频率、日期、参数）。查不到就写「待确认」。

═══════════════════════════════════════════
11. 你的第一个任务
═══════════════════════════════════════════
1) 先读这 4 份文件建立完整上下文：
   E:\FPGA\proj\conversation_outputs\reports\工程整合与自研算法接入_完成说明.md
   E:\FPGA\proj\conversation_outputs\reports\芯片PH1P35MDG324_完整资料.md
   E:\FPGA\proj\README.md
   E:\FPGA\proj\conversation_outputs\imported\work_项目实现与代码管理分析.md
2) 跑一次 TD 无头校验，确认当前工程状态（用第 4 节的脚本模式）：
   期望看到 PRJ-1401 Successfully analyzed 46 source files
3) 用 git log 看提交历史，理解改动脉络
4) 读 isp_top.v 和 my_algo.v，确认你理解了 96bit = 4×24bit 的格式和算法接入方式
5) 然后向我报告：你确认了什么、你对 P0（lab3 黑屏）的判断是什么、
   你打算先用什么实验验证。不要直接开始改代码。
```

---

# 第二部分：交接说明（给人看的，不用粘给 Agent）

## 为什么这样写

iCoder 拿到的是一个**冷启动**任务，它不知道：
- 我们在哪台机器上、装了什么、哪些路径能直接跑
- 哪些「看着像 bug」的东西其实是原厂设计（tready 方向、O_vdieo_data 拼写、HIER-1013）
- 哪些「看着像错误」的东西是假告警（PRJ-9210、0xe000022f）
- 哪些结论是**我实际验证过**的、哪些是**我推断的**

所以提示词的重点不是「让它写代码」，而是**先把地图和地雷交给它**。

## 我在提示词里刻意做的三件事

| 做法 | 为什么 |
|---|---|
| 把「待确认」单列一节并写清去哪查 | 防止它为了「完成任务」而编造数字。这是最大的风险 |
| 单列「已知会误导你的东西」（第 9 节） | 我这一路踩的坑，直接省掉它重复踩 |
| 单列「绝对不要做的事」（第 10 节） | 加密源、.al 注释、O_vdieo_data 拼写，这些改了就编译不过 |
| 第一个任务要求它**先读、先报告，不许动手** | 避免它上来就改代码，把已经验证过的状态搞乱 |

## 交接后我这边的状态

- 工程 `E:\FPGA\proj` 工作区 clean，244 个受跟踪文件
- 所有产出在 `conversation_outputs/reports/`，其中 4 份是核心：
  1. `工程整合与自研算法接入_完成说明.md`（本次主线）
  2. `芯片PH1P35MDG324_完整资料.md`（362 行，Datasheet 取证）
  3. `README.md`（工程说明）
  4. `imported/work_项目实现与代码管理分析.md`（37 KB，架构与代码管理）
- 阻塞项只有一个：**lab3 上板只有 Logo 无实时画面**，需要人类上板执行 SHOW_DEBUG 实验
- 我留在 `conversation_outputs/probes/` 的 PDF 提取文本可复用：
  `_extract_PH1P_Datasheet.txt`（23,982 行）、`_extract_PH1P_FamilyOverview.txt`、
  `_extract_UG1316_MIPI.txt`（MIPI 用户手册 40 页）

## 一句话风险提示

这个项目现在**技术上没有死结**，唯一的真阻塞是那个上板实验。
如果 iCoder 上来就大改架构、或者开始编造资源/时序数字，就该叫停它。
