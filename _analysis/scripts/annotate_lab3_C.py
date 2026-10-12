# -*- coding: utf-8 -*-
"""
lab3 / 6 个 Verilog 文件的"只加注释"批处理。
- 以 rb 读 / wb 写，逐字节保留原有换行(全部为 CRLF)与编码(部分文件含 GBK 字节)
- 新插入的注释按 UTF-8 写入(CJK 字符)
- 只做三类操作: 文件头前置、在指定行前插入整行注释、在指定行尾追加行内注释
"""
import io, sys, os, difflib

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

ROOT = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
BAK = r'E:\FPGA\_backup\20261009_comments\awb'

HDR_TPL = """//=============================================================================
// 文件      : {path}
// 模块      : {mod}
// 功能      : {func}
// 数据通路  : {data}
// 时钟/复位 : {clk}
// 依赖      : {dep}
// 综合/实现 : {syn}
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\\FPGA\\_analysis\\reports\\rename_report.txt
//============================================================================="""


def hdr(path, mod, func, data, clk, dep, syn):
    return HDR_TPL.format(path=path, mod=mod, func=func, data=data, clk=clk, dep=dep, syn=syn)


# =============================================================================
# 1. isp/awb/awb.v
# =============================================================================
AWB = dict(
    src=os.path.join(ROOT, r'isp\awb\awb.v'),
    header=hdr(
        path='isp/awb/awb.v',
        mod='awb',
        func='自动白平衡(AWB)。按行统计 4 路像素的 R/G/B 累加和，用除法器求 G/R、G/B 比值作为 R、B 通道增益(20bit Q16 定点)，乘回像素后饱和截断到 8bit 输出，使画面三通道均值趋于一致。',
        data='I_tdata(96bit = 4 像素 × RGB888) → 打 3 拍寄存 → 拆 4 组 RGB888 → 按行累加 sum_r/sum_g/sum_b[0:3] → 4 组 × (G/R、G/B) divider IP 求 Q16 商 → 20bit 增益寄存器 in_r_rX/in_b_rX → signal_delay 缓存 50 拍把像素对齐到增益 → R/B 增益乘法(28bit) → 饱和截断回 8bit → 拼回 96bit。',
        clk='单时钟 I_clk；I_rst_n 低电平异步复位(所有时序块为 posedge I_clk or negedge I_rst_n)；I_tuser(帧首)在统计与增益块中作同步清零，用于按行重开统计窗。',
        dep='divider（TD 生成的除法器网表，定义在 isp/awb/divider/divider_gate.v，参数 PIPLE=50 即流水 50 拍）、signal_delay（本目录内，内部用 blk_mem_gen_awb_delay_signal）。',
        syn='generate for 展开 4 组、共 8 个除法器实例；本模块自身不含 BRAM。默认参数 IMG_HEIGHT=1080/IMG_WIDTH=1920，本工程由 isp_top.v:144 例化为 IMG_HEIGHT=720、IMG_WIDTH=1280。',
    ),
    before={
        60: ['//---- 输入数据/有效信号打拍（3 级流水） ----'],
        64: ['//---- 白平衡统计累加器（4 通道并行，按行清零） ----'],
        99: ['//---- 96bit 拆 4×RGB888（每组 24bit：R@[23:16] G@[15:8] B@[7:0]） ----'],
        120: ['//---- 行内累加：统计窗 = 一整行 ----'],
        164: ['//---- 除法器输出与增益来源 ----'],
        197: ['//---- 除法器 IP 例化：4 通道 × (G/R, G/B)，流水 50 拍 ----'],
        224: ['//---- 数据延迟 50 拍：与除法器流水(DIVIDER 参数 PIPLE=50)对齐 ----'],
        245: ['//---- 增益寄存器（20bit Q16 定点；1.0 = 20\'h10000） ----'],
        257: ['//---- 增益计算与上限钳位（4 通道同构，仅各自 done 拍更新） ----'],
        330: ['//---- 延时链再打 1 拍：把 valid/data/tuser 对齐到同一拍 ----'],
        363: ['//---- 从延时后的 96bit 中再拆 4×RGB888 ----'],
        383: ['//---- 增益乘法：R/B 乘增益，G 旁路 ----'],
        441: ['//---- 输出截断回 8bit：R/B 饱和，G 直通 ----'],
        461: ['//---- 输出同步信号：valid/tuser 打 1 拍，tlast 取 valid 下降沿 ----'],
    },
    eol={
        89: '  // I_tvalid_r0/r1 两级有效信号一并清零',
        91: '  // d0 = 当前输入，与 I_tvalid_r0 同拍',
        92: '  // d1 = 上一拍数据',
        93: '  // d2 在本文件内未见其它引用（仅此处移位）',
        104: '  // 像素0 R = bit[23:16]',
        108: '  // 像素1 R = bit[47:40]',
        112: '  // 像素2 R = bit[71:64]',
        116: '  // 像素3 R = bit[95:88]',
        122: '  // 帧首(I_tuser)同步清零：统计窗按行重开',
        139: '  // 仅在数据有效拍累加',
        172: '  // 通道0：G/R 商（Q16 定点）',
        173: '  // 通道0：G/B 商（Q16 定点）',
        206: '  // 分母 = 本行 R 累加和',
        207: '  // 分子 = G 累加和左移 16 位，使商为 Q16',
        208: '  // quotient ≈ (G/R) × 65536',
        217: '  // 分子同为 G 累加和，分母换成 B 累加和',
        218: '  // quotient ≈ (G/B) × 65536',
        260: '  // R 增益 = 1.0（Q16：65536 = 20\'h10000）',
        261: '  // B 增益 = 1.0',
        265: '  // 上钳位 20\'hfffff = 1048575 ≈ 16.0×（本工程调优认为偏松，拟收紧到 20\'h40000 ≈ 4.0×，本次不改）',
        267: '  // 取商低 20 位（高位已判定为 0，未溢出）',
        269: '  // B 增益同样钳到 ≈16.0×',
        403: '  // 20bit(Q16) × 8bit = 28bit，结果仍为 Q16 → 整数部分在 [27:16]',
        404: '  // G 不乘增益，等价 1.0×',
        442: '  // 整数部分为 [27:16]；若高 4 位 [27:24] 非 0 说明 >255，饱和到 255，否则取 [23:16]',
        443: '  // G 已是 8bit（G_new_r1 高 20 位为 0）',
        474: '  // valid 的下降沿 = 一行数据结束',
        479: '  // 4 个像素合并回 96bit（像素1 位于最低 24bit）',
        485: '  // 无内部缓存，直接透传反压',
    },
)

