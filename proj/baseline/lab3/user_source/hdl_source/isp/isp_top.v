//=============================================================================
// [HDR-2026-10-09] 文件      : isp_top.v
// 模块      : isp_top
// 功能      : ISP 顶层：把传感器 RAW10 四像素一拍的数据依次过「去马赛克 → 位宽重切 → 自动白平衡 → 自研算法 → 位宽重切」，输出 128bit/拍的 RGB888。
// 数据通路  : I_tdata[39:0](RAW10，4 像素×10bit) → demosaic(128bit) → data128_96(96bit，4 像素×24bit RGB) → awb(白平衡) → my_algo(算法/MODE) → data_96bit_to_128bit(128bit) → O_tdata
// 时钟/复位 : axi4s_video_aclk = S_csi_rx_clk（约 100 MHz）；I_rst_n 低有效。全部子模块同域。
// 依赖      : demosaic(BAYER_MODE="BGGR",1280x720) / data128_96 / awb / my_algo(MODE_INIT=3'd2,THRESH=8'd128) / data_96bit_to_128bit
// 综合/实现 : ■ (:86-89) 输出接线是本文件的关键：O_tdata 取 128bit 级的 awb_O_tdata_128，而 O_tlast 取 96bit 级的 awb_O_tlast（与官方 lab_ex1 的 isp_top.v:36-40 逐字一致），O_tuser/O_tvalid 取 awb_*_128。
//           ■ 96bit 数据格式 = [23:16]=R [15:8]=G [7:0]=B，一拍 4 个像素。
//-----------------------------------------------------------------------------
// 修改记录  :
//   2026-09-27  [230f479] 导入官方 lab3 基线
//   2026-09-27  [6440c52] 在 awb 与 data_96bit_to_128bit 之间插入自研算法模块 my_algo
//   2026-10-06  （未提交）★修复输出悬空：原文件缺失 `assign O_tdata = awb_O_tdata_128;`，导致 ISP 输出端口无消费者，TD 在 phy 阶段执行 PHY-1001 Remove keep and sweep redundant instances 把整条 ISP 链路优化掉（#RAMs 40→12、#DSPs 9→1），上板全黑只剩 OSD；本次补齐该行，并把 O_tuser/O_tvalid 由 96bit 级改取 128bit 级，避免与 O_tdata 相位错配
//   2026-10-09  （未提交）标识符改名 25 处：局部 wire 拼写错误 m_aixs_* → m_axis_*
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑，见 E:\FPGA\_analysis\rename_report.txt）
//=============================================================================
module isp_top (
    input 			axi4s_video_aclk,
    input 			I_rst_n			,
    input 			I_tlast			,
    input 			I_tuser			,
    input [39:0] 	I_tdata			,
    input 			I_tvalid		,
    input [9:0] 	I_tdest			,
    input 			O_tready		,
    output [127:0] 	O_tdata			,
    output 			O_tlast			,
    output 			O_tuser			,
    output 			O_tvalid		,
    output 			I_tready		,
    // [OUR ALGO] 自研算法模式选择，来自按键（key_mode_ctrl.v）
    //   ★必须与 design_top_wrapper 的 S_algo_mode 和 my_algo 的 I_mode 同为 3 bit★
    //   曾经写成 [1:0]，导致模式 4(卡通化) 被截成 2'b00 = 原图直通，
    //   出现「状态行显示 MODE 4，但画面没变化」的静默故障。
    input [2:0]     I_algo_mode     ,
    // [HDR-2026-10-10] 板上乒乓开关 SW1/SW2（顶层已同步到本时钟域）
    //   I_blk_bypass  : SW1，1 = 黑电平扣除【直通】（= 2026-10-09 之前的老行为），0 = 启用扣除
    //   I_gamma_bypass: SW2，1 = S 曲线【直通】，0 = 启用 S 曲线
    //   复位期间顶层把这两根都拉成 1 ⇒ 上电老行为，绝不会「一上电就变样」。
    input           I_blk_bypass    ,
    input           I_gamma_bypass  ,
  // [HDR-2026-10-14] LSC（镜头色彩暗角校正）运行期旁路，1 = 直通
  input           I_lsc_bypass    ,
    //--------------------------------------------------------------------------
    // [HDR-2026-10-12] AE（自动曝光）帧统计输出
    //   全部在本模块 axi4s_video_aclk（= S_csi_rx_clk，60MHz）域；每帧只更新一次、
    //   之后保持约 16.7ms 不变 ⇒ 准静态跨域；顶层用 O_ae_frame_tgl（每帧末翻转）
    //   这个单 bit 的上升/下降沿去采样它们。
    //   统计点 = awb 的输入（m_axis_tdata_96 / m_axis_tvalid / m_axis_tuser），即
    //   「去马赛克之后、白平衡与 S 曲线之前」：
    //     · 在 awb 之前 ⇒ AE 与 AWB 互不耦合（AWB 调 gain 不改变 AE 的观测量）；
    //     · 在 isp_gamma 之前 ⇒ 拨 SW2 开关 S 曲线不会让 AE 的目标亮度漂移。
    //--------------------------------------------------------------------------
    output [39:0]   O_ae_luma_sum   ,
    output [31:0]   O_ae_pix_cnt    ,
    output [31:0]   O_ae_hi_cnt     ,
    output [31:0]   O_ae_lo_cnt     ,
    output          O_ae_frame_tgl ,
    //--------------------------------------------------------------------------
    // [HDR-2026-10-12k] 白平衡遥测：把 awb 实际在用的 R/B 增益原样送到顶层。
    //   纯直通，不参与任何运算。顶层把 [19:4] 拆成 4 位十六进制显示在 OSD 上
    //   （0x1000 = 1.000x，0x1240 = 1.140x）。
    //   这是判定"偏色到底出在 AWB 计算、AWB 施加、还是 AWB 之后"的唯一直接证据：
    //     屏幕上 R/G 明显 <1.0 而 O_gain_r 一直停在 0x1000  ⇒ 增益没算出来/没施加；
    //     屏幕上 R/G <1.0 而 O_gain_r ≈ 0x1240（已经在补偿） ⇒ 偏色在 AWB 之后。
    //--------------------------------------------------------------------------
    output [19:0]   O_wb_gain_r     ,
    output [19:0]   O_wb_gain_b
);
 
