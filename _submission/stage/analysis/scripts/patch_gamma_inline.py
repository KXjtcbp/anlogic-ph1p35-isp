# -*- coding: utf-8 -*-
"""
把 isp_gamma.v 的 ROM 初始化从 $readmemh 改成「表内容内联在 RTL 里」。

为什么必须改：
  TD 综合时的工作目录 = run 目录（..._Runs\\syn_1，见 run.bat 里的 cd /d "%~dp0"），
  相对路径的 gamma_lut_p118_k125.hex 在那里找不到 ⇒ 静默退化成 y=x 直通
  ⇒ 上板后 S 曲线完全不生效（而且没有任何报错）。

做法：只内联 mem_b00 的 256 个初值，其余 11 张表用 for 循环复制 ⇒ 12 路严格同表。
表内容来自 E:\\FPGA\\_analysis\\lut\\gamma_lut_p118_k125.hex（gen_gamma_lut.py 生成）。
"""
import io, os, shutil, sys

HEX = r'E:\FPGA\_analysis\lut\gamma_lut_p118_k125.hex'
SRC = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source\isp\isp_gamma.v'
BAK = SRC + '.bak_20261010_readmemh'

raw = io.open(HEX, 'r', encoding='utf-8').read().split()
assert len(raw) == 256, 'hex file must have 256 lines, got %d' % len(raw)
tbl = [int(x, 16) for x in raw]
assert tbl[0] == 0 and tbl[118] == 118 and tbl[255] == 255
assert all(tbl[i] <= tbl[i + 1] for i in range(255)), 'table must be monotonic'

lines = []
lines.append('//=============================================================================')
lines.append('// 2. 初始化：★表内容直接内联在 RTL 里（自包含，不依赖任何外部文件）★')
lines.append('//    ★为什么不 $readmemh★ —— TD 综合时的工作目录是 run 目录')
lines.append('//      （..._Runs\\syn_1，见 run.bat 的 `cd /d "%~dp0"`），')
lines.append('//      相对路径的表文件在那里根本找不到，而且【不报错】，只会静默退化成')
lines.append('//      y=x 直通 ⇒ 上板后 S 曲线完全不生效。内联表没有任何路径依赖，')
lines.append('//      仿真 / 综合 / 上板三者结果必然一致。')
lines.append('//    表内容 = gamma_lut_p118_k125.hex（gen_gamma_lut.py 生成，已逐条核对）；')
lines.append('//      曲线 x<=P: y=P*(x/P)^A / x>P: y=P+(255-P)*(1-((255-x)/(255-P))^B)，')
lines.append('//      P=118, A=B=1.25（中等档）。')
lines.append('//    只写 mem_b00 的 256 个初值，其余 11 张表在下面用 for 循环整体复制')
lines.append('//      ⇒ 12 路严格同表（也就绝不会出现通道间色调不一致）。')
lines.append('//=============================================================================')
lines.append('integer k;')
lines.append('initial begin')
lines.append('    //---- mem_b00[0..255]：S 曲线表（每行 4 个）----')
for i in range(0, 256, 4):
    row = '    '
    for j in range(4):
        row += 'mem_b00[%3d] = 8\'h%02x;' % (i + j, tbl[i + j])
        if j != 3:
            row += ' '
    lines.append(row)
lines.append('    //---- 其余 11 张表整体复制 mem_b00（12 路严格同表）----')
lines.append('    for (k = 0; k < 256; k = k + 1) begin')
lines.append('        mem_b01[k] = mem_b00[k];   mem_b02[k] = mem_b00[k];   mem_b03[k] = mem_b00[k];')
lines.append('        mem_b04[k] = mem_b00[k];   mem_b05[k] = mem_b00[k];   mem_b06[k] = mem_b00[k];')
lines.append('        mem_b07[k] = mem_b00[k];   mem_b08[k] = mem_b00[k];   mem_b09[k] = mem_b00[k];')
lines.append('        mem_b10[k] = mem_b00[k];   mem_b11[k] = mem_b00[k];')
lines.append('    end')
lines.append('end')
lines.append('')
newblock = '\n'.join(lines) + '\n'

txt = io.open(SRC, 'r', encoding='utf-8', newline='').read()
nl = '\r\n' if '\r\n' in txt else '\n'
flat = txt.replace('\r\n', '\n')

a = flat.index('// 2. 初始化')
b = flat.index('// 3. 第 1 级')
old = flat[a:b]
assert '$readmemh' in old and old.count('end') >= 1, 'unexpected section 2'

out = flat[:a] + newblock + flat[b:]
if nl == '\r\n':
    out = out.replace('\n', '\r\n')

if not os.path.exists(BAK):
    shutil.copy2(SRC, BAK)
io.open(SRC, 'w', encoding='utf-8', newline='').write(out)

print('patched: %s' % SRC)
print('  backup: %s' % BAK)
print('  old section2 %d chars -> new %d chars' % (len(old), len(newblock)))
print('  file %d -> %d bytes' % (len(txt), len(out)))
print('  table[0]=%d table[16]=%d table[64]=%d table[118]=%d table[200]=%d table[255]=%d'
      % (tbl[0], tbl[16], tbl[64], tbl[118], tbl[200], tbl[255]))
