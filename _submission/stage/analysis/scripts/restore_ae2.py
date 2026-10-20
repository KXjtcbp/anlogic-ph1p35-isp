# -*- coding: utf-8 -*-
# 内容说明：把 2026-10-10 误清空的 uics500regAE.v 恢复出来并打上 2026-10-10d 补丁。
#   来源 = E:\FPGA\_analysis\reports\ae_restored_orig.txt（从 ae_dump.txt 逐行反转义重建，已与
#   原厂副本 E:\FPGA\官方资料\2_Example\32_cs500_mipi_hdmi\src\uics500_cfg\uics500regAE.v
#   逐行比对：代码行只差 2026-10-09 的改名，其余完全一致）。
#   头部注释块被 splitlines() 拆坏过，这里用干净重写版替换；`timescale 之后（原厂 ASCII 部分
#   + 模块体）逐字保留，只加 2026-10-10d 的三处改动。
#   写盘用 临时文件 + os.replace，绝不允许先截断目标文件。
import os

TGT = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source\uics500_cfg\uics500regAE.v'
SRC = r'E:\FPGA\_analysis\reports\ae_restored_orig.txt'

orig = open(SRC, 'r', encoding='utf-8').read()          # latin-1 视图字符串（每字符 < 256）
tail = orig[orig.index('`timescale'):]                  # 原厂 ASCII 部分 + 模块体

# ---- 施加补丁（模块体）----
a = 'input      [15:0]  I_analog_gain\n);'
assert tail.count(a) == 1, ('port anchor', tail.count(a))
tail = tail.replace(a,
    'input      [15:0]  I_analog_gain,\n'
    'input      [15:0]  I_digital_gain,      // [2026-10-10d] 16bit digital gain = {3e06, 3e07}\n'
    'input               I_test_pattern       // [2026-10-10d] 1 = write 0x4501 = 0xbc (gray ramp, runtime self-check)\n);')
a2 = "assign\tREG_SIZE = 9'd5;"
assert tail.count(a2) == 1, ('size anchor', tail.count(a2))
tail = tail.replace(a2, "assign\tREG_SIZE = 9'd8;      // [2026-10-10d] 5 -> 8: + 3e06 / 3e07 / 4501")
a3 = "I_analog_gain[7 :0]};"
assert tail.count(a3) == 1, ('case anchor', tail.count(a3))
tail = tail.replace(a3, a3 + '\n'
    "\t\t5:\tREG_DATA = {16'h3e06, I_digital_gain[15:8]};\n"
    "\t\t6:\tREG_DATA = {16'h3e07, I_digital_gain[7 :0]};\n"
    "\t\t7:\tREG_DATA = {16'h4501, I_test_pattern ? 8'hbc : 8'hb4};")

HEADER = '''//=============================================================================
// [HDR-2026-10-09] 文件      : uics500regAE.v
// 模块      : uics500regAE
// 功能      : 运行时的曝光/增益寄存器表：把 16bit 曝光、16bit 模拟增益、16bit 数字增益
//             拆成逐条 I2C 写（3e00/3e01/3e02 曝光，3e08/3e09 模拟增益，3e06/3e07 数字增益），
//             外加 0x4501 一条用于"运行时写通路自检"。
// 数据通路  : I_exposure_time / I_analog_gain / I_digital_gain / I_test_pattern
//             -> 按 REG_INDEX 拆位 -> REG_DATA
// 时钟/复位 : 组合逻辑（always @(*) case）；无时钟。
// 依赖      : 被 uicfgcs500_720p.v 例化
//             （.I_exposure_time / .I_analog_gain / .I_digital_gain / .I_test_pattern）
// 综合/实现 : ■ 曝光 16bit 拆成 3e00[3:0]/3e01[7:0]/3e02[7:4]；
//             模拟增益 16bit 拆成 3e08[7:0]/3e09[7:0]；数字增益 16bit 拆成 3e06[7:0]/3e07[7:0]。
//           ■ 本表只在"运行时"下发（uicfgcs500_720p 的 AE 分支）；上电初始化走
//             uics500reg_720p60 的 init 表。init 表只在复位/上电后走一遍，所以
//             开关选值的寄存器必须靠本表在运行时补发（见 design_top_wrapper.v 的 2026-10-10d 段）。
//           ■ 2026-10-10d：模拟增益不再经过 SC500GainTbl（该表只有索引 0..73，封顶 ≈4.28×），
//             改由 uicfgcs500_720p.v 直接给出寄存器原始字节。
//-----------------------------------------------------------------------------
// 修改记录  :
//   2026-09-27  [230f479] 导入官方 lab3 基线（Milianke 参考例程）
//   2026-10-09  （未提交）标识符改名 7 处：I_AE/I_AG -> I_exposure_time/I_analog_gain
//   2026-10-10d 运行时表由 5 条扩到 8 条：新增 3e06/3e07（数字增益）与 4501（灰度递增
//             测试图自检）；REG_SIZE 5->8。目的：SW3/SW4 拨动后无需断电重启即可生效。
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑，见 E:\\FPGA\\_analysis\\reports\\rename_report.txt）
//=============================================================================
'''

final = HEADER.encode('utf-8').decode('latin-1') + tail
data = final.encode('latin-1')

tmp = TGT + '.tmp'
open(tmp, 'wb').write(data)
os.replace(tmp, TGT)
print('restored+patched ->', TGT, len(data), 'bytes')