# =============================================================================
# 2. isp/awb/signal_delay.v
# =============================================================================
SIGDELAY = dict(
    src=os.path.join(ROOT, r'isp\awb\signal_delay.v'),
    header=hdr(
        path='isp/awb/signal_delay.v',
        mod='signal_delay',
        func='用一块 96bit × 2048 的双口 BRAM 把像素数据缓存后延迟读出，并把 valid/tuser 同步延迟；用途是把像素数据对齐到 awb 中除法器 50 拍的流水延迟(DELAY_CYCLE=50)。',
        data='I_data/I_valid → 打 1 拍 → 写口 A(addra 行内递增) → 读口 B(addrb 比写口晚 DELAY_CYCLE-3 拍开读、读满一行停) → O_data；O_valid 为 rd_valid 再打 1 拍，O_tuser 在 v_cnt==0 且 rd_cnt==1 时给出。',
        clk='单时钟 I_clk（读写同源）；I_rst_n 低电平异步复位；I_tuser 作为同步清零条件，复位行列计数与读写地址。',
        dep='blk_mem_gen_awb_delay_signal（安路 IP 包装壳，内部是 PH1_LOGIC_ERAM 真双口原语，见 isp/awb/ram/blk_mem_gen_awb_delay_signal.v）。',
        syn='localparam IMG_WIDTH_4x = IMG_WIDTH>>2：每拍送 4 个像素，故行内节拍数 = 行像素数/4。BRAM 深度 2048 × 96bit。默认参数 1080/1920，实际由 awb 例化时传入（awb.v 中 IMG_HEIGHT/IMG_WIDTH 再来自 isp_top.v 的 720/1280，DELAY_CYCLE=50）。',
    ),
    before={
        34: ['//---- 内部信号 ----'],
        48: ['//---- 输入打 1 拍（写侧数据与使能对齐） ----'],
        59: ['//---- 行列计数器：h_cnt = 行内节拍，v_cnt = 行号 ----'],
        71: ['//---- 读使能：行首第 DELAY_CYCLE-3 拍开读，读满一行关闭 ----'],
        83: ['//---- 读数据计数（判断一行读完） ----'],
        95: ['//---- 写地址（行内递增） ----'],
        104: ['//---- 读地址（行内递增） ----'],
        113: ['//---- 输出有效信号打拍（与 BRAM 读延迟对齐） ----'],
        125: ['//---- BRAM 例化：96bit × 2048 真双口，A 口写 / B 口读 ----'],
    },
    eol={
        34: '  // 读使能（组合）',
        36: '  // 11bit 地址 → 2048 深度',
        37: '  // 读地址',
        40: '  // 行内节拍计数',
        41: '  // 行号计数',
        42: '  // 读节拍计数',
        44: '  // 写入 BRAM 的数据打 1 拍',
        47: '  // 每拍 4 个像素，行内节拍数 = 行像素数 / 4',
        66: '  // 行内节拍递增，到 IMG_WIDTH_4x-1 回卷',
        67: '  // 行号递增，帧末回卷',
        76: '  // 延迟 DELAY_CYCLE-3 拍后开始读（配合 BRAM 读延迟与输出打拍，整体约 50 拍）',
        79: '  // 一行数据读完即停',
        89: '  // 读满一行重新计数',
        100: '  // 写地址行内 +1',
        109: '  // 读地址行内 +1',
        119: '  // 再打 1 拍，与 BRAM 输出 dob 同步',
        123: '  // 第一行且读到第 2 拍时给出帧首标记',
    },
)

