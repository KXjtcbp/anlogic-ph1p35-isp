import numpy as np
from PIL import Image
paths = [
 r"E:\FPGA\captures\2026-10-10_基线\00.png",
 r"E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 21-46-50.png",
 r"E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 21-55-21.png",
 r"E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 21-55-46.png",
]
crops=[]
for p in paths:
    im = Image.open(p).convert("RGB")
    c = im.crop((520,150,920,215)).resize((400*3,65*3), Image.LANCZOS)
    crops.append(c)
W = max(c.width for c in crops); H = sum(c.height for c in crops)
out = Image.new("RGB",(W,H),(0,0,0))
y=0
for c in crops:
    out.paste(c,(0,y)); y+=c.height
out.save(r"E:\FPGA\_analysis\out\cnt_zoom.png")
print("saved", out.size)
