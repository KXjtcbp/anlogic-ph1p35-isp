# `_analysis/sim/awb/` —— 活档 AWB「前缀增益」缺陷取证台

本目录是一次分析性仿真（**没有改任何 RTL**）。目的：用 ModelSim 门级仿真证明
`proj\baseline\lab3\user_source\hdl_source\awb.v`（`camera_to_dsi_display.al` 里
唯一参与综合的那份 AWB）的除法器启动方式有缺陷。

## 1. 结论一句话

`awb.v` 把除法器的 `.start` 接成 `I_tvalid_r1`（每拍有效像素的电平），
而 `divider.ipc` 配的是 `<level_nu>50</level_nu>` + `<model_select>pipline</model_select>`
（完全流水）。门级实测：**`done` 在 1,1,0 图案下逐拍拉高**（4000 拍里 2667 拍高、
1334 个上升沿），于是 `else if(done[0]) in_r_r1 <= ...` 这个分支**每个有效像素都执行一次**，
`in_r_r1` 里装的是「到该拍为止的运行中前缀比值」，而不是整帧比值。

后果（空间不均匀画面）：**帧内竖直方向的色偏 + 平均校正量不足**。

## 2. 复现命令

```powershell
cd D:\harness\fpga\fpgacnds\_analysis\sim\awb
# 集合：真实 1,1,0 valid 图案 + 门级 divider，对着冻结的原始 RTL 跑
vsim -c -do run_awb_live_final.tcl > run_final2.log 2>&1
# 单独量门级 divider 的 done 节奏
vsim -c -do run_div_rate.tcl > run_div_rate.log 2>&1
```

脚本内容要点（`run_awb_live_final.tcl`）：

| 顺序 | 文件 |
|---|---|
| 1 | `_analysis/sim/awb/glbl.v`（本地 glbl stub） |
| 2 | `E:/anlu/sim_release/common/al_map_basic.v`、`al_map_lut.v`、`al_map_adder.v`、`al_map_seq.v` |
| 3 | `proj/baseline/lab3/user_source/ip_source/divider/divider_gate.v`（门级网表） |
| 4 | `_analysis/sim/awb/sim_blk_mem_gen_awb_delay_signal.v`（BRAM 行为级替身） |
| 5 | `proj/baseline/lab3/user_source/hdl_source/signal_delay.v` |
| 6 | `_analysis/sim/awb/awb_pristine_b60eb85.v`　← **被测 RTL 的冻结副本** |
| 7 | `_analysis/sim/awb/tb_awb_live_ratio.v` |

`vsim` 参数：`vsim -c -nolog -L work work.tb_awb_live_ratio work.glbl -do "run -all; quit -f"`
（`work.glbl` 必须显式给，因为 `al_map_basic.v` 引用 `glbl.gsrn`/`glbl.done_gwe`。）

## 3. ⚠ 为什么被测 RTL 用的是 `awb_pristine_b60eb85.v` 而不是工作区那份

`proj\baseline\lab3\user_source\hdl_source\awb.v` 在本次仿真的时间窗内
（2026-10-12 23:23~23:31）**被另一路同时修改**：加了 `in_r_nxt/in_b_nxt` 双缓冲、
把增益寄存器改成只在 `I_tuser` 沿切换。
同一套 TB、同一个 divider 网表，改前/改后跑出完全不同的数字
（改后三个 CASE 全 `R/G=2.5500`，`gainR=fffff` 饱和，因为 `0/0` 的全 1 商被钳到最大增益）。

所以取证必须钉住 RTL 快照：

* `awb_pristine_b60eb85.v` = `git b60eb85`（= HEAD）里那份 awb.v，**22055 B**，
  与 `_analysis/sim/awb_before/awb.v` 逐字节相同（未改动的原始版本）。
* 该副本里的缺陷写法见第 296~309 行：
  `if(!I_rst_n) in_r_r1 <= 20'h10000; else if(done[0]) in_r_r1 <= |in_r_x1[47:20] ? 20'hfffff : in_r_x1[19:0];`
  —— 没有 `I_tuser` 复位、没有双缓冲，`done[0]` 每拍覆盖。

重新生成冻结副本（幂等，不含破坏性操作）：

```powershell
cd D:\harness\fpga\fpgacnds
git cat-file blob b89f8b05c14fb15cd5df0337f3f9897d5bb27fdf | Out-File -Encoding utf8 _tmp.txt
# 再用 UTF8(no BOM) + CRLF 写回 _analysis/sim/awb/awb_pristine_b60eb85.v，得到 22055 B
```
（pwsh 的 `>` 重定向默认写 UTF-16LE，会把文件搞成两倍大且 vlog 解析不了，所以必须手工转码；
见 `extract_pristine.ps1`。）

## 4. 激励与用例

