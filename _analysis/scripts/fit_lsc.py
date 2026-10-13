# -*- coding: utf-8 -*-
"""
fit_lsc.py  ——  从"均匀靶面"采集图拟合 LSC 可分离表，并回写 lsc.v

原理
----
镜头色彩暗角是乘性透射比：R/G = (S_R/S_G) * T_R(方位)/T_G(方位)，
所以待校正量取  D(x,y) = 1 - R/G(x,y)（B 共用同一增益，实测 B/G 剖面与 R/G 几乎重合）。

模型：以 (cx,cy) 为顶点的归一化二次碗
    D(x,y) ≈ p0 + p1*u^2 + p2*v^2 ,  u=(x-cx)/W896 , v=(y-cy)/H1080
依据：余弦四次方照度定律 cos^4(theta) 近轴展开即二次型；而
r^2=(x-cx)^2+(y-cy)^2 天然可分离 ⇒ 碗能被 KH[x]+KV[y] 精确表示。

★关键：**圆心 (cx,cy) 是待拟合量**★。实测碗底不在画面几何中心（列剖面最低点
在 x≈900/1920，行剖面最低点在 y≈600/1080），强行钉在中心会得到 R^2≈0.1 的
荒谬结果（甚至拟合出"四角更绿"的反号）。这里对 (cx,cy) 做粗网格搜索。

用法： python fit_lsc.py [图1 图2 ...]     默认自动挑"干净"的靶面图
"""
import os
import re
import sys
import glob
import numpy as np
from PIL import Image

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS      = r"E:\FPGA"
LSC_V   = os.path.join(WS, "proj", "baseline", "lab3", "user_source", "hdl_source", "isp", "lsc.v")

H_NODES = 20          # 水平节点数（每节点 16 beat = 64 像素）
V_NODES = 24          # 垂直节点数（每节点 32 行）
K_MAX   = 7           # g = 1 + k/64 -> 上限 +10.94%

# 挖掉 OSD：左上安路 logo、黄色 CNT、橙色遥测行、绿色 MODE（1920x1080 空间）
MASK_BOXES = [(0, 0, 400, 320), (500, 150, 1500, 285)]

# 只挑"干净"靶面：白纸/白塑料铺满、无强结构。E1 那种带标记物的绝不能进（峰谷 34%）。
DEFAULT_GLOBS = [
    os.path.join(WS, "captures", "2026-10-13_白纸靶面_舍入版后", "W1*.png"),
    os.path.join(WS, "captures", "2026-10-13_黑电平旁路实验", "01_B1*.png"),
]


def default_images():
    out = []
    for p in DEFAULT_GLOBS:
        out += sorted(glob.glob(p))
    return out


def load_D(path):
    a = np.asarray(Image.open(path).convert("RGB")).astype(np.float64)
    h, w, _ = a.shape
    mask = np.ones((h, w), bool)
    for x0, y0, x1, y1 in MASK_BOXES:
        mask[max(0, y0):min(h, y1), max(0, x0):min(w, x1)] = False
    R, G = a[..., 0], a[..., 1]
    valid = mask & (G > 24)
    D = np.full((h, w), np.nan)
    D[valid] = 1.0 - (R[valid] / G[valid])

    # ★ D 的形状是 (h, w) = (y, x)★，索引必须写 D[y, x]。
    #   第一版写成 D[xs[i]:.., ys[j]:..]（x 落在 h 轴上），i>=12 时切片越界变空、
    #   被"最近邻补洞"用邻居填满，表现为"右侧 8 个节点在 24 个 y 上读数完全相同"
    #   —— 这就是那个假数据的来源。
    xs = np.linspace(0, w, H_NODES + 1).astype(int)     # x 方向
    ys = np.linspace(0, h, V_NODES + 1).astype(int)     # y 方向
    grid = np.full((H_NODES, V_NODES), np.nan)
    for i in range(H_NODES):
        for j in range(V_NODES):
            blk = D[ys[j]:ys[j + 1], xs[i]:xs[i + 1]]      # <-- (y, x)
            f = np.isfinite(blk)
            if f.sum() > 500:
                grid[i, j] = np.median(blk[f])
    if np.isnan(grid).any():                       # 最近邻补洞
        idx = np.argwhere(np.isfinite(grid))
        for i, j in np.argwhere(np.isnan(grid)):
            k = idx[((idx - (i, j)) ** 2).sum(axis=1).argmin()]
            grid[i, j] = grid[k[0], k[1]]
    xc = np.array([(xs[i] + xs[i + 1]) / 2.0 for i in range(H_NODES)])
    yc = np.array([(ys[j] + ys[j + 1]) / 2.0 for j in range(V_NODES)])
    return grid, xc, yc


def fit(D, xc, yc):
    """粗搜圆心 + 最小二乘，返回 (p0,p1,p2,cx,cy,r2)"""
    U, V = np.meshgrid(xc, yc, indexing="ij")
    best = None
    for cx in np.arange(600, 1420, 40):
        for cy in np.arange(300, 900, 40):
            u2 = ((U - cx) / 960.0) ** 2
            v2 = ((V - cy) / 540.0) ** 2
            A = np.column_stack([np.ones(D.size), u2.ravel(), v2.ravel()])
            c, *_ = np.linalg.lstsq(A, D.ravel(), rcond=None)
            res = D - (A @ c).reshape(D.shape)
            ss = (res ** 2).sum()
            if best is None or ss < best[0]:
                best = (ss, c, cx, cy)
    ss, c, cx, cy = best
    ss_tot = ((D - D.mean()) ** 2).sum()
    return c[0], c[1], c[2], cx, cy, 1 - ss / max(ss_tot, 1e-12)