# =============================================================================
# 3. isp/awb/ram/blk_mem_gen_awb_delay_signal.v
# =============================================================================
BLKMEM = dict(
    src=os.path.join(ROOT, r'isp\awb\ram\blk_mem_gen_awb_delay_signal.v'),
    header=hdr(
        path='isp/awb/ram/blk_mem_gen_awb_delay_signal.v',
        mod='blk_mem_gen_awb_delay_signal',
        func='安路 TD IP Generator 生成的 ERAM 包装壳：96bit × 2048 真双口 RAM，A 口写、B 口读，内部直接例化 PH1_LOGIC_ERAM 原语。本文件不含任何逻辑，只有参数声明与一次原语例化。',
        data='端口与原语一一对应，不做事理运算：addra/dia/wea/clka → A 口；addrb/clkb → B 口；dob 为 B 口读出数据。',
        clk='clka/clkb 为两个独立时钟，本工程由 signal_delay 接到同一个 I_clk（即同步双口）；RESETMODE 为 ASYNC，但 rsta/rstb 被固定接 1\'b0，故复位实际未参与。',
        dep='PH1_LOGIC_ERAM（安路 PH1 系列嵌入式 RAM 原语，由 TD 工具链提供实现/仿真模型）。',
        syn='参数可被上层重定义；MODE="DP" 真双口；IMPLEMENT="20K(FAST)" 用 20Kbit 块；REGMODE_A/B="NOREG" 表示输出无额外寄存器。',
    ),
    before={
        20: ['//---- 参数：A/B 各 96bit × 2048 深 ----'],
        33: ['//---- 端口：A（写）与 B（读）两套对称端口 ----'],
        49: ['//---- 原语例化：PH1_LOGIC_ERAM，MODE="DP" 真双口 ----'],
    },
    eol={
        20: '  // 每个地址 96bit = 4 个 RGB888 像素',
        21: '  // 11bit 地址',
        22: '  // 深度 2048',
        24: '  // B 口同样 96bit',
        26: '  // 输出无额外寄存器，dob 与 addrb 同拍有效',
        27: '  // 同上（B 口）',
        29: '  // 同址读写时先读出旧值',
        55: '  // DP = 真双口',
        60: '  // 用 20Kbit 块实现',
        71: '  // 不做初始化',
        78: '  // A 口时钟使能常开',
        79: '  // B 口时钟使能常开',
        86: '  // 字节写使能未使用',
        91: '  // ECC 未使用，状态输出悬空',
    },
)

