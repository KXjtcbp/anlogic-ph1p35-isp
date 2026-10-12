import os, io

ROOT = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
OUT = r"E:\FPGA\_analysis\wl_E\utf8_copy"
os.makedirs(OUT, exist_ok=True)

files = [
    r"image_correction.v",
    r"uics500_cfg\uii2c.v",
    r"uics500_cfg\uicfgcs500.v",
]

def decode(b):
    for enc in ("utf-8-sig", "utf-8", "gb18030", "gbk"):
        try:
            return b.decode(enc), enc
        except Exception:
            pass
    return b.decode("latin-1"), "latin-1"

for rel in files:
    p = os.path.join(ROOT, rel)
    b = open(p, "rb").read()
    txt, enc = decode(b)
    op = os.path.join(OUT, rel.replace("\\", "__") + ".txt")
    with open(op, "w", encoding="utf-8", newline="") as f:
        f.write(txt)
    print(rel, "->", enc, "->", op, "chars", len(txt))
