import glob, os, numpy as np
from PIL import Image

paths = []
for pat in ("*.jpg","*.jpeg","*.png","*.bmp","*.tif","*.tiff"):
    paths += glob.glob(os.path.join(r"E:\FPGA", pat))
paths += glob.glob(os.path.join(r"E:\FPGA\tools\compare\demo", "*.png"))
paths.sort(key=lambda p: os.path.getmtime(p))

print(f"{'file':46s} {'WxH':>11s} {'mtime':17s} {'luma_mean':>9s} {'luma_p50':>8s} {'luma_p99':>8s} "
      f"{'luma_max':>8s} {'R-G':>6s} {'B-G':>6s} {'sat_mean':>8s} {'gray%':>6s}")
for p in paths:
    try:
        im = Image.open(p)
        a = np.asarray(im.convert('RGB')).astype(np.float32)
    except Exception as e:
        print(f"{os.path.basename(p):46s} ERROR {e}")
        continue
    # crop away OSD: use right 55% and bottom 80%
    cam = a[int(a.shape[0]*0.20):, int(a.shape[1]*0.45):, :]
    luma = 0.299*cam[:,:,0]+0.587*cam[:,:,1]+0.114*cam[:,:,2]
    sat = cam.max(axis=2)-cam.min(axis=2)
    gray = ((cam[:,:,0]==cam[:,:,1]) & (cam[:,:,1]==cam[:,:,2])).mean()*100
    import datetime
    ts = datetime.datetime.fromtimestamp(os.path.getmtime(p)).strftime("%m-%d %H:%M:%S")
    print(f"{os.path.basename(p):46s} {a.shape[1]}x{a.shape[0]:<6d} {ts:17s} "
          f"{luma.mean():9.2f} {np.percentile(luma,50):8.0f} {np.percentile(luma,99):8.0f} "
          f"{luma.max():8.0f} {cam[:,:,0].mean()-cam[:,:,1].mean():+6.2f} {cam[:,:,2].mean()-cam[:,:,1].mean():+6.2f} "
          f"{sat.mean():8.2f} {gray:6.1f}")
