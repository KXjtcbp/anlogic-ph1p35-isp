# -*- coding: utf-8 -*-
"""
Only add comments (file header + section titles + inline notes) to 6 Verilog files.
Pure byte-level: read raw bytes, decode GBK, insert comment-only text, encode GBK, write.
Dry-run by default; pass --apply to write.
"""
import os, re, sys, shutil

SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\demosaic_4x_2_0"
BAK = r"E:\FPGA\_backup\20261009_comments\demosaic"

FILES = {}

# ============================== demosaic.v ==============================
FILES["demosaic.v"] = dict(
  path="isp/demosaic_4x_2_0/demosaic.v",
  module="demosaic",
  func="去马赛克（demosaic）链路的小顶层：把 40bit/拍的 RAW10 输入（4 个像素 × 10bit）经过 3×3 邻域窗口缓存与双线性插值，还原成 128bit/拍的 RGB888 输出（4 个像素 × 32bit，每像素 {8'b0, R, G, B}）。",
  datapath="axi4s_video_tdata[39:0]（RAW10×4）-> raw_matrix_3x3_buffer_d（内含 mipi_to_raw_converter + zhenghe + 2 级 line_buffer_demosaic，输出 bayer_ypos 与 matrix_last/cur/next_line[95:0]）-> bilinear_interpolation_d -> O_tdata[127:0]",
  clock="单时钟域，I_clk 在工程中接 axi4s_video_aclk；I_rst_n 低有效，异步复位。两个子模块用同一个 I_clk / I_rst_n。",
  deps="例化 raw_matrix_3x3_buffer、bilinear_interpolation（都在 isp/demosaic_4x_2_0/ 下）。本文件本身不含任何厂商原语，RAM 都在子模块里。",
  impl=[
    "■ 本文件没有 always 块、没有 assign、没有寄存器，只有 wire 声明与两个模块例化，所以它的综合结果就是这两个实例以及它们之间的连线。",
    "■ 工程实际参数由上层决定：isp_top.v:116-121 传 IMG_HEIGHT=720 / IMG_WIDTH=1280 / data_complete_delay=50 / BAYER_MODE=\"BGGR\"，因此本文件里 1080/1920 的默认值在本工程不生效。",
    "■ IMG_WIDTH=1280 时 IMG_WIDTH_4x=(IMG_WIDTH>>2)=320，即一拍 4 个像素、每行 320 拍；行缓存内部硬编码的地址位宽 [10:0] 只用到其中 320 个地址。",
  ],
  body=[
    (20,'B',"""//---- 模块参数：图像尺寸、整合延时与 Bayer 相位 ----
// IMG_HEIGHT/IMG_WIDTH 在这条链路上只用来推算「一拍 4 像素之后每行有多少拍」（IMG_WIDTH>>2）与行数，不决定任何存储深度。
// 本工程由 isp_top.v:116-121 传入 720 / 1280 / 50 / "BGGR"（SC500CS 输出为 BGGR 相位）；本文件默认的 1080 / 1920 在本工程不生效。"""),
    (27,'B',"""//---- 时钟与复位 ----
// 单时钟域：I_clk 在工程中接 axi4s_video_aclk，两个子模块共用它；I_rst_n 低有效、异步复位（posedge I_clk or negedge I_rst_n）。"""),
    (30,'B',"""//---- AXI4-Stream 输入：RAW10，4 个像素/拍 ----
// axi4s_video_tdata[39:0] 是 4 个像素 × 10bit（每个 10bit 一个像素，取高 8 位用）；
// axi4s_video_tdest[9:0] 在本链路里没有被消费；tuser 标帧首、tlast 标行尾、tvalid 标数据有效，tready 由本模块回压给上一级。"""),
    (37,'B',"""//---- AXI4-Stream 输出：RGB888，4 个像素/拍 ----
// O_tdata[127:0] = 4 个像素 × 32bit，每 32bit 是 {8'b0, R[7:0], G[7:0], B[7:0]}，即高 8 位恒为 0。"""),
    (45,'B',"""//---- 内部互连：两个子模块之间的全部信号 ----"""),
    (51,'B',"""// 下面三根 96bit 各是一个「6 像素」滑窗：[71:64] 与 [31:24] 各只有 1 个像素，是插值时额外要用的两个边界像素
// （在 bilinear_interpolation.v 里被拆成 matrix13 与 matrix18；这两个槽位谁对应图像左、谁对应图像右，未能从本文件确认）；
// 中间的 [63:32] 才是这一拍输出的 4 个像素，对应插值模块里的 matrix14..matrix17。"""),
    (55,'B',"""//---- 例化 1：3×3 窗口缓存（里面含 RAW10 -> RAW8、BRAM 整合与两级行缓存） ----
// 它同时给出 bayer_ypos（Bayer 行相位）与三行窗口；详细机制见 raw_matrix_3x3_buffer.v 的注释。"""),
    (82,'B',"""//---- 例化 2：双线性插值 ----
// BAYER_MODE 原样透传给插值模块，由它内部用 generate 选中对应相位分支；本工程是 "BGGR"。
// 整条链路的时延 = 窗口缓存内部的时延 + 插值模块内部的 5 级流水（见 bilinear_interpolation.v）。"""),
  ])

