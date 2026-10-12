# -*- coding: utf-8 -*-
"""
verify_comments.py —— 注释改动的安全校验（只读，不改文件）

对每个已在备份目录中存在 .bak 的目标文件做两件事：
1. 逐行剥离 // 注释、空行后比较代码序列，必须与备份完全一致（顺序、字符）
2. 报告编码、BOM、换行风格与原文件是否保持

用法: python verify_comments.py [相对路径 ...]
不传参数则校验备份目录里已有的所有 .bak 对应的目标文件。
"""
import os, sys

SRC = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
BAK = r"E:\FPGA\_backup\20261009_comments\video"

TARGETS = [
    "video_in.v", "video_out.v", "vtc/uivtc.v", "hdmi_tx.v",
    "hdmi_phy_wrapper.v", "pll_hdmi.v", "lane_lvds_10_1.v",
    "mipi_rx_error_detect.v", "key_remove_shakes.v", "video_cuttting.v",
    "ps_wrapper.v", "mc_to_user_interface.v", "I2S_receiver.v",
    "audio_arc_calculate.v",
]


def decode(raw):
    for enc in ("utf-8-sig", "utf-8", "gbk"):
        try:
            return raw.decode(enc), enc
        except UnicodeDecodeError:
            continue
    return None, None


def code_seq(text):
    """按行剥离 // 注释与空白，丢掉空行，返回代码行序列"""
    out = []
    for ln in text.replace("\r\n", "\n").split("\n"):
        c = ln.split("//")[0].strip()
        if c:
            out.append(c)
    return out


def eol_style(raw):
    """返回 (CRLF 行数, 纯 LF 行数)，行数增加属正常（插入注释行）"""
    t = raw.decode("latin-1")
    crlf = t.count("\r\n")
    lf = t.count("\n") - crlf
    return crlf, lf


def main():
    targets = sys.argv[1:] or TARGETS
    bad = 0
    for rel in targets:
        bakname = rel.replace("/", "__").replace("\\", "__") + ".bak"
        bak = os.path.join(BAK, bakname)
        cur = os.path.join(SRC, rel)
        if not os.path.exists(bak):
            print("%-30s  [跳过：无备份]" % rel)
            continue
        rb = open(bak, "rb").read()
        rc = open(cur, "rb").read()
        tb, eb = decode(rb)
        tc, ec = decode(rc)
        sb, sc = code_seq(tb), code_seq(tc)
        # 代码序列必须完全一致；换行风格只需保持"哪种为主 / 有无混杂"不变
        style_b = ("CRLF" if eol_style(rb)[0] else "LF") + ("+mix" if min(eol_style(rb)) else "")
        style_c = ("CRLF" if eol_style(rc)[0] else "LF") + ("+mix" if min(eol_style(rc)) else "")
        bom_b = rb[:3] == b"\xef\xbb\xbf"
        bom_c = rc[:3] == b"\xef\xbb\xbf"
        note = []
        ok = True
        if sb != sc:
            ok = False
            note.append("代码序列不一致!!")
            for i in range(max(len(sb), len(sc))):
                a = sb[i] if i < len(sb) else "<缺>"
                b = sc[i] if i < len(sc) else "<缺>"
                if a != b:
                    note.append("   第%d行: 原=%r 新=%r" % (i, a, b))
                    break
        if eb != ec:
            ok = False
            note.append("编码变化 %s -> %s" % (eb, ec))
        if style_b != style_c:
            ok = False
            note.append("换行风格变化 %s -> %s" % (style_b, style_c))
        if bom_b != bom_c:
            ok = False
            note.append("BOM 变化 %s -> %s" % (bom_b, bom_c))
        if not ok:
            bad += 1
        print("%-30s %s 代码行 %d/%d 编码 %s 换行 %s 行数 %d->%d %s"
              % (rel, "OK  " if ok else "FAIL", len(sb), len(sc), ec, style_c,
                 rb.count(b"\n"), rc.count(b"\n"), " ".join(note)))
    print("==== 校验结束：%d 个文件有问题 ====" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
