//=============================================================================
//  tb_lsc.v  ——  lsc.v 的 Testbench
//  只验"会真的坏掉的地方"：
//    CASE 1 复位
//    CASE 2 bypass 必须是逐位恒等（含 0 / 255 边界）
//    CASE 3 非 bypass 时逐像素与 TB 侧独立参考模型对齐（含全部 4 个像素位）
//    CASE 4 延迟必须恰好 2 拍（下游 tvalid/tuser/tlast 与数据同相）
//    CASE 5 行/列计数器（320 beat 一行、720 行一帧，tlast/tuser 归零）
//    CASE 6 饱和（v=255, k=7 -> 255，不许回绕）
//    CASE 7 完整二维表：kR/kB 都在 0..15，且画面中心抬得比四角多
//  本模块不例化任何 IP，不需要 glbl。
//=============================================================================
`timescale 1ns / 1ps

module tb_lsc;

    reg         clk = 0;
    reg         rst_n = 0;
    reg         bypass = 0;
    reg  [95:0] i_data = 0;
    reg         i_valid = 0, i_user = 0, i_last = 0;
    wire [95:0] o_data;
    wire        o_valid, o_user, o_last;

    integer errors = 0;
    integer n_chk  = 0;

    localparam [11:0] H_BEATS = 12'd320;
    localparam [11:0] V_LINES = 12'd720;
    localparam [9:0]  K_MAX   = 10'd1023;

    always #5 clk = ~clk;      // 100 MHz 便于观察

    lsc #(
        .LSC_ENABLE(1'b1),
        .H_BEATS   (H_BEATS),
        .V_LINES   (V_LINES),
        .K_MAX     (K_MAX)
    ) dut (
        .I_clk(clk), .I_rst_n(rst_n), .I_bypass(bypass),
        .I_tdata(i_data), .I_tvalid(i_valid), .I_tuser(i_user), .I_tlast(i_last),
        .O_tdata(o_data), .O_tvalid(o_valid), .O_tuser(o_user), .O_tlast(o_last)
    );

    // ---- TB 侧独立参考模型（与 DUT 的 F_mul/F_apply 同构但不共用代码）----
    // ★2026-10-14 改：系数 4bit(1/64) -> 10bit(1/1024)★
    //  DUT 用 10 条显式条件加法；这里刻意改成 for 循环移位累加 —— 两套实现不同源，
    //  才抓得到 DUT 里某一位漏加/加错。
    function [17:0] ref_mul(input [7:0] v, input [9:0] kq);
        integer i;
        reg [17:0] acc;
        begin
            acc = 18'd0;
            for (i = 0; i < 10; i = i + 1)
                if (kq[i]) acc = acc + ({10'd0, v} << i);
            ref_mul = acc;
        end
    endfunction

    function [7:0] ref_apply(input [7:0] v, input [9:0] kq);
        reg [17:0] p;
        reg [8:0]  s;
        begin
            p = ref_mul(v, kq);             // 函数返回值不能直接做位选，先存下来
            s = {1'b0, v} + {1'b0, p[17:10]};
            ref_apply = s[8] ? 8'd255 : s[7:0];
        end
    endfunction

    task chk(input [255:0] name, input cond);
        begin
            n_chk = n_chk + 1;
            if (!cond) begin
                errors = errors + 1;
                $display("  [FAIL] %0s", name);
            end
        end
    endtask

    // 把 4 个像素打包
    function [95:0] pack4(input [7:0] r0, g0, b0, r1, g1, b1, r2, g2, b2, r3, g3, b3);
        pack4 = {r3, g3, b3, r2, g2, b2, r1, g1, b1, r0, g0, b0};
    endfunction

    // 打一拍（推进一个 beat）
    task step(input [95:0] d, input v, input u, input l);
        begin
            @(negedge clk);
            i_data = d; i_valid = v; i_user = u; i_last = l;
            @(posedge clk);
            #1;
        end
    endtask

    integer i, k;
    reg [7:0] v0;
    reg [95:0] din, dref;
    reg [9:0]  kq;
    reg [9:0]  kqb;
    integer    iy, ix;
    reg [19:0] kv2;
    reg [19:0] kc, ke;

    initial begin
        $display("=== tb_lsc start ===");
        rst_n = 0;
        repeat (4) @(posedge clk);
        #1;

        // ---------------- CASE 1 复位 ----------------
        chk("CASE1 o_valid=0",  o_valid === 1'b0);
        chk("CASE1 o_data=0",   o_data  === 96'd0);
        chk("CASE1 bx=0",       dut.S_bx === 9'd0);
        chk("CASE1 y=0",        dut.S_y  === 12'd0);
        $display("[CASE 1] reset ok");

        rst_n = 1;
        repeat (2) @(posedge clk);

        // ---------------- CASE 4 延迟恰好 2 拍 ----------------
        @(negedge clk);
        i_data = pack4(8'd10,8'd10,8'd10, 8'd20,8'd20,8'd20, 8'd30,8'd30,8'd30, 8'd40,8'd40,8'd40);
        i_valid = 1'b1; i_user = 1'b0; i_last = 1'b0;
        @(posedge clk); #1;
        chk("CASE4 v after1 = 0", o_valid === 1'b0);
        @(posedge clk); #1;
        chk("CASE4 v after2 = 1", o_valid === 1'b1);
        $display("[CASE 4] latency = 2 cycles ok");
        @(negedge clk); i_valid = 0; i_user = 0; i_last = 0;
        repeat (3) @(posedge clk);

        // ---------------- CASE 2 bypass = 逐位恒等 ----------------
        bypass = 1'b1;
        @(negedge clk);
        din = pack4(8'd0,8'd1,8'd2, 8'd253,8'd254,8'd255, 8'd17,8'd99,8'd200, 8'd128,8'd64,8'd32);
        i_data = din; i_valid = 1'b1;
        @(posedge clk); @(posedge clk); @(posedge clk); #1;
        chk("CASE2 bypass identity", o_data === din);
        @(negedge clk); i_valid = 0;
        repeat (3) @(posedge clk);
        $display("[CASE 2] bypass identity ok");
        bypass = 1'b0;
        repeat (2) @(posedge clk);

        // ---------------- CASE 3 非 bypass：逐像素对独立参考模型 ----------------
        // 在若干个 (x,y) 位置上灌入固定图样，比较 DUT 输出与 ref_apply(v, S_k_r)
        for (i = 0; i < 40; i = i + 1) begin
            v0 = (i * 37 + 11) & 8'hff;
            @(negedge clk);
            din = pack4(v0, 8'd200, v0^8'h5a, v0+8'd7, 8'd180, v0^8'h33,
                        v0+8'd19, 8'd150, v0^8'h77, v0+8'd31, 8'd120, v0^8'h11);
            i_data = din; i_valid = 1'b1;
            @(posedge clk); #1;
            // ★采样时机★ 延迟恰好 2 拍：本拍 S_k_r/S_d_r 装的正是刚灌进去的 beat，
            //   再等一拍 F_apply 的组合结果才被 O_tdata 锁存。早拍或晚拍都会错位。
            kq  = dut.S_kr_r;
            kqb = dut.S_kb_r;
            @(posedge clk); #1;
            dref = pack4(ref_apply(din[23:16], kq ), din[15: 8], ref_apply(din[ 7: 0], kqb),
                         ref_apply(din[47:40], kq ), din[39:32], ref_apply(din[31:24], kqb),
                         ref_apply(din[71:64], kq ), din[63:56], ref_apply(din[55:48], kqb),
                         ref_apply(din[95:88], kq ), din[87:80], ref_apply(din[79:72], kqb));
            if (o_data !== dref) begin
                errors = errors + 1;
                $display("  [FAIL] CASE3 i=%0d kR=%0d kB=%0d dut=%h ref=%h", i, kq, kqb, o_data, dref);
            end
            n_chk = n_chk + 1;
            // G 通道必须逐位不动
            if (o_data[15:8]!==din[15:8] || o_data[39:32]!==din[39:32] ||
                o_data[63:56]!==din[63:56] || o_data[87:80]!==din[87:80]) begin
                errors = errors + 1; $display("  [FAIL] CASE3 G 通道被改动了 i=%0d", i);
            end
            n_chk = n_chk + 1;
        end
        @(negedge clk); i_valid = 0;
        repeat (3) @(posedge clk);
        $display("[CASE 3] 逐像素参考模型比对 ok (40 组 x 4 像素)");

        // ---------------- CASE 6 饱和 ----------------
        chk("CASE6 ref_apply(255,1023)=255", ref_apply(8'd255, 10'd1023) === 8'd255);
        chk("CASE6 ref_apply(255,0)=255",    ref_apply(8'd255, 10'd0   ) === 8'd255);
        chk("CASE6 ref_apply(0,1023)=0",     ref_apply(8'd0,   10'd1023) === 8'd0);
        chk("CASE6 ref_apply(100,0)=100",    ref_apply(8'd100, 10'd0   ) === 8'd100);
        $display("[CASE 6] saturation ok");

        // ---------------- CASE 7 表合法性（完整二维表版）----------------
        for (iy = 0; iy < 12; iy = iy + 1)
            for (ix = 0; ix < 20; ix = ix + 1) begin
                kv2 = dut.F_k2d(iy[3:0], ix[4:0]);
                chk("CASE7 kR in 0..1023", kv2[19:10] <= 10'd1023);
                chk("CASE7 kB in 0..1023", kv2[ 9: 0] <= 10'd1023);
            end
        // 画面中心必须比四角抬得更多（否则表装反了）
        kc = dut.F_k2d(4'd6, 5'd9);
        ke = dut.F_k2d(4'd0, 5'd0);
        chk("CASE7 center kR > corner kR", kc[19:10] > ke[19:10]);
        chk("CASE7 center kB > corner kB", kc[ 9: 0] > ke[ 9: 0]);
        $display("[CASE 7] 二维表范围 0..1023 且中心抬得比四角多 ok (center kR=%0d kB=%0d / corner kR=%0d kB=%0d)",
                 kc[19:10], kc[9:0], ke[19:10], ke[9:0]);

        // ---------------- CASE 5 计数器 ----------------
        // 灌满一行（H_BEATS 拍，最后一拍 tlast）后 bx 应回到 0、y 加 1
        rst_n = 0; repeat (3) @(posedge clk); rst_n = 1; repeat (2) @(posedge clk);
        for (i = 0; i < H_BEATS; i = i + 1)
            step(pack4(8'd60,8'd60,8'd60, 8'd60,8'd60,8'd60, 8'd60,8'd60,8'd60, 8'd60,8'd60,8'd60),
                 1'b1, 1'b0, (i == H_BEATS-1));
        @(negedge clk); i_valid = 0; i_last = 0;
        repeat (2) @(posedge clk); #1;
        chk("CASE5 bx wrap to 0", dut.S_bx === 9'd0);
        chk("CASE5 y = 1",        dut.S_y  === 12'd1);
        $display("[CASE 5] 行计数 ok (bx=%0d y=%0d)", dut.S_bx, dut.S_y);

        // tuser 应把行列都清 0
        step(pack4(8'd60,8'd60,8'd60, 8'd60,8'd60,8'd60, 8'd60,8'd60,8'd60, 8'd60,8'd60,8'd60),
             1'b1, 1'b1, 1'b0);
        @(negedge clk); i_valid = 0; i_user = 0;
        repeat (2) @(posedge clk); #1;
        chk("CASE5 tuser clears bx", dut.S_bx === 9'd0);
        chk("CASE5 tuser clears y",  dut.S_y  === 12'd0);
        $display("[CASE 5] tuser 清零 ok");

        // ---------------- CASE 8 双线性插值 F_lerp 参考校验 ----------------
        // ★2026-10-14 新增★ DUT 的 F_lerp 用 4 项条件移位相加实现 (k1-k0)*f，
        // 这里用有符号整数乘法搭一套独立参考，两套实现不同源，才抓得到漏项/位宽问题。
        begin : case8
            integer ki, fi;
            reg [9:0] la, lb, lgot;
            reg signed [15:0] ld, lexp, lprod;
            for (ki = 0; ki < 14; ki = ki + 1) begin
                case (ki)
                    0:  begin la = 10'd0;    lb = 10'd0;    end
                    1:  begin la = 10'd0;    lb = 10'd1023; end
                    2:  begin la = 10'd1023; lb = 10'd0;    end
                    3:  begin la = 10'd100;  lb = 10'd110;  end
                    4:  begin la = 10'd512;  lb = 10'd512;  end
                    5:  begin la = 10'd1023; lb = 10'd1023; end
                    6:  begin la = 10'd1;    lb = 10'd2;    end
                    7:  begin la = 10'd1000; lb = 10'd1001; end
                    8:  begin la = 10'd0;    lb = 10'd16;   end
                    9:  begin la = 10'd64;   lb = 10'd80;   end
                    10: begin la = 10'd900;  lb = 10'd1000; end
                    11: begin la = 10'd7;    lb = 10'd8;    end
                    12: begin la = 10'd0;    lb = 10'd1023; end
                    default: begin la = 10'd1023; lb = 10'd0; end
                endcase
                for (fi = 0; fi < 16; fi = fi + 1) begin
                    ld    = $signed({6'b000000, lb}) - $signed({6'b000000, la});
                    lprod = ld * fi;                       // TB 侧用乘法，与 DUT 的移位加法不同源
                    lexp  = $signed({6'b000000, la}) + (lprod >>> 4);
                    lgot  = dut.F_lerp(la, lb, fi[3:0]);
                    chk("CASE8 F_lerp", lgot === lexp[9:0]);
                end
            end
            $display("[CASE 8] F_lerp 224 组参考校验 ok (含端点与负差方向)");
        end

        $display("");
        if (errors == 0) $display("*** ALL PASS, errors=0  (n_chk=%0d) ***", n_chk);
        else             $display("*** FAILED, errors=%0d  (n_chk=%0d) ***", errors, n_chk);
        $finish;
    end

    // 超时保护
    initial begin
        #500000;
        $display("*** TIMEOUT ***");
        $finish;
    end

endmodule
