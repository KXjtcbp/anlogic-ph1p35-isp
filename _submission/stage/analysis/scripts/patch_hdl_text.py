# -*- coding: utf-8 -*-
"""
patch_hdl_text.py —— 给 UTF-8 编码的 .v 打补丁（本次：isp_top.v / design_top_wrapper.v）

为什么不用编辑器直接改：
  这两个文件是 CRLF 行尾（isp_top.v 还是 CRLF/LF 混排），直接做多行替换时
  很容易因为行尾字符对不上而匹配失败或把整个文件的行尾改掉。
  这里用「正则按 \r?\n 匹配 + 按实际命中的行尾生成替换文本」的方式，
  保证文件里除被替换的那几行之外，其余字节一个都不动。

每个替换都要求「命中且只命中 1 次」，否则整脚本不写盘。
写盘前先存 .bak_20261010 备份。
"""
import os
import re
import sys

ISP = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_top.v"
TOP = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source\design_top_wrapper.v"

# ============================================================ isp_top.v
P_ISP = [
    # ---- 1. 顶层端口增加两个旁路输入 ----
    (
        "    input [2:0]     I_algo_mode\n"
        ");\n",
        "    input [2:0]     I_algo_mode     ,\n"
        "    // [HDR-2026-10-10] 板上乒乓开关 SW1/SW2（顶层已同步到本时钟域）\n"
        "    //   I_blk_bypass  : SW1，1 = 黑电平扣除【直通】（= 2026-10-09 之前的老行为），0 = 启用扣除\n"
        "    //   I_gamma_bypass: SW2，1 = S 曲线【直通】，0 = 启用 S 曲线\n"
        "    //   复位期间顶层把这两根都拉成 1 ⇒ 上电老行为，绝不会「一上电就变样」。\n"
        "    input           I_blk_bypass    ,\n"
        "    input           I_gamma_bypass\n"
        ");\n",
    ),
    # ---- 2. 新增 isp_gamma 的中间信号 ----
    (
        "  wire         algo_O_tvalid;  //synthesis keep \n",
        "  wire         algo_O_tvalid;  //synthesis keep \n"
        "\n"
        "  //--------------------------------------------------------------------------\n"
        "  // [HDR-2026-10-10] S 曲线查表级（isp_gamma）的中间信号\n"
        "  //   位置：awb 之后、my_algo 之前；固定 2 拍延迟（ROM 同步读 1 拍 + 输出 1 拍）\n"
        "  //--------------------------------------------------------------------------\n"
        "  wire         gam_I_tready;   //synthesis keep \n"
        "  wire         gam_O_tlast;    //synthesis keep \n"
        "  wire         gam_O_tuser;    //synthesis keep \n"
        "  wire [ 95:0] gam_O_tdata;    //synthesis keep \n"
        "  wire         gam_O_tvalid;   //synthesis keep \n"
        "  wire         algo_I_tready;  //synthesis keep \n",
    ),
    # ---- 3. awb 的 O_tready 改由 gamma 给出（原来是直接接 O_tready）----
    (
        "  assign awb_O_tready = O_tready;\n",
        "  // [HDR-2026-10-10] 原来这里直接把 awb 的 O_tready 接到顶层 O_tready。\n"
        "  //   插入 isp_gamma 之后 awb 的下游变成 gamma，回压信号改由 gamma 给出；\n"
        "  //   gamma 内部就是 `assign I_tready = O_tready;`（与 awb.v:513、my_algo.v:96\n"
        "  //   同一条写法），所以 awb_O_tready 的波形与改动前逐拍相同，全链路仍无真反压。\n"
        "  assign awb_O_tready = gam_I_tready;\n",
    ),
    # ---- 4. O_tlast 改取 gamma 输出（= awb_O_tlast 延 2 拍，语义与原来逐拍等价）----
    (
        "  assign O_tlast  = awb_O_tlast     ;\n",
        "  // [HDR-2026-10-10] ★这一行的取值从 awb 那级改成 gamma 那级★\n"
        "  //   原厂写法的语义是「O_tlast = my_algo 输入那一拍的 tlast」；\n"
        "  //   插入 isp_gamma（2 拍）后，my_algo 的输入 beat 就是 gamma 的输出 beat，\n"
        "  //   所以必须改成 gam_O_tlast ⇒ 与加 gamma 之前逐拍等价（= awb_O_tlast 延 2 拍）。\n"
        "  //   若仍取 awb_O_tlast，O_tlast 会比数据早 2 拍 ⇒ 行尾标记错位。\n"
        "  assign O_tlast  = gam_O_tlast     ;\n",
    ),
    # ---- 5. demosaic 例化加 I_blk_bypass ----
    (
        "    .I_rst_n \t\t\t(I_rst_n)\t,   // 复位信号，低有效\n",
        "    .I_rst_n \t\t\t(I_rst_n)\t,   // 复位信号，低有效\n"
        "    .I_blk_bypass \t\t(I_blk_bypass)\t,  // [HDR-2026-10-10] 黑电平扣除旁路（1=直通）\n",
    ),
    # ---- 6. 在 awb 与 my_algo 之间插入 isp_gamma 例化 ----
    (
        "    .O_tvalid(awb_O_tvalid),\n"
        "    .O_tready(awb_O_tready)\n"
        ");\n",
        "    .O_tvalid(awb_O_tvalid),\n"
        "    .O_tready(awb_O_tready)\n"
        ");\n"
        "\n"
        "    //==========================================================================\n"
        "    // [HDR-2026-10-10] S 曲线（色调曲线）查表级 —— 插在 awb 与 my_algo 之间\n"
        "    //   12 个 8bit 分量共用同一张 256×8 表（R/G/B 同表 ⇒ 不动白平衡）；\n"
        "    //   表内容 = gamma_lut_p118_k125.hex（P=118, A=B=1.25 中等档 S 曲线）。\n"
        "    //   固定 2 拍延迟，无空拍；bypass 也是 2 拍（不会错帧）。\n"
        "    //   ★该级绝不能停拍（全链路无真反压，见 isp_gamma.v 头部说明）。\n"
        "    //==========================================================================\n"
        "    isp_gamma u_isp_gamma (\n"
        "        .I_clk          ( axi4s_video_aclk ),\n"
        "        .I_rst_n        ( I_rst_n          ),\n"
        "        .I_tlast        ( awb_O_tlast      ),\n"
        "        .I_tuser        ( awb_O_tuser      ),\n"
        "        .I_tdata        ( awb_O_tdata      ),\n"
        "        .I_tvalid       ( awb_O_tvalid     ),\n"
        "        .I_tready       ( gam_I_tready     ),\n"
        "        .I_gamma_bypass ( I_gamma_bypass   ),\n"
        "        .O_tdata        ( gam_O_tdata      ),\n"
        "        .O_tlast        ( gam_O_tlast      ),\n"
        "        .O_tuser        ( gam_O_tuser      ),\n"
        "        .O_tvalid       ( gam_O_tvalid     ),\n"
        "        .O_tready       ( algo_I_tready    )\n"
        "    );\n",
    ),
    # ---- 7. my_algo 的 5 个连接改接 gamma 输出 ----
    (
        "        .I_tlast    ( awb_O_tlast      ),\n"
        "        .I_tuser    ( awb_O_tuser      ),\n"
        "        .I_tdata    ( awb_O_tdata      ),\n"
        "        .I_tvalid   ( awb_O_tvalid     ),\n"
        "        .I_tready   ( awb_O_tready     ),\n",
        "        // [HDR-2026-10-10] 输入源由 awb 改为 isp_gamma 的输出（多 2 拍延迟）\n"
        "        .I_tlast    ( gam_O_tlast      ),\n"
        "        .I_tuser    ( gam_O_tuser      ),\n"
        "        .I_tdata    ( gam_O_tdata      ),\n"
        "        .I_tvalid   ( gam_O_tvalid     ),\n"
        "        .I_tready   ( algo_I_tready    ),\n",
    ),
]

