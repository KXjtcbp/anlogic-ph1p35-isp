# -*- coding: utf-8 -*-
"""measure.py —— 以备份（原文件）为准，测量编码 / BOM / 换行风格 / 行数"""
import os

BAK = r"E:\FPGA\_backup\20261009_comments\video"
ORIG = r"E:\FPGA\_analysis\orig_copy\hdl_source"
SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"

TARGETS = [
    "video_in.v", "video_out.v", "vtc/uivtc.v", "hdmi_tx.v",
    "hdmi_phy_wrapper.v", "pll_hdmi.v", "lane_lvds_10_1.v",
    "mipi_rx_error_detect.v", "key_remove_shakes.v", "video_cuttting.v",
    "ps_wrapper.v", "mc_to_user_interface.v", "I2S_receiver.v",
    "audio_arc_calculate.v",
]


def probe(path):
    if not os.path.exists(path):
        return None
    b = open(path, "rb").read()
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n") - crlf
    bom = b[:3] == b"\xef\xbb\xbf"
    try:
        b.decode("utf-8")
        enc = "utf-8"
    except UnicodeDecodeError:
        enc = "gbk"
    return dict(size=len(b), crlf=crlf, lf=lf, bom=bom, enc=enc,
                lines=b.count(b"\n") + (0 if b.endswith(b"\n") else 1))


def main():
    print("%-30s %-46s %s" % ("文件", "原始（备份/基线）", "当前"))
    for rel in TARGETS:
        flat = rel.replace("/", "__").replace("\\", "__")
        o = probe(os.path.join(ORIG, rel)) or probe(os.path.join(BAK, flat + ".bak"))
        c = probe(os.path.join(SRC, rel))
        def fmt(d):
            if d is None:
                return "-- 无原始副本 --"
            return "enc=%-6s bom=%-5s crlf=%-4d lf=%-3d bytes=%d" % (d["enc"], d["bom"], d["crlf"], d["lf"], d["size"])
        mark = ""
        if o and c:
            same = (o["enc"] == c["enc"] and o["bom"] == c["bom"]
                    and (o["crlf"] > 0) == (c["crlf"] > 0) and (o["lf"] > 0) == (c["lf"] > 0))
            mark = "" if same else "   <<< 风格不一致"
        print("%-30s %-46s %s%s" % (rel, fmt(o), fmt(c), mark))


if __name__ == "__main__":
    main()
