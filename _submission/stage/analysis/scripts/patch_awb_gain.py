# -*- coding: utf-8 -*-
"""
模块 C（白平衡增益帧锁存 + 阻尼 + 钳位）补丁
==========================================
改 `isp/awb/awb.v`，4 个通道（done[0..3]）各一处 always 块。

现状（原厂实现，:281-:352 四个同构块）：
    always @(posedge I_clk or negedge I_rst_n)
        if (!I_rst_n || I_tuser) begin in_r_rN <= 20'h10000; in_b_rN <= 20'h10000; end
        else if (done[N-1]) begin ... in_r_rN <= in_r_xN[19:0]; ... end

问题（由 `sim/awb/tb_awb_zones.v` 实测，job pwsh-149）：
  * `done[N-1]` 每个有效拍都在更新增益，而累加和是「第 0..N 行」的运行值
    => 增益在帧内是一条斜坡。分区激励（帧均值 R/G 恰为 1.0000）实测输出 R/G = 1.3396，
       逐行 0.99/0.99/0.99/1.96/1.63/1.46/1.36 => 偏 34%。
  * `I_tuser` 复位增益 => **每帧第 0 行永远未校正**，画面顶部带一条色带。

改法（本脚本）：
  1. 新增 `in_r_tgtN / in_b_tgtN`：每拍跟踪最新商（自由运行的估计值），只做钳位。
  2. 原增益寄存器 `in_r_rN / in_b_rN` 改为**只在 `I_tuser` 更新一次**（帧边界），
     用阻尼 `g += (tgt - g) >>> WB_DAMP_SHIFT` 平滑 -> 帧内严格恒定，
     整帧均值被真正归一化，同时抑制自动曝光游走引起的抖动。
  3. 钳位从 `20'hfffff`（≈16x）收紧到 `[WB_GAIN_MIN, WB_GAIN_MAX] = [0.50x, 4.00x]`。
     传感器侧模拟增益上限 15.75x、室内实测原生 R/G≈0.86 => 实际需要 ≤1.2x，4x 余量充足。

用法：python patch_awb_gain.py [--dry-run]
"""
import argparse
import os
import re
import shutil
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

AWB_V = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\awb\awb.v"
BACKUP = r"E:\FPGA\_backup"

# ---------------------------------------------------------------- 新增声明
DECL_ANCHOR = """    reg  [19:0]   in_r_r4;
    reg  [19:0]   in_b_r4;
"""

DECL_NEW = DECL_ANCHOR + """
// ================= [HDR-2026-10-11f] 白平衡增益：帧锁存 + 阻尼 + 钳位 =================
// 见 _analysis/scripts/patch_awb_gain.py 与 sim/awb/tb_awb_zones.v
//   WB_GAIN_MIN/MAX  Q16 定点：20'h10000 = 1.000x
//   WB_DAMP_SHIFT    每帧只更新一次，时间常数 ~= 2^WB_DAMP_SHIFT 帧
    localparam [19:0] WB_GAIN_MIN   = 20'h08000;   // 0.500x
    localparam [19:0] WB_GAIN_MAX   = 20'h40000;   // 4.000x
    localparam [4:0]  WB_DAMP_SHIFT = 5'd2;        // ~4 帧时间常数

    reg  [19:0]   in_r_tgt1, in_b_tgt1;            // 自由运行的目标增益（每拍跟踪商）
    reg  [19:0]   in_r_tgt2, in_b_tgt2;
    reg  [19:0]   in_r_tgt3, in_b_tgt3;
    reg  [19:0]   in_r_tgt4, in_b_tgt4;

    // I_tuser 上升沿检测：上游若把 tuser 给成电平（多拍），增益也必须只更新一次
    reg  S_tuser_d;
    wire S_tuser_rise;
    always @(posedge I_clk or negedge I_rst_n)
        if (!I_rst_n) S_tuser_d <= 1'b0;
        else          S_tuser_d <= I_tuser;
    assign S_tuser_rise = I_tuser & ~S_tuser_d;

    // 商 -> 钳位后的 Q16 增益
    function [19:0] wb_clamp_gain;
        input [47:0] q;
        begin
            if (|q[47:20])                  wb_clamp_gain = WB_GAIN_MAX;  // 溢出 => 上限
            else if (q[19:0] < WB_GAIN_MIN) wb_clamp_gain = WB_GAIN_MIN;  // 下限兜底
            else                            wb_clamp_gain = q[19:0];
        end
    endfunction

    // 阻尼：每帧向目标走 1/2^WB_DAMP_SHIFT，保证至少 1 LSB 以便收敛
    function [19:0] wb_damp_gain;
        input [19:0] cur;
        input [19:0] tgt;
        reg   [19:0] d;
        begin
            d = (tgt > cur) ? (tgt - cur) : (cur - tgt);
            d = d >> WB_DAMP_SHIFT;
            if (d == 20'd0) d = 20'd1;
            wb_damp_gain = (tgt > cur) ? (cur + d) : (cur - d);
        end
    endfunction
// ===================================================================================
"""


