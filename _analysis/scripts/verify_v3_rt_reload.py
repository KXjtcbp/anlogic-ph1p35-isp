# -*- coding: utf-8 -*-
# 内容说明：2026-10-10d "SW3/SW4 运行时生效" 改动的自检（39 项）。
#   核对 4 个文件：design_top_wrapper.v（触发逻辑 + 连线顺序）、uicfgcs500_720p.v
#   （运行时表输入）、uics500regAE.v（5→8 条）、uics500reg_720p60.v（init 表未被动过）。
#   输出：E:\FPGA\_analysis\reports\verify_v3_rt_reload.txt
#   ★教训：不要用 pwsh 的 Get-Content -Raw / Set-Content 往返改这个文件（默认按 ANSI 解码，
#    会把 UTF-8 中文毁掉并可能吞掉引号 => SyntaxError）。
import io, os, re, sys

SRC = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
TOP = os.path.join(SRC, 'design_top_wrapper.v')
CFG = os.path.join(SRC, 'uics500_cfg', 'uicfgcs500_720p.v')
AE  = os.path.join(SRC, 'uics500_cfg', 'uics500regAE.v')
INI = os.path.join(SRC, 'uics500_cfg', 'uics500reg_720p60.v')
OUT = r'E:\FPGA\_analysis\reports\verify_v3_rt_reload.txt'

top = open(TOP, encoding='utf-8', errors='replace').read()
cfg = open(CFG, encoding='utf-8', errors='replace').read()
ae  = open(AE,  'rb').read().decode('latin-1')          # 混合编码，按字节看
ini = open(INI, encoding='utf-8', errors='replace').read()

res = []
def ck(cond, tag):
    res.append((bool(cond), tag))

# ---------- A. design_top_wrapper.v ----------
ck('wire        S_ae_req_all;' in top,            'A1 声明 wire S_ae_req_all')
ck('wire        S_tp_canary;' in top,             'A2 声明 wire S_tp_canary')
ck('assign S_ae_req_all = S_ae_req | S_gain_sw_req;' in top, 'A3 S_ae_req_all = AE算法请求 | 开关变化请求')
ck('assign S_tp_canary = ~(S_sw1_sync1 | S_sw2_sync1 | S_sw3_sync1 | S_sw4_sync1);' in top,
                                                  'A4 自检信号 = 四开关全"上"')
ck('.I_ae_req(S_ae_req_all),' in top,             'A5 例化用 S_ae_req_all')
ck('.I_test_pattern(S_tp_canary),' in top,        'A6 例化用 S_tp_canary')
ck(".I_test_pattern(1'b0)" not in top,            "A7 已无 .I_test_pattern(1'b0) 残留")
ck("S_boot_cnt == 25'd24_000_000" in top,         "A8 上电 1s 自检常量 25'd24_000_000 @24MHz")
ck("S_gain_dbcnt == 20'd240_000" in top,          "A9 去抖常量 20'd240_000 = 10ms @24MHz")
ck(len(re.findall(r"S_gain_sw_req\s*<=\s*1'b1;", top)) == 2,
                                                  'A10 两处触发：上电 1s + 开关变化去抖后')
ck('S_gain_applied != {S_sw3_sync1, S_sw4_sync1}' in top, 'A11 只在选择值变化时触发（不重复下发）')
ck('reg  [24:0] S_boot_cnt;' in top,              'A12 S_boot_cnt 位宽 25（24e6 需 25 bit）')
i_decl = top.index('wire        S_tp_canary;')
i_use  = top.index('.I_test_pattern(S_tp_canary),')
i_decl1= top.index('reg S_sw1_sync0, S_sw1_sync1;')
i_asg  = top.index('assign S_tp_canary =')
ck(i_decl < i_use,                                'A13 S_tp_canary 先声明后用于例化（避免 vlog-2730）')
ck(i_decl1 < i_asg,                               'A14 assign S_tp_canary 在 S_sw1_sync1 声明之后')
ck(top.count('S_ae_req_all') >= 3,                'A15 S_ae_req_all 至少 3 处（声明/assign/例化）')
ck('negedge S_rst_n' in top[i_asg-4000:i_asg],    'A16 触发逻辑在 S_24m_clk / S_rst_n 域（与 I2C 同步）')
ck('if (S_cam_cfg_done) begin' in top,            'A17 1s 计数器有 S_cam_cfg_done 门控')
ck('else if (S_gain_applied != {S_sw3_sync1, S_sw4_sync1}) begin' in top,
                                                  'A18 去抖分支挂在 boot 一次性之后（上电不会误触发）')