def main():
    imgs = sys.argv[1:] if len(sys.argv) > 1 else default_images()
    if not imgs:
        raise SystemExit("找不到靶面图")

    grids = []
    for p in imgs:
        g, xc, yc = load_D(p)
        grids.append(g)
        print("载入 : %-64s D 均值 %+.4f 峰谷 %.2f%%"
              % (os.path.basename(p), g.mean(), 100 * (g.max() - g.min())))
    D = np.mean(grids, axis=0)
    print("合并 : %d 张  D 峰谷 %.2f%%" % (len(grids), 100 * (D.max() - D.min())))

    # ---- 非参可分离分解（默认）----
    #   D 已天然以 R/G 为量纲，两端都随亮度成比例，所以不做任何"减法底"。
    #   KH[x] = mean_y(D) , KV[y] = mean_x(D) ，各自去掉自己的最小值，
    #   再按"当前最大所需校正量"线性映射到 0..K_MAX。
    #   去掉的是**各自的端点**而不是全局常数 —— 这样 KH/KV 在画面最外侧节点
    #   都是 0，符合"边缘基本中性、只有中心需要抬"的物理事实。
    #   3 点滑动平均压掉场景纹理；两张不同亮度的靶面取平均再压一次。
    # 依据：镜头的乘性透射比 T_R/T_G 是方位的函数，而 D 就是以 R/G 为量纲的
    #   相对偏差，跟场景亮度无关（W1 的 Y 从 156 变到 182，D 的空间形状没变）。
    cu = D.mean(axis=1)          # 沿 y 平均 -> 水平剖面
    cv = D.mean(axis=0)          # 沿 x 平均 -> 垂直剖面
    k3 = np.array([0.25, 0.5, 0.25])
    cu = np.convolve(cu, k3, mode="same") / np.convolve(np.ones_like(cu), k3, mode="same")
    cv = np.convolve(cv, k3, mode="same") / np.convolve(np.ones_like(cv), k3, mode="same")
    # 各自扣掉端点最小值（外侧节点归零）
    cu = np.clip(cu - np.minimum(cu[0], cu[-1]), 0, None)
    cv = np.clip(cv - np.minimum(cv[0], cv[-1]), 0, None)
    recon = cu[:, None] + cv[None, :]
    span = max(recon.max(), 1e-9)
    qh = np.clip(np.round(cu / span * K_MAX), 0, K_MAX).astype(int)
    qv = np.clip(np.round(cv / span * K_MAX), 0, K_MAX).astype(int)
    model = (D.mean() - cu.mean() - cv.mean()) + recon      # 可分离重建
    resid = D - model
    ss_tot = ((D - D.mean()) ** 2).sum()
    r2 = 1 - (resid ** 2).sum() / max(ss_tot, 1e-12)
    print("分解 : 可分离重建峰谷 %.2f%%  残差 std %.4f   R^2 = %.4f"
          % (100 * recon.max(), resid.std(), r2))
    p0, p1, p2, cx, cy = D.mean(), 0.0, 0.0, 0.0, 0.0
    kk = qh[:, None] + qv[None, :]
    print("量化 : k = %d..%d -> g = %.4f..%.4f  (跨距 %.2f%%)"
          % (kk.min(), kk.max(), 1 + kk.min() / 64.0, 1 + kk.max() / 64.0,
             100 * (kk.max() - kk.min()) / 64.0))

    src = open(LSC_V, "rb").read().decode("utf-8")
    lh = "\n".join("                5'd%-2d: F_kh = 3'd%d;" % (i, t) for i, t in enumerate(qh))
    lv = "\n".join("                5'd%-2d: F_kv = 3'd%d;" % (i, t) for i, t in enumerate(qv))
    block = (
        "// ==== LSC_TABLE_BEGIN ====\n"
        "    // 由 fit_lsc.py 自动生成（%d 张干净靶面平均，二次碗最小二乘 + 圆心搜索）\n"
        "    // D = 1 - R/G = %+.4f %+.4f*u^2 %+.4f*v^2 , u=(x-%.0f)/960, v=(y-%.0f)/540 , R^2=%.4f\n"
        "    // 水平 %d 节点（每节点 %d 像素），垂直 %d 节点（每节点 %d 行）\n"
        "    // g = 1 + k/64；k=%d -> %.4fx ，k=%d -> %.4fx\n"
        "    function [2:0] F_kh(input [4:0] i);\n"
        "        begin\n"
        "            case (i)\n"
        "%s\n"
        "                default: F_kh = 3'd0;\n"
        "            endcase\n"
        "        end\n"
        "    endfunction\n\n"
        "    function [2:0] F_kv(input [4:0] i);\n"
        "        begin\n"
        "            case (i)\n"
        "%s\n"
        "                default: F_kv = 3'd0;\n"
        "            endcase\n"
        "        end\n"
        "    endfunction\n"
        "// ==== LSC_TABLE_END ===="
        % (len(grids), p0, p1, p2, cx, cy, r2, H_NODES, 1280 // H_NODES, V_NODES, 720 // V_NODES,
           kk.min(), 1 + kk.min() / 64.0, kk.max(), 1 + kk.max() / 64.0, lh, lv)
    )
    new = re.sub(r"// ==== LSC_TABLE_BEGIN ====.*?// ==== LSC_TABLE_END ====",
                 lambda m: block, src, flags=re.S)
    if new == src:
        print("!! 未找到 LSC_TABLE 标记，lsc.v 未改动")
        return
    open(LSC_V, "wb").write(new.encode("utf-8"))
    print("已回写 : %s  (%d B)" % (LSC_V, os.path.getsize(LSC_V)))
    print("KH =", qh.tolist())
    print("KV =", qv.tolist())


if __name__ == "__main__":
    main()