# ====================== mipi_to_raw_converter.v ======================
FILES["mipi_to_raw_converter.v"] = dict(
  path="isp/demosaic_4x_2_0/mipi_to_raw_converter.v",
  module="mipi_to_raw_converter",
  func="位宽/格式转换：把 MIPI CSI-2 侧 40bit/拍的 RAW10（4 个像素 × 10bit）各取高 8bit，拼成 32bit/拍的 RAW8（4 个像素 × 8bit），并把 tlast/tuser/tvalid 跟着数据一起打 1 拍；tready 直通，不做反压。",
  datapath="I_raw_tdata[39:0] -> 取 {[9:2], [19:12], [29:22], [39:32]} -> raw_data_r0[31:0]（寄存器，1 拍延迟）-> O_raw_tdata[31:0]；I_raw_tlast/tuser/tvalid -> 3 个 1bit 寄存器（同样 1 拍）-> O_raw_tlast/tuser/tvalid",
  clock="单时钟域 I_clk；I_rst_n 低有效，异步复位（posedge I_clk or negedge I_rst_n）。",
  deps="无子模块、无厂商原语、无 RAM，纯 RTL 寄存器与连线。",
  impl=[
    "■ 只有 2 个 always 块：1 个给数据打拍、1 个给流控信号打拍；寄存器一共 4 个（raw_data_r0[31:0] 与 3 个 1bit）。",
    "■ 数据与 tlast/tuser/tvalid 是同一拍一起打的，所以输出相对输入整体固定延迟 1 拍，这 4 个信号彼此同相。",
    "■ I_raw_tready 直接接 O_raw_tready，是纯组合连线；本模块不产生背压、也不做跨时钟处理。",
  ],
  body=[
    (20,'B',"""//---- 端口：RAW10 输入侧 ----"""),
    (32,'B',"""//---- 端口：RAW8 输出侧（4 个像素/拍） ----"""),
    (39,'B',"""//---- 寄存器声明：数据 1 拍 + 流控 1 拍 ----"""),
    (45,'B',"""//---- 数据格式转换：RAW10（4 个 10bit）-> RAW8（4 个 8bit） ----"""),
    (46,'B',"""// 只取每个 10bit 像素的高 8bit（丢掉低 2bit）：RAW10 里高 8 位承载的灰度信息占绝大部分，
// 直接截断就能满足后面 8bit/像素的链路，不必做 10->8 的缩放。"""),
    (50,'I',"// 位拼接顺序：I_raw_tdata[9:2]->[31:24]、[19:12]->[23:16]、[29:22]->[15:8]、[39:32]->[7:0]，即 10bit 字段自低位起依次落到 MSB 侧；哪个字段对应图像左侧未能从本文件确认"),
    (56,'B',"""//---- 流控信号打拍：tlast/tuser/tvalid 与数据同拍延迟 1 ----"""),
    (68,'B',"""//---- 输出连线：数据与流控同相，tready 纯组合直通 ----"""),
    (74,'I',"// 纯组合直通：本模块不做反压，上一级的 ready 就是下一级的 ready"),
  ])

# ====================== line_buffer_demosaic.v ======================
FILES["line_buffer_demosaic.v"] = dict(
  path="isp/demosaic_4x_2_0/line_buffer_demosaic.v",
  module="line_buffer_demosaic",
  func="单行缓存（1 行延迟）：把 33bit/拍的输入（32bit 数据 + 1bit tuser）写进一块双口 BRAM，再用一个和写地址同规律推进、但要等第 1 行写满之后才启动的读地址把它读出来，于是在输出端拿到的是「上一行同一列」的数据，供 3×3 窗口取行用。",
  datapath="I_data[32:0] -> data_d0（打 1 拍）-> blk_mem_gen_demosaic 端口 A 写（addra，0..IMG_WIDTH_4x-1）-> 端口 B 用 addrb 读 -> O_data[32:0]；I_valid -> valid_d0 -> 既是写使能也决定 O_valid",
  clock="单时钟域 I_clk，BRAM 的 clka/clkb 都接 I_clk；I_rst_n 低有效，帧首信号 I_tuser 用来把 addra / addrb / tlast_lock_d0 清零。",
  deps="例化 blk_mem_gen_demosaic（同目录 isp/demosaic_4x_2_0/blk_mem_gen_demosaic/，安路 TD 6.1.155545 生成的 BRAM 包装：33bit × 2048 深、地址位宽 11、端口 B 只读）。",
  impl=[
    "■ 本文件唯一的存储就是那 1 块 BRAM；没有别的 RAM，也没有乘法/除法，只有比较与自增。",
    "■ 地址寄存器是硬编码的 [10:0]（2048 深），不随 IMG_WIDTH 变化；本工程 IMG_WIDTH=1280 时 IMG_WIDTH_4x=320，只占 320 个地址，其余深度空置。",
    "■ 「读比写晚整整一行」不是靠地址减法实现的，而是靠 tlast_lock_d0：写侧从帧首就开始写，读侧必须等写地址第一次回绕（也就是第 1 行写完）才放行，之后读写以相同速率推进。",
    "■ 一处未能在代码内确认的点：包装内 IP 参数写的是 REGMODE_A/REGMODE_B(\"NOREG\")，而 raw_matrix_3x3_buffer.v:194 的既有注释是按「BRAM 输出延迟 1 拍」来解释三行对齐的；本注释只按代码既有说明描述对齐关系，没有断言硬件实际读延迟。",
  ],
  body=[
    (20,'B',"""//---- 参数：图像宽高（只用于推算每行拍数） ----
// IMG_WIDTH 只用来算 IMG_WIDTH_4x（一拍 4 个像素之后每行有多少个 32bit 字）；IMG_HEIGHT 在本文件内其实没有被使用到。"""),
    (24,'B',"""//---- 端口 ----"""),
    (33,'B',"""//---- 内部信号 ----"""),
    (36,'B',"""//---- 地址计数器与数据寄存器 ----
// 注意 data_d0 是 33bit，比数据多出的最高位 [32] 放的是 tuser，这样 tuser 能和这一行的数据一起被存进 BRAM、一起读出来。"""),
    (42,'B',"""//---- 每行拍数 ----
// IMG_WIDTH_4x = IMG_WIDTH >> 2：一拍搬 4 个像素，所以一行的拍数就是宽度除以 4；本工程 1280 => 320。
// 地址寄存器是硬编码的 [10:0]（2048 深），不随这个 localparam 变化。"""),
    (45,'B',"""//---- 输入数据打 1 拍：写进 BRAM 的时序对齐 ----"""),
    (56,'B',"""//---- 写地址计数器 addra：每个有效输入拍 +1 ----"""),
    (62,'I',"// 到 IMG_WIDTH_4x-1 回绕到 0：一拍 4 个像素，所以一行的拍数就是 IMG_WIDTH_4x"),
    (68,'B',"""//---- 第一次写满一行后锁定 tlast_lock_d0 ----"""),
    (72,'I',"// 只在 addra 第一次走到行尾时置 1，一旦置 1 就一直保持到下一帧 tuser，因此它等价于「第 1 行已经写完了」"),
    (77,'B',"""//---- 读使能 rd_en ----"""),
    (78,'I',"// 必须同时满足「这一拍有输入数据」与「第 1 行已经写完」才允许读；这就是本模块相对输入整整延迟一行的地方"),
    (81,'B',"""//---- 读地址计数器 addrb：与 addra 同样的回绕规律，但只在 rd_en 有效时走 ----"""),
    (87,'I',"// 读地址因此始终与写地址同步推进（都从 0 走到 IMG_WIDTH_4x-1），读到的就是同一地址上一次写入的内容，即上一行同列的数据"),
    (93,'B',"""//---- 输出有效：与读出的数据同拍 ----"""),
    (94,'I',"// 与 O_data 同相：valid_d0 有效且第 1 行已写完时，读出的数据才是有效的上一行数据"),
    (98,'B',"""//---- 例化单行 BRAM（双口，读写同钟） ----
// 端口 A 负责写（clka=I_clk、wea=valid_d0、addra、dia=data_d0），端口 B 只负责读（clkb=I_clk、addrb），dob 就是读出的上一行数据。
// 本实例没有接端口 B 的写信号（dib/web）与端口 A 的读输出（doa），所以它是「A 写 B 读」的用法。"""),
  ])

