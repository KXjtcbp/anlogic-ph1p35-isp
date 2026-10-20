# -*- coding: utf-8 -*-
"""把 _analysis/黑电平校正_模块A方案与验收_20261011.md 第 6 节的"内嵌陈旧源码"
   换成"实测证据 + 踩坑清单 + 指向真实文件"。按行号切割，避免大段字符串匹配。
"""
import io, os, sys

DOC = r"E:\FPGA\_analysis\黑电平校正_模块A方案与验收_20261011.md"

NEW = u"""\
> **本节的源码不在这里重复粘贴** —— 唯一权威版本是
> `_analysis/sim/blc_gamma/tb_blc_template.v`（270 行）。文档里贴代码必然与文件
> 脱节，上一版就是因此过时（贴出去的还是字段顺序写反的版本）。
> 交付时以文件为准，本节只记录**验证结论**和**必须避开的四个坑**。

### 6.1 实测结论（2026-10-11 14:52，ModelSim ASE）

运行方式（PowerShell，逐条调用 exe；**不要写 .bat**）：

```powershell
$MS = "E:\\modelsim\\modelsim_ase\\win32aloem"
mkdir E:\\FPGA\\_analysis\\sim\\blc_gamma\\run_tb -Force
cd E:\\FPGA\\_analysis\\sim\\blc_gamma\\run_tb
& "$MS\\vlib.exe" work                       # ★ 必须先建库，否则 (vlog-19) ENOENT
& "$MS\\vlog.exe" "E:\\FPGA\\proj\\baseline\\lab3\\user_source\\hdl_source\\isp\\demosaic_4x_2_0\\mipi_to_raw_converter.v" "E:\\FPGA\\_analysis\\sim\\blc_gamma\\tb_blc_template.v"
& "$MS\\vsim.exe" -c -do "run -all; quit -f" tb_blc_template
```

实测输出（完整日志 `_analysis/out/_tb_blc_template.log`）：

```
# Errors: 0, Warnings: 0
# ==========================================================
# [CASE 1] reset ............... ok
# [CASE 2] 11 anchors .......... ok
# [CASE 3] full sweep (4096) ... ok
# [CASE 4] bypass == v>>2 ...... ok
# [CASE 5] field independence .. ok
# [CASE 6] hot bypass switch ... ok
# ==========================================================
#  ALL PASS, errors=0
# End time: 14:52:58 on Oct 11,2026
```

**编译 0 错误 0 警告、仿真 ALL PASS errors=0** —— 这是模块 A 可以上板的前提。
注意 CASE 3 的 4096 = 0…1023 全量扫描 × 4 个像素字段，等价于把整条
`clamp → +2 → >>2` 通路穷举了一遍，不是抽样。

### 6.2 ★四个必须避开的坑（TB 侧，全部实际踩过）★

**坑 1：40 bit 字面量写 12 个十六进制位会被静默截断。**
`40'h0A2_13F_001_3FF`（12 位十六进制 = 48 bit）不会报错，只在编译时给一句
`(vlog-2600) [RDGN] - Redundant digits in numeric literal`，然后**悄悄丢掉高 8 位**。
第一版 TB 因此产生 1029 个 FAIL，看起来像 DUT 算错。
⇒ 40 bit 一律写成 4 个 10 bit 拼接：`{10'h0A2, 10'h13F, 10'h001, 10'h3FF}`。
10 bit 字段的位宽在源码里一眼可数，不会写错。

**坑 2：参考模型的字段顺序与 DUT 相反。**
DUT 是

```verilog
raw_data_r0 <= {S_blk_f0[9:2], S_blk_f1[9:2], S_blk_f2[9:2], S_blk_f3[9:2]};
```

而 `S_blk_f0` 取自 `I_raw_tdata[9:0]`（**最低位**字段）。
⇒ **输出的最高字节对应最低的输入字段**。TB 必须写

```verilog
exp4 = { exp_one(v[ 9: 0], byp), exp_one(v[19:10], byp),
         exp_one(v[29:20], byp), exp_one(v[39:30], byp) };
```

写反的症状是**逐字节镜像**：`got=f200ee13 exp=13ee00f2`。
它看起来像"全错"，其实是顺序问题 —— 如果只盯着一个字段调试会浪费很多时间。

**坑 3：NBA 采样 —— 只写 `@(posedge clk)` 会读到上一拍。**
`@(posedge clk)` 在 active region 就恢复执行，而 DUT 的 `raw_data_r0 <= ...`
是 NBA，要到**同一时间步的 NBA region** 才更新。于是 TB 读到的是上一拍的值。
危害最隐蔽的地方在于：**数据不变时"看起来是对的"**（因为上一拍的值恰好相同），
只有某个拍真的发生变化时才暴露 —— 例如 CASE 6 热切换 bypass 报
`FAIL hot-switch(1) got=f2f2f2f2 exp=ffffffff`，而 CASE 1–5 全过。
⇒ 采样一律写 `@(posedge clk); #1;`。

**坑 4：不要用 `.bat` 包 ModelSim 命令。**
写一个含中文注释的 UTF-8 `.bat` 再 `cmd /c` 跑，cmd 完全不认 UTF-8，
会把注释里的汉字拆成单字节命令，报一屏
`'o' is not recognized as an internal or external command` /
`'work\\' is not recognized` / `The system cannot find the path specified.`，
真正的错误被淹没。⇒ 直接在 PowerShell 里依次调用 `.exe`。

### 6.3 TB 覆盖判据

每条都必须 0 错误才算模块 A 通过：

1. 复位后输出确定（无 X）
2. 11 个手算锚点，特别是 **56 / 57 / 58 三点**（`BLACK_LEVEL` 边界）
3. 0…1023 全量扫描 × 4 字段 = 4096 个值
4. `bypass=1` 时**逐位等于** `v >> 2`（等同回退到 10-09 版本）
5. 四个像素字段互不串扰
6. 运行时热切换 bypass 立即生效、拍数不变

### 6.4 DUT 端口清单（写 TB 时直接照抄）

```
mipi_to_raw_converter
  I_clk, I_rst_n, I_blk_bypass
  I_raw_tdata[39:0], I_raw_tdest[9:0], I_raw_tlast, I_raw_tvalid, I_raw_tuser
  output I_raw_tready                       // ★ 注意是 output（无反压命名）
  output O_raw_tdata[31:0], O_raw_tlast, O_raw_tvalid, O_raw_tuser
  input  O_raw_tready                       // ★ 注意是 input
```

★ `I_raw_tdest[9:0]` 容易被漏掉，TB 里接 `10'd0` 即可 ★
（这一组反向命名是原厂 `edge_detect_96.v` 的风格，`isp/isp_top.v` 里所有模块都这样。）

---

"""

