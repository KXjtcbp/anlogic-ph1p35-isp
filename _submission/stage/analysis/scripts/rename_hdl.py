# -*- coding: utf-8 -*-
"""HDL 标识符改名器（第二版：改全树手写文件 + 顺手修文件名拼写）。

设计要点：
  * 按 **字节** 读写（保留原编码与换行）——isp/raw10_unpacket_2lane.v 不是合法 UTF-8。
  * 一次正则替换（alternation 按长度降序 + dict 查表），避免"A→B 之后 B 又被 C 规则改掉"的级联。
  * 只动显式列出的名字；`I`/`O` 这两个高危单字母名只在 3 个既定文件里换。
  * 禁止清单（约束文件引用的顶层端口/网名/实例名）永不触碰。
  * 目标文件 = hdl_source 下全部 .v/.sv（排除加密件）；实测只有 11 个手写文件命中，
    厂商/生成件（ph1p35_ddr / mipi_dphy_rx / blk_mem_gen_* / divider_gate / anlogic_logo_rom）零命中。
"""
import re, sys, os, shutil
from collections import defaultdict

ROOT = r"E:\FPGA\proj\baseline\lab3\user_source\hdl_source"
BACKUP = r"E:\FPGA\_backup\20261009_rename\hdl_source"
AL_FILE = r"E:\FPGA\proj\baseline\lab3\td_project\camera_to_dsi_display.al"
TYPO_OLD, TYPO_NEW = "hdmi_phy_warpper", "hdmi_phy_wrapper"
APPLY = "--apply" in sys.argv

# ---------- 全局改名表（对所有手写文件生效）----------
GLOBAL = {
    # SC500 增益/曝光接口：I_ag / I_ae 看不出含义
    "I_ag": "I_analog_gain",
    "I_AG": "I_analog_gain",
    "I_ae": "I_exposure_time",
    "I_AE": "I_exposure_time",
    "O_ag": "O_analog_gain",
    "O_ae": "O_exposure_time",
    "S_ag": "S_analog_gain",
    "S_ae": "S_exposure_time",
    "r_ag_set": "r_analog_gain_set",
    "r_ae_set": "r_exposure_set",
    "r_ag_tick": "r_analog_gain_step",
    "r_ae_tick": "r_exposure_step",
    "rc_ag_tick": "r_analog_gain_accum",
    "r_ag": "r_analog_gain",
    "r_ae": "r_exposure",
    # 拼写错误 aixs -> axis（isp_top.v 内部的局部 wire）
    "m_aixs_tvalid": "m_axis_tvalid",
    "m_aixs_tdata_96": "m_axis_tdata_96",
    "m_aixs_tdata": "m_axis_tdata",
    "m_aixs_tuser": "m_axis_tuser",
    "m_aixs_tlast": "m_axis_tlast",
    "m_aixs_tready": "m_axis_tready",
    # 相位计数器：S_cnt 看不出数什么
    "S_cnt": "S_phase_cnt",
    # OSD 十进制位计数器（hdmi_mixer.v 内局部）
    "S_cnt_d0": "S_dec_digit_0",
    "S_cnt_d1": "S_dec_digit_1",
    "S_cnt_d2": "S_dec_digit_2",
    "S_cnt_d3": "S_dec_digit_3",
    "S_cnt_d4": "S_dec_digit_4",
    "S_cnt_d5": "S_dec_digit_5",
}

# ---------- 仅限指定文件的改名（高危单字母）----------
LOCAL = {
    "uics500_cfg/SC500GainTbl.v": {"I": "I_gain_idx", "O": "O_gain_code"},
    "uics500_cfg/uicfgcs500_720p.v": {"I": "I_gain_idx", "O": "O_gain_code"},
    "uics500_cfg/uicfgcs500.v": {"I": "I_gain_idx", "O": "O_gain_code"},
}