# ============================== zhenghe.v ==============================
FILES["zhenghe.v"] = dict(
  path="isp/demosaic_4x_2_0/zhenghe.v",
  module="zhenghe",
  func="流控「整合」：用一块双口 BRAM 把 4 个像素/拍（DATA_WIDTH 位，本工程 32bit）的输入先存进去，再按自己测出来的行长把它读出来，同时重新生成 tuser/tlast/tvalid，使输出的一行与输入的一行重新对齐；每帧由 I_tuser 重新复位，因此不会串到下一帧去。",
  datapath="I_tdata[DATA_WIDTH-1:0] -> data_d0（打 1 拍）-> blk_mem_gen_zhenghe 端口 A 写（addra）-> 端口 B 用 addrb 读 -> data_d -> O_tdata；I_tlast/I_tuser/I_tvalid -> 打拍 + 计数 -> 重新生成 O_tlast/O_tuser/O_tvalid",
  clock="单时钟域 I_clk（BRAM 两端同钟）；I_rst_n 低有效；I_tuser（帧首）复位 addra/addrb/y_cnt/x_cnt，所以每一帧都重新对齐。",
  deps="例化 blk_mem_gen_zhenghe（同目录 isp/demosaic_4x_2_0/blk_mem_gen_zhenghe/ 下的安路 BRAM 包装）。本模块没有 tready 端口，不做反压。",
  impl=[
    "■ 默认参数是 [12:0] IMG_WIDTH=640、IMG_HEIGHT=480、[8:0] DATA_WIDTH=96、data_complete_delay=50；但本工程在 raw_matrix_3x3_buffer.v:153-158 例化时把 DATA_WIDTH 覆盖成 32、IMG_WIDTH/IMG_HEIGHT 传 1280/720，所以这里的默认值在本工程不生效。",
    "■ 地址寄存器硬编码 [10:0]（2048 深）；IMG_WIDTH_4x = IMG_WIDTH>>2 是一拍容纳的 4 像素组数，1280 时等于 320。",
    "■ 行长不是直接照抄参数，而是用帧首第一行实测到的 cnt_first 来修正（只有实测值 > IMG_WIDTH_4x 时才采用），用来容忍上游实际给的拍数与参数不一致。",
    "■ 每行读出的拍数恰好是一整行：rd_valid 的上下界之差再减 1 正好等于 IMG_WIDTH_4x，见下面 rd_valid_width_d0/d1 的注释。",
    "■ 声明情况：rd_valid 在本文件内没有显式声明，是 assign 左值产生的隐式 1bit wire（综合/仿真时会有 implicit wire 警告）；其余信号都有显式声明。",
  ],
  body=[
    (21,'B',"""//---- 参数：行长、行数与数据位宽 ----
// 这里的默认值只是形参初值；本工程实际由 raw_matrix_3x3_buffer.v:153-158 覆盖为 IMG_WIDTH=1280 / IMG_HEIGHT=720 / DATA_WIDTH=32。
// data_complete_delay 的含义见文件头注释：一行数据在 BRAM 里传完之后，与这一行最后一个数据之间的距离。"""),
    (27,'B',"""//---- 端口：纯流式，没有 tready（本模块不做反压） ----"""),
    (41,'B',"""//---- 内部寄存器与线网 ----"""),
    (45,'I',"// 行计数器：每来一个行尾（I_tlast_d0）加 1，帧首 I_tuser 清零；只在本模块内部用来标记「第几行」"),
    (46,'I',"// 行内拍计数器：flag_valid 为高的期间每拍加 1，离开有效区就清零；它是下面读窗口判据的唯一时间基准"),
    (49,'B',"""//---- 每行拍数 ----
// IMG_WIDTH_4x = IMG_WIDTH >> 2：一拍 4 个像素，所以一行的拍数就是宽度除以 4；本工程 1280 => 320。"""),
    (51,'B',"""//---- 派生信号：有效区标志、读窗口边界与行列计数器 ----"""),
    (60,'B',"""//---- 输入信号打 1 拍：数据、有效、行尾、帧首各打一拍，让它们同相 ----"""),
    (81,'B',"""//---- 用「帧首第一行实测的拍数」修正有效行长 ----
// flag_valid_first 在帧首置 1、在第一个行尾清 0，只罩住第一行；cnt_first 就是这一行实际来了多少拍。
// valid_width 默认取 IMG_WIDTH_4x，只有当实测值比它大时才改用实测值（防御上游拍数与参数不一致）。"""),
    (100,'I',"// 每帧开头先回到参数值 IMG_WIDTH_4x，再按实测值修正一次，所以行长是「每帧重新确认」的"),
    (106,'B',"""//---- 行计数器 y_cnt：每个行尾 +1 ----"""),
    (114,'B',"""//---- 行内有效区标志 ----
// flag_valid_d0 罩住「本行从第 1 个数据到最后一个数据」，flag_valid_d1 罩住「本行最后一个数据到下一行第 1 个数据」，
// 两者相或得到 flag_valid：它在一行里几乎一直为高，只在行首那一两拍短暂变低，x_cnt 就是靠这一次变低回到 0，从而完成行同步。"""),
    (133,'B',"""//---- 读窗口的上下界（都以 x_cnt 计） ----
// rd_valid_width_d0 = valid_width - IMG_WIDTH_4x + data_complete_delay：读出起点相对行首的偏移；
// rd_valid_width_d1 = valid_width + data_complete_delay + 1：读出终点。
// 两者之差再减 1 恰好等于 IMG_WIDTH_4x，也就是说每行只读出一整行的字数（1280 时是 320 拍）。"""),
    (134,'I',"// 读出起点：行长与参数一致时 (= IMG_WIDTH_4x) 就等于 data_complete_delay"),
    (135,'I',"// 读出终点：比起点多 IMG_WIDTH_4x+1，所以 rd_valid 的有效拍数正好是一整行"),
    (137,'B',"""//---- 列计数器 x_cnt：行内位置 ----
// flag_valid 为高时每拍加 1，flag_valid 为低（行首那一两拍）时清零；上面所有读窗口判据都比对的是它。"""),
    (146,'I',"// rd_valid 没有显式声明，靠这条 assign 产生隐式 1bit wire；它同时决定 addrb 是否推进和 O_tvalid"),
    (149,'B',"""//---- A 端口：写入 ----
// 写地址在帧首清零，之后每个有效输入拍 +1，到 IMG_WIDTH_4x-1 回绕，因此写地址就是「行内位置」。"""),
    (159,'B',"""//---- B 端口：读出 ----
// 读地址只在 rd_valid 有效时 +1，回绕条件与写地址相同，因此读指针始终跟着写指针走，读出的就是先前写进去的那一行。"""),
    (167,'B',"""//---- 例化 BRAM（双口，读写同钟） ----
// 端口 A 写（clka=I_clk、wea=valid_r0、addra、dia=data_d0），端口 B 只读（clkb=I_clk、addrb），dob 就是读出的数据。"""),
    (176,'B',"""//---- 输出流控与数据的重新生成 ----
// 帧首 O_tuser_d 用「x_cnt 恰好落在读出起点、且还在第 0 行」来判断，所以它标志的是「读出数据流的帧首」而不是输入帧首；
// O_tvalid_d 直接就是 rd_valid；O_tlast_d 落在读出终点前一拍。"""),
    (177,'I',"// 读出第 0 行的第一个数据那一拍：即输出帧首"),
    (180,'I',"// 读出终点前一拍：即输出行尾"),
    (183,'B',"""//---- 输出再打 1 拍，与 BRAM 读出的数据对齐 ----"""),
  ])