def block_new(n):
    """n = 1..4, dn = n-1 (done 索引)"""
    d = n - 1
    return """    // [HDR-2026-10-11f] 通道%d：目标增益每拍跟踪（只钳位），实际增益只在帧边界按阻尼更新
    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_tgt%d <= 20'h10000;
            in_b_tgt%d <= 20'h10000;
        end
        else if(done[%d])begin
            in_r_tgt%d <= wb_clamp_gain(in_r_x%d);
            in_b_tgt%d <= wb_clamp_gain(in_b_x%d);
        end
    end

    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_r%d <= 20'h10000;   // R 增益 = 1.0（Q16：65536 = 20'h10000）
            in_b_r%d <= 20'h10000;   // B 增益 = 1.0
        end
        else if(S_tuser_rise)begin   // 只在帧边界（tuser 上升沿）更新 => 帧内严格恒定
            in_r_r%d <= wb_damp_gain(in_r_r%d, in_r_tgt%d);
            in_b_r%d <= wb_damp_gain(in_b_r%d, in_b_tgt%d);
        end
    end
""" % (n, n, n, d, n, n, n, n, n, n, n, n, n, n, n, n)


def block_pattern(n):
    return re.compile(
        r"always @\(posedge I_clk or negedge I_rst_n\)begin\s*"
        r"if\(!I_rst_n\s*\|\|\s*I_tuser\)begin\s*"
        r"in_r_r%d <= 20'h10000;.*?"
        r"in_b_r%d <= in_b_x%d\[19:0\];\s*end\s*end" % (n, n, n),
        re.S)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    txt = open(AWB_V, "r", encoding="utf-8").read()
    print("target : %s  (%d B)" % (AWB_V, os.path.getsize(AWB_V)))

    if "WB_DAMP_SHIFT" in txt:
        raise SystemExit("FATAL: awb.v already patched (WB_DAMP_SHIFT present). Revert first.")

    for n in (1, 2, 3, 4):
        hits = block_pattern(n).findall(txt)
        m = len(block_pattern(n).findall(txt))
        print("  channel %d: %d match(es) of the stock gain block" % (n, m))
        if m != 1:
            raise SystemExit("FATAL: channel %d matched %d times, expected exactly 1" % (n, m))

    if txt.count(DECL_ANCHOR) != 1:
        raise SystemExit("FATAL: declaration anchor matched %d times" % txt.count(DECL_ANCHOR))
    print("  declaration anchor: 1 match")

    if a.dry_run:
        print("\n--dry-run: nothing written.")
        return

    stamp = time.strftime("%Y%m%d_%H%M%S")
    bdir = os.path.join(BACKUP, "20261011h_awb_gain")
    os.makedirs(bdir, exist_ok=True)
    shutil.copy2(AWB_V, os.path.join(bdir, "awb.v.before"))
    print("\nbackup -> %s\\awb.v.before" % bdir)

    txt = txt.replace(DECL_ANCHOR, DECL_NEW, 1)
    for n in (1, 2, 3, 4):
        txt, cnt = block_pattern(n).subn(block_new(n), txt, count=1)
        assert cnt == 1, "channel %d substitution failed" % n

    with open(AWB_V, "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    head = open(AWB_V, "rb").read(3)
    assert head != b"\xef\xbb\xbf", "BOM written"
    print("wrote  -> %s  (%d B)" % (AWB_V, os.path.getsize(AWB_V)))
    print("         no BOM; WB_DAMP_SHIFT x%d, wb_clamp_gain x%d, wb_damp_gain x%d" % (
        txt.count("WB_DAMP_SHIFT"), txt.count("wb_clamp_gain"), txt.count("wb_damp_gain")))
    left = sum(len(block_pattern(n).findall(txt)) for n in (1, 2, 3, 4))
    print("         stock blocks remaining: %d  (must be 0)" % left)


if __name__ == "__main__":
    main()