# =============================================================================
# 4. isp/raw10_unpacket_2lane.v
# =============================================================================
RAW10 = dict(
    src=os.path.join(ROOT, r'isp\raw10_unpacket_2lane.v'),
    header=hdr(
        path='isp/raw10_unpacket_2lane.v',
        mod='raw10_unpacket_2lane',
        func='把 CSI 字节流(2 lane、32bit/拍)按 RAW10 的“4 像素 / 5 字节”打包规则重新拼装为 40bit(=4×10bit 像素)输出，并同步给出帧首/帧尾/有效。★重要：黑电平减法与 10bit→8bit 右移截位、RAW8 输出、FIFO 读写控制那一整段位于 /* 块注释内(本文件 :141-:233)，未参与综合；因此本模块当前实际只输出 O_raw10_*，并不产生 RAW8，也不做任何黑电平修正。',
        data='I_csi_data(32bit/拍) 与 I_csi_valid → 各打 2 拍 → S_phase_cnt(0..4) 相位机 → case 按相位把相邻两拍的字节与 lane 尾部 2bit 拼成 4 个 10bit → S_raw10_wr_data[39:30]/[29:20]/[19:10]/[9:0] → 输出寄存器 O_raw10_data 时把 4 个字段次序反转后送出。',
        clk='只有 I_clk，本文件内全部为同步时序、无复位逻辑；I_rst_n 端口存在但在本文件内未被引用。',
        dep='无子模块被例化（w40_d40_fifo 的例化位于注释区内，未生效）。',
        syn='本文件没有 `timescale；关键信号带 //synthesis keep 属性。每 5 拍为一个相位循环、其中 4 拍出数据共 16 个像素，第 5 拍为空拍。I_camera_black_level 端口在本工程 design_top_wrapper.v:571 例化时未连接（悬空按 0 处理），且使用它的逻辑本身处于注释区内。',
    ),
    before={
        50: ['//---- 内部信号 ----'],
        65: ['//---- CSI 输入打拍：valid/data 各 2 级 ----'],
        77: ['//---- 相位计数器 S_phase_cnt：0..4，每 5 拍一个循环 ----'],
        86: ['//---- 40bit 拆 4×10bit：按相位把两拍字节与 lane 尾部 2bit 拼装 ----'],
        134: ['//---- 输出寄存器：字段次序反转后送出 ----'],
        141: ['//---- 以下整段(:141-:233)处于块注释区内、未参与综合：黑电平减法 + 10bit→8bit 右移截位 + FIFO 读写控制 + RAW8 输出 ----'],
    },
    eol={
        42: '  // 黑电平基座输入；本工程 design_top_wrapper.v:571 例化时未连接（悬空=0）',
        54: '  // 3bit 相位：0..3 出数据，4 为空拍',
        78: '  // 只有相隔 1 拍的两个 valid 同时有效(3\'b101)才推进相位（CSI valid 不连续）',
        91: '  // 每个 10bit = 高 8bit + 跨字节的 2 个低位 bit',
        119: '  // 相位 4：空拍，输出全 0',
        136: '  // 注意：与写入时字段次序相反，原 [39:30] 落到输出的最低位',
        138: '  // 写使能打 1 拍即 O_raw10_valid',
        158: '  // 先减黑电平基座、再右移 2 位（10bit→8bit，即除以 4）；整段当前处于注释区内，未综合',
        161: '  // 四个 10bit 字段同构处理',
    },
)