96 bit = 4 像素/拍，像素 i 占 `tdata[24*i+16 +: 8]=R`、`[24*i+8 +: 8]=G`、`[24*i +: 8]=B`。
每行 320 有效拍（=1280 像素 = `IMG_WIDTH`），行间空 2 拍，共 8 行，每帧 10240 像素；
`I_tuser` 只在该帧第 0 行第 0 拍拉高；`O_tready` 常高；时钟 `#8.3335`（≈60 MHz）。

| CASE | 上半 4 行 (R/G/B) | 下半 4 行 | 用途 |
|---|---|---|---|
| A | 80/100/90 | 80/100/90 | 均匀场对照（比值可精确表示，`gain_r=0x14000` 精确） |
| B | 100/100/100 | 60/100/90 | 空间不均匀；整帧 ΣR/ΣG 与 A 相同 |
| C | 81/100/91 | 81/100/91 | 均匀但增益不可精确表示，量化输出截断偏置 |

## 5. 实测数字（门级 divider，冻结原始 RTL，`run_final2.log`）

见 `run_final2.log`。要点（`outN` 收满 10240 才算整帧）：

* **CASE B**：输出 **R/G=0.8293**、B/G=0.9598；逐行分桶显示
  row0~2 = 100/100/100（R/G=1.0000，**增益还是 1.000x**）、row3 起才吃到非中性像素、
  后面几行 R/G 只有 0.6325 / 0.6863 / 0.7272 / 0.7594 —— 越靠近帧末越接近理想值，
  整帧仍是欠校正。理想（逐像素正确增益 1.25）应为 R/G=1.0000、`sumR=2,560,000`，
  实测 `sumR=743,096`。
* **CASE C**：输出 R 均值 = 99，G = 100 ⇒ `R/G=0.9900`，`mean R-G=-1`；
  增益只有 20 bit 且除法器余数被丢掉，`(81*80909)>>16 = 99.9999` 截断成 **99**。
* **CASE A**：`R/G=1.0000`（80×0.8→100 精确）但 `B/G=0.9900`（`gain_b` 同理被截断）。
* `div: vld_cyc=2560 done_hi=2560` ⇒ 每拍都 `done`。

## 6. divider 单独测（`run_div_rate.log`）

* 单拍 `start`：`first_done_cyc=73`（复位后再加几拍 idle，实际流水深度 ≈50）、`done_hi=1`。
* `start` 按 1,1,0 循环 4000 拍：**`done_hi=2667`（占 66%，正好等于占空）、`done_rise=1334`**，
  `quotient` 恒为 `0x14000`（81920，正确）。
  ⇒ `done` 跟随 `start` 逐拍拉高，不是「每 50 拍才更新一次」。

## 7. 已知坑

* vlog 不支持 `%+n.mf`；`%0.2d` 也不支持（`vlog-10557`，会被忽略，打印出 `0.          0`），
  只能用 `%02d`。
* `AWB_TB=both` 时 `run_awb_live*.tcl` 的第二段（div TB）**从不执行**：第一段 `vsim -do`
  跑完 `quit -f` 之后整条 vsim 进程就结束了，后面的 vlog/vsim 行没有机会跑。
  要两个 TB 就分两次调用 vsim（`run_div_rate.tcl` 单独一份就是为此）。
* 帧末 `repeat(DRAIN)` 必须 ≥ 2400 拍，否则最后一个输出行会被 `$display` 之后
  的 `$finish` 截掉（表现为 `outN=8960` 而不是 10240）。
* 门级 `divider_gate.v` 有 55k 实例，一次装载+跑 ≈7 分钟（Intel Starter 版会警告超容量）；
  实测 `Errors: 0`，423 条 `[TFMPC] Missing connection for port ...` 是原语悬空端口的噪声，无害。
* 本目录的 `work`/`work_div`/`*.log`/`*_pristine_*.v` 都是分析产物，不要提交 git。

## 8. 文件清单

| 文件 | 说明 |
|---|---|
| `tb_awb_live_ratio.v` | 主 TB：3 个 CASE、逐行分桶、done 计数、诊断打印 |
| `tb_div_done_rate.v` | 只用 divider 量 done 节奏 |
| `run_awb_live_final.tcl` | **推荐复现入口**（冻结 RTL + 门级 divider） |
| `run_awb_live_pristine.tcl` | 同上，main+div 两个 TB（第二段会不执行，见坑） |
| `run_div_rate.tcl` | 单独跑 divider 节奏 TB |
| `run_awb_live.tcl` | 原始脚本，被测 RTL 仍是工作区那份（会被同时修改影响） |
| `divider_behav.v` | 行为级 divider 替身（同端口/同 50 拍流水）。**本次没用它** |
| `awb_pristine_b60eb85.v` | 冻结的被测 RTL（git b60eb85，22055 B） |
| `extract_pristine.ps1` | 从 git 重新导出上面那份副本 |
| `run_*.log` | 各次实跑日志（`run_final2.log` 是最终数字） |
