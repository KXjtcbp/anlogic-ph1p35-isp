# -*- coding: utf-8 -*-
"""eol_scan.py —— 找出每个文件里换行符与文件主风格不一致的行（编辑前检查锚点用）"""
import os

SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
TARGETS = [
    "video_in.v", "video_out.v", "vtc/uivtc.v", "hdmi_tx.v",
    "hdmi_phy_wrapper.v", "pll_hdmi.v", "lane_lvds_10_1.v",
    "mipi_rx_error_detect.v", "key_remove_shakes.v", "video_cuttting.v",
    "ps_wrapper.v", "mc_to_user_interface.v", "I2S_receiver.v",
    "audio_arc_calculate.v",
]

for rel in TARGETS:
    p = os.path.join(SRC, rel)
    raw = open(p, "rb").read()
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("gbk")
    lines = text.split("\n")
    crlf = sum(1 for i, ln in enumerate(lines[:-1]) if ln.endswith("\r"))
    lf = sum(1 for i, ln in enumerate(lines[:-1]) if not ln.endswith("\r"))
    dom = "CRLF" if crlf >= lf else "LF"
    odd = [i + 1 for i, ln in enumerate(lines[:-1])
           if (dom == "CRLF" and not ln.endswith("\r")) or (dom == "LF" and ln.endswith("\r"))]
    print("%-28s dom=%-4s crlf=%-4d lf=%-4d odd_lines=%s" % (rel, dom, crlf, lf, odd if len(odd) < 40 else str(len(odd)) + " lines"))
