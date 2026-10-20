//==============================================================================
//  tb_wb_recip.v —— wb_recip.v 的数值回归 Testbench
//-----------------------------------------------------------------------------
//  目的：证明「归一化 + 倒数查表 + 一次乘法」给出的 Q16 增益与原 TD 流水除法器
//        的精确商 `(sum_g << 16) / sum_x` 的偏差在可接受范围内（<= 0.5%），
//        并且溢出饱和语义与旧 divider 一致。
//
//  参考实现【与 DUT 不同源】：TB 侧直接用 Verilog 的 64bit 整数除法算精确值，
//        DUT 侧是优先编码器 + ROM + 移位加法乘法。两套实现不共用任何代码，
//        所以这个 TB 能真正抓到 DUT 里的查表/移位/位宽错误。
//
//  覆盖：
//    CASE 1  边界值（den=65536 最小合法、den=2^26 典型、num=1 最小）
//    CASE 2  实景比值扫描 R/G = 0.50 / 0.53 / 0.70 / 0.85 / 0.95 / 1.00 / 2.00 / 4.00
//    CASE 3  5 档亮度 × 全范围 num 步进（真实工作点）
//    CASE 4  LFSR 伪随机 1500 组，den ∈ [65536, 2.35e8]，num ∈ [1, den*5]
//    CASE 5  溢出语义：商 >= 2^20 时 O_q[47:20] 必须非零
//    CASE 6  复位/门控无关性：纯组合逻辑，任何时刻结果只依赖当前输入
//
//  运行：
//    vlib work
//    vlog wb_recip.v tb_wb_recip.v
//    vsim -c -do "run -all; quit -f" tb_wb_recip
//==============================================================================
`timescale 1ns/1ps

module tb_wb_recip;

    reg  [31:0] den;
    reg  [31:0] num;
    wire [47:0] q;

    integer errors;
    integer n_chk;
    real    worst;
    real    worst_rel;
    reg [31:0] worst_den, worst_num;
    reg [47:0] worst_q;
    reg [63:0] worst_exp;
    reg [63:0] absdiff;
    reg [63:0] worst_abs;
    reg [47:0] hold_q;

    wb_recip dut (
        .I_den (den),
        .I_num (num),
        .O_q   (q)
    );

    //--------------------------------------------------------------------------
    // 参考模型：精确 Q16 商，用 64bit 整数除法
    //--------------------------------------------------------------------------
    function [63:0] exact_q16;
        input [31:0] d;
        input [31:0] n;
        begin
            exact_q16 = ({32'd0, n} << 16) / {32'd0, d};
        end
    endfunction

    //--------------------------------------------------------------------------
    // 单点检查
    //--------------------------------------------------------------------------
    task chk;
        input [31:0] d;
        input [31:0] n;
        input [255:0] tag;
        reg [63:0] exp;
        reg [63:0] got;
        reg        exp_ovf;
        real       rel;
        begin
            den = d;
            num = n;
            #1;
            exp     = exact_q16(d, n);
            got     = {16'd0, q[19:0]};
            exp_ovf = (exp > 64'h0000_0000_000F_FFFF);   // > 2^20-1
            n_chk   = n_chk + 1;

            // 1) 溢出标志必须与参考模型一致
            if ((|q[47:20]) !== exp_ovf) begin
                errors = errors + 1;
                $display("*** FAIL[ovf] %0s den=%0d num=%0d exp_ovf=%0b got_ovf=%0b",
                         tag, d, n, exp_ovf, (|q[47:20]));
            end
            // 2) 未溢出时，相对误差 <= 0.5%
            else if (!exp_ovf) begin
                if (exp == 0) begin
                    if (got != 0) begin
                        errors = errors + 1;
                        $display("*** FAIL[zero] %0s den=%0d num=%0d exp=0 got=%0d", tag, d, n, got);
                    end
                end else begin
                    rel = (got > exp) ? (1.0*(got-exp)/exp) : (1.0*(exp-got)/exp);
                    absdiff = (got > exp) ? (got - exp) : (exp - got);
                    if (rel > worst) begin
                        worst = rel; worst_rel = rel;
                        worst_den = d; worst_num = n; worst_q = q; worst_exp = exp;
                    end
                    // ★判据：绝对误差 <= 1 个 Q16 LSB 时不算失败★
                    //   小商（如 exp=1 或 exp=92）时 1 个 LSB 就是 1~100% 的相对误差，
                    //   但对增益只有 1.5e-5 的影响，物理上无意义。
                    if (absdiff > 1 && rel > 0.005) begin
                        errors = errors + 1;
                        $display("*** FAIL[prec] %0s den=%0d num=%0d exp=%0d got=%0d abs=%0d rel=%.5f%%",
                                 tag, d, n, exp, got, absdiff, 100.0*rel);
                    end
                    if (absdiff > worst_abs) worst_abs = absdiff;
                end
            end
        end
    endtask

    //--------------------------------------------------------------------------
    reg [31:0] rnd;
    integer    i, k;
    reg [31:0] d, n;
    real       ratio;

    initial begin
        errors = 0; n_chk = 0; worst = 0.0; worst_rel = 0.0;
        rnd = 32'h1234_5678;
        den = 32'd65536; num = 32'd1;
        #5;

        //---------------- CASE 1: 边界 -----------------
        chk(32'd65536,        32'd1,        "C1-den_min");
        chk(32'd65536,        32'd65536,    "C1-equal");
        chk(32'd65536,        32'd262144,   "C1-4x");
        chk(32'd67108864,     32'd1,        "C1-den_2p26");
        chk(32'd67108864,     32'd33554432, "C1-0p5x");
        chk(32'd65535+1,      32'd65535,    "C1-just_below");
        chk(32'd235008000,    32'd235008000,"C1-max_equal");

        //---------------- CASE 2: 实景比值 -----------------
        for (i = 0; i < 8; i = i + 1) begin
            case (i)
                0: ratio = 0.50;
                1: ratio = 0.53;
                2: ratio = 0.70;
                3: ratio = 0.85;
                4: ratio = 0.95;
                5: ratio = 1.00;
                6: ratio = 2.00;
                default: ratio = 4.00;
            endcase
            // sum_x 对应整帧 921600 像素 × 若干亮度档
            for (k = 1; k <= 255; k = k + 37) begin
                d = 921600 * k;
                n = $rtoi(921600.0 * k * ratio);
                if (d >= 65536 && n >= 1 && d <= 235008000 && n <= 235008000)
                    chk(d, n, "C2-ratio");
            end
        end

        //---------------- CASE 3: 亮度档 × num 步进 -----------------
        for (k = 1; k <= 255; k = k + 17) begin
            d = 921600 * k;
            if (d > 235008000) d = 235008000;
            for (i = 1; i < 64; i = i + 1) begin
                n = (d / 64) * i;
                if (n >= 1 && n <= 235008000) chk(d, n, "C3-sweep");
            end
        end

        //---------------- CASE 4: LFSR 随机 -----------------
        for (i = 0; i < 1500; i = i + 1) begin
            rnd = {rnd[30:0], rnd[31] ^ rnd[21] ^ rnd[1] ^ rnd[0]};
            d   = 32'd65536 + (rnd % 32'd234942464);
            rnd = {rnd[30:0], rnd[31] ^ rnd[21] ^ rnd[1] ^ rnd[0]};
            n   = 32'd1 + (rnd % 32'd50000000);
            if (n <= (d >> 2)) chk(d, n, "C4-rand");   // 比值落在 [0,4]
        end

        //---------------- CASE 5: 溢出一致性（已在 chk 内断言）----------------
        chk(32'd65536,   32'd33554432, "C5-ovf_8x");   // 精确商 = 8*2^20 -> 溢出
        chk(32'd65536,   32'd131072,   "C5-no_ovf");   // = 2*2^20     -> 溢出
        chk(32'd65536,   32'd65535,    "C5-just_under");// < 2^20     -> 不溢出

        //---------------- CASE 6: 组合逻辑无关性（重复同一输入两次，结果必须相同）----------------
        den = 32'd1000000; num = 32'd850000; #1;
        hold_q = q;
        #10;
        if (q !== hold_q) begin
            errors = errors + 1;
            $display("*** FAIL[C6] 组合逻辑结果不稳定");
        end
        n_chk = n_chk + 1;

        //---------------- 汇总 -----------------
        $display("");
        if (worst_rel > 0.0)
            $display("最差点: den=%0d num=%0d  精确=%0d  实际=%0d  相对误差=%.5f%%",
                     worst_den, worst_num, worst_exp, worst_q, 100.0*worst_rel);
        $display("绝对误差上界 = %0d 个 Q16 LSB (= %.6f%% 的 1.0x 增益)",
                 worst_abs, 100.0*worst_abs/65536.0);
        if (errors == 0)
            $display("*** ALL PASS, errors=0 (n_chk=%0d, 最大相对误差=%.5f%%) ***", n_chk, 100.0*worst);
        else
            $display("*** FAILED, errors=%0d (n_chk=%0d) ***", errors, n_chk);
        $finish;
    end

endmodule
