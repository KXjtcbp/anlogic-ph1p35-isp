import numpy as np, sys
from PIL import Image

def mask_osd(a):
    m = np.ones(a.shape[:2], bool)
    # OSD boxes at 1.5x scale of 1280x720 grid -> scale factor
    s = a.shape[1]/1280.0
    for (x0,y0,x1,y1) in [(0,0,180,180),(360,110,600,150),(165,165,270,195)]:
        m[int(y0*s):int(y1*s), int(x0*s):int(x1*s)] = False
    return m

def stats(path):
    im = Image.open(path).convert('RGB')
    a = np.asarray(im).astype(np.int32)
    h,w,_ = a.shape
    m = mask_osd(a)
    px = a[m]
    R,G,B = px[:,0],px[:,1],px[:,2]
    Y = (77*R+150*G+29*B)>>8
    sat = px.max(1)-px.min(1)
    neu = (sat==0).mean()*100
    blk = (px.max(1)==0).mean()*100
    ov  = (Y>=250).mean()*100
    # column profile of mid band
    band = a[int(h*0.35):int(h*0.65)]
    bandm = m[int(h*0.35):int(h*0.65)]
    col = np.array([band[i][bandm[i]].mean() if bandm[i].any() else np.nan for i in range(band.shape[0])])
    prof = np.nanmean(band.astype(np.float64),axis=(0,2))
    x0,x1 = int(w*0.10), int(w*0.55)
    xs = np.arange(x0,x1); ys = prof[x0:x1]
    A = np.polyfit(xs,ys,1); pred = np.polyval(A,xs)
    r2 = 1-((ys-pred)**2).sum()/((ys-ys.mean())**2).sum()
    print(f"== {path.split(chr(92))[-1]}")
    print(f"   size {w}x{h}  R/G/B mean {R.mean():.2f}/{G.mean():.2f}/{B.mean():.2f}  R-G {R.mean()-G.mean():+.2f}  B-G {B.mean()-G.mean():+.2f}  R/G {R.mean()/G.mean():.4f}  B/G {B.mean()/G.mean():.4f}")
    q = np.percentile(Y,[50,90,99,99.9])
    print(f"   luma mean {Y.mean():.2f}  p50 {q[0]:.0f} p90 {q[1]:.0f} p99 {q[2]:.0f} p99.9 {q[3]:.0f}  max {Y.max()}  over>=250 {ov:.3f}%")
    print(f"   chan max {R.max()}/{G.max()}/{B.max()}  ch sat p50 {np.percentile(sat,50):.0f} p99 {np.percentile(sat,99):.0f} max {sat.max()}")
    print(f"   neutral R=G=B {neu:.2f}%   pure black {blk:.2f}%")
    print(f"   column profile x[{x0}:{x1}] slope {A[0]:+.4f}  R2 {r2:.5f}  -> {'SYNTH RAMP(测试图)' if r2>0.9 else 'real scene'}")
    return

for p in sys.argv[1:]:
    stats(p)