# =============================================================================
# 5. isp/csi_unpacket_2lane.v
# =============================================================================
CSI = dict(
    src=os.path.join(ROOT, r'isp\csi_unpacket_2lane.v'),
    header=hdr(
        path='isp/csi_unpacket_2lane.v',
        mod='csi_unpacket_2lane',
        func='解析 MIPI CSI-2 RX 核输出的 16bit(2 lane × 1 byte)数据流：用 valid 上升沿定位包头，按 DT 识别帧首(0x00)、帧尾(0x01)与 RAW10 数据长包(0x2B)，从包头取出字计数并圈出数据区，把 2 拍 16bit 拼成 32bit 输出。',
        data='I_hs_valid/I_hs_data → 打 1 拍 → S_head_en(= 本拍 valid 且上一拍 !valid) → DT 判定 → S_data_length(字节数 >> 1，单位换算成 2lane 的拍数) → S_data_en / S_data_en_cnt 圈出数据区 → csi_valid_r 每拍翻转产生 2 拍一次的 O_csi_valid → O_csi_data 由 {旧 [15:0], I_hs_data} 移位拼接。',
        clk='单时钟 I_clk；I_rst_n 低电平异步复位(仅 S_data_en 块使用)；其余时序块只含 posedge I_clk。',
        dep='无子模块例化。',
        syn='`timescale 1ns/1ns；关键信号带 //synthesis keep 属性。FRAME_DATA_DT 选 0x2B(RAW10)，0x2A(RAW8) 那一行被注释掉；对帧首/帧尾只做输出指示，并不截断数据区。',
    ),
    before={
        60: ['//---- 长包数据类型定义（DT） ----'],
        65: ['//---- 内部信号 ----'],
        73: ['//---- 帧头使能：valid 上升沿（每个包的首字节） ----'],
        75: ['//---- 输入打 1 拍 ----'],
        82: ['//---- 帧起始判断：包头 DT = 0x00 ----'],
        87: ['//---- 帧结束判断：包头 DT = 0x01 ----'],
        91: ['//---- 数据长包：取字计数 WC，换算成 2lane 的拍数 ----'],
        104: ['//---- 数据有效窗口（S_data_en） ----'],
        117: ['//---- 数据长度计数器 ----'],
        125: ['//---- 16bit→32bit 拼接与输出有效信号 ----'],
    },
    eol={
        60: '  // RAW10 长包；RAW8 对应 0x2A（见下一行被注释的定义）',
        73: '  // 上一拍无效、本拍有效 → 包头首字节',
        84: '  // 包头首字节的高 8bit 即 DT',
        89: '  // 同上，DT=0x01 表示帧结束',
        95: '  // WC 为字节数，2 lane 每拍 2 字节，故右移 1 得拍数',
        111: '  // 计满长度即关闭数据窗口',
        120: '  // 数据窗口内逐拍累加',
        129: '  // 窗口内每拍翻转 → 2 拍一次的 32bit 有效指示',
        131: '  // HS 状态透传',
        135: '  // 新数据进低位，2 拍凑满 32bit',
    },
)

# =============================================================================
# 6. isp/BLC/BLC.v
# =============================================================================
BLC = dict(
    src=os.path.join(ROOT, r'isp\BLC\BLC.v'),
    header=hdr(
        path='isp/BLC/BLC.v',
        mod='BLC',
        func='黑电平校正(Black Level Correction)：对 40bit 数据里的 4 个 10bit 像素各自减去一组可配置偏移量，结果为负则钳位到 0。★★本工程未例化、未接入数据通路：全树搜索不到对 BLC 的例化（仅本文件的 module 声明），属备用/未接入模块。',
        data='I_tdata(40bit = 4×10bit) → 拆成 I_blc_data[0..3] → generate 展开 4 路并行的“减法 + 下钳位”(偏移取 parameter Black_level_offset_r0..r3) → 拼回 O_tdata；tlast/tuser/tvalid 打 1 拍跟随输出。',
        clk='I_clk 单时钟；I_rst_n 低电平异步复位（只清 tlast/tuser/tvalid 打拍寄存器）；减法 always 块只有 posedge I_clk、以 I_tvalid 为使能且无复位。',
        dep='无子模块例化。',
        syn='generate for 展开 4 路；4 组偏移量默认均为 15(10bit 域)。O_tdest 输出在文件内未见赋值(无驱动)、I_tdest 输入未被引用，即这两个端口实际未参与运算。',
    ),
    before={
        38: ['//---- 控制信号寄存器 ----'],
        42: ['//---- 偏移量：parameter → 4 路数组 ----'],
        49: ['//---- 数据拆分（40bit → 4×10bit）与输出寄存器 ----'],
        56: ['//---- 逐像素减法 + 下钳位（generate 展开 4 路并行） ----'],
        75: ['//---- 控制信号打 1 拍 ----'],
        86: ['//---- 输出拼接与握手 ----'],
    },
    eol={
        12: '  // 第0路偏移；4 路对应 40bit 中的 4 个像素（是否对应 Bayer 的 R/Gr/Gb/B 未能从代码确认）',
        15: '  // 第3路偏移',
        25: '  // 本文件内未被引用',
        32: '  // 本文件内未见对该输出的赋值（无驱动）',
        44: '  // parameter 常量映射为数组，便于 generate 索引',
        51: '  // 字段分布：[9:0] / [19:10] / [29:20] / [39:30]',
        63: '  // 严格大于才相减，避免无符号下溢回绕',
        67: '  // 不足则钳到 0',
        90: '  // 4 个 10bit 拼回 40bit',
        92: '  // 直通反压',
    },
)