with io.open(DOC, "r", encoding="utf-8", newline="") as f:
    lines = f.readlines()

# 定位：从 '## 6. Testbench 模板' 之后，到 '**TB 覆盖判据**' 之前，全部替换
try:
    i6 = next(i for i, l in enumerate(lines) if l.startswith(u"## 6. Testbench"))
    icrit = next(i for i, l in enumerate(lines) if l.startswith(u"**TB \u8986\u76d6\u5224\u636e**"))
except StopIteration as e:
    print("ANCHOR-NOT-FOUND", e); sys.exit(1)

head = lines[:i6 + 2]          # 含 '## 6.' 行与其后一个空行
tail = lines[icrit:]           # 从判据行起（判据已在 NEW 里重写，丢掉）
# 丢掉 NEW 里已重写的判据段：找到 tail 中 '---' 之后
# 简单做法：tail 从判据行开始，跳过到下一个 '---' 行之后
for k, l in enumerate(tail):
    if l.strip() == "---":
        tail = tail[k + 1:]
        break

new_lines = head + [NEW] + tail

with io.open(DOC, "w", encoding="utf-8", newline="") as f:
    f.writelines(new_lines)

print("OK  old span lines %d..%d replaced" % (i6 + 1, icrit + 1))
print("    new line count = %d" % len(new_lines))
