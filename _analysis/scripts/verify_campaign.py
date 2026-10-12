# -*- coding: utf-8 -*-
"""独立复核"改名 + 只加注释"改造：不信任子代理的自验，用它们自己的 .bak 重新验证。

判定式：
    去空白(去注释(改名(基线)))  ==  去空白(去注释(当前文件))
基线 = 改动前那一刻的字节拷贝（20261009_rename = 改名之前；20261009_comments/* = 加注释之前）。
"""
import os, re

ROOT = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
B_RENAME = r"E:\FPGA\_backup\20261009_rename\hdl_source"
B_COMMENTS = r"E:\FPGA\_backup\20261009_comments"

GLOBAL = {
    "I_ag": "I_analog_gain", "I_AG": "I_analog_gain", "I_ae": "I_exposure_time", "I_AE": "I_exposure_time",
    "O_ag": "O_analog_gain", "O_ae": "O_exposure_time", "S_ag": "S_analog_gain", "S_ae": "S_exposure_time",
    "r_ag_set": "r_analog_gain_set", "r_ae_set": "r_exposure_set",
    "r_ag_tick": "r_analog_gain_step", "r_ae_tick": "r_exposure_step", "rc_ag_tick": "r_analog_gain_accum",
    "r_ag": "r_analog_gain", "r_ae": "r_exposure",
    "m_aixs_tvalid": "m_axis_tvalid", "m_aixs_tdata_96": "m_axis_tdata_96", "m_aixs_tdata": "m_axis_tdata",
    "m_aixs_tuser": "m_axis_tuser", "m_aixs_tlast": "m_axis_tlast", "m_aixs_tready": "m_axis_tready",
    "S_cnt": "S_phase_cnt",
    "S_cnt_d0": "S_dec_digit_0", "S_cnt_d1": "S_dec_digit_1", "S_cnt_d2": "S_dec_digit_2",
    "S_cnt_d3": "S_dec_digit_3", "S_cnt_d4": "S_dec_digit_4", "S_cnt_d5": "S_dec_digit_5",
}
LOCAL = {
    "uics500_cfg/SC500GainTbl.v": {"I": "I_gain_idx", "O": "O_gain_code"},
    "uics500_cfg/uicfgcs500_720p.v": {"I": "I_gain_idx", "O": "O_gain_code"},
    "uics500_cfg/uicfgcs500.v": {"I": "I_gain_idx", "O": "O_gain_code"},
}


def read(p):
    with open(p, "rb") as f:
        return f.read()


def strip_comments(b):
    b = re.sub(rb"/\*.*?\*/", b" ", b, flags=re.S)
    b = re.sub(rb"//[^\n]*", b" ", b)
    return b


def strip_ws(b):
    return re.sub(rb"\s+", b"", b)


def rename_bytes(data, rel):
    mapping = dict(GLOBAL)
    mapping.update(LOCAL.get(rel, {}))
    pat = re.compile(rb"\b(" + b"|".join(re.escape(k).encode() for k in sorted(mapping, key=len, reverse=True)) + rb")\b")
    return pat.sub(lambda m: mapping[m.group(1).decode()].encode(), data)


def norm_cur(p):
    return strip_ws(strip_comments(read(p)))


# 当前树索引（basename -> 路径列表）
index = {}
for dp, _d, fns in os.walk(ROOT):
    for fn in fns:
        index.setdefault(fn, []).append(os.path.join(dp, fn))

rows = []


def check(group, rel_cur, baseline_path, pre_rename):
    cur = os.path.join(ROOT, rel_cur.replace("/", os.sep))
    if not os.path.exists(cur):
        rows.append((group, rel_cur, baseline_path, "当前文件不存在")); return
    b = read(baseline_path)
    if pre_rename:
        b = rename_bytes(b, rel_cur)
    a1 = norm_cur(cur)
    b1 = strip_ws(strip_comments(b))
    verdict = "CODE-IDENTICAL" if a1 == b1 else "*** 不一致 ***"
    rows.append((group, rel_cur, os.path.basename(baseline_path), verdict, len(b1), len(a1)))