wire         m_axis_tvalid;  //synthesis keep 
  wire [127:0] m_axis_tdata;  //synthesis keep 
  wire         m_axis_tuser;  //synthesis keep 
  wire         m_axis_tlast;  //synthesis keep 
  wire         m_axis_tready;  //synthesis keep 
  
  wire [ 95:0] m_axis_tdata_96;  //synthesis keep 


  wire         awb_O_tlast;  //synthesis keep 
  wire         awb_O_tuser;  //synthesis keep 
  wire [ 95:0] awb_O_tdata;  //synthesis keep 
  wire         awb_O_tvalid;  //synthesis keep 
  wire         awb_O_tready;  //synthesis keep 

  wire         awb_O_tuser_128;  //synthesis keep 
  wire         awb_O_tvalid_128;  //synthesis keep 
  wire [127:0] awb_O_tdata_128;  //synthesis keep 

  //--------------------------------------------------------------------------
  // [OUR ALGO] 自研算法 my_algo 的中间信号
  //   位置：awb 之后、data_96bit_to_128bit 之前
  //   96 bit = 4 像素 x 24 bit，位宽与 awb 输出一致
  //--------------------------------------------------------------------------
  wire         algo_O_tlast;   //synthesis keep 
  wire         algo_O_tuser;   //synthesis keep 
  wire [ 95:0] algo_O_tdata;   //synthesis keep 
  wire         algo_O_tvalid;  //synthesis keep 

  //--------------------------------------------------------------------------
  // [HDR-2026-10-10] S 曲线查表级（isp_gamma）的中间信号
  //   位置：awb 之后、my_algo 之前；固定 2 拍延迟（ROM 同步读 1 拍 + 输出 1 拍）
  //--------------------------------------------------------------------------
  wire         gam_I_tready;   //synthesis keep 
  wire         gam_O_tlast;    //synthesis keep 
  wire         gam_O_tuser;    //synthesis keep 
  wire [ 95:0] gam_O_tdata;    //synthesis keep 
  wire         gam_O_tvalid;   //synthesis keep 
  wire         algo_I_tready;  //synthesis keep 

  // [HDR-2026-10-10] 原来这里直接把 awb 的 O_tready 接到顶层 O_tready。
  //   插入 isp_gamma 之后 awb 的下游变成 gamma，回压信号改由 gamma 给出；
  //   gamma 内部就是 `assign I_tready = O_tready;`（与 awb.v:513、my_algo.v:96
  //   同一条写法），所以 awb_O_tready 的波形与改动前逐拍相同，全链路仍无真反压。
  assign awb_O_tready = gam_I_tready;
  //--------------------------------------------------------------------------
  // ★★ 这四根输出的取法：必须与官方原厂 lab3 的 isp_top.v 完全一致 ★★
  //   铁证出处（原厂文件第 37-40 行，路径：
  //   E:\FPGA\官方资料\7_lab_ex_2026_nosoft\lab_ex3_osd_SC500_720P\
  //   lab_ex3_osd\user_source\hdl_source\isp\isp_top.v）：
  //     assign O_tdata  = awb_O_tdata_128;   // 128bit 级
  //     assign O_tlast  = awb_O_tlast    ;   // 96bit 级，原厂就这么写
  //     assign O_tuser  = awb_O_tuser_128;   // 128bit 级
  //     assign O_tvalid = awb_O_tvalid_128;  // 128bit 级
  //
  //   为什么 O_tdata / O_tuser / O_tvalid 必须取 128bit 那一级：
  //   data_96bit_to_128bit 是「4 x 96bit = 3 x 128bit = 384bit = 16 像素」
  //   的重切模块，每 4 拍输入只出 3 拍有效（S_phase_cnt∈{1,2,3} 时
  //   O_128b_valid=1；S_phase_cnt==0 那拍 O_128b_valid=0 且 O_128b_data 被清 0）。
  //   数据与有效信号取自同一级才同相位，下游 video_in.v 的 FIFO 写使能
  //   才恰好是 3 词/4 拍 = 3 词/16 像素，与显示侧 video_out.v 的
  //   「3 词/16 像素」精确对齐。
  //
  //   2026-10-05/06 两次踩坑记录（血泪，别再动这几行）：
  //   ① 把 O_tlast/O_tuser/O_tvalid 改成 96bit 级的 algo_O_*（只剩
  //      O_tdata 还是 128bit 级）⇒ 写侧 4/4 全高、数据侧只有 3/4，
  //      逐行错位 ⇒ 上板满屏彩色细斜纹（10-05 19:20 那次，照片
  //      IMG_20261005_192605.jpg / 192615.jpg 就是它），但此时 ISP
  //      还在设计里（#RAMs 40 / #DSPs 9）。
  //   ② 更糟：改这段时把 assign O_tdata 整行弄丢 ⇒ O_tdata 悬空
  //      ⇒ TD 认为整条 ISP 链路无消费者，在 phy 阶段打印
  //        PHY-1001 : Remove keep and sweep redundant instances
  //      把 u_my_algo、两个 divider、awb 的延时 BRAM、demosaic 的两条
  //      行缓存 BRAM 全当冗余扫掉：
  //        route.qor  #slices 15748 -> 9041, #RAMs 40 -> 12, #DSPs 9 -> 1
  //      结果上板无论哪个 MODE 都是黑屏（只剩 OSD）。
  //   ⇒ 判据：综合后 #RAMs 必须是 40、#DSPs 必须是 9；
  //     若变成 34/12/1，就是这段端口接线又出问题了。
  //--------------------------------------------------------------------------
  assign O_tdata  = awb_O_tdata_128 ;
  // [HDR-2026-10-10] ★这一行的取值从 awb 那级改成 gamma 那级★
  //   原厂写法的语义是「O_tlast = my_algo 输入那一拍的 tlast」；
  //   插入 isp_gamma（2 拍）后，my_algo 的输入 beat 就是 gamma 的输出 beat，
  //   所以必须改成 gam_O_tlast ⇒ 与加 gamma 之前逐拍等价（= awb_O_tlast 延 2 拍）。
  //   若仍取 awb_O_tlast，O_tlast 会比数据早 2 拍 ⇒ 行尾标记错位。
  assign O_tlast  = gam_O_tlast     ;
  assign O_tuser  = awb_O_tuser_128 ;
  assign O_tvalid = awb_O_tvalid_128;
  
  //assign m_axis_tready = O_tready;
  //assign O_tdata  = m_axis_tdata;
  //assign O_tlast  = m_axis_tlast    ;
  //assign O_tuser  = m_axis_tuser    ;
  //assign O_tvalid = m_axis_tvalid   ;
 
 