# ============================================================ design_top_wrapper.v
P_TOP = [
    # ---- 1. 顶层端口增加 4 位乒乓开关 ----
    (
        "    inout wire [3:0]  I_button,\n",
        "    inout wire [3:0]  I_button,\n"
        "\n"
        "    // [HDR-2026-10-10] 板上乒乓开关 SW1-SW4\n"
        "    //   手册《新HX1P35A开发板手册-HDL版2604》P396-404：\n"
        "    //     「SW1-SW4 是作为与 FPGA 的 IO 输入信号，拨上为\"1\"，拨下为\"0\"」\n"
        "    //     引脚 SW1=A4 / SW2=B4 / SW3=E11 / SW4=D11\n"
        "    //   SW1(A4) = 黑电平扣除旁路：1 = 直通（老行为），0 = 启用扣除\n"
        "    //   SW2(B4) = S 曲线旁路    ：1 = 直通（老行为），0 = 启用 S 曲线\n"
        "    //   SW3/SW4 暂未使用，先接进顶层备后续扩展（pin.adc 已声明，内部上拉）\n"
        "    input wire [3:0]  I_switch,\n",
    ),
    # ---- 2. 插入同步器 + 旁路信号，位置紧贴 isp_top 例化之前 ----
    (
        "//ISP算法顶层模块\n",
        "//=============================================================================\n"
        "// [HDR-2026-10-10] 乒乓开关 SW1/SW2 → ISP 旁路控制（跨时钟域同步）\n"
        "//   拨上=1=【旁路】= 加黑电平扣除 / S 曲线之前的老行为；拨下=0=启用新功能。\n"
        "//   pin.adc 里对这 4 根都声明了 PULLUP ⇒ 开关未焊/悬空时读到 1 ⇒ 自动老行为。\n"
        "//   机械开关抖动极慢（毫秒级），这里只做 2 级同步消除亚稳态，不做去抖。\n"
        "//   复位期间输出 1（旁路）⇒ 上电瞬间画面就是老行为，不会闪。\n"
        "//=============================================================================\n"
        "reg S_sw1_sync0, S_sw1_sync1;\n"
        "reg S_sw2_sync0, S_sw2_sync1;\n"
        "always @(posedge S_csi_rx_clk or negedge S_rst_n) begin\n"
        "    if(!S_rst_n) begin\n"
        "        S_sw1_sync0 <= 1'b1;\n"
        "        S_sw1_sync1 <= 1'b1;\n"
        "        S_sw2_sync0 <= 1'b1;\n"
        "        S_sw2_sync1 <= 1'b1;\n"
        "    end\n"
        "    else begin\n"
        "        S_sw1_sync0 <= I_switch[0];\n"
        "        S_sw1_sync1 <= S_sw1_sync0;\n"
        "        S_sw2_sync0 <= I_switch[1];\n"
        "        S_sw2_sync1 <= S_sw2_sync0;\n"
        "    end\n"
        "end\n"
        "\n"
        "wire S_blk_bypass   = S_sw1_sync1;   // 1 = 黑电平扣除直通\n"
        "wire S_gamma_bypass = S_sw2_sync1;   // 1 = S 曲线直通\n"
        "\n"
        "//ISP算法顶层模块\n",
    ),
    # ---- 3. isp_top 例化加两根旁路 ----
    (
        "// [OUR ALGO] 算法模式来自 24 MHz 按键域，my_algo 内部有 2 级同步器\n"
        ".I_algo_mode     (S_algo_mode)\n"
        "  );\n",
        "// [OUR ALGO] 算法模式来自 24 MHz 按键域，my_algo 内部有 2 级同步器\n"
        ".I_algo_mode     (S_algo_mode),\n"
        "// [HDR-2026-10-10] SW1/SW2 旁路控制（已在 S_csi_rx_clk 域做过 2 级同步）\n"
        ".I_blk_bypass    (S_blk_bypass  ),\n"
        ".I_gamma_bypass  (S_gamma_bypass)\n"
        "  );\n",
    ),
]