# ---- 第一组：改名之前 的基线（现已被改名 + 加注释）----
group1 = {
    "uics500_cfg__uics500regAE.v": "uics500_cfg/uics500regAE.v",
    "uics500_cfg__uicfgcs500.v": "uics500_cfg/uicfgcs500.v",
    "uics500_cfg__SC500GainTbl.v": "uics500_cfg/SC500GainTbl.v",
    "hdmi_phy_warpper.v__orig": "hdmi_phy_wrapper.v",
    "data_96bit_to_128bit.v": "data_96bit_to_128bit.v",
    "isp__raw10_unpacket_2lane.v": "isp/raw10_unpacket_2lane.v",
    "uiisp_beta__raw10_unpacket_2lane.v": "uiisp_beta/raw10_unpacket_2lane.v",
    "raw10_unpacket.v": "raw10_unpacket.v",
    "isp__data96_128__data96_128.v": "isp/data96_128/data96_128.v",
    "uiisp_beta__ae_set.v": "uiisp_beta/ae_set.v",
    "uics500_cfg__uicfgcs500_720p.v": "uics500_cfg/uicfgcs500_720p.v",
    "hdmi_mixer.v": "hdmi_mixer.v",
    "isp__isp_top.v": "isp/isp_top.v",
    "design_top_wrapper.v": "design_top_wrapper.v",
}
for base, rel in sorted(group1.items()):
    check("RENAME基线", rel, os.path.join(B_RENAME, base), pre_rename=True)

# ---- 第二组：加注释之前 的基线（无 __ 编码的按分组目录定点解析）----
FIXED = {
    "awb/raw10_unpacket_2lane.v": "isp/raw10_unpacket_2lane.v",
    "awb/csi_unpacket_2lane.v": "isp/csi_unpacket_2lane.v",
    "awb/BLC.v": "isp/BLC/BLC.v",
    "awb/awb.v": "isp/awb/awb.v",
    "awb/signal_delay.v": "isp/awb/signal_delay.v",
    "awb/blk_mem_gen_awb_delay_signal.v": "isp/awb/ram/blk_mem_gen_awb_delay_signal.v",
    "legacy/awb.v": "awb.v",
    "legacy/signal_delay.v": "signal_delay.v",
}
for dp, _d, fns in os.walk(B_COMMENTS):
    grp = os.path.basename(dp)
    for fn in sorted(fns):
        if not fn.endswith(".bak"):
            continue
        key = grp + "/" + fn[:-4]
        if key in FIXED:
            rel = FIXED[key]
        elif key in ("demosaic/" + fn[:-4],):
            rel = "isp/demosaic_4x_2_0/" + fn[:-4]
        elif fn[:-4].count("__"):
            rel = fn[:-4].replace("__", "/") if grp in ("core", "legacy") else "isp/demosaic_4x_2_0/" + fn[:-4]
        else:
            cands = [p for p in index.get(fn[:-4], []) if "\\blk_mem_gen_" not in p]
            if len(cands) != 1:
                rows.append(("COMMENT基线/" + grp, fn[:-4], fn, f"路径歧义({len(cands)})")); continue
            rel = os.path.relpath(cands[0], ROOT).replace("\\", "/")
        check("COMMENT基线/" + grp, rel, os.path.join(dp, fn), pre_rename=False)

# ---- 第三组：.al 工程文件（只应差 hdmi_phy_warpper -> hdmi_phy_wrapper 这一处路径）----
_al_old = os.path.join(B_RENAME, "camera_to_dsi_display.al.orig")
_al_new = r"E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display.al"
_a = read(_al_old).replace(b"hdl_source/hdmi_phy_warpper", b"hdl_source/hdmi_phy_wrapper")
_b = read(_al_new)
rows.append(("AL基线", "td_project/camera_to_dsi_display.al", "camera_to_dsi_display.al.orig",
             "CODE-IDENTICAL" if _a == _b else "*** 不一致 ***", len(_a), len(_b)))

# ---- 报告 ----
out = []
out.append("%-22s %-52s %-34s %s" % ("基线组", "当前文件", "基线文件", "判定"))
out.append("-" * 150)
bad = 0
for r in sorted(rows, key=lambda x: (x[0], x[1])):
    if len(r) == 4 and isinstance(r[3], str) and not r[3].startswith("CODE") and r[3] != "":
        verdict = r[3]
        if verdict.startswith("***"):
            bad += 1
        out.append("%-22s %-52s %-34s %s" % (r[0], r[1], r[2], verdict))
    else:
        g, rel, b, v, lb, la = r
        if v.startswith("***"):
            bad += 1
        out.append("%-22s %-52s %-34s %-16s 码字符数 基线=%d 当前=%d" % (g, rel, b, v, lb, la))
out.append("")
out.append("共复核 %d 个文件，判定不一致 %d 个。" % (len(rows), bad))
open(r"E:\FPGA\_analysis\reports\verify_campaign.txt", "w", encoding="utf-8").write("\n".join(out))
print("不一致:", bad, "| 总:", len(rows))