# ====================== raw_matrix_3x3_buffer.v ======================
FILES["raw_matrix_3x3_buffer.v"] = dict(
  path="isp/demosaic_4x_2_0/raw_matrix_3x3_buffer.v",
  module="raw_matrix_3x3_buffer",
  func="3×3 邻域窗口生成：先用 mipi_to_raw_converter 把 40bit 的 RAW10 变成 32bit 的 RAW8，再用 zhenghe 做 BRAM 整合，然后用两级 line_buffer_demosaic 分别取到「上一行」「上两行」的数据；三行数据各配一个 96bit 滑窗寄存器，输出 3 行 × 6 像素的邻域窗口，并给出 Bayer 行相位 bayer_ypos，供双线性插值使用。",
  datapath="axi4s_video_tdata[39:0] -> mipi_to_raw_converter -> raw_data[31:0]（4 个像素 × 8bit）-> zhenghe -> data[0] -> line_buffer_demosaic ×2（generate 展开）-> data[1]（上一行）、data[2]（上两行）-> 打拍对齐 -> matrix_last_line / matrix_cur_line / matrix_next_line[95:0] + bayer_ypos",
  clock="单时钟域 I_clk（所有子模块与 BRAM 同钟）；I_rst_n 低有效、异步复位；帧首用 zhenghe_tuser 复位 h_cnt / v_cnt 与三行缓冲。",
  deps="例化 mipi_to_raw_converter、zhenghe、line_buffer_demosaic（都在 isp/demosaic_4x_2_0/ 下）；line_buffer_demosaic 内部再例化 blk_mem_gen_demosaic。",
  impl=[
    "■ 本文件一共例化出 3 块 BRAM IP：2 块 blk_mem_gen_demosaic（两级行缓存）+ 1 块 blk_mem_gen_zhenghe，是这条 demosaic 链路 RAM 数的主要来源；三行滑窗本身只是寄存器（移位拼接），不占 RAM。",
    "■ 参数 IMG_HEIGHT/IMG_WIDTH 默认 1080/1920，本工程由 isp_top.v:116-121 传 720/1280；IMG_WIDTH_4x = IMG_WIDTH>>2 = 320 既是每行字数，也是 h_cnt/v_cnt 的回绕值。",
    "■ 全文件没有任何乘法与除法，只有比较、拼接、移位（IMG_WIDTH>>2）与加法。",
    "■ 边界处理不用补零，而是复制边界像素（行首把第 1 个像素复制到左邻位、行尾把最后 1 个像素复制到右邻位），这样图像右/左边缘不会因为补零而出现黑边或变暗。",
  ],
  body=[
    (21,'B',"""//---- 参数：图像尺寸与整合延时 ----
// IMG_HEIGHT/IMG_WIDTH 只在下面推算每行拍数（IMG_WIDTH>>2）与计数器回绕值；本工程由 isp_top.v:116-121 传 720/1280。"""),
    (27,'B',"""//---- 端口 ----"""),
    (49,'B',"""//---- 功能函数：clog2b（本文件内没有被调用） ----
// 这是一个「求表示 depth 需要多少 bit」的函数，但下面没有任何地方调用它，也没有用它推导过任何位宽；
// 位宽在本文件里都是直接写死的（见常数声明）。"""),
    (66,'B',"""//---- 常数声明 ----
// N=3 是 3×3 矩阵的边长；DATA_WIDTH=32 是一拍 4 个 8bit 像素；
// IMG_WIDTH_4x = IMG_WIDTH>>2 是「一拍 4 像素」之后每行的字数（本工程 1280 => 320），下面 h_cnt/v_cnt 的回绕值就用它。"""),
    (72,'B',"""//---- 线网（wire）声明 ----"""),
    (95,'B',"""//---- 寄存器声明 ----
// matrix_*_line_buffer 是 96bit 滑窗（不是 RAM）：中间 4 个字节是本拍输出的 4 个像素，左右各 1 个字节是插值要用的邻像素。"""),
    (113,'B',"""//---- 组合逻辑 ----"""),
    (123,'B',"""//---- 矩阵滑窗输出：三行窗口直接送给插值模块 ----"""),
    (129,'B',"""//---- Bayer 行相位判断 ----
// bayer_ypos_d0 = !v_cnt_d[0] & ch_valid：用「中心行的行号最低位」来区分两种行相位。
// BGGR 下同一行里 R/G/B 由列位置决定，而列位置就是下面滑窗里 matrix1x 的下标：
//   下标 4、6 与 5、7 交替，相邻两列必为一色一 G；
//   再配合行相位（本信号），就能确定每个位置到底是 R、Gr、Gb 还是 B。
// v_cnt_d 与 ch_valid 都是打 1 拍之后的量，所以它与同一拍输出的 matrix_*_line 描述的是同一行。"""),
    (130,'I',"// 1 = 中心行处于「含 R、G」的行相位；0 = 「含 B、G」的行相位（插值模块里的 bayer_ypos_r1 就是它再打 2 拍）"),
    (135,'B',"""//---- 例化 1：RAW10 -> RAW8（4 个 8bit/拍） ----"""),
    (152,'B',"""//---- 例化 2：zhenghe（BRAM 弹性整合） ----
// 这里把 DATA_WIDTH 覆盖成 32（与 raw_data 位宽一致），IMG_WIDTH/IMG_HEIGHT 传工程实际值。"""),
    (174,'B',"""//---- 例化 3：两级行缓存（generate 展开成 2 个 line_buffer_demosaic） ----
// i=1：把 data[0] 延迟一行得到 data[1]；i=2：把 data[1] 再延迟一行得到 data[2]。
// 因此 data[0] 是当前收到的行，data[1] 是上一行，data[2] 是上两行（也是空间上最上面那一行）。
// 注意 I_tuser 取的是 data[i-1][32] & valid[i-1]：tuser 就存在 33bit 数据的最高位里，跟着数据一起过 BRAM。"""),
    (194,'B',"""//---- 三行数据对齐打拍 ----
// 每一级 BRAM 的读出口相对写入口会多 1 拍，所以 data[1] 比 data[0] 多 1 拍、data[2] 比 data[0] 多 2 拍。
// 为了让三行在同一拍上对应同一列，这里把 data[0] 再延 2 拍（data_d0_d -> data_d0）、把 data[1] 延 1 拍（data_d1）、data[2] 不延（data_d2）。
// 对齐完成后：data_d2 = 上两行、data_d1 = 上一行、data_d0 = 当前行，三者在同一拍上列号相同。"""),
    (213,'B',"""//---- 3×3 矩阵的形成：滑窗与边界复制填充 ----
// 每个 matrix_*_line_buffer 是 96bit 的滑窗：每拍把 [63:0] 左移 32bit、再把本行最新的 4 个像素字补进 [31:0]。
// 于是 [71:24] 这 48bit（6 个连续像素）天然构成「中间 4 个是本拍输出的像素、两端各多 1 个边界像素」的窗口：
//   [63:32] 的 4 个字节 = 本拍输出的 4 个像素（插值模块里的 matrix14..matrix17）；
//   [71:64] 与 [31:24] 各剩 1 个像素，对应插值模块里的 matrix13 / matrix18（两者的图像左右对应关系未能从本文件确认）。
// 三个行下标：last = 空间上方那行、cur = 中心那行、next = 空间下方那行。
// 边界不补零而是复制边界像素，避免在图像边缘引入黑色边框。"""),
    (223,'B',"// 帧首第一行（v_cnt==0）：上下都没有真实的行，三行一律取当前行，等于「把本行同时当作上一行和下一行」"),
    (224,'B',"// 行首像素：边界槽位 [71:64] 不补零，直接复制本拍的第一个像素 data_d0[31:24]，输出仍是本拍这 4 个像素"),
    (228,'B',"// 行尾像素：边界槽位 [31:24] 复制本行最后一个像素（先把 [63:0] 左移、再把 8bit 的边界像素塞回去），其余位补零"),
    (232,'B',"// 行中间像素：正常滑动，把本拍 4 个像素整体移进最低 32bit"),
    (238,'B',"// 第二行（v_cnt==1）：上面还没有真实行，matrix_last 跟随 matrix_cur，等于把第 1 行复制到上方做边界"),
    (253,'B',"// 第三行及以后：last/cur/next 分别是上两行(data_d2)、上一行(data_d1)、当前行(data_d0)，三行都是真实数据"),
    (269,'I',"// 非有效拍：三行滑窗清零，避免下游把残值当数据用"),
    (276,'B',"""//---- 行列计数器 ----
// h_cnt：每个有效拍 +1，到 IMG_WIDTH_4x-1 回绕到 0。因为一拍搬 4 个像素，所以「一行的拍数」就是 IMG_WIDTH_4x。
// v_cnt：只在行尾（h_cnt 回绕的那一拍）加 1，到 IMG_HEIGHT-1 回绕到 0，因此它就是行号。
// 两者都在帧首由 zhenghe_tuser 清零；h_cnt 回绕与 v_cnt 加 1 用的是同一拍，所以行号与列位置的配合不会错位。"""),
    (282,'I',"// h_cnt 回绕条件：IMG_WIDTH_4x-1，即每行最后一个字"),
    (283,'I',"// v_cnt 只在 h_cnt 回绕那一拍加 1；到 IMG_HEIGHT-1 回绕，保证帧内行号单调"),
    (287,'B',"""//---- 有效信号与行相位的延迟对齐 ----
// ch_valid 是再打 1 拍的有效信号，与同一拍输出的 matrix_*_line 严格同相；
// v_cnt_d 同样再打 1 拍，用它的最低位给出 bayer_ypos，正好对应同一行。"""),
    (298,'I',"// 对外的行相位就是上面算出来的 bayer_ypos_d0，它经过 ch_valid 门控，非有效拍时为 0"),
    (300,'B',"""//---- 流控信号同步 ----
// tuser/tlast 各打 3 拍，使它们与已经过 3 拍（BRAM 打拍 + 上面的对齐打拍）的数据重新对齐，然后才输出。"""),
    (321,'I',"// 输出帧首（与数据同相）"),
    (322,'I',"// 输出行尾（与数据同相）"),
    (323,'I',"// 输出数据有效：ch_valid 与 matrix_*_line 同拍"),
  ])