demosaic #(
    .IMG_HEIGHT          (720 ), // 图像高度
    .IMG_WIDTH           (1280), // 图像宽度
    .data_complete_delay (50  ),
    .BAYER_MODE          ("BGGR")
)
u_demosaic
(
    .I_clk   			(axi4s_video_aclk)	,   // 时钟信号
    .I_rst_n 			(I_rst_n)	,   // 复位信号，低有效
    .I_blk_bypass 		(I_blk_bypass)	,  // [HDR-2026-10-10] 黑电平扣除旁路（1=直通）
    .axi4s_video_tdata 	(I_tdata)	,  // AXI4-Stream视频数据
    .axi4s_video_tdest 	(I_tdest)	,
    .axi4s_video_tlast 	(I_tlast)	,  // 行结束信号
    .axi4s_video_tvalid	(I_tvalid)	,  // 数据有效信号
    .axi4s_video_tuser 	(I_tuser)	,  // 帧开始信号
    .axi4s_video_tready	(I_tready)	,  // 从模块准备好接受数据
    .O_tlast  			(m_axis_tlast)	,  // 输出行结束信号
    .O_tuser  			(m_axis_tuser)	,  // 输出帧开始信号
    .O_tdata  			(m_axis_tdata)	,  // 输出数据
    .O_tvalid 			(m_axis_tvalid)	,  // 输出数据有效信号
    .O_tready   		(m_axis_tready)	   // 输出数据准备好信号
);
 
