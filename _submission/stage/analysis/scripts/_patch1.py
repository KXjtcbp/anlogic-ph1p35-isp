p = r"E:\FPGA\_analysis\scripts\annotate.py"
t = open(p, encoding="utf-8").read()
a = "        text, enc, _ = decode(raw)"
b = "        text, enc, bom = decode(raw)"
assert a in t
t = t.replace(a, b)
a2 = "        newraw = new.encode(enc)"
b2 = '        newraw = (b"\\xef\\xbb\\xbf" if bom else b"") + new.encode(enc)'
assert a2 in t
t = t.replace(a2, b2)
open(p, "w", encoding="utf-8", newline="").write(t)
print("patched")