FILES = [AWB, SIGDELAY, BLKMEM, RAW10, CSI, BLC]


def build(spec):
    raw = open(spec['src'], 'rb').read()
    # 用文件自身的主换行符拼接，新增行也用它，避免出现混合换行
    eol_b = b'\r\n' if b'\r\n' in raw else b'\n'
    lines = raw.split(b'\n')
    bodies = [l[:-1] if l.endswith(b'\r') else l for l in lines]  # 逻辑行（去掉行尾 CR）
    assert eol_b.join(bodies) == raw, 'EOL reconstruction mismatch: ' + spec['src']
    hdr_lines = [l.encode('utf-8') for l in spec['header'].split('\n')]
    before = {n: [t.encode('utf-8') for t in v] for n, v in spec['before'].items()}
    eol = {n: v.encode('utf-8') for n, v in spec['eol'].items()}

    n_lines = len(bodies)
    for n in list(before) + list(eol):
        if not (1 <= n <= n_lines):
            raise SystemExit('line out of range in %s: %d (file has %d)' % (spec['src'], n, n_lines))

    out = []
    for idx, body in enumerate(bodies, 1):
        if idx == 1:
            out.extend(hdr_lines)
        if idx in before:
            out.extend(before[idx])
        if idx in eol:
            body = body + eol[idx]
        out.append(body)
    return raw, eol_b.join(out), eol_b


def strip_comments(b):
    """删掉所有 // 与 /* */ 注释，再去掉全部空白字节 —— 用于证明代码一个字符都没变。"""
    res = bytearray()
    i, n = 0, len(b)
    while i < n:
        c = b[i:i + 2]
        if c == b'//':
            j = b.find(b'\n', i)
            i = n if j < 0 else j
        elif c == b'/*':
            j = b.find(b'*/', i + 2)
            i = n if j < 0 else j + 2
        else:
            if b[i] not in b' \t\r\n':
                res.append(b[i])
            i += 1
    return bytes(res)


def main():
    apply = '--apply' in sys.argv
    report = []
    for spec in FILES:
        name = os.path.basename(spec['src'])
        raw, new, eol_b = build(spec)
        code_same = strip_comments(raw) == strip_comments(new)
        # 换行一致性：新文件里不允许出现裸 LF / 裸 CR
        bare_lf = (new.count(b'\n') - new.count(b'\r\n')) + (new.count(b'\r') - new.count(b'\r\n'))
        inserted = len(spec['header'].split('\n')) + sum(len(v) for v in spec['before'].values())
        n_old = raw.count(b'\n') + (0 if raw.endswith(b'\n') else 1)
        n_new = new.count(b'\n') + (0 if new.endswith(b'\n') else 1)
        nb = os.path.join(BAK, name + '.bak')
        bak_raw = open(nb, 'rb').read() if os.path.exists(nb) else None
        bak_ok = (bak_raw == raw)
        ok = code_same and bak_ok and bare_lf == 0 and (n_new - n_old == inserted)
        report.append((name, len(raw), len(new), n_old, n_new, inserted, code_same, bak_ok, bare_lf, ok))
        if apply:
            if not ok:
                raise SystemExit('precondition failed for ' + name)
            open(spec['src'], 'wb').write(new)
    print('%-36s %7s %7s %5s %5s %5s %-9s %-9s %-6s %s' %
          ('file', 'old B', 'new B', 'oldL', 'newL', 'ins', 'code-same', 'backup-ok', 'bareLF', 'OK'))
    for r in report:
        print('%-36s %7d %7d %5d %5d %5d %-9s %-9s %-6d %s' % r)
    print('\nmode:', 'APPLIED' if apply else 'DRY-RUN')


main()