# ==================== bilinear_interpolation.v ====================
FILES["bilinear_interpolation.v"] = dict(
  path="isp/demosaic_4x_2_0/bilinear_interpolation.v",
  module="bilinear_interpolation",
  func="双线性去马赛克插值：对 3×3 窗口里的 4 个像素（matrix14..matrix17）分别算出 R/G/B 三个通道——本来就是这个颜色的像素取原值，缺的颜色用同色邻居的算术平均代替。全部运算只有加法与 >>1（除以 2）、>>2（除以 4），没有任何乘法。",
  datapath="matrix_last/cur/next_line[95:0] + bayer_ypos -> 拆成 3 行 × 6 像素（matrix03..matrix28）-> 按相位求部分和（sum_part0/1，9bit）-> 总和（matrix_plus，10bit）-> 均值（mean，9bit，按相位选择不除 / >>1 / >>2）-> 8bit 饱和 -> 打包成 {8'b0,R,G,B} × 4 -> rgb_data[127:0] -> O_tdata[127:0]",
  clock="单时钟域 I_clk；I_rst_n 低有效，异步复位。内部共 5 级流水（部分和 -> 总和 -> 均值 -> 饱和 -> 打包），输出有效信号 I_tvalid_r[4] 就是 I_tvalid 打 5 拍的结果。",
  deps="无子模块、无 RAM、无 DSP（没有任何乘法）；只用 generate 按 BAYER_MODE 选择相位分支。",
  impl=[
    "■ 四个相位分支（BGGR / GBRG / RGGB / GRBG）用 generate if / else if 并列展开，同一时刻只有一个分支会被实现；本工程由 isp_top.v:116-121 传 BAYER_MODE=\"BGGR\"，所以实际综合出来的只有 BAYER_MODE_BGGR 这一个分支。",
    "■ 位宽关系：sum_part* 是 9bit（2 个 8bit 相加），matrix_plus 是 10bit（最多 4 个 8bit 相加），mean 是 9bit（最高位 [8] 用来判断结果是否超过 255），最后饱和成 8bit。",
    "■ 本文件自带的 version 2.0 文件头记录的是上游（官方）修正 RGGB/GBRG 分支里三元操作符判断分支写反的问题；本工程自官方 lab3 基线导入后没有再改动本文件。",
    "■ 算法性质：这是纯线性平均的双线性插值，没有沿边缘方向的梯度比较与方向修正，因此在高频细节处会产生 zipper（拉链）伪影与伪彩，详见下面「算法性质」那段注释。",
  ],
  body=[
    (22,'B',"""//---- 模块参数：Bayer 相位 ----
// BAYER_MODE 决定用下面哪一个 generate 分支；本工程传 "BGGR"。
// 四个分支的差别只是「哪一路该取平均、哪一路该取原值」的相位互换，算法结构完全相同。"""),
    (25,'B',"""//---- 端口：窗口输入 + 4 像素 RGB 输出 ----"""),
    (48,'B',"""//---- function 与相位常量 ----"""),
    (74,'B',"""//---- 寄存器声明：三级流水对应的三组寄存器 ----
//  *_sum_part0 / *_sum_part1（9bit）：一拍最多 2 个 8bit 像素相加得到的部分和，拆成两组是为了让相加不至于一次太长；
//  *_matrix_plus（10bit）：两个部分和再相加得到的总和（最多 4 个像素之和）；
//  *_mean（9bit）：总和除以 1 / 2 / 4 之后的通道均值，最高位 [8] 留作溢出判断。"""),
    (100,'B',"""// 下标约定：r0..r3 / g0..g3 / b0..b3 就是同一拍 4 个像素各自的三个通道；
// 它们与下面 96bit 窗口里的 matrix14..matrix17 一一对应（r0 对 matrix14、r1 对 matrix15、r2 对 matrix16、r3 对 matrix17）。"""),
    (106,'B',"""// 4 个像素的 RGB 打包结果，每个像素 32bit = {8'b0, R[7:0], G[7:0], B[7:0]}"""),
    (111,'B',"""// 流水线有效信号：I_tvalid_r 是 5 位移位寄存器，每位对应一级流水
//   I_tvalid      -> 求部分和；[0] -> 求总和；[1] -> 求均值；[2] -> 8bit 饱和；[3] -> 打包；[4] -> 送输出"""),
    (118,'B',"""//---- 6 像素滑窗的拆线 ----
// matrix_*_line 是 96bit：[95:72] 补零、[71:64] 与 [31:24] 各只剩 1 个像素、中间 [63:32] 是 4 个像素。
// 这里把三行各自的 [71:24] 拆成 6 个 8bit 像素：
//   matrixX3 = 边界槽位 [71:64] 里的那 1 个像素（位于中心 4 像素的一侧，对应图像左还是右未能从本文件确认）
//   matrixX4..matrixX7 = 本拍要输出的 4 个像素
//   matrixX8 = 边界槽位 [31:24] 里的那 1 个像素（位于中心 4 像素的另一侧，对应图像左还是右未能从本文件确认）
// 行下标 X：0 = 上一行（空间上方）、1 = 中心行、2 = 下一行；列下标 Y 越大越靠近 MSB 端（左右对应关系同上未能确认）。"""),
    (135,'B',"""//---- 信号延迟：Bayer 行相位打 2 拍 ----
// bayer_ypos_r0 是 bayer_ypos 打 1 拍、bayer_ypos_r1 再打 1 拍；
// 因为求均值那一级（用 I_tvalid_r[1] 门控）比输入晚了 2 拍，所以相位也要跟着延迟 2 拍才能对齐。"""),
    (154,'B',"""//---- 算法性质：纯线性平均的双线性插值（这是已知的画质特性，不是缺陷报告） ----
// 本模块对每个像素只用「同色邻居的算术平均」来估计缺失的两个通道，全部运算只有加法与 >>1（除以 2）、>>2（除以 4），
// 没有任何乘法，也没有沿水平/垂直方向的梯度比较与方向修正。因此在高频细节（细密条纹、锐利边缘）处会有两类已知伪影：
//   · zipper（拉链）伪影：边缘两侧的插值结果沿边缘方向交替偏亮/偏暗，看起来像拉链；
//   · 伪彩：R/B 平面在高频处被错误平均，在边缘上出现原本并不存在的颜色。
// 这是本工程做画质调优时的已知结论，只说明机制，不代表本文件相对某个版本有缺陷。"""),
    (160,'B',"""//---- BGGR 相位：bayer_ypos=1 时中心行是「G R G R」，bayer_ypos=0 时是「B G B G」 ----
// 每拍对 4 个像素（matrix14..matrix17）各算 R/G/B 三个通道，取法只有四种：
//   · 像素本身就是这个颜色（例如相机阵列在该位置的滤色片就是它）-> 直接取原值，不除；
//   · 同行的左右两个同色邻居 -> 相加后 >>1（除以 2）；
//   · 上下的两个同色邻居     -> 相加后 >>1（除以 2）；
//   · 只有上/下/左/右的 4 个同色邻居 -> 相加后 >>2（除以 4）。
// 判断用哪一路，靠的就是 bayer_ypos_r1 给出的行相位加上像素在 4 个位置里的下标（列相位）。"""),
    (162,'B',"""//---- BGGR 的 R 通道：算出 4 个像素各自需要的 R 之和 ----
// 每个求和拆成 part0/part1 两组（各不超过 2 个像素），下一拍再相加成总和。"""),
    (196,'B',"""//---- BGGR 的 G 通道：算出 4 个像素各自需要的 G 之和 ----"""),
    (233,'B',"""//---- BGGR 的 B 通道：算出 4 个像素各自需要的 B 之和 ----"""),
    (266,'B',"""//---- 两组部分和相加成通道总和（10bit，最多 4 个 8bit 像素） ----"""),
    (293,'B',"""//---- 除以 1 / 2 / 4 得到通道均值：整段只用 >>1 与 >>2，没有乘法 ----
// 每个均值都是一句三元表达式：bayer_ypos_r1 为真时走一支、为假时走另一支，
// 「不移位」表示这一路本来就是原值，「>>1」表示 2 个同色邻居的平均，「>>2」表示 4 个同色邻居的平均。"""),
    (301,'I',"// r0=matrix14：中心行是 G R G R 时，它的 R 只能取本行左右两个 R（2 个样本 -> >>1 除以 2）；是 B G B G 时取 4 个对角 R（4 个样本 -> >>2 除以 4）"),
    (302,'I',"// g0=matrix14：前一种相位它本身就是 G（取原值，不移位）；后一种相位取上/下/左/右 4 个 G（>>2 除以 4）"),
    (303,'I',"// b0=matrix14：前一种相位取上下两个 B（>>1 除以 2）；后一种相位它本身就是 B（取原值）"),
    (305,'I',"// r1=matrix15：G R G R 行里它本身就是 R（原值）；B G B G 行里取上下两个 R（>>1 除以 2）"),
    (306,'I',"// g1=matrix15：G R G R 行里它本身是 R，要取上/下连同行的 4 个 G（>>2 除以 4）；B G B G 行里它本身就是 G（原值）"),
    (307,'I',"// b1=matrix15：G R G R 行里取 4 个对角 B（>>2 除以 4）；B G B G 行里取同行左右两个 B（>>1 除以 2）"),
    (309,'I',"// r2=matrix16：与 r0 同构，只是邻像素取的是 matrix15/matrix17 那一侧"),
    (310,'I',"// g2=matrix16：与 g0 同构"),
    (311,'I',"// b2=matrix16：与 b0 同构"),
    (313,'I',"// r3=matrix17：与 r1 同构（它是这一拍 4 个像素里最右边那个）"),
    (314,'I',"// g3=matrix17：与 g1 同构"),
    (315,'I',"// b3=matrix17：与 b1 同构"),
    (327,'B',"""//---- GBRG 分支：算法结构与 BGGR 完全相同，但相位条件整体取反 ----
// 本分支的三元表达式写成 bayer_ypos_r1 ? 平均 : 原值 或 (!bayer_ypos_r1) ? ... : ...，
// 与 BGGR 的写法相反（文件头 version 2.0 提到的「RGGB/GBRG 的条件判断分支颠倒」就是指这里）；
// 阅读时请把每个「?」与「:」的两支和 BGGR 对照，注意哪一支是原值、哪一支是 >>1/>>2 的平均。"""),
    (467,'B',"""//---- GBRG 的均值级：同样只用 >>1 与 >>2，条件取反 ----"""),
    (498,'B',"""//---- RGGB 分支：结构同 BGGR，条件同样写成 (!bayer_ypos_r1)，即与 BGGR 相反 ----
// 文件头 version 2.0 的修改说明就是针对 RGGB / GBRG 这两个分支的条件写法。"""),
    (638,'B',"""//---- RGGB 的均值级：条件取反，注意「原值」与「平均」两支的位置 ----"""),
    (671,'B',"""//---- GRBG 分支：结构同 BGGR，条件同样取反（GRBG 与 BGGR 的相位正好相差一个像素） ----"""),
    (813,'B',"""//---- GRBG 的均值级：条件取反 ----"""),
    (844,'B',"""//---- 8bit 饱和 ----
// 均值是 9bit，最高位 [8] 为 1 就说明结果已经超过 255（多个 8bit 相加后溢出），这时钳到 255；否则取低 8bit。
// 正常情况下 4 个样本的均值最大就是 255、2 个样本的均值也是最大 255，所以这里主要是防御性钳位。"""),
    (855,'I',"// mean[8] 为 1 表示 >255：钳到 255，否则截取低 8bit（r/g/b 三通道同样的写法，共 12 行）"),
    (873,'B',"""//---- 打包成 {8'b0,R,G,B}，再把 4 个像素拼成 128bit ----"""),
    (882,'I',"// 一个像素 32bit = {8'b0, R, G, B}；rgb_data0..3 分别对应本拍的 4 个像素"),
    (890,'B',"""//---- 输入流控信号打 5 拍，与上面 5 级流水对齐 ----
// I_tlast_r / I_tuser_r / I_tvalid_r 都是 5 位移位寄存器，[4] 出来的信号正好落在数据那一级上。"""),
    (904,'I',"// 输出行尾：与 O_tdata 同相（已延迟 5 拍）"),
    (905,'I',"// 输出帧首：与 O_tdata 同相"),
    (906,'I',"// 输出数据有效：与 O_tdata 同相"),
    (909,'I',"// 输出数据就是打包好的 128bit"),
    (910,'I',"// 本模块不做反压：上游 ready 直通下游 ready"),
  ])