data128_96 u_data128_96 (
    .I_tdata(m_axis_tdata),
    .O_tdata(m_axis_tdata_96)
);

//------------------------------------------------------------------------------
// [HDR-2026-10-14] LSC 镜头色彩暗角校正
//   插在 data128_96 之后、ae_stat / awb 之前，理由：
//     ① 放在 awb 之前 —— AWB 看到的是已经校平的画面，"整帧 R/G = 1" 这个判据
//        才有意义；放在 awb 之后会被它的全局增益重新搅混。
//     ② 放在 ae_stat 之前 —— AE 的帧均值直接取自校正后的画面。
//   本模块带 2 拍流水，所以下游的 tvalid / tuser / tlast 必须取它延迟后的版本，
//   否则帧边界会与数据错开 2 拍。
//------------------------------------------------------------------------------
wire [95:0] lsc_tdata_96;
wire        lsc_tvalid, lsc_tuser, lsc_tlast;

lsc #(
    .LSC_ENABLE(1'b1       ),
    .H_BEATS   (12'd320    ),
    .V_LINES   (12'd720    ),
    .K_MAX     (4'd15      )
) u_lsc (
    .I_clk    (axi4s_video_aclk),
    .I_rst_n  (I_rst_n         ),
    .I_bypass (I_lsc_bypass    ),
    .I_tdata  (m_axis_tdata_96 ),
    .I_tvalid (m_axis_tvalid   ),
    .I_tuser  (m_axis_tuser    ),
    .I_tlast  (m_axis_tlast    ),
    .O_tdata  (lsc_tdata_96    ),
    .O_tvalid (lsc_tvalid      ),
    .O_tuser  (lsc_tuser       ),
    .O_tlast  (lsc_tlast       )
);

//------------------------------------------------------------------------------
// [HDR-2026-10-12] AE 帧统计器 —— 与 u_awb 并联挂在同一条 96bit 码流上
//   挂在 awb 的输入侧（而不是输出侧）：AE 与 AWB 互不耦合。
//   本模块只读不写数据通路，不产生任何反压（无 I_tready），完全被动监听。
//   零乘法（77/150/29 全部拆移位加法）⇒ 不占 DSP；无 ERAM。
//------------------------------------------------------------------------------
ae_stat u_ae_stat (
    .I_clk       (axi4s_video_aclk),
    .I_rst_n     (I_rst_n         ),
    .I_tvalid    (lsc_tvalid      ),
    .I_tuser     (lsc_tuser       ),
    .I_tdata     (lsc_tdata_96    ),
    .O_luma_sum  (O_ae_luma_sum   ),
    .O_pix_cnt   (O_ae_pix_cnt    ),
    .O_hi_cnt    (O_ae_hi_cnt     ),
    .O_lo_cnt    (O_ae_lo_cnt     ),
    .O_frame_tgl (O_ae_frame_tgl  )
);

awb #(
    .IMG_HEIGHT(720 ),
    .IMG_WIDTH (1280)
) u_awb (
    .I_clk   (axi4s_video_aclk),
    .I_rst_n (I_rst_n),
    .I_tlast (lsc_tlast    ),
    .I_tuser (lsc_tuser    ),
    .I_tdata (lsc_tdata_96 ),
    .I_tvalid(lsc_tvalid   ),
    .I_tready(m_axis_tready),
    .O_tlast (awb_O_tlast ),
    .O_tuser (awb_O_tuser ),
    .O_tdata (awb_O_tdata ),
    .O_tvalid(awb_O_tvalid),
    .O_tready(awb_O_tready),
    .O_gain_r(O_wb_gain_r),
    .O_gain_b(O_wb_gain_b)
);

    //==========================================================================
    // [HDR-2026-10-10] S 曲线（色调曲线）查表级 —— 插在 awb 与 my_algo 之间
    //   12 个 8bit 分量共用同一张 256×8 表（R/G/B 同表 ⇒ 不动白平衡）；
    //   表内容 = gamma_lut_p118_k125.hex（P=118, A=B=1.25 中等档 S 曲线）。
    //   固定 2 拍延迟，无空拍；bypass 也是 2 拍（不会错帧）。
    //   ★该级绝不能停拍（全链路无真反压，见 isp_gamma.v 头部说明）。
    //==========================================================================
    isp_gamma u_isp_gamma (
        .I_clk          ( axi4s_video_aclk ),
        .I_rst_n        ( I_rst_n          ),
        .I_tlast        ( awb_O_tlast      ),
        .I_tuser        ( awb_O_tuser      ),
        .I_tdata        ( awb_O_tdata      ),
        .I_tvalid       ( awb_O_tvalid     ),
        .I_tready       ( gam_I_tready     ),
        .I_gamma_bypass ( I_gamma_bypass   ),
        .O_tdata        ( gam_O_tdata      ),
        .O_tlast        ( gam_O_tlast      ),
        .O_tuser        ( gam_O_tuser      ),
        .O_tvalid       ( gam_O_tvalid     ),
        .O_tready       ( algo_I_tready    )
    );

    //==========================================================================
    // [OUR ALGO] 自研图像增强算法 —— RGB 点运算算法集
    //   数据格式：96 bit = 4 像素 x 24 bit（[23:16]=R [15:8]=G [7:0]=B）
    //   端口方向照抄原厂 edge_detect_96.v：I_tready 是 output、O_tready 是 input
    //   算法与参考例程不同源：本例程参考实现是 Sobel 空间域边缘检测，
    //   本模块是点运算（BT.601 灰度 / 伪彩热力图 / 阈值二值化 / 原图直通 / 卡通化），
    //   5 种模式由按键经 I_algo_mode（3 bit）实时切换。
    //==========================================================================
    my_algo #(
        .THRESH     ( 8'd128 ),
        .MODE_INIT  ( 3'd0   )
    ) u_my_algo (
        .I_clk      ( axi4s_video_aclk ),
        .I_rst_n    ( I_rst_n          ),
        // [HDR-2026-10-10] 输入源由 awb 改为 isp_gamma 的输出（多 2 拍延迟）
        .I_tlast    ( gam_O_tlast      ),
        .I_tuser    ( gam_O_tuser      ),
        .I_tdata    ( gam_O_tdata      ),
        .I_tvalid   ( gam_O_tvalid     ),
        .I_tready   ( algo_I_tready    ),
        .O_tdata    ( algo_O_tdata     ),
        .O_tlast    ( algo_O_tlast     ),
        .O_tuser    ( algo_O_tuser     ),
        .O_tvalid   ( algo_O_tvalid    ),
        .O_tready   ( O_tready         ),
        .I_mode     ( I_algo_mode      )
    );

    data_96bit_to_128bit u_data_96bit_to_128bit(
        .I_clk              ( axi4s_video_aclk  ),
        .I_rst_n            ( I_rst_n           ),
	
        .I_96b_frame_start  ( algo_O_tuser	    ),
        .I_96b_valid        ( algo_O_tvalid 	),
        .I_96b_data         ( algo_O_tdata		),
	
        .O_128b_frame_start ( awb_O_tuser_128  	),
        .O_128b_valid       ( awb_O_tvalid_128 	),
        .O_128b_data        ( awb_O_tdata_128  	)
    );



//data96_128 u_data96_128 (
//    .I_tdata(awb_O_tdata),
//    .O_tdata(awb_O_tdata_128)
//);
	
endmodule
