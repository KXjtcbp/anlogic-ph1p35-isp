import cv2, numpy as np
NEW = r"E:\FPGA\captures\2026-10-10_测试图诊断\Screenshot 2026-10-10 21-46-50.png"
REF = r"E:\FPGA\captures\2026-10-10_基线\00.png"

im = cv2.imread(NEW)
g = im[:,:,1]
print("=== MODE 数字字形（G>40 为亮，原生坐标 x376..398, y260..282）===")
for y in range(260, 283):
    row = "".join("#" if g[y, x] > 40 else "." for x in range(376, 399))
    print("y=%3d %s" % (y, row))
print()
print("=== 第 4/5/6 格字形（x330..400）===")
for y in range(262, 281):
    row = "".join("#" if g[y, x] > 40 else "." for x in range(330, 400))
    print("y=%3d %s" % (y, row))

print()
print("=== 判据：RGB 是否为 Y 的确定函数（MODE2/3 会成立）===")
for p in (REF, NEW):
    a = cv2.imread(p)
    b, gg, r = [a[..., i].astype(np.int32) for i in range(3)]
    Y = (77*r + 150*gg + 29*b) >> 8
    flat = (r.astype(np.uint32) << 16) | (gg.astype(np.uint32) << 8) | b.astype(np.uint32)
    yv = Y.ravel(); fv = flat.ravel()
    order = np.argsort(yv, kind="stable")
    ys, fs = yv[order], fv[order]
    bounds = np.searchsorted(ys, np.arange(257))
    multi, mx = 0, 0
    for i in range(256):
        seg = fs[bounds[i]:bounds[i+1]]
        if seg.size:
            n = np.unique(seg).size
            mx = max(mx, n)
            if n > 1: multi += 1
    print("  %-40s 出现过的 Y 值 %d 个，其中 %d 个 Y 对应 >1 种 RGB，单 Y 最多 %d 种 RGB"
          % (p.split("\\")[-1], int((bounds[1:]>bounds[:-1]).sum()), multi, mx))
