# -*- coding: utf-8 -*-
"""
black_level_check.py —— 用 ChipWatcher 采集的 CSV 判定"黑电平基座"取值。

背景：工程里 mipi_to_raw_converter.v 用了 S_blk_level = 56（2026-10-09 标定）。
问题：此后模拟增益可能被改大（0x3e08/0x3e09 从 0f/20=4.0x 改到 1f/2d=11.25x），
      若黑基座随模拟增益等比放大，则扣 56 会留下大量灰雾（"画面发灰"的直接来源）。
判据：若两组成像条件明显不同（信号幅度差数倍）的采集，其 RAW10 黑基座相同，
      则说明传感器内部 BLC 在增益之后、基座不随增益变化 -> 56 仍然适用。

CSV 列：Sample,Trigger,S_ISP_O_tdata[127:0],S_ISP_O_tlast,S_ISP_O_tuser,S_ISP_O_tvalid,
        S_axis_tdata[39:0],S_axis_tlast,S_axis_tuser,S_axis_tvalid
        （S_axis_tdata 是 40 位二进制字符串，MSB 在前：前 10 字符 = 位[39:30] = RTL 的字段3）
"""
import os
import statistics as st

FILES = [
    ("test1.csv", "16:59 测试"),
    ("全黑.csv", "19:34 盖镜头"),
    ("室内常光.csv", "19:35 室内常光"),
    ("全黑2.csv", "20:09 盖镜头"),
    ("室内常光2.csv", "20:09 室内常光"),
]
ROOT = r"E:\FPGA"


def parse(path):
    """返回 (raw_fields[4][值...], isp_words[列表 of 128bit整数字符串], 统计)"""
    f40 = [[], [], [], []]
    isp_bytes = []
    n_valid_raw = 0
    n_valid_isp = 0
    n_raw_max = 0
    raw_all = []
    with open(path, "r", encoding="utf-8", errors="replace") as fp:
        next(fp)  # 表头
        for line in fp:
            p = line.rstrip("\n").split(",")
            if len(p) < 10:
                continue
            if p[9] == "1" and len(p[6]) == 40:           # S_axis_tvalid & 位宽正确
                n_valid_raw += 1
                for i in range(4):
                    v = int(p[6][10 * i:10 * i + 10], 2)
                    f40[i].append(v)
                    raw_all.append(v)
                    if v == 1023:
                        n_raw_max += 1
            if p[5] == "1" and len(p[2]) == 128:          # S_ISP_O_tvalid
                n_valid_isp += 1
                for i in range(0, 128, 8):
                    isp_bytes.append(int(p[2][i:i + 8], 2))
    return f40, raw_all, isp_bytes, n_valid_raw, n_valid_isp, n_raw_max


def line_stats(v, tag):
    if not v:
        return "%s: 无数据" % tag
    v2 = sorted(v)
    def pct(q):
        return v2[min(len(v2) - 1, int(q * (len(v2) - 1)))]
    return ("%s n=%5d min=%4d p1=%4d p5=%4d 中位=%6.1f 均值=%7.2f 标准差=%6.2f p95=%4d max=%4d"
            % (tag, len(v), v2[0], pct(0.01), pct(0.05), st.median(v), st.mean(v),
               st.pstdev(v) if len(v) > 1 else 0.0, pct(0.95), v2[-1]))


print("=" * 118)
print("一、RAW10（ISP 输入端 S_axis_tdata[39:0]）逐字段统计 —— 黑基座与噪声")
print("=" * 118)
summary = {}
for fn, tag in FILES:
    path = os.path.join(ROOT, fn)
    if not os.path.exists(path):
        print("缺失: %s" % path)
        continue
    f40, raw_all, isp_bytes, nvr, nvi, nrm = parse(path)
    print("\n--- %s  (%s)  有效RAW拍=%d  有效ISP拍=%d ---" % (fn, tag, nvr, nvi))
    for i in range(4):
        print("   " + line_stats(f40[i], "字段%d" % i))
    print("   " + line_stats(raw_all, "全体  "))
    print("   1023 饱和样本占比 = %.2f%%" % (100.0 * nrm / max(1, len(raw_all))))
    if isp_bytes:
        nz = [b for b in isp_bytes if b != 0]
        print("   ISP输出字节: n=%d 非零占比=%.1f%% 非零均值=%.2f 非零中位=%.1f 最大=%d"
              % (len(isp_bytes), 100.0 * len(nz) / len(isp_bytes),
                 st.mean(nz) if nz else 0, st.median(nz) if nz else 0, max(isp_bytes)))
    summary[fn] = (f40, raw_all, isp_bytes, nvr, nvi, nrm)

print()
print("=" * 118)
print("二、结论用的关键量：黑基座（盖镜头时的最小值/中位）在不同成像状态之间是否变化")
print("=" * 118)
for fn in ("全黑.csv", "全黑2.csv", "室内常光.csv", "室内常光2.csv"):
    if fn not in summary:
        continue
    f40, raw_all, isp_bytes, nvr, nvi, nrm = summary[fn]
    mn = min(raw_all) if raw_all else -1
    md = st.median(raw_all) if raw_all else -1
    nz = [b for b in isp_bytes if b != 0]
    print("%-14s RAW10: min=%4d 中位=%6.1f 均值=%7.2f  |  ISP非零均值=%7.2f"
          % (fn, mn, md, st.mean(raw_all) if raw_all else 0,
             st.mean(nz) if nz else 0))

print()
print("=" * 118)
print("三、判定")
print("=" * 118)
blk = [summary[k][1] for k in ("全黑.csv", "全黑2.csv") if k in summary]
if len(blk) == 2:
    a, b = blk
    print("两次盖镜头采集的 RAW10 最小值: %d 与 %d；中位: %.1f 与 %.1f"
          % (min(a), min(b), st.median(a), st.median(b)))
    sig = [st.mean(summary[k][1]) for k in ("室内常光.csv", "室内常光2.csv") if k in summary]
    if len(sig) == 2:
        print("两次室内常光的 RAW10 均值: %.1f 与 %.1f  （相差 %.2f 倍 = 成像状态明显不同）"
              % (sig[0], sig[1], max(sig) / max(1e-9, min(sig))))
    print("若两次盖镜头的基座相同 => 基座与增益/积分时间无关 => S_blk_level=56 仍然适用。")
