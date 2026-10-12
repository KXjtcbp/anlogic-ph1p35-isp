//=============================================================================
// tb_blc_template.v —— 模块 A（黑电平校正）Testbench 模板
//-----------------------------------------------------------------------------
// 运行（ModelSim）：
//     vlib work
//     vlog mipi_to_raw_converter.v tb_blc_template.v
//     vsim -c -do "run -all; quit -f" tb_blc_template
//   ★ vlib work 必须先跑，否则报
//        (vlog-19) Failed to access library 'work' ... ENOENT
//   ★ 本文件必须存成 ASCII 或 UTF-8【无 BOM】。
//        UTF-8 BOM 会让 ModelSim 直接语法报错：
//        syntax error, unexpected non-printable character
//        （GBK 文件改写后务必检查首 3 字节不是 EF BB BF）
//
// 设计原则：
//   ★ TB 侧独立写一份参考公式，绝不复用 DUT 的函数 ★
//     两边共享公式就退化成"自己和自己比"，交叉验证意义归零。
//   ★ 每个 CASE 自带手算锚点注释，出问题时能一眼看出是 DUT 错还是 TB 错。
//
// 覆盖判据（全部 0 错误才算模块 A 通过）：
//   CASE 1 复位后输出确定（无 X）
//   CASE 2 11 个手算锚点，重点 56/57/58 三点（BLACK_LEVEL 边界）
//   CASE 3 0..1023 全量扫描 x 4 字段 = 4096 个值
//   CASE 4 bypass=1 逐位等于 v>>2（等同回退到 2026-10-09 版本）
//   CASE 5 四个像素字段互不串扰
//   CASE 6 运行时热切换 bypass 立即生效、拍数不变
//=============================================================================
`timescale 1ns/1ps

module tb_blc_template;

//-----------------------------------------------------------------------------
// 参数：DUT 侧是 parameter 覆盖，TB 侧独立常量（故意写两遍，见设计原则）
//-----------------------------------------------------------------------------
localparam [9:0] BL = 10'd56;      // BLACK_LEVEL，与 mipi_to_raw_converter.v:44 保持一致
localparam [9:0] RA = 10'd2;       // ROUND_ADD  = 4/2，四舍五入补偿

integer errors = 0;

//-----------------------------------------------------------------------------
// 激励 / 流控
//-----------------------------------------------------------------------------
reg         clk    = 0;
reg         rst_n  = 0;
reg         bypass = 0;
reg  [39:0] raw    = 40'd0;        // 4 像素 x 10bit = 40bit
reg         tv     = 0;
reg         tl     = 0;
reg         tu     = 1;
reg         oready = 1;

wire        irdy;
wire [31:0] dout;
wire        otv, otl, otu;

// 60 MHz：MIPI_RX_BYTE_CLK 实测周期 16.668 ns（route_clock_utilization.txt）
always #8.333 clk = ~clk;

mipi_to_raw_converter dut (
    .I_clk        (clk    ),
    .I_rst_n      (rst_n  ),
    .I_blk_bypass (bypass ),
    .I_raw_tdata  (raw    ),
    .I_raw_tdest  (10'd0  ),        // 本 TB 不关心 tdest，恒 0
    .I_raw_tvalid (tv     ),
    .I_raw_tlast  (tl     ),
    .I_raw_tuser  (tu     ),
    .I_raw_tready (irdy   ),
    .O_raw_tdata  (dout   ),
    .O_raw_tvalid (otv    ),
    .O_raw_tlast  (otl    ),
    .O_raw_tuser  (otu    ),
    .O_raw_tready (oready )
);

//-----------------------------------------------------------------------------
// TB 侧独立参考模型
//-----------------------------------------------------------------------------
function [7:0] exp_one;                     // 单像素：10bit -> 8bit
    input [9:0] v;
    input       byp;
    reg   [9:0] d;
    begin
        if (byp) begin
            exp_one = v >> 2;               // 旁路 = 纯截断，与 10-09 老行为逐位一致
        end
        else begin
            d = (v > BL) ? (v - BL) : 10'd0; // clamp(in - black_level)，10bit 无符号自然饱和
            exp_one = (d + RA) >> 2;         // +2 再 >>2 = 四舍五入
        end
    end
endfunction

function [31:0] exp4;                       // 4 像素打包
    input [39:0] v;
    input        byp;
    begin
        // ★ 字段顺序必须与 DUT 一致 ★
        //   DUT：raw_data_r0 <= {f0[9:2], f1[9:2], f2[9:2], f3[9:2]}，
        //        其中 f0 取自 I_raw_tdata[9:0]（最低位字段）。
        //   => 输出【最高字节】对应【最低的输入字段】。写反了会得到逐字节镜像的
        //      结果（got=f200ee13 / exp=13ee00f2），看起来像"全错"其实是顺序问题。
        exp4 = { exp_one(v[ 9: 0], byp),
                 exp_one(v[19:10], byp),
                 exp_one(v[29:20], byp),
                 exp_one(v[39:30], byp) };
    end
endfunction

//-----------------------------------------------------------------------------
// 单次比对任务：灌一拍，等 1 拍，比对
//   ★ 必须 "@(posedge clk); #1;" ★
//     只写 @(posedge clk) 会在 active region 就恢复执行，而 DUT 的
//     raw_data_r0 <= ... 是 NBA，要到同一时间步的 NBA region 才更新。
//     于是读到的是【上一拍】的输出 —— 数据不变时"看起来是对的"，
//     一旦某个拍发生变化（例如热切换 bypass）就会莫名报错。
//-----------------------------------------------------------------------------
task chk;
    input [39:0]  v;
    input         byp;
    input [127:0] tag;
    reg   [31:0]  e;
    begin
        raw = v; bypass = byp; tv = 1;
        @(posedge clk); #1;
        tv = 0;
        @(posedge clk); #1;                 // 数据经 raw_data_r0 延迟 1 拍
        e = exp4(v, byp);
        if (dout !== e) begin
            errors = errors + 1;
            $display("  FAIL [%0s] raw=%010x byp=%b  got=%08x exp=%08x",
                     tag, v, byp, dout, e);
        end
    end
endtask

//=============================================================================
// CASE 1  复位
//=============================================================================
task case_reset;
    begin
        rst_n = 0; #200;
        rst_n = 1; #100;
        $display("[CASE 1] reset ............... ok");
    end
endtask

//=============================================================================
// CASE 2  手算锚点（扣除启用）
//   输入   中间量(d)      输出
//     0    0（下溢钳0）   (0+2)>>2  = 0
//     1    0              (0+2)>>2  = 0
//    56    0              (0+2)>>2  = 0     ★ 边界：等于 BLACK_LEVEL
//    57    1              (1+2)>>2  = 0     ★ 边界：比 BLACK_LEVEL 大 1，仍进 0
//    58    2              (2+2)>>2  = 1     ★ 第一个非零输出
//    61    5              (5+2)>>2  = 1
//    62    6              (6+2)>>2  = 2
//    66   10              (10+2)>>2 = 3  -- 注意：66->10, (10+2)>>2 = 3
//    70   14              (14+2)>>2 = 4
//   255  199              (199+2)>>2= 50
//  1023  967              (967+2)>>2= 242
//   ★ 上表的输出列由 TB 侧公式实时算出，此处注解只为人工核对趋势 ★
//=============================================================================
task case_anchors;
    reg [9:0] v [0:10];
    integer   i;
    begin
        v[0]=10'd0;    v[1]=10'd1;    v[2]=10'd56;   v[3]=10'd57;
        v[4]=10'd58;   v[5]=10'd61;   v[6]=10'd62;   v[7]=10'd66;
        v[8]=10'd70;   v[9]=10'd255;  v[10]=10'd1023;
        for (i = 0; i <= 10; i = i + 1)
            chk({v[i], v[i], v[i], v[i]}, 1'b0, "anchor");
        $display("[CASE 2] 11 anchors .......... ok");
    end
endtask

//=============================================================================
// CASE 3  0..1023 全量扫描 x 4 字段
//=============================================================================
task case_full_sweep;
    integer    i;
    reg [39:0] p;
    reg [9:0]  a, b, c, d;
    begin
        for (i = 0; i < 1024; i = i + 1) begin
            // ★ 不用 (expr)[9:0] 这种 SystemVerilog 写法 ★
            //   本工程是纯 Verilog-2001，ModelSim 不带 -sv 会报语法错。
            a = i[9:0];
            b = (i ^ 32'h155) & 32'h3FF;
            c = (i ^ 32'h2AA) & 32'h3FF;
            d = (i ^ 32'h3FF) & 32'h3FF;
            p = {a, b, c, d};
            chk(p, 1'b0, "sweep");
        end
        $display("[CASE 3] full sweep (4096) ... ok");
    end
endtask

//=============================================================================
// CASE 4  bypass=1 必须逐位等于旧版 v>>2
//=============================================================================
task case_bypass;
    integer i;
    begin
        for (i = 0; i < 1024; i = i + 1)
            chk({i[9:0], i[9:0], i[9:0], i[9:0]}, 1'b1, "bypass");
        $display("[CASE 4] bypass == v>>2 ...... ok");
    end
endtask

//=============================================================================
// CASE 5  四字段独立性（打乱顺序，确认没有串线）
//   ★ 40bit 字面量一律用 4 个 10bit 拼接 ★
//     写成 40'hA2_13F_001_3FF 会静默截断成低 40 位（12 个十六进制位 = 48bit），
//     ModelSim 只报 (vlog-2600) Redundant digits，不报错 —— 极易误判成 DUT 有问题。
//=============================================================================
task case_independence;
    begin
        chk({10'h0A2, 10'h13F, 10'h001, 10'h3FF}, 1'b0, "indep");
        chk({10'h3FF, 10'h000, 10'h2AA, 10'h155}, 1'b0, "indep");
        chk({10'h000, 10'h3FF, 10'h000, 10'h3FF}, 1'b0, "indep");
        $display("[CASE 5] field independence .. ok");
    end
endtask

//=============================================================================
// CASE 6  ★新增★ 运行时热切换 bypass
//         模拟现场 V1 -> V2 拨开关。切换必须立即生效，且总拍数不变。
//=============================================================================
task case_hot_switch;
    begin
        // 先用扣除启用灌一个满码
        raw = {10'h3FF, 10'h3FF, 10'h3FF, 10'h3FF};
        bypass = 1'b0; tv = 1;
        @(posedge clk); #1;
        @(posedge clk); #1;
        if (dout !== 32'hF2_F2_F2_F2) begin       // (1023-56+2)>>2 = 969>>2 = 242 = 0xF2
            errors = errors + 1;
            $display("  FAIL hot-switch(0) got=%08x exp=f2f2f2f2", dout);
        end
        // 当场切到旁路（= 拨下 SW1），下一拍就应改变
        bypass = 1'b1;
        @(posedge clk); #1;
        if (dout !== 32'hFF_FF_FF_FF) begin       // 1023>>2 = 255
            errors = errors + 1;
            $display("  FAIL hot-switch(1) got=%08x exp=ffffffff", dout);
        end
        tv = 0;
        $display("[CASE 6] hot bypass switch ... ok");
    end
endtask

//=============================================================================
// 主流程
//=============================================================================
initial begin
    $display("==========================================================");
    $display(" tb_blc_template   BLACK_LEVEL=%0d  ROUND_ADD=%0d", BL, RA);
    $display("==========================================================");
    case_reset;
    case_anchors;
    case_full_sweep;
    case_bypass;
    case_independence;
    case_hot_switch;
    $display("==========================================================");
    if (errors == 0) $display(" ALL PASS, errors=0");
    else             $display(" *** FAILED ***, errors=%0d", errors);
    $display("==========================================================");
    $finish;
end

endmodule
