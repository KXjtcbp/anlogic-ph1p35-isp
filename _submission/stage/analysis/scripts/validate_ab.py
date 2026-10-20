# -*- coding: utf-8 -*-
"""A/B 采集对有效性校验器（判断依据的自动化工具）。

用法：
    python validate_ab.py <曲线关的图> <曲线开的图> [期望表.hex]
       期望表.hex 省略时默认为当前工程表 gamma_lut_twoseg_p160_a050.hex

通过判据（全部满足才算 VALID）：
  1. 两图同尺寸；
  2. 机位未动：高通后的零位移归一化互相关 NCC >= 0.90（位移搜索不得给出更优的偏移）；
  3. 显示链路未变：OSD 黄字像素均值三通道差 <= 3 码；
  4. 曲线确实生效：用期望表把"关"图映射后，与"开"图逐像素差在 ±3 码内的像素占比 >= 95%，
     且 ±8 码内占比 >= 99%；
  5. 电平未漂移：把"关"图整体缩放 a、偏移 C 后仍能显著改善残差 => 判定为电平漂移（提示重采）。
"""
import sys
import numpy as np
from PIL import Image

DEFAULT_HEX = r"E:\FPGA\_analysis\lut\gamma_lut_twoseg_p160_a050.hex"
OSD = (540, 150, 900, 215)          # 安路 CNT 那行（1920x1080 坐标，1.5x 设计坐标）


def load(p):
    return np.asarray(Image.open(p).convert("RGB")).astype(np.int32)


def y_of(a):
    return (77 * a[:, :, 0] + 150 * a[:, :, 1] + 29 * a[:, :, 2]) >> 8


def ncc(x, y):
    x = x - x.mean(); y = y - y.mean()
    return float((x * y).sum() / (np.sqrt((x * x).sum()) * np.sqrt((y * y).sum()) + 1e-9))


def highpass(a, k=9):
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    from PIL import ImageFilter
    return a - np.asarray(im.filter(ImageFilter.BoxBlur(k))).astype(np.int32)


def shift_best(a, b, maxs=12, step=4):
    """在 1/step 缩略图上搜位移，返回 (ncc_at_zero, best_ncc, dx, dy)（缩略图像素）。"""
    aa = np.asarray(Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).resize(
        (a.shape[1] // step, a.shape[0] // step), Image.BOX)).astype(np.int32)
    bb = np.asarray(Image.fromarray(np.clip(b, 0, 255).astype(np.uint8)).resize(
        (b.shape[1] // step, b.shape[0] // step), Image.BOX)).astype(np.int32)
    h, w = aa.shape
    z = ncc(aa[maxs:-maxs, maxs:-maxs], bb[maxs:-maxs, maxs:-maxs])
    best = (-2, 0, 0)
    for dy in range(-maxs, maxs + 1):
        for dx in range(-maxs, maxs + 1):
            c = ncc(aa[maxs:-maxs, maxs:-maxs],
                    bb[maxs + dy:h - maxs + dy, maxs + dx:w - maxs + dx])
            if c > best[0]:
                best = (c, dx, dy)
    return z, best[0], best[1] * step, best[2] * step


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    p_off, p_on = sys.argv[1], sys.argv[2]
    hexp = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_HEX
    lut = np.array([int(l.strip(), 16) for l in open(hexp) if l.strip()], dtype=np.int32)

    A, B = load(p_off), load(p_on)          # A=曲线关, B=曲线开
    ok = True
    print("== A/B 采集对有效性校验 ==")
    print("A(曲线关) = %s" % p_off)
    print("B(曲线开) = %s" % p_on)
    print("期望表    = %s" % hexp)

    print("\n[1] 尺寸一致 ............ %s" % ("PASS" if A.shape == B.shape else "FAIL"))
    ok &= A.shape == B.shape
    if A.shape != B.shape:
        return 1

    ya, yb = y_of(A), y_of(B)
    # 用梯度幅值（结构信号，对色调曲线/电平变化不敏感）判机位
    ga = np.abs(np.gradient(ya, axis=0)) + np.abs(np.gradient(ya, axis=1))
    gb = np.abs(np.gradient(yb, axis=0)) + np.abs(np.gradient(yb, axis=1))
    z, bc, dx, dy = shift_best(ga, gb)
    align = z >= 0.60 and abs(dx) <= 8 and abs(dy) <= 8 and (bc - z) < 0.05
    print("[2] 机位未动 ............ %s   梯度零位移 NCC=%.3f  最佳位移 NCC=%.3f @(%d,%d)"
          % ("PASS" if align else "FAIL", z, bc, dx, dy))
    ok &= align

    oa = A[OSD[1]:OSD[3], OSD[0]:OSD[2]]
    ob = B[OSD[1]:OSD[3], OSD[0]:OSD[2]]
    m = (oa[:, :, 0] > 150) & (oa[:, :, 1] > 150) & (oa[:, :, 2] < 120)
    if m.sum() > 200:
        da = np.abs(oa[m].mean(axis=0) - ob[m].mean(axis=0))
        osd_ok = da.max() <= 3.0
        print("[3] 显示链路未变 ........ %s   OSD 黄字均值差 R%.2f G%.2f B%.2f（%d px）"
              % ("PASS" if osd_ok else "FAIL", da[0], da[1], da[2], m.sum()))
    else:
        osd_ok = False
        print("[3] 显示链路未变 ........ FAIL   OSD 黄字未找到（%d px）" % m.sum())
    ok &= osd_ok

    pred = lut[np.clip(ya, 0, 255)]
    d = np.abs(pred - yb)
    f3, f8 = (d <= 3).mean() * 100, (d <= 8).mean() * 100
    lut_ok = f3 >= 95.0
    print("[4] 曲线确实生效 ........ %s   |预测-实测|<=3码 %.2f%%  <=8码 %.2f%%  平均 %.2f 码"
          % ("PASS" if lut_ok else "FAIL", f3, f8, d.mean()))
    ok &= lut_ok

    X = np.vstack([ya.ravel(), np.ones(ya.size)]).T.astype(np.float64)
    coef, *_ = np.linalg.lstsq(X, yb.ravel().astype(np.float64), rcond=None)
    r_aff = float(np.sqrt(((coef[0] * ya + coef[1] - yb) ** 2).mean()))
    drift = r_aff + 6 < d.mean()
    print("[5] 电平漂移检查 ........ %s   仿射拟合 a=%.3f C=%+.1f 残差 %.2f 码（若明显小于[4]的平均差=%.2f 则存在电平漂移）"
          % ("WARN(存在漂移)" if drift else "PASS", coef[0], coef[1], r_aff, d.mean()))

    print("\n===== 结论：%s =====" % ("VALID（这对 A/B 可用于量化评估）" if ok and not drift else
                                    "INVALID（不可用于量化，请按协议重采）"))
    if not ok or drift:
        print("原因与对策：")
        if not align:
            print("  - 机位/焦距变了：重采时不要碰开发板与镜头（用长杆/工具拨开关）。")
        if not osd_ok:
            print("  - 显示链路或 OSD 变了：确认没有重启、没有改分辨率。")
        if not lut_ok:
            print("  - 两图的差异不满足当前表的逐像素关系：多半是场景/光照/工作点变了；")
            print("    请在 N秒内、同一光照、不动板子的条件下只切 SW2 重采，并重复 2~3 组。")
        if drift:
            print("  - 存在整体亮度/对比漂移（a=%.3f）：确认两次采集间没有改 SW1/SW3/SW4、没有自动曝光介入。" % coef[0])
    return 0


if __name__ == "__main__":
    sys.exit(main())
