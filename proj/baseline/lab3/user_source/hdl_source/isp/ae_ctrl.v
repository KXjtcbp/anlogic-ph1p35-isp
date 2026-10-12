//=============================================================================
// [HDR-2026-10-12] 文件      : ae_ctrl.v
// 模块      : ae_ctrl
// 功能      : 自动曝光（AE）闭环控制器 —— 读 ae_stat 的逐帧亮度统计，按保守比例律
//             调节 SC500CS 的模拟增益，把整帧平均亮度锁到 TARGET_MEAN。
// 数据通路  : ae_stat(60MHz ISP 域) --单bit翻转跨域--> 本模块(24MHz 配置域)
//             --> O_ae_req/O_exposure_time/O_analog_gain --> uicfgcs500_720p --> I2C --> 传感器
// 时钟/复位 : I_clk = S_24m_clk（24 MHz 配置域）；I_rst_n 低有效（与全工程一致）。
// 综合/实现 : ■ 零乘法器、零除法器、零 BRAM。所有阈值在 elaboration 期由 parameter 折叠成常数
//               （TARGET_SUM / DEADBAND_SUM 等），运行时只做 40bit 比较与加减。
//             ■ 增益阶梯 = 7 bit 索引 gi[6:0]，共 128 档、单调：
//                 gi[6:5] 选 0x3e08 粗档 {0x03,0x07,0x0F,0x1F} = x1/x2/x4/x8
//                 gi[4:0] 选 0x3e09 细档 0x20..0x3F        = x1.000..x1.969
//               相邻两档比值 1.6%~3.1%，全量程 1.000x ~ 15.750x，与 SW3 的数字增益相乘。
//             ■ ★曝光为什么固定 1990★：1990 = 2*VTS-10（VTS=1000 @720p60），再长会让帧长
//               超过 60Hz ⇒ 掉帧。所以 720p60 下曝光**没有余量**，AE 唯一可用的连续杠杆是
//               模拟增益。EXPOSURE_FIXED 仍留成 parameter，将来换帧率时改一处即可。
// 依赖      : ae_stat.v（统计）、design_top_wrapper.v（例化 + SW4 使能）、uicfgcs500_720p.v
//-----------------------------------------------------------------------------
// 设计依据（官方评分标准原文）:
//   《全国大学生嵌入式芯片与系统设计竞赛'2026选题指南》选题二 2.6 评分标准
//     一、基础要求（4）系统稳定性：…… **光线剧烈变化时工作正常**。
//     二（二）高阶挑战项（5）**画面自动曝光/白平衡等优化**。
//   ⇒ AE 是「基础要求(4)」的评分点，同时是「高阶挑战项(5)」，不是纯加分项。
//-----------------------------------------------------------------------------
// 控制律（保守版，用户要求"偏向保守" + "尽可能减少可现场手调的部分"）:
//   1) 稳定帧数：cam_cfg_done 之后先数 SETTLE_FRAMES 帧不动（等传感器收敛）。
//   2) 高光护栏（最高优先级）：hi_cnt > pix_cnt>>HI_GUARD_SHIFT ⇒ 无条件降档。
//   3) 暗场景护栏：lo_cnt > pix_cnt>>LO_GUARD_SHIFT ⇒ 停止加亮（防把夜景硬拉成白天）。
//      ★2026-10-12 上板后默认关闭（LO_GUARD_SHIFT=0）★：本工程的使用场景
//      （宿舍、只开显示器）整帧 65%~95% 都是近黑像素，该护栏会把 AE 完全锁死。
//      实测数据见 _analysis/out/inbox_stats.txt 的 dk<=8% 一列。
//   4) 死区：|帧亮度和 - TARGET_SUM| < TARGET_SUM/21（约 4.8%）⇒ 不动作，防抖。
//   5) 比例步长：误差 >100% 走 STEP_FAST 档；>25% 走 STEP_MID 档；否则 STEP_SLOW 档。
//      每帧只走一次（60fps ⇒ 最快 8 档/帧 ≈ 0.22 倍/帧），1~2 秒内收敛，不会过冲振荡。
//   6) 逐档下发：一次 O_ae_req 只改一档，等 I_ae_cfg_done 回高再考虑下一次 ⇒ 天然限速。
//   7) 冻结：I_ae_en=0 时不改任何值、不发请求 ⇒ "以最后值作为冻结值"。
//-----------------------------------------------------------------------------
// 修改记录  :
//   2026-10-12  [新建] AE 第 2 步：闭环控制器。与 ae_stat.v 配套。
//-----------------------------------------------------------------------------

