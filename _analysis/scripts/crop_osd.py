import cv2, numpy as np
p = r"E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 21-46-50.png"
im = cv2.imread(p)
# OSD 绿色 MODE 行：原图 1.5x 上采样自 1280x720，OSD 在 (176,176)-(259,185) -> x1.5 = (264,264)-(389,278)
crop = im[258:290, 255:400]
big = cv2.resize(crop, (crop.shape[1]*8, crop.shape[0]*8), interpolation=cv2.INTER_NEAREST)
cv2.imwrite(r"E:\FPGA\_analysis\out\osd_mode_zoom.png", big)
print("crop", crop.shape, "->", big.shape)
# 同时给出该区域每列的 G 通道剖面（便于数字识别）
g = crop[:,:,1]
prof = g.mean(axis=0).astype(int)
print("G col profile:", " ".join("%3d" % v for v in prof))
