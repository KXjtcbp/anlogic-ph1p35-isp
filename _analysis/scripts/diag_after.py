import sys, numpy as np
from PIL import Image
import cv2

def stat(path):
    im = Image.open(path)
    a = np.asarray(im.convert('RGB')).astype(np.int32)
    print("="*78)
    print(f"{path}  mode={im.mode} size={im.size}")
    # 排除 OSD：OSD 在左上角区域。右侧 2/3 大致是纯相机画面
    cam = a[:, int(a.shape[1]*0.45):, :]
    g = cam[:, :, 1]
    print(f"相机区 bbox: rows0..{a.shape[0]} cols{int(a.shape[1]*0.45)}..{a.shape[1]}")
    print("  通道均值  R={:.2f} G={:.2f} B={:.2f}   R-G={:+.2f} B-G={:+.2f}".format(
        cam[:,:,0].mean(), g.mean(), cam[:,:,2].mean(),
        cam[:,:,0].mean()-g.mean(), cam[:,:,2].mean()-g.mean()))
    print("  通道 std   R={:.2f} G={:.2f} B={:.2f}".format(
        cam[:,:,0].std(), g.std(), cam[:,:,2].std()))
    for i,n in enumerate("RGB"):
        c = cam[:,:,i]
        print(f"  {n}: min={c.min()} p1={np.percentile(c,1):.0f} p50={np.percentile(c,50):.0f} "
              f"p99={np.percentile(c,99):.0f} max={c.max()} ==255:{(c==255).mean()*100:.2f}% ==0:{(c==0).mean()*100:.2f}%")
    gray = (cam[:,:,0]==cam[:,:,1]) & (cam[:,:,1]==cam[:,:,2])
    print(f"  ★严格 R==G==B 像素占比 = {gray.mean()*100:.2f}%")
    mx = cam.max(axis=2); mn = cam.min(axis=2)
    sat = mx-mn
    print(f"  ★彩度 (max-min): mean={sat.mean():.2f} p50={np.percentile(sat,50):.0f} p99={np.percentile(sat,99):.0f} max={sat.max()}")
    luma = (0.299*cam[:,:,0]+0.587*cam[:,:,1]+0.114*cam[:,:,2])
    print(f"  亮度 luma: mean={luma.mean():.2f} p50={np.percentile(luma,50):.0f} p95={np.percentile(luma,95):.0f} p99={np.percentile(luma,99):.0f}")
    # 低位活动：若只有偶数值 => 低位被截断
    for i,n in enumerate("RGB"):
        c = cam[:,:,i].ravel()
        odd = (c & 1).mean()*100
        # bit0/bit1 是否有信息
        print(f"  {n}: 奇数值占比={odd:.2f}%  唯一码值数={len(np.unique(c))}")
    # 噪声：高频能量
    lap = cv2.Laplacian(cv2.cvtColor(cam.astype(np.uint8), cv2.COLOR_RGB2GRAY), cv2.CV_64F)
    print(f"  Laplacian 绝对均值(噪声/细节)= {np.abs(lap).mean():.3f}")
    # 分块亮度，看是否有结构
    h,w = luma.shape
    bh,bw = h//6, w//6
    print("  亮度分块均值 (6x6, 单位码值):")
    for r in range(6):
        row = "   "
        for c in range(6):
            row += f"{luma[r*bh:(r+1)*bh, c*bw:(c+1)*bw].mean():6.1f}"
        print(row)
    return a, cam

for p in sys.argv[1:]:
    stat(p)