# ---------- B. uicfgcs500_720p.v ----------
ck("wire [15:0] rt_exposure     = 16'h07C6;" in cfg,      'B1 运行时曝光常量 0x07C6 = 1990')
ck("I_gain_high    ? 16'h1F3F : 16'h0F20" in cfg,          'B2 运行时模拟增益 15.750x / 4.000x')
ck("I_gain_digital ? 16'h0180 : 16'h0080" in cfg,          'B3 运行时数字增益 x2.000 / x1.000')
ck('.I_analog_gain      (rt_analog_gain),' in cfg,         'B4 AE 表接 rt_analog_gain')
ck('.I_exposure_time    (rt_exposure),' in cfg,            'B5 AE 表接 rt_exposure')
ck('.I_digital_gain     (rt_digital_gain),' in cfg,        'B6 AE 表接 rt_digital_gain')
ck('.I_test_pattern     (I_test_pattern)' in cfg,          'B7 AE 表接 I_test_pattern（自检）')
ck('.I_analog_gain      (gain_value)' not in cfg,          'B8 AE 表不再吃 SC500GainTbl 的封顶值')

# ---------- C. uics500regAE.v ----------
ck("assign\tREG_SIZE = 9'd8;" in ae,              'C1 AE 表 REG_SIZE = 8')
for a, d, t in [('3e00', "4'h0", '曝光高'), ('3e01', 'I_exposure_time[11: 4]', '曝光中'),
                ('3e02', 'I_exposure_time[3:0]', '曝光低'), ('3e08', 'I_analog_gain[15:8]', '模拟增益高'),
                ('3e09', 'I_analog_gain[7 :0]', '模拟增益低'), ('3e06', 'I_digital_gain[15:8]', '数字增益高'),
                ('3e07', 'I_digital_gain[7 :0]', '数字增益低'),
                ('4501', "I_test_pattern ? 8'hbc : 8'hb4", '测试图自检')]:
    ck((a in ae) and (d in ae), 'C2..C9 AE 表条目 %s (%s)' % (a, t))
ck('input      [15:0]  I_digital_gain,' in ae,    'C10 AE 表新增端口 I_digital_gain')
ck('input               I_test_pattern' in ae,    'C11 AE 表新增端口 I_test_pattern')

# ---------- D. init 表必须没被动过 ----------
ck("assign REG_SIZE = 9'd123;" in ini,            'D1 init 表 REG_SIZE 仍 = 123')
ck("I_gain_high ? 8'h1f : 8'h0f" in ini,          'D2 init 表模拟增益开关选值')
ck("I_gain_digital ? 8'h01 : 8'h00" in ini,       'D3 init 表数字增益开关选值')
ck("(TEST_PATTERN & I_test_pattern)" in ini,      'D4 init 表测试图用 &（恒 0xb4）')

ok = sum(1 for r, _ in res if r)
lines = ['==== verify_v3_rt_reload  (%d/%d PASS) ====' % (ok, len(res))]
for r, t in res:
    lines.append(('  [PASS] ' if r else '  [FAIL] ') + t)
txt = '\n'.join(lines) + '\n'
with open(OUT, 'w', encoding='utf-8') as f:
    f.write(txt)
print(txt)
print('FAIL 数 =', len(res) - ok)