# =====================================================================
EOL_HEADER = "//============================================================================="
EOL_SEP    = "//-----------------------------------------------------------------------------"


def build_header(d):
    L = [EOL_HEADER,
         "// 文件      : " + d["path"],
         "// 模块      : " + d["module"],
         "// 功能      : " + d["func"],
         "// 数据通路  : " + d["datapath"],
         "// 时钟/复位 : " + d["clock"],
         "// 依赖      : " + d["deps"],
         "// 综合/实现 : " + d["impl"][0]]
    for extra in d["impl"][1:]:
        L.append("//           " + extra)
    L += [EOL_SEP,
          "// 修改记录  :",
          "//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改",
          EOL_SEP,
          "// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\\FPGA\\_analysis\\reports\\rename_report.txt",
          EOL_HEADER]
    return L


def split_lines(t):
    out, i, n = [], 0, len(t)
    while i < n:
        j = t.find("\n", i)
        if j < 0:
            out.append(t[i:])
            break
        out.append(t[i:j + 1])
        i = j + 1
    return out


def strip_comments(code):
    """Remove // and /* */ comments, keep string literals. Needed to prove code is untouched."""
    out, i, n, state = [], 0, len(code), "code"
    while i < n:
        c = code[i]
        if state == "code":
            if c == '"':
                state = "str"; out.append(c); i += 1
            elif c == "/" and i + 1 < n and code[i + 1] == "/":
                state = "line"; i += 2
            elif c == "/" and i + 1 < n and code[i + 1] == "*":
                state = "block"; i += 2
            else:
                out.append(c); i += 1
        elif state == "str":
            out.append(c)
            if c == "\\":
                if i + 1 < n:
                    out.append(code[i + 1]); i += 2; continue
            i += 1
            if c == '"':
                state = "code"
        elif state == "line":
            if c == "\n":
                state = "code"; out.append(c)
            i += 1
        else:  # block
            if c == "*" and i + 1 < n and code[i + 1] == "/":
                state = "code"; i += 2
            else:
                if c == "\n":
                    out.append(c)
                i += 1
    return "".join(out)