`timescale 1ns / 1ns

module ae_ctrl #(
    // ---- 目标与场景描述（改这里就能调，不需要读逻辑）----
    parameter [7:0]  TARGET_MEAN     = 8'd70,     // 目标：整帧平均线性亮度（8bit）
    parameter [31:0] NOM_PIX         = 32'd921600,// 正常一帧的像素数 = 1280*720
    parameter [15:0] EXPOSURE_FIXED  = 16'd1990,  // 2*VTS-10，见文件头
    parameter [6:0]  GAIN_IDX_INIT   = 7'd64,     // 复位默认档：64 = 0x3e08=0x0F,0x3e09=0x20 = 4.000x（厂商原值）
    // ---- 时序与步长 ----
    parameter [7:0]  SETTLE_FRAMES   = 8'd60,     // 配置完成后先等 60 帧（约 1s）
    parameter [6:0]  STEP_FAST       = 7'd8,      // 误差 >100% 时每帧步进
    parameter [6:0]  STEP_MID        = 7'd2,      // 误差 >25% 时每帧步进
    parameter [6:0]  STEP_SLOW       = 7'd1,      // 其余每帧步进
    // ---- 护栏（阈值都是 2 的负幂，用移位比较，零硬件代价）----
    parameter [5:0]  HI_GUARD_SHIFT  = 6'd6,      // hi_cnt > pix_cnt/64  = 1.56%  ⇒ 降档
    parameter [5:0]  LO_GUARD_SHIFT  = 6'd0,      // ★0 = 关闭该护栏★（>>0 = 自身，永不成立）
                                                  //   上板实测 2026-10-12：本场景 dk<=8 占 65%~95%，
                                                  //   旧的 6'd2（25%）把加亮通道整个堵死。详见 215 行注释。
    parameter        AE_ENABLE_RESET = 1'b0       // 复位值，仅用于文档化（实际由 SW4 决定）
)(
    input  wire        I_clk,             // 24 MHz 配置域（S_24m_clk）
    input  wire        I_rst_n,           // 低有效
    input  wire        I_ae_en,           // SW4 拨上 = 1 = AE 使能；0 = 冻结在最后值

    // ---- 来自 ae_stat（60 MHz ISP 域，未同步的原始信号）----
    input  wire        I_stat_tgl,        // 每帧末翻转
    input  wire [39:0] I_luma_sum,
    input  wire [31:0] I_pix_cnt,
    input  wire [31:0] I_hi_cnt,
    input  wire [31:0] I_lo_cnt,

    // ---- 与 uicfgcs500_720p 的握手 ----
    input  wire        I_cam_cfg_done,    // init 表下发完成
    input  wire        I_ae_cfg_done,     // AE 表下发完成（下载中为 0）
    output reg         O_ae_req,          // ★单拍脉冲★（uicfgcs500_720p 在 state==0 里检查，
                                          //   拉高不放会一直复位 reg_index ⇒ 必须只高一个周期）

    // ---- 给传感器的值 ----
    output reg  [15:0] O_exposure_time,   // 曝光行数
    output reg  [15:0] O_analog_gain,     // {0x3e08 值, 0x3e09 值}

    // ---- 观测（OSD / ChipWatcher 用）----
    output reg  [7:0]  O_meas_luma,       // 上一帧实测平均亮度（≈真值 *0.989）
    output reg  [6:0]  O_gain_idx,        // 当前生效的增益索引
    output reg  [1:0]  O_state            // 0=等配置 1=稳定中 2=闭环中 3=冻结
);

    //=========================================================================
    // 0. elaboration 期常数（不消耗任何硬件）
    //=========================================================================
    localparam [47:0] TARGET_SUM   = NOM_PIX * TARGET_MEAN;   // 目标亮度"和"
    localparam [47:0] DEADBAND_SUM = TARGET_SUM / 21;         // 约 4.76% 死区

    //=========================================================================
    // 1. 跨域：单 bit 翻转 → 两级同步 → 边沿脉冲 → 数据锁存
    //    ae_stat 的数据在翻转沿之后保持约 16.7ms，本域晚 2 个 24MHz 周期
    //    （83ns）取样，窗口余量约 200000 倍，不需要握手。
    //=========================================================================
    reg        S_tgl_s0, S_tgl_s1, S_tgl_s2;
    reg [39:0] S_luma_sum;
    reg [31:0] S_pix_cnt, S_hi_cnt, S_lo_cnt;

    wire S_frame_evt = S_tgl_s1 ^ S_tgl_s2;      // 单周期脉冲

    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            S_tgl_s0   <= 1'b0;
            S_tgl_s1   <= 1'b0;
            S_tgl_s2   <= 1'b0;
            S_luma_sum <= 40'd0;
            S_pix_cnt  <= 32'd0;
            S_hi_cnt   <= 32'd0;
            S_lo_cnt   <= 32'd0;
        end else begin
            S_tgl_s0 <= I_stat_tgl;
            S_tgl_s1 <= S_tgl_s0;
            S_tgl_s2 <= S_tgl_s1;
            if (S_frame_evt) begin
                S_luma_sum <= I_luma_sum;
                S_pix_cnt  <= I_pix_cnt;
                S_hi_cnt   <= I_hi_cnt;
                S_lo_cnt   <= I_lo_cnt;
            end
        end
    end

    //=========================================================================
    // 2. 判据（全部是常数比较，零乘法/零除法）
    //=========================================================================
    wire [31:0] S_pix_v   = (S_pix_cnt == 32'd0) ? 32'd1 : S_pix_cnt;
    wire        S_frame_ok = (S_pix_cnt > (NOM_PIX >> 1));    // 少于半帧不动作（防半帧/丢帧误判）

    wire        S_hi_hot  = (S_hi_cnt > (S_pix_v >> HI_GUARD_SHIFT)); // 削顶过多
    wire        S_lo_hot  = (S_lo_cnt > (S_pix_v >> LO_GUARD_SHIFT)); // 见下方 LO_GUARD_SHIFT 的说明

    //-------------------------------------------------------------------------
    // ★★ 2026-10-12 修：量纲对齐 ★★
    //   ae_stat.v 的 O_luma_sum 契约是 Σ(Y * 256)（它把 77R+150G+29B 直接累加，
    //   没有做 >>8；见 ae_stat.v:66 的注释与 :90-93 的移位加法树）。
    //   而 TARGET_SUM 是 ΣY（scale x1）。两者差 256 倍。
    //
    //   原写法 `wire [39:0] S_lsum = S_luma_sum;` 直接比 ⇒ S_lsum 永远比
    //   S_target 大 256 倍 ⇒ S_too_bright 恒真 ⇒ 每一帧都执行 S_gi_dec
    //   ⇒ 增益一路砸到最低档。上板现象（2026-10-12 20:03 批次）：
    //     A1 Ymean 6.24 -> A2 2.17 -> A3 1.12 -> A4 0.98，越开越黑。
    //
    //   取高 32 位 = 精确除以 256（因为 Σ(Y*256) 一定是 256 的整数倍，无信息损失）。
    //   量程校验：ΣY 最大 = 921600*255 = 2.35e8 < 2^28，32 位绰绰有余。
    //-------------------------------------------------------------------------
    wire [39:0] S_lsum      = {8'd0, S_luma_sum[39:8]};
    wire [39:0] S_target    = TARGET_SUM[39:0];
    wire [39:0] S_dband     = DEADBAND_SUM[39:0];
    wire [39:0] S_hi_bound  = S_target + S_dband;
    wire [39:0] S_lo_bound  = S_target - S_dband;

    wire        S_too_dark   = (S_lsum < S_lo_bound);
    wire        S_too_bright = (S_lsum > S_hi_bound);
    wire [39:0] S_absdiff    = S_too_bright ? (S_lsum - S_target) : (S_target - S_lsum);
    wire        S_big_err    = (S_absdiff > S_target);        // 误差 >100%
    wire        S_mid_err    = (S_absdiff > (S_target >> 2)); // 误差 >25%

    wire [6:0]  S_step_n = S_big_err ? STEP_FAST : (S_mid_err ? STEP_MID : STEP_SLOW);

    // ---- 实测亮度回读（luma_sum + luma_sum/8) >> 20 ≈ 真均值 *0.989 ----
    wire [39:0] S_meas_tmp = S_lsum + (S_lsum >> 3);
    wire [19:0] S_meas20   = S_meas_tmp >> 20;
    wire [7:0]  S_meas8    = (S_meas20 > 20'd255) ? 8'd255 : S_meas20[7:0];

    //=========================================================================
    // 3. 增益索引 → 寄存器字节
    //    0x3e08 = 0x03/0x07/0x0F/0x1F（x1/x2/x4/x8，注意不是 0x03<<n）
    //    0x3e09 = 0x20 + 细档 0..31（x1.000..x1.969）
    //=========================================================================
    function [7:0] f_coarse;
        input [1:0] idx;
        begin
            case (idx)
                2'd0:    f_coarse = 8'h03;
                2'd1:    f_coarse = 8'h07;
                2'd2:    f_coarse = 8'h0F;
                default: f_coarse = 8'h1F;
            endcase
        end
    endfunction

    function [15:0] f_gain_bytes;
        input [6:0] idx;
        begin
            f_gain_bytes = {f_coarse(idx[6:5]), (8'h20 + {3'b000, idx[4:0]})};
        end
    endfunction

    //=========================================================================
    // 4. 主状态机
    //=========================================================================
    reg [7:0] S_settle;
    reg [6:0] S_gi;            // 当前已下发生效的索引
    reg [6:0] S_gi_tgt;        // ★本帧决定的目标档：必须锁存★
    reg       S_req_pend;      // 已决定要改档，等一次下发机会

    // 期望的下一档（组合）
    // ★必须显式写 [6:0]★ —— 写成 `wire S_gi_dec = ...`（无位宽）会被推断成 1 bit 的线，
    //   于是 120-1=119 被截成 119 的最低位 = 1，增益一帧就从 120 掉到 1。
    //   （2026-10-12 tb_ae_ctrl CASE 5 抓到这个 bug。同类隐患：任何做算术的 wire 都要写位宽。）
    wire [6:0] S_gi_dec = (S_gi > S_step_n) ? (S_gi - S_step_n) : 7'd0;
    // ★加档必须在 8 位上求和，再判溢出★
    //   写成 `wire [6:0] S_gi_inc_raw = S_gi + S_step_n;` 会让 124+8=132 先在
    //   7 位里截成 4，之后 `4 > 127` 恒假 ⇒ 钳位形同虚设 ⇒ 增益从接近满档
    //   直接跳到接近最低档，然后在"爬升→回绕→再爬升"之间振荡。
    //   （2026-10-12 tb_ae_ctrl CASE 6 抓到：增益 116 -> 4，一帧掉 112 档。）
    //   这与 CASE 5 那个"漏写位宽"是同一类错误：**凡是做算术的 wire，
    //   既要写对位宽，也要保证溢出判断发生在截断之前。**
    wire [7:0] S_gi_inc_raw = {1'b0, S_gi} + {1'b0, S_step_n};
    wire [6:0] S_gi_inc = (S_gi_inc_raw > 8'd127) ? 7'd127 : S_gi_inc_raw[6:0];

    // 是否允许在本帧做决策
    wire S_can_act = I_cam_cfg_done && I_ae_cfg_done && I_ae_en &&
                     S_frame_ok && (S_settle == SETTLE_FRAMES) && !S_req_pend;

    wire [6:0] S_gi_next = !S_can_act          ? S_gi
                         : (S_hi_hot)          ? S_gi_dec          // 护栏优先：无条件降
                         : (S_too_bright)      ? S_gi_dec
                         : (S_too_dark && !S_lo_hot) ? S_gi_inc
                         :                       S_gi;
    //   ★!!S_lo_hot 这一项默认恒真（LO_GUARD_SHIFT = 0 ⇒ >>0 = 自身 ⇒
    //     S_lo_cnt > S_pix_cnt 永不成立）★
    //   原因：上板实测（2026-10-12 20:03/20:04）这一场景 dk<=8 的像素占
    //   65%~95%，旧的 LO_GUARD_SHIFT=2（阈值 25%）把加亮通道整个堵死，
    //   AE 在"本来就暗"的场景里反而完全不动 —— 而那不是我们想要的：
    //   暗场景加增益正是相机的正确行为，真正需要防的是高光削顶，
    //   那一侧已经有 S_hi_hot 兜着（阈值 1/64 ≈ 1.56%）。
    //   若将来要恢复"太黑就别追了"的策略，把 LO_GUARD_SHIFT 调回 2 即可。

    always @(posedge I_clk or negedge I_rst_n) begin
        if (!I_rst_n) begin
            S_settle        <= 8'd0;
            S_gi            <= GAIN_IDX_INIT;
            S_gi_tgt        <= GAIN_IDX_INIT;
            S_req_pend      <= 1'b0;
            O_ae_req        <= 1'b0;
            O_exposure_time <= EXPOSURE_FIXED;
            O_analog_gain   <= f_gain_bytes(GAIN_IDX_INIT);
            O_gain_idx      <= GAIN_IDX_INIT;
            O_meas_luma     <= 8'd0;
            O_state         <= 2'd0;
        end else begin
            // 默认：请求线拉低 ⇒ 只在下面那一个分支里高一个周期
            O_ae_req        <= 1'b0;
            O_exposure_time <= EXPOSURE_FIXED;

            // ---------- 4.1 状态指示 ----------
            if (!I_cam_cfg_done)
                O_state <= 2'd0;                       // 0 = 等 init 表 / AE 表下载中
            else if (!I_ae_en)
                O_state <= 2'd3;                       // 3 = 冻结
            else if (S_settle != SETTLE_FRAMES)
                O_state <= 2'd1;                       // 1 = 稳定计时中
            else if (!I_ae_cfg_done)
                O_state <= 2'd0;                       // 0 = AE 表下载中
            else
                O_state <= 2'd2;                       // 2 = 闭环运行

            // ---------- 4.2 每帧：更新回读值 + 数稳定帧 + 决策 ----------
            if (S_frame_evt) begin
                O_meas_luma <= S_meas8;
                // ★稳定帧计数只在 init 表未完成时清零★
                //   不能把 I_ae_cfg_done 也写进清零条件 —— 每下发一次 AE 表它都会拉低，
                //   若一起清零，AE 就退化成"每 SETTLE_FRAMES 帧才走一档"，收敛慢 60 倍。
                if (!I_cam_cfg_done)
                    S_settle <= 8'd0;
                else if (S_settle != SETTLE_FRAMES)
                    S_settle <= S_settle + 8'd1;
                else if (S_can_act && (S_gi_next != S_gi)) begin
                    // ★必须把目标档锁存到 S_gi_tgt，不能在下发那一拍再算 S_gi_next★
                    //   下发那一拍 S_req_pend 已经拉高 ⇒ S_can_act 变假 ⇒ S_gi_next 会被
                    //   组合地"回退"成 S_gi，结果 S_gi <= S_gi，增益永远不动。
                    //   （2026-10-12 tb_ae_ctrl CASE 4 抓到这个 bug：req_n=90 但 gain_idx 恒 64。）
                    S_gi_tgt   <= S_gi_next;
                    S_req_pend <= 1'b1;
                end
            end

            // ---------- 4.3 下发（与 I2C 表握手，天然限速）----------
            if (S_req_pend && I_ae_cfg_done && I_cam_cfg_done) begin
                S_gi          <= S_gi_tgt;
                O_gain_idx    <= S_gi_tgt;
                O_analog_gain <= f_gain_bytes(S_gi_tgt);
                O_ae_req      <= 1'b1;      // ★单拍脉冲★
                S_req_pend    <= 1'b0;
            end
        end
    end

endmodule