FORBIDDEN = set("""
I_sys_clk I_rst_n O_cam_scl IO_cam_sda O_cam_24m O_cam_rst I_button O_screen_pwm
O_tmds_ch0_p O_tmds_ch1_p O_tmds_ch2_p O_tmds_clk_p
IO_rx_clk_pad_p
u_PLL u_mipi_dphy_rx_ph1p_mipiio_wrapper u_ph1p_mipiio_rx_wrapper u_PH1P_LOGIC_DPHY_MIPI_RX
u_ph1p35_324_ddr_wrapper u_ddr2 u_key_mode_ctrl u_hdmi_mixer
""".split())

allnames = set(GLOBAL)
for d in LOCAL.values():
    allnames |= set(d)
bad = allnames & FORBIDDEN
assert not bad, f"改名表与禁止清单冲突: {bad}"

# ---------- 收集目标文件：全树 .v/.sv，排除加密件 ----------
files = []
for dirpath, _dirs, fnames in os.walk(ROOT):
    for fn in fnames:
        if not fn.endswith((".v", ".sv")):
            continue
        if ".enc." in fn:            # 厂商加密件，绝不改
            continue
        files.append(os.path.join(dirpath, fn))
files.sort()

def relpath(abspath):
    return os.path.relpath(abspath, ROOT).replace("\\", "/")

report, total_hits = [], defaultdict(int)
P = report.append
touched = []

if APPLY:
    os.makedirs(BACKUP, exist_ok=True)

for f in files:
    rel = relpath(f)
    with open(f, "rb") as fh:
        data = fh.read()
    mapping = dict(GLOBAL)
    mapping.update(LOCAL.get(rel, {}))
    pat = re.compile(rb"\b(" + b"|".join(re.escape(k).encode() for k in
                                         sorted(mapping, key=len, reverse=True)) + rb")\b")

    def sub(m):
        old = m.group(1).decode()
        total_hits[old] += 1
        return mapping[old].encode()

    new = pat.sub(sub, data)
    if new != data:
        n = sum(1 for _ in pat.finditer(data))
        P(f"  {rel:<58} {n:>5} 处")
        touched.append(rel)
        if APPLY:
            shutil.copy2(f, os.path.join(BACKUP, rel.replace("/", "__")))
            with open(f, "wb") as fh:
                fh.write(new)

# ---------- 文件名拼写修复（模块名本来就是对的，只有文件名错）----------
P("")
old_path = os.path.join(ROOT, TYPO_OLD + ".v")
new_path = os.path.join(ROOT, TYPO_NEW + ".v")
if os.path.exists(old_path):
    P(f"  文件改名: {TYPO_OLD}.v -> {TYPO_NEW}.v")
    if APPLY:
        shutil.copy2(old_path, os.path.join(BACKUP, TYPO_OLD + ".v__orig"))
        os.rename(old_path, new_path)
    with open(AL_FILE, "rb") as fh:
        al = fh.read()
    al2 = al.replace(("hdl_source/" + TYPO_OLD).encode(),
                     ("hdl_source/" + TYPO_NEW).encode())
    if al2 != al:
        P(f"  工程文件同步: {os.path.basename(AL_FILE)}  {al.count(('hdl_source/'+TYPO_OLD).encode())} 处路径")
        if APPLY:
            shutil.copy2(AL_FILE, os.path.join(BACKUP, "camera_to_dsi_display.al.orig"))
            with open(AL_FILE, "wb") as fh:
                fh.write(al2)

P("")
P("== 各旧名命中总数 ==")
for k, v in sorted(total_hits.items(), key=lambda kv: -kv[1]):
    P(f"  {k:<18} -> {(GLOBAL.get(k) or '(仅限文件)'):<24} {v}")

outfile = r"E:\FPGA\_analysis\reports\rename_report.txt"
open(outfile, "w", encoding="utf-8").write("\n".join(report))
print(("APPLY " if APPLY else "DRY-RUN ") + "完成")
print("改动文件数:", len(touched), "| 名字命中总数:", sum(total_hits.values()))
print("报告:", outfile)