def compact(code):
    return re.sub(r"\s+", "", strip_comments(code))


def process(name, d, apply_):
    p = os.path.join(SRC, name)
    raw = open(p, "rb").read()
    text = raw.decode("gbk")

    # dominant EOL
    eol = "\r\n" if "\r\n" in text else "\n"

    orig_lines = split_lines(text)
    kinds = {}
    for ln, kind, txt in d["body"]:
        kinds.setdefault(ln, []).append((kind, txt))

    # sanity: every target line number exists
    for ln in kinds:
        if not (1 <= ln <= len(orig_lines)):
            return f"[{name}] ERROR target line {ln} out of range (file has {len(orig_lines)} lines)"

    result = []
    n_before = n_inline = 0
    for idx, line in enumerate(orig_lines, start=1):
        body, tail = line, ""
        # split off EOL
        stripped = body
        e = ""
        if stripped.endswith("\n"):
            e = "\n"
            stripped = stripped[:-1]
            if stripped.endswith("\r"):
                e = "\r\n"
                stripped = stripped[:-1]
        body, tail = stripped, e
        for kind, txt in kinds.get(idx, []):
            if kind == "B":
                for t in txt.split("\n"):
                    result.append(t + eol); n_before += 1
            else:
                if "//" in body:
                    return f"[{name}] ERROR inline target line {idx} already has a // comment: {body!r}"
                body = body + "  " + txt; n_inline += 1
        result.append(body + tail)

    header = [h + eol for h in build_header(d)] + [eol]
    new_text = "".join(header) + "".join(result)

    # ---- integrity checks ----
    if compact(text) != compact(new_text):
        return f"[{name}] ERROR code characters changed (compact mismatch)"
    for ol in split_lines(text):
        if ol.rstrip("\r\n") not in new_text:
            return f"[{name}] ERROR original line not preserved: {ol!r}"

    try:
        new_bytes = new_text.encode("gbk")
    except UnicodeEncodeError as ex:
        bad = new_text[ex.start:ex.end]
        return f"[{name}] ERROR not GBK-encodable: {bad!r} at {ex.start}"

    info = (f"{name}: lines {len(orig_lines)} -> {len(split_lines(new_text))}, "
            f"+{n_before} comment lines, +{n_inline} inline comments, "
            f"enc=gkb, eol={repr(eol)}, bytes {len(raw)} -> {len(new_bytes)}")

    if apply_:
        os.makedirs(BAK, exist_ok=True)
        bakp = os.path.join(BAK, name + ".bak")
        shutil.copyfile(p, bakp)
        open(p, "wb").write(new_bytes)
        info += f"  [BAK {bakp}]"
    return info


def main():
    apply_ = "--apply" in sys.argv
    print("APPLY" if apply_ else "DRY-RUN")
    ok = True
    for name, d in FILES.items():
        msg = process(name, d, apply_)
        print(msg)
        if "ERROR" in msg:
            ok = False
    print("ALL OK" if ok else "HAS ERRORS")


main()
