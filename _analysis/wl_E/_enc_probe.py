import os, sys

ROOT = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
files = [
    r"osd_char_lib.v",
    r"isp\data96_128\data96_128.v",
    r"isp\data128_96\data128_96.v",
    r"data_96bit_to_128bit.v",
    r"raw10_unpacket.v",
    r"csi_unpacket.v",
    r"raw8_to_rgb888.v",
    r"auto_white_balance.v",
    r"image_correction.v",
    r"awb.v",
    r"signal_delay.v",
    r"uics500_cfg\uii2c.v",
    r"uics500_cfg\uics500reg.v",
    r"uics500_cfg\uicfgcs500.v",
]

for rel in files:
    p = os.path.join(ROOT, rel)
    b = open(p, "rb").read()
    kinds = []
    try:
        b.decode("utf-8")
        kinds.append("utf-8")
    except Exception as e:
        kinds.append("NOT-utf8")
    for enc in ("gbk", "gb18030", "cp936", "latin-1"):
        try:
            b.decode(enc)
            kinds.append(enc + ":ok")
        except Exception:
            kinds.append(enc + ":FAIL")
    crlf = b.count(b"\r\n")
    lf = b.count(b"\n")
    bom = b[:3] == b"\xef\xbb\xbf"
    has_tab = b.count(b"\t")
    nonascii = sum(1 for c in b if c > 127)
    print(f"{rel}\n   size={len(b)} crlf={crlf} lf={lf} bom={bom} tab={has_tab} nonascii_bytes={nonascii}\n   {kinds}")