def patch(path, pairs, dry=False):
    raw = open(path, "rb").read()
    try:
        txt = raw.decode("utf-8-sig")
        enc = "utf-8-sig"
    except UnicodeDecodeError:
        txt = raw.decode("gbk")
        enc = "gbk"
    print("--- %s  (编码 %s, %d 字节)" % (os.path.basename(path), enc, len(raw)))
    ok = True
    new = txt
    for old, rep in pairs:
        rx = "\r?\n".join(re.escape(p) for p in old.split("\n"))
        ms = list(re.finditer(rx, new))
        head = old.strip().splitlines()[0][:60]
        if len(ms) != 1:
            print("    ★★ 命中 %d 次 : %s" % (len(ms), head))
            ok = False
            continue
        m = ms[0]
        nl = "\r\n" if "\r\n" in m.group(0) else "\n"
        r2 = rep.replace("\n", nl)
        new = new[: m.start()] + r2 + new[m.end():]
        print("    OK  命中 1 次 (%s) : %s" % ("CRLF" if nl == "\r\n" else "LF", head))
    if not ok:
        print("    ⇒ 有替换未唯一命中，本文件未写盘")
        return False
    if dry:
        print("    ⇒ dry-run 通过（未写盘）")
        return True
    with open(path + ".bak_20261010", "wb") as f:
        f.write(raw)
    with open(path, "wb") as f:
        f.write(new.encode("utf-8-sig" if enc == "utf-8-sig" else "gbk"))
    print("    ⇒ 已写盘（备份 .bak_20261010）")
    return True


if __name__ == "__main__":
    dry = "--dry" in sys.argv
    a = patch(ISP, P_ISP, dry)
    b = patch(TOP, P_TOP, dry)
    print("\n结果: isp_top=%s design_top_wrapper=%s" % (a, b))
