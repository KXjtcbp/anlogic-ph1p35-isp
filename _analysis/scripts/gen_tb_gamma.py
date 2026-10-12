# -*- coding: utf-8 -*-
"""生成 isp_gamma 的 ModelSim 测试台：从 RTL 里解析出 mem_b00 的 256 个值，
   写进 TB 的期望表，逐条比对"输入 i -> 输出 tbl[i]"（全 12 个字节通道同值，
   同时验证 12 张表复制循环、2 拍流水、旁路直通）。"""
import re, os

RTL = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v"
TB = r"E:\FPGA\_analysis\tb\tb_gamma_lut.v"

src = open(RTL, "r", encoding="utf-8", newline="").read()
tbl = re.search(r"    mem_b00\[  0\] = .*?mem_b00\[255\] = 8'h[0-9a-f]{2};", src, re.S).group(0)
vals = [int(v, 16) for v in re.findall(r"8'h([0-9a-f]{2})", tbl)]
assert len(vals) == 256, len(vals)

exp_lines = []
for i in range(0, 256, 8):
    exp_lines.append("        " + " ".join("exp_tbl[%3d] = 8'h%02x;" % (i + j, vals[i + j])
                                           for j in range(8)))
exp_block = "\n".join(exp_lines)

tb = r"""//=============================================================================
// [自动生成] 不要手改：由 E:\FPGA\_analysis\gen_tb_gamma.py 从 isp_gamma.v 的
//   内联表 mem_b00[0..255] 逐条导出期望值生成。
// 验证内容：
//   1) 旁路 I_gamma_bypass=1：8bit 原样通过（仍是 2 拍延迟）
//   2) 启用   I_gamma_bypass=0：输入 i 的输出必须 == 表[i]（256 条全查）
//   3) 12 个字节通道（4 像素 x RGB）逐拍严格相等（验证 12 张表复制循环）
//=============================================================================
`timescale 1ns/1ns
module tb_gamma_lut;
    reg         clk = 1'b0;
    always #5   clk = ~clk;
    reg         rst_n = 1'b0;
    reg  [95:0] td = 96'd0;
    reg         tvalid = 1'b0, tlast = 1'b0, tuser = 1'b0;
    reg         bypass = 1'b1, o_ready = 1'b1;
    wire [95:0] od;
    wire        ol, ou, ov, iready;

    isp_gamma dut (
        .I_clk(clk), .I_rst_n(rst_n), .I_tlast(tlast), .I_tuser(tuser),
        .I_tdata(td), .I_tvalid(tvalid), .I_tready(iready),
        .I_gamma_bypass(bypass),
        .O_tdata(od), .O_tlast(ol), .O_tuser(ou), .O_tvalid(ov), .O_tready(o_ready)
    );

    reg  [7:0] exp_tbl [0:255];
    reg  [7:0] got     [0:1023];
    integer n_got = 0, errors = 0, lane_err = 0, i, k;

    initial begin
__EXP__
    end

    // 采集输出（ov 高时抓一拍）；同时检查 12 个字节通道是否严格相等
    always @(posedge clk) begin
        if (ov) begin
            got[n_got] = od[7:0];
            if (od !== {12{od[7:0]}}) lane_err = lane_err + 1;
            n_got = n_got + 1;
        end
    end

    task drive(input [7:0] val);
    begin
        td = {12{val}};
        tvalid = 1'b1;
        @(posedge clk);
    end
    endtask

    task idle(input integer n);
    begin
        tvalid = 1'b0;
        td = 96'd0;
        for (i = 0; i < n; i = i + 1) @(posedge clk);
    end
    endtask

    integer t0;
    initial begin
        @(posedge clk);
        rst_n = 1'b0; @(posedge clk); @(posedge clk);
        rst_n = 1'b1; @(posedge clk);

        // ---- 用例 1：旁路直通 ----
        bypass = 1'b1;
        n_got = 0;
        drive(8'h00); drive(8'h2a); drive(8'hec); drive(8'hff); drive(8'h12); drive(8'h55);
        idle(4);
        $display("[1] bypass=1 收到 %0d 拍", n_got);
        if (n_got != 6) begin
            $display("  FAIL: 期望 6 拍直通"); errors = errors + 1;
        end
        for (i = 0; i < 6; i = i + 1) begin
            t0 = (i == 0) ? 8'h00 : (i == 1) ? 8'h2a : (i == 2) ? 8'hec :
                 (i == 3) ? 8'hff : (i == 4) ? 8'h12 : 8'h55;
            if (got[i] !== t0[7:0]) begin
                $display("  FAIL 直通[%0d]: got %02x exp %02x", i, got[i], t0[7:0]);
                errors = errors + 1;
            end
        end
        if (errors == 0) $display("  PASS: 000 2a ec ff 12 55 原样通过");

        // ---- 用例 2：256 条查表全覆盖 ----
        bypass = 1'b0;
        n_got = 0;
        for (k = 0; k < 256; k = k + 1) drive(k[7:0]);
        idle(4);
        $display("[2] bypass=0 收到 %0d 拍", n_got);
        if (n_got != 256) begin
            $display("  FAIL: 期望 256 拍"); errors = errors + 1;
        end
        for (i = 0; i < 256; i = i + 1) begin
            if (got[i] !== exp_tbl[i]) begin
                if (errors < 12) $display("  FAIL 查表[%0d]: got %02x exp %02x", i, got[i], exp_tbl[i]);
                errors = errors + 1;
            end
        end
        $display("  查表逐条比对错误数 = %0d", errors);
        $display("  12 通道不一致拍数   = %0d", lane_err);
        errors = errors + lane_err;

        // ---- 锚点 ----
        $display("  锚点: 0->%02x 4->%02x 8->%02x 42->%02x 64->%02x 118->%02x 160->%02x 200->%02x 236->%02x 255->%02x",
                 exp_tbl[0], exp_tbl[4], exp_tbl[8], exp_tbl[42], exp_tbl[64],
                 exp_tbl[118], exp_tbl[160], exp_tbl[200], exp_tbl[236], exp_tbl[255]);

        if (errors == 0) $display("==== ALL PASS ====");
        else             $display("==== FAIL: %0d ====", errors);
        $finish;
    end
endmodule
"""
tb = tb.replace("__EXP__", exp_block)
os.makedirs(os.path.dirname(TB), exist_ok=True)
with open(TB, "w", encoding="utf-8", newline="\n") as f:
    f.write(tb)
print("已生成 " + TB + "  (%d 期望值)" % len(vals))
