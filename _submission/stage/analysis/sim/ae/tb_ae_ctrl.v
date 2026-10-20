//=============================================================================
// [HDR-2026-10-12] 文件 : tb_ae_ctrl.v
// 模块 : tb_ae_ctrl   —— ae_ctrl.v 的 Testbench
// 用法 : vlib work
//        vlog ae_ctrl.v tb_ae_ctrl.v
//        vsim -c -do "run -all; quit -f" tb_ae_ctrl
// 说明 : 本 TB 不需要 glbl（ae_ctrl 不例化任何 IP 原语）。
//        TB 侧自带一个 uicfgcs500_720p 的 AE 表握手模型：
//          O_ae_req 单拍脉冲 -> I_ae_cfg_done 拉低 AE_DL_CYCLES 拍 -> 再拉高。
// 覆盖 : CASE1 复位默认值      CASE2 配置未完成时不动作
//        CASE3 稳定期不动作     CASE4 欠亮 -> 逐档加亮并收敛进死区
//        CASE5 高光护栏优先降档 CASE6 极暗场景必须加亮（lo_hot 默认关闭）
//        CASE7 冻结(I_ae_en=0)  CASE8 请求脉冲宽度必须恰好 1 拍
//        CASE9 量纲回归（Σ(Y*256)）  CASE10 板上实测 A4 暗场景必须加亮
//=============================================================================
`timescale 1ns / 1ns

module tb_ae_ctrl;

    //-------------- 与 DUT 的 parameter 保持一致（TB 用小尺寸便于快速收敛）------
    localparam [7:0]  TGT       = 8'd70;
    localparam [31:0] NOM       = 32'd1048576;  // 2^20 ：使 DUT 的 >>20 回读有意义
    localparam [6:0]  GI_INIT   = 7'd64;        // 0x0F20 = 4.000x
    localparam [7:0]  SETTLE    = 8'd4;
    localparam [15:0] EXP       = 16'd1990;
    localparam integer AE_DL_CYCLES = 20;

    // TARGET_SUM = 2^20 * 70 = 73400320 ; DEADBAND = /21 = 3495253
    localparam [39:0] TSUM      = 40'd73400320;
    localparam [39:0] DBAND     = 40'd3495253;

    reg         clk = 0;
    reg         rst_n = 0;
    reg         ae_en = 1;
    reg         stat_tgl = 0;
    reg  [39:0] luma_sum = 0;
    reg  [31:0] pix_cnt = 0, hi_cnt = 0, lo_cnt = 0;
    reg         cam_cfg_done = 0;
    reg         ae_cfg_done  = 0;

    wire        ae_req;
    wire [15:0] exposure_time, analog_gain;
    wire [7:0]  meas_luma;
    wire [6:0]  gain_idx;
    wire [1:0]  state;

    integer errors = 0;
    integer req_n  = 0;
    reg     req_seen = 0;
    reg     req_stuck = 0;
    integer max_pulse = 0;
    integer cur_pulse = 0;

    //-------------- DUT -------------------------------------------------------
    ae_ctrl #(
        .TARGET_MEAN    (TGT),
        .NOM_PIX        (NOM),
        .EXPOSURE_FIXED (EXP),
        .GAIN_IDX_INIT  (GI_INIT),
        .SETTLE_FRAMES  (SETTLE)
    ) dut (
        .I_clk           (clk),
        .I_rst_n         (rst_n),
        .I_ae_en         (ae_en),
        .I_stat_tgl      (stat_tgl),
        .I_luma_sum      (luma_sum),
        .I_pix_cnt       (pix_cnt),
        .I_hi_cnt        (hi_cnt),
        .I_lo_cnt        (lo_cnt),
        .I_cam_cfg_done  (cam_cfg_done),
        .I_ae_cfg_done   (ae_cfg_done),
        .O_ae_req        (ae_req),
        .O_exposure_time (exposure_time),
        .O_analog_gain   (analog_gain),
        .O_meas_luma     (meas_luma),
        .O_gain_idx      (gain_idx),
        .O_state         (state)
    );

    //-------------- 时钟 -------------------------------------------------------
    always #10 clk = ~clk;          // 20 ns

    //-------------- 请求脉冲监测 ----------------------------------------------
    always @(posedge clk) begin
        if (ae_req) begin
            req_n = req_n + 1;
            cur_pulse = cur_pulse + 1;
            if (req_seen) req_stuck = 1;      // 连续两拍高 = 不是脉冲
            req_seen = 1;
            if (cur_pulse > max_pulse) max_pulse = cur_pulse;
        end else begin
            req_seen = 0;
            cur_pulse = 0;
        end
    end

    //-------------- uicfgcs500_720p 的 AE 表握手模型 --------------------------
    integer dl;
    always @(posedge clk) begin
        if (!rst_n) begin
            dl = 0;
            ae_cfg_done <= 1'b0;
        end else if (ae_req) begin
            dl = AE_DL_CYCLES;
            ae_cfg_done <= 1'b0;
        end else if (dl != 0) begin
            dl = dl - 1;
            if (dl == 1) ae_cfg_done <= 1'b1;
        end
    end

    //-------------- 一帧的统计值 ----------------------------------------------
    // 亮度模型：luma_sum = 当前增益索引 * 110  (gi=122..127 时落在 14000 附近)
    task do_frame(input [39:0] ls, input [31:0] hi, input [31:0] lo);
        begin
            luma_sum = ls;
            pix_cnt  = NOM;
            hi_cnt   = hi;
            lo_cnt   = lo;
            #200;
            stat_tgl = ~stat_tgl;       // 帧结束
            #1000;                      // 留足时间给下发模型
        end
    endtask

    // 用当前增益索引算出这一帧的亮度总和（x1 口径）。
    // 亮度模型：mean(gi) = gi * 9 / 16  （gi=124 -> 69.75, gi=127 -> 71.4）
    //           ΣY = mean * 2^20 = gi * 589824
    function [39:0] ls_x1(input [6:0] gi);
        begin
            ls_x1 = gi * 40'd589824;
        end
    endfunction

    //==========================================================================
    // ★★ 接口契约（2026-10-12 补）★★
    //   ae_stat.v 的 O_luma_sum 口径是 Σ(Y * 256)，不是 ΣY —— 它把
    //   77R+150G+29B 直接累加、没有 >>8。证据：
    //     ae_stat.v:66    注释写的就是 "Σ (Y * 256)"
    //     ae_stat.v:90-93 移位加法树输出 18bit 后直接累加，无右移
    //     tb_ae_stat.v CASE 2  sum=8153600 = 256*(77*200+150*100+29*50)
    //   ae_ctrl 内部再取 [39:8] 还原成 ΣY 后与 TARGET_SUM 比较。
    //
    //   旧版 TB 直接往 I_luma_sum 灌 ΣY，**恰好把这个 256 倍量纲错误遮住了**：
    //   TB 全过、上板才暴露（AE 每帧都判"过亮"，增益一路降到最低档，
    //   画面越开越黑：A1 6.24 -> A2 2.17 -> A3 1.12 -> A4 0.98）。
    //   所以这里必须按 Σ(Y*256) 灌，并加 CASE 9 做量纲回归。
    //==========================================================================
    function [39:0] ls_of_gi(input [6:0] gi);
        begin
            ls_of_gi = ls_x1(gi) << 8;
        end
    endfunction

    // 把"想要的 ΣY"换算成 ae_stat 的口径
    function [39:0] as_stat(input [39:0] sum_x1);
        begin
            as_stat = sum_x1 << 8;
        end
    endfunction

    // TB 侧独立的"索引 -> 寄存器字节"参考模型（与 DUT 的 f_gain_bytes 同构，
    // 但不共用任何代码，用来抓 DUT 里查表写错的情况）
    function [7:0] exp_coarse(input [1:0] c);
        begin
            case (c)
                2'd0:    exp_coarse = 8'h03;
                2'd1:    exp_coarse = 8'h07;
                2'd2:    exp_coarse = 8'h0F;
                default: exp_coarse = 8'h1F;
            endcase
        end
    endfunction

    function [15:0] exp_gain_bytes(input [6:0] gi);
        reg [7:0] fine;
        begin
            fine = 8'h20 + {3'b000, gi[4:0]};
            exp_gain_bytes = {exp_coarse(gi[6:5]), fine};
        end
    endfunction

    task chk(input [255:0] name, input cond);
        begin
            if (cond) $display("  [OK]   %0s", name);
            else begin $display("  [FAIL] %0s", name); errors = errors + 1; end
        end
    endtask

    //==========================================================================
    integer i;
    reg [6:0] gi_before, gi_after;

    initial begin
        $display("=== tb_ae_ctrl start ===");

        //--------------------- CASE 1 : 复位默认值 ---------------------------
        rst_n = 0; #200; rst_n = 1; #100;
        $display("[CASE 1] reset defaults");
        chk("gain_idx resets to GAIN_IDX_INIT", gain_idx == GI_INIT);
        chk("analog_gain = 16'h0F20 (4.000x)", analog_gain == 16'h0F20);
        chk("exposure  = 1990",                exposure_time == 16'd1990);
        chk("state    = 0",                    state == 2'd0);
        chk("no request yet",                  req_n == 0);

        //--------------------- CASE 2 : 配置未完成 -> 不动作 -----------------
        $display("[CASE 2] cam_cfg_done=0 (no action)");
        cam_cfg_done = 0; ae_cfg_done = 0;
        for (i = 0; i < 20; i = i + 1) do_frame(40'd1000, 32'd0, 32'd0);  // 极暗
        chk("gain_idx unchanged", gain_idx == GI_INIT);
        chk("no request",         req_n == 0);

        //--------------------- CASE 3 : 稳定期不动作 -------------------------
        $display("[CASE 3] settle window (SETTLE_FRAMES=%0d)", SETTLE);
        cam_cfg_done = 1; ae_cfg_done = 1; #100;
        for (i = 0; i < SETTLE - 1; i = i + 1) do_frame(40'd1000, 32'd0, 32'd0);
        chk("still no request during settle", req_n == 0);
        chk("gain_idx still unchanged",       gain_idx == GI_INIT);
        chk("state == 1 (settling)",          state == 2'd1);

        //--------------------- CASE 4 : 欠亮 -> 加亮并收敛 -------------------
        $display("[CASE 4] under-exposed -> climb then converge");
        for (i = 0; i < 90; i = i + 1) begin
            do_frame(ls_of_gi(gain_idx), 32'd0, 32'd0);
        end
        $display("        final gain_idx=%0d  luma_sum(x1)=%0d  state=%0d  req_n=%0d",
                 gain_idx, ls_x1(gain_idx), state, req_n);
        chk("gain_idx climbed",                 gain_idx > GI_INIT);
        chk("converged inside dead-band",       (ls_x1(gain_idx) >= (TSUM-DBAND)) &&
                                                (ls_x1(gain_idx) <= (TSUM+DBAND)));
        chk("gain_idx in expected range 116..127", (gain_idx >= 7'd116) && (gain_idx <= 7'd127));
        chk("state == 2 (closed loop)",         state == 2'd2);
        chk("meas_luma plausible (65..85)",     (meas_luma >= 8'd65) && (meas_luma <= 8'd85));
        chk("requests were generated",          req_n > 10);

        //--------------------- CASE 5 : 高光护栏优先降档 ---------------------
        $display("[CASE 5] highlight guard overrides (hi_cnt=20 > 200/64=3)");
        gi_before = gain_idx;
        do_frame(as_stat(TSUM), 32'd0, 32'd0);          // flush：先让上一用例的高光统计过去
        gi_before = gain_idx;
        for (i = 0; i < 4; i = i + 1) begin
            do_frame(as_stat(TSUM), 32'd20000, 32'd0);  // 亮度在靶心 + 高光超限
            $display("        frame %0d : O_gain_idx=%0d (S_gi=%0d) step=%0d req_n=%0d",
                     i, gain_idx, dut.S_gi, dut.S_step_n, req_n);
        end
        gi_after = gain_idx;
        gi_after = gain_idx;
        $display("        gain_idx %0d -> %0d", gi_before, gi_after);
        chk("index decreased despite in-band brightness", gi_after < gi_before);

        //--------------------- CASE 6 : 极暗场景必须加亮 ----------------------
        // ★2026-10-12 行为变更★：LO_GUARD_SHIFT 默认改成 0（关闭该护栏），
        //   因为上板场景（宿舍、只开显示器）整帧 dk<=8 占 65%~95%，
        //   旧的阈值 25% 把加亮通道整个堵死 —— 而暗场景加增益正是相机的
        //   正确行为；真正要防的削顶由 S_hi_hot 兜着。
        //   本用例断言：整帧近黑 + 亮度远低于靶 ⇒ 必须加亮。
        $display("[CASE 6] very dark scene must BRIGHTEN (lo_hot disabled by default)");
        do_frame(as_stat(40'd1000000), 32'd0, 32'd300000);   // flush
        gi_before = gain_idx;
        for (i = 0; i < 8; i = i + 1) do_frame(as_stat(40'd1000000), 32'd0, 32'd300000);
        gi_after = gain_idx;
        $display("        gain_idx %0d -> %0d  (near-black frac = 300000/1048576 = 28.6%%)",
                 gi_before, gi_after);
        chk("index INCREASED despite 28.6% near-black pixels", gi_after > gi_before);

        //--------------------- CASE 7 : 冻结 ---------------------------------
        $display("[CASE 7] freeze (I_ae_en=0)");
        ae_en = 0; #200;
        gi_before = gain_idx;
        for (i = 0; i < 12; i = i + 1) do_frame(40'd1000, 32'd0, 32'd0);
        gi_after = gain_idx;
        $display("        gain_idx %0d -> %0d  state=%0d", gi_before, gi_after, state);
        chk("index frozen",           gi_after == gi_before);
        chk("analog_gain frozen",     analog_gain == exp_gain_bytes(gi_before));
        chk("state == 3",             state == 2'd3);
        ae_en = 1; #200;

        //--------------------- CASE 8 : 请求脉冲宽度 -------------------------
        $display("[CASE 8] O_ae_req pulse width");
        $display("        total requests=%0d  max pulse width=%0d cycles", req_n, max_pulse);
        chk("every request is exactly 1 cycle wide", (req_stuck == 0) && (max_pulse == 1));

        //--------------------- CASE 9 : ★量纲回归（2026-10-12 上板 bug）★ ----
        //   灌一个"在 ×256 口径下正好等于 TARGET_SUM"的值：
        //     正确实现 ⇒ S_lsum = TARGET_SUM ⇒ 落在死区内 ⇒ 索引不动
        //     旧实现   ⇒ S_lsum = TARGET_SUM<<8 ⇒ 判为过亮 ⇒ 降档   ← 就是这个 bug
        $display("[CASE 9] scale regression: luma_sum = TARGET_SUM<<8 must be in dead-band");
        do_frame(as_stat(TSUM), 32'd0, 32'd0);
        // 结果级检查：DUT 内部还原出来的 S_lsum 必须正好等于 TARGET_SUM。
        // 旧写法（直接比 I_luma_sum）会得到 TARGET_SUM<<8，这一条立刻报错。
        $display("        dut.S_lsum=%0d   TARGET_SUM=%0d", dut.S_lsum, TSUM);
        chk("DUT S_lsum == TARGET_SUM (x1 scale restored)", dut.S_lsum == TSUM);
        gi_before = gain_idx;
        for (i = 0; i < 6; i = i + 1) do_frame(as_stat(TSUM), 32'd0, 32'd0);
        gi_after = gain_idx;
        $display("        gain_idx %0d -> %0d (must be equal)", gi_before, gi_after);
        chk("in dead-band => index unchanged", gi_after == gi_before);

        //--------------------- CASE 10 : 板上实测场景回归 ---------------------
        //   2026-10-12 20:03 A4 实测：Ymean 0.98、dk<=8 占 95.4%、几乎全黑。
        //   换算 ΣY = 0.98 * 2^20 ≈ 1027604（TB 用 NOM=2^20）。
        //   旧实现这里会降档（→ 上板"越开越黑"）；正确实现必须加档。
        //   lo_cnt 故意取 1000000（占 95.4%），刚好卡在旧阈值 25% 之上 ——
        //   同时验证 lo_hot 护栏确实已关闭。
        $display("[CASE 10] on-board A4 scene (Ymean 0.98, 95.4%% near-black) must BRIGHTEN");
        // 先把增益压到低档：喂一个远高于靶的亮帧。否则上一用例已把增益顶到 127，
        // "必须加档"在满档上无法成立。
        for (i = 0; i < 30; i = i + 1) do_frame(as_stat(40'd800000000), 32'd0, 32'd0);
        $display("        preset: gain_idx driven down to %0d", gain_idx);
        do_frame(as_stat(40'd1027604), 32'd0, 32'd1000000);
        gi_before = gain_idx;
        for (i = 0; i < 6; i = i + 1) do_frame(as_stat(40'd1027604), 32'd0, 32'd1000000);
        gi_after = gain_idx;
        $display("        gain_idx %0d -> %0d (must increase)", gi_before, gi_after);
        chk("dark on-board scene brightens",  gi_after > gi_before);

        //--------------------- 汇总 ------------------------------------------
        if (errors == 0) $display("*** ALL PASS, errors=0 ***");
        else             $display("*** FAILED, errors=%0d ***", errors);
        $display("=== tb_ae_ctrl end ===");
        $finish;
    end

    // 防跑飞
    initial begin
        #5_000_000;
        $display("*** TIMEOUT ***");
        $finish;
    end

endmodule
