#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
[HDR-2026-10-10] 应用"传感器 AGC 使能 + 增益档选择 + 测试图开关"改动。
只在 3 个文件里做「追加式」改动，不动任何现有逻辑：
  1) user_source/hdl_source/uics500_cfg/uics500reg_720p60.v  —— 加 2 个输入端口、REG_SIZE 117→120、追加索引 117/118/119
  2) user_source/hdl_source/uics500_cfg/uicfgcs500_720p.v    —— 加 2 个输入端口、例化时接过去
  3) user_source/hdl_source/design_top_wrapper.v             —— SW3/SW4 同步器 + 接到 uicfgcs500_720p + 修正极性注释
所有文件保持原编码(UTF-8 无 BOM)与原换行符。运行前自动备份为 *.bak_20261010_agc
"""
import os, shutil, sys, difflib

ROOT = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
F_TBL  = os.path.join(ROOT, r'uics500_cfg\uics500reg_720p60.v')
F_CFG  = os.path.join(ROOT, r'uics500_cfg\uicfgcs500_720p.v')
F_TOP  = os.path.join(ROOT, r'design_top_wrapper.v')

BAK = '.bak_20261010_agc'


def load(p):
    b = open(p, 'rb').read()
    t = b.decode('utf-8')                      # 三个文件都是 UTF-8 无 BOM
    nl = '\r\n' if '\r\n' in t else '\n'
    return t.split(nl), nl, t


def save(p, lines, nl, orig):
    new = nl.join(lines)
    assert new != orig, '没有产生任何改动: ' + p
    if not os.path.exists(p + BAK):
        shutil.copy2(p, p + BAK)
    open(p, 'wb').write(new.encode('utf-8'))
    d = list(difflib.unified_diff(orig.splitlines(), new.splitlines(),
                                  'a/' + os.path.basename(p), 'b/' + os.path.basename(p), lineterm='', n=2))
    print('\n'.join(d))
    print('--- %s : 写入 %d 字节 (备份 %s) ---\n' % (os.path.basename(p), len(new.encode('utf-8')), os.path.basename(p) + BAK))


def find1(lines, sub, start=0):
    hit = [i for i, l in enumerate(lines) if sub in l and i >= start]
    assert len(hit) == 1, '锚点 %r 命中 %d 次: %r' % (sub, len(hit), hit)
    return hit[0]


# ============================ 1) 传感器寄存器表 ============================
lines, nl, orig = load(F_TBL)

i = find1(lines, 'output reg [31:0] REG_DATA,')
lines[i:i] = [
    '    input             I_test_pattern,   // SW3：1 = 打开 Sensor 灰度递增测试图（0x4501 Bit[3]=1 → 0xbc）',
    '    input             I_gain_high,      // SW4：1 = 模拟增益高档 11.25×（0x1f/0x2d）；0 = 低档 4.000×（0x0f/0x20）',
]

i = find1(lines, "assign REG_SIZE = 9'd117;")
lines[i] = ("assign REG_SIZE = 9'd120;   // 原有 0..116 共 117 条 + 本次追加 117/118/119 共 3 条 = 120 条")

i = find1(lines, "116: REG_DATA={16'h4501,")
lines[i] = ("        116: REG_DATA={16'h4501, (TEST_PATTERN | I_test_pattern) ? 8'hbc : 8'hb4};")

add = [
    '        // ---- [HDR-2026-10-10] AGC 控制位（手册表2-3 p24 / §2.2.3）★本次唯一功能性改动★ ----',
    "        //   手册原文：「SC500CS AGC 控制方法：将寄存器 16'h3e03 的 Bit[3:0] 设置为 4'hb」",
    '        //   本表（= 官方 lab_ex1/2/3 的 720p60 原表，逐条比对只差索引 112/113）从来没有写过 0x3e03',
    '        //   ⇒ 疑似 0x3e08/0x3e09 的增益值被传感器忽略、停在默认档（≈1×）。',
    '        //   ★追加而不是插队：索引 115 是 uicfgcs500_720p.v:72 硬编码的"stream on 后延时"触发点，',
    '        //     一旦整体后移就会丢延时，所以新条目一律排在表尾。',
    "        117: REG_DATA={16'h3e03,8'h0b};",
    '        // ---- 在 0x3e03 使能之后再重写一遍模拟增益，确保"使能后"的值被采纳（值本身不变）----',
    '        //   SW4 拨上 = 高档 11.25×（0x1f/0x2d，2026-10-08 起的现值）；',
    '        //   SW4 拨下 = 低档 4.000×（0x0f/0x20，厂商原值）——复位默认就是它（同步器复位值 1，顶层取反）。',
    "        118: REG_DATA={16'h3e08, I_gain_high ? 8'h1f : 8'h0f};",
    "        119: REG_DATA={16'h3e09, I_gain_high ? 8'h2d : 8'h20};",
]
i = find1(lines, "116: REG_DATA={16'h4501,")
lines[i + 1:i + 1] = add

# 顶部注释同步
i = find1(lines, 'REG_SIZE 必须等于表内 case 条目总数')
lines[i] = ('// 综合/实现 : ■ REG_SIZE 必须等于表内 case 条目总数（当前 9\'d120，索引 0..119）；追加条目只需改 REG_SIZE + 加一条 case，'
            '且必须追加在表尾（索引 115 被 uicfgcs500_720p.v:72 硬编码为延时触发点）。')
i = find1(lines, '2026-10-08  （未提交）索引 113')
lines.insert(i + 1, '//   2026-10-10  （未提交）追加索引 117 `{3e03,0x0b}`（手册要求的 AGC 控制位）；118/119 在使能后重写模拟增益，'
                    '由 SW4 选 4.000×(0x0f/0x20，默认) / 11.25×(0x1f/0x2d)；索引 116 的测试图改为 SW3 运行时可选')
save(F_TBL, lines, nl, orig)

# ============================ 2) 传感器配置 FSM ============================
lines, nl, orig = load(F_CFG)

i = find1(lines, 'input  wire [15:0] I_analog_gain,')
lines[i + 1:i + 1] = [
    '    input  wire        I_test_pattern,   // SW3：1 = 传感器灰度递增测试图（0x4501=0xbc）',
    '    input  wire        I_gain_high,      // SW4：1 = 模拟增益 11.25×；0 = 4.000×',
]

i = find1(lines, '.REG_SIZE  (init_size)')
lines[i + 1:i + 1] = [
    '    .I_test_pattern (I_test_pattern),',
    '    .I_gain_high    (I_gain_high)',
]
save(F_CFG, lines, nl, orig)

# ============================ 3) 顶层 wrapper ============================
lines, nl, orig = load(F_TOP)

i = find1(lines, 'uicfgcs500_720p #(')
blk = [
    '    // ---- [HDR-2026-10-10] SW3 / SW4（24MHz 域 2 级同步）----------------------------',
    '    //   实测极性（与手册相反）：拨下 = 逻辑 1，拨上 = 逻辑 0。',
    '    //   SW3：拨上 = 打开传感器灰度递增测试图（手册表2-10：0x4501 Bit[3]=1）；拨下/复位 = 正常图像。',
    '    //        ★测试图寄存器只在开机那张初始化表里写一次 ⇒ 拨动 SW3 后必须复位或断电重启才生效。',
    '    //   SW4：拨上 = 模拟增益高档 11.25×；拨下/复位 = 低档 4.000×（厂商原值，安全默认）。',
    '    //        同样只在开机初始化时下发 ⇒ 换档后需复位/断电重启。',
    '    reg S_sw3_sync0, S_sw3_sync1;',
    '    reg S_sw4_sync0, S_sw4_sync1;',
    '    always @(posedge S_24m_clk or negedge S_rst_n) begin',
    '        if(!S_rst_n) begin',
    "            S_sw3_sync0 <= 1'b1;",
    "            S_sw3_sync1 <= 1'b1;",
    "            S_sw4_sync0 <= 1'b1;",
    "            S_sw4_sync1 <= 1'b1;",
    '        end',
    '        else begin',
    '            S_sw3_sync0 <= I_switch[2];',
    '            S_sw3_sync1 <= S_sw3_sync0;',
    '            S_sw4_sync0 <= I_switch[3];',
    '            S_sw4_sync1 <= S_sw4_sync0;',
    '        end',
    '    end',
    '    wire S_test_pattern = ~S_sw3_sync1;   // 复位默认 0 = 正常图像（安全默认）',
    '    wire S_gain_high    = ~S_sw4_sync1;   // 复位默认 0 = 4.000×（厂商原值，安全默认）',
    '',
]
lines[i:i] = blk

i = find1(lines, '.O_cfg_done(S_cam_cfg_done)')
lines[i:i] = [
    '      .I_test_pattern(S_test_pattern),   // [HDR-2026-10-10] SW3：灰度递增测试图',
    '      .I_gain_high(S_gain_high),         // [HDR-2026-10-10] SW4：模拟增益 4.000×/11.25×',
]

i = find1(lines, '拨上为')
lines[i] = ('    //     手册原文：「SW1-SW4 是作为与 FPGA 的 IO 输入信号，拨上为"1"，拨下为"0"」\n'
            '    //   ★2026-10-10 实测极性相反：【拨下 = 逻辑 1】【拨上 = 逻辑 0】（用 2×2 开关对照图确认）')

i = find1(lines, 'SW3/SW4 暂未使用')
lines[i] = ('    //   SW3(E11) = 传感器灰度递增测试图：拨上 = 打开（0x4501=0xbc）；拨下/复位 = 正常图像\n'
            '    //   SW4(D11) = 模拟增益档：拨上 = 11.25×（0x1f/0x2d）；拨下/复位 = 4.000×（0x0f/0x20）\n'
            '    //   ★SW3/SW4 都只在开机初始化表里下发一次 ⇒ 拨动后需复位或断电重启才生效。')

i = find1(lines, '拨上=1=【旁路】=')
lines[i] = '//   ★实测极性（与手册相反）：拨下 = 1 = 【旁路】= 加黑电平扣除 / S 曲线之前的老行为（最亮）；拨上 = 0 = 启用新功能。'
save(F_TOP, lines, nl, orig)

print('全部改动完成。')
