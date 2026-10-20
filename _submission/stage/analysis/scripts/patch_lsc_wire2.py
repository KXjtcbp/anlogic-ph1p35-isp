# -*- coding: utf-8 -*-
"""patch_lsc_wire.py 的收尾：isp_top.v 的三处接线 + .al 加 lsc.v
   ★教训：这两个文件都是 CRLF；精确匹配前必须先把 \\r\\n 归一成 \\n。
   ★.al 里 P&R 是字面量 '&'，不是 '&amp;'。"""
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")
ISP = os.path.join(HDL, "isp", "isp_top.v")
AL  = os.path.join(WS, "proj", "baseline", "lab3", "td_project", "camera_to_dsi_display.al")
FL  = os.path.join(WS, "_analysis", "reports", "hdl_filelist.txt")


def rd_lf(p):
    return open(p, "rb").read().decode("utf-8").replace("\r\n", "\n")


def wr_crlf(p, t):
    open(p, "wb").write(t.replace("\r\n", "\n").replace("\n", "\r\n").encode("utf-8"))


def sub1(t, old, new, tag):
    n = t.count(old)
    if n != 1:
        print("  !! %s : 匹配 %d 处（期望 1）" % (tag, n))
        return t
    print("  ok %s" % tag)
    return t.replace(old, new, 1)


# ---------------- isp_top.v ----------------
t = rd_lf(ISP)
if "u_lsc" in t:
    print("isp_top.v: 已有 u_lsc，跳过")
else:
    t = sub1(t, """data128_96 u_data128_96 (
    .I_tdata(m_axis_tdata),
    .O_tdata(m_axis_tdata_96)
);
""", """data128_96 u_data128_96 (
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
    .K_MAX     (4'd7       )
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
""", "lsc 例化")
    t = sub1(t, "    .I_tvalid    (m_axis_tvalid   ),\n    .I_tuser     (m_axis_tuser    ),\n    .I_tdata     (m_axis_tdata_96 ),",
             "    .I_tvalid    (lsc_tvalid      ),\n    .I_tuser     (lsc_tuser       ),\n    .I_tdata     (lsc_tdata_96    ),",
             "ae_stat 输入")
    t = sub1(t, "    .I_tlast (m_axis_tlast),\n    .I_tuser (m_axis_tuser),\n    .I_tdata (m_axis_tdata_96),\n    .I_tvalid(m_axis_tvalid),",
             "    .I_tlast (lsc_tlast    ),\n    .I_tuser (lsc_tuser    ),\n    .I_tdata (lsc_tdata_96 ),\n    .I_tvalid(lsc_tvalid   ),",
             "awb 输入")
    wr_crlf(ISP, t)
    print("isp_top.v -> %d B" % os.path.getsize(ISP))

# ---------------- .al ----------------
a = rd_lf(AL)
if "isp/lsc.v" in a:
    print(".al: 已有 lsc.v，跳过")
else:
    m = re.search(r'[ \t]*<File Path="\.\./user_source/hdl_source/isp/ae_ctrl\.v">.*?</File>\n', a, flags=re.S)
    if not m:
        print("!! .al 里找不到 ae_ctrl.v 条目")
        sys.exit(1)
    blk = ('            <File Path="../user_source/hdl_source/isp/lsc.v">\n'
           '                <FileInfo>\n'
           '                    <Attr Name="UsedInSyn" Val="true"/>\n'
           '                    <Attr Name="UsedInP&R" Val="true"/>\n'
           '                    <Attr Name="BelongTo" Val="design_1"/>\n'
           '                    <Attr Name="CompileOrder" Val="57"/>\n'
           '                </FileInfo>\n'
           '            </File>\n')
    a = a[:m.end()] + blk + a[m.end():]
    wr_crlf(AL, a)
    print(".al -> %d B" % os.path.getsize(AL))

# ---------------- hdl_filelist.txt ----------------
if os.path.exists(FL):
    t = open(FL, "rb").read().decode("utf-8")
    p = os.path.join(HDL, "isp", "lsc.v")
    if p not in t:
        if not t.endswith("\n"):
            t += "\n"
        open(FL, "wb").write((t + p + "\n").encode("utf-8"))
        print("hdl_filelist.txt -> %d B" % os.path.getsize(FL))
    else:
        print("hdl_filelist.txt: 已有，跳过")
print("done")
