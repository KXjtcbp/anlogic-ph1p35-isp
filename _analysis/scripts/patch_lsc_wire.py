# -*- coding: utf-8 -*-
"""把 lsc 接进 isp_top.v + design_top_wrapper.v + .al + hdl_filelist.txt（幂等）"""
import os, re, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WS = r"E:\FPGA"
HDL = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source")
ISP = os.path.join(HDL, "isp", "isp_top.v")
DTW = os.path.join(HDL, "design_top_wrapper.v")
AL  = os.path.join(WS, "proj", "baseline", "lab3", "td_project", "camera_to_dsi_display.al")
FL  = os.path.join(WS, "_analysis", "reports", "hdl_filelist.txt")


def rd(p):
    return open(p, "rb").read().decode("utf-8")


def wr(p, t):
    open(p, "wb").write(t.encode("utf-8"))


def sub1(t, old, new, tag):
    n = t.count(old)
    if n != 1:
        print("  !! %s : 精确匹配到 %d 处（期望 1）" % (tag, n))
        return t, False
    print("  ok %s" % tag)
    return t.replace(old, new), True


# ---------------- isp_top.v ----------------
t = rd(ISP)
if "u_lsc" in t:
    print("isp_top.v: 已接过 lsc，跳过")
else:
    t, _ = sub1(t, "input           I_gamma_bypass  ,",
                "input           I_gamma_bypass  ,\n  // [HDR-2026-10-14] LSC（镜头色彩暗角校正）运行期旁路，1 = 直通\n  input           I_lsc_bypass    ,",
                "isp port")
    t, _ = sub1(t, """data128_96 u_data128_96 (
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
//     ① 放在 awb 之前 —— AWB 看到的是已经校平的画面，它的"整帧 R/G = 1"判据
//        才有意义；放在 awb 之后会被 AWB 的全局增益重新搅混。
//     ② 放在 ae_stat 之前 —— AE 的帧均值直接取自校正后的画面，亮暗判据不受影响。
//   本模块带 2 拍流水，所以下游的 tvalid/tuser/tlast 必须取它延迟后的版本，
//   否则帧边界会与数据错开 2 拍。
//------------------------------------------------------------------------------
wire [95:0] lsc_tdata_96;
wire        lsc_tvalid, lsc_tuser, lsc_tlast;

lsc #(
    .LSC_ENABLE(1'b1),
    .H_BEATS   (12'd320),
    .V_LINES   (12'd720),
    .K_MAX     (4'd7)
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
""", "isp lsc inst")
    t, _ = sub1(t, "    .I_tvalid    (m_axis_tvalid   ),\n    .I_tuser     (m_axis_tuser    ),\n    .I_tdata     (m_axis_tdata_96 ),",
                "    .I_tvalid    (lsc_tvalid      ),\n    .I_tuser     (lsc_tuser       ),\n    .I_tdata     (lsc_tdata_96    ),",
                "ae_stat in")
    t, _ = sub1(t, "    .I_tlast (m_axis_tlast),\n    .I_tuser (m_axis_tuser),\n    .I_tdata (m_axis_tdata_96),\n    .I_tvalid(m_axis_tvalid),",
                "    .I_tlast (lsc_tlast    ),\n    .I_tuser (lsc_tuser    ),\n    .I_tdata (lsc_tdata_96 ),\n    .I_tvalid(lsc_tvalid   ),",
                "awb in")
    wr(ISP, t)
    print("isp_top.v -> %d B" % os.path.getsize(ISP))

# ---------------- design_top_wrapper.v（CRLF/CR 混杂，按字节处理） ----------------
raw = open(DTW, "rb").read()
t = raw.decode("utf-8", errors="replace")
if "S_lsc_bypass" in t:
    print("design_top_wrapper.v: 已接过 lsc，跳过")
else:
    # 在 AE 一节之前插一条 wire（该文件里找 ae_ctrl 例化前的注释块收尾）
    anchor = "    //----------------------------------------------------------------------\n    // [HDR-2026-10-12] 自动曝光闭环\n"
    if anchor not in t:
        # 退路：找 ae_ctrl 例化行
        m = re.search(r"[ \t]*ae_ctrl #\(", t)
        if not m:
            print("  !! design_top_wrapper.v 里找不到 ae_ctrl 例化，无法定位插入点")
            sys.exit(1)
        anchor = m.group(0)
    ins = ("    // [HDR-2026-10-14] LSC 镜头色彩暗角校正使能（0 = 开启校正，1 = 直通）\n"
           "    //   用 localparam 而不是拨码开关：四个开关已全部占满，且这一步属于「标定」\n"
           "    //   而不是「操作」，现场不需要手动切换；要对比就重综合一版。\n"
           "    //   与 AE_TARGET_MEAN 同一种模式。\n"
           "    localparam       LSC_BYPASS   = 1'b0;\n"
           "    wire             S_lsc_bypass = LSC_BYPASS;\n\n")
    t = t.replace(anchor, ins + anchor, 1)
    print("  ok dtw wire")

    m = re.search(r"\.I_gamma_bypass\s*\(\s*S_gamma_bypass\s*\)", t)
    if not m:
        print("  !! 找不到 .I_gamma_bypass(S_gamma_bypass)")
        sys.exit(1)
    t = t[:m.end()] + ",\n        .I_lsc_bypass (S_lsc_bypass )" + t[m.end():]
    print("  ok dtw port")
    open(DTW, "wb").write(t.encode("utf-8"))
    print("design_top_wrapper.v -> %d B" % os.path.getsize(DTW))

# ---------------- .al ----------------
t = rd(AL)
if "isp/lsc.v" in t:
    print(".al: 已有 lsc.v，跳过")
else:
    m = re.search(r'([ \t]*)<File Path="\.\./user_source/hdl_source/isp/ae_ctrl\.v">.*?</File>\n',
                  t, flags=re.S)
    if not m:
        print("!! .al 里找不到 ae_ctrl.v 条目")
        sys.exit(1)
    blk = ('            <File Path="../user_source/hdl_source/isp/lsc.v">\n'
           '                <FileInfo>\n'
           '                    <Attr Name="UsedInSyn" Val="true"/>\n'
           '                    <Attr Name="UsedInP&amp;R" Val="true"/>\n'
           '                    <Attr Name="BelongTo" Val="design_1"/>\n'
           '                    <Attr Name="CompileOrder" Val="57"/>\n'
           '                </FileInfo>\n'
           '            </File>\n')
    t = t[:m.end()] + blk + t[m.end():]
    wr(AL, t)
    print(".al -> %d B" % os.path.getsize(AL))

# ---------------- hdl_filelist.txt ----------------
if os.path.exists(FL):
    t = rd(FL)
    p = os.path.join(HDL, "isp", "lsc.v")
    if p not in t:
        if not t.endswith("\n"):
            t += "\n"
        t += p + "\n"
        wr(FL, t)
        print("hdl_filelist.txt -> %d B" % os.path.getsize(FL))
    else:
        print("hdl_filelist.txt: 已有，跳过")
print("done")
