# 2026-10-18_rowfix —— obj_detect 行计数器根因修复版

## 本版修的是什么（一句话）
`obj_detect.v` 把 `I_tlast` 当成“行末”，但 AXI4-Stream 视频包里它是“帧末”——一帧只来一次。
于是 `S_lyc`/`S_byn` 变成“每帧 +1”，一个帧内 `S_byn` 恒定，掩码只写同一行；
跨 720 帧轮完 9 行后，画面上就看到“一整列贯穿全帧、跟着笔走”的绿框。

## 改动清单（全部在 proj/baseline/lab3/user_source/hdl_source/isp/obj_detect.v）
1. 行/帧事件分离：`S_row_end = (S_bx == H_BEATS-1)`；`I_tlast` 只当帧末。
2. 计数推进改由 `S_row_end` 驱动（`S_y`/`S_bxc`/`S_bxn`/`S_lyc`/`S_byn`）。
3. 累加区间改为整块 80x80（`S_blk_end = S_beat_last & S_lyc_last`），掩码只在块末写。
4. 恢复两帧确认（`S_now & S_prev`），帧末合成。
5. 恢复 9 位扩位比较 `{1'b0,R} >= {1'b0,G} + CHR_MIN`，杜绝 8bit 减法回绕。
6. `O_obj_any` 在帧末由新掩码决定；`blk_cnt` 去掉重复条件。

## 数值（本版）
- Setup WNS **+110 ps** / S-EP 0；Hold WNS **+20 ps** / H-EP 0
- `#slices 17069 / 21216 = 80.45%`；`#lut6 15978 = 75.31%`；`#reg 11965`；`#eram 51/108`；`#dsp 10/40`
- `u_obj_detect` = 574 LUT / 220 ripple / 694 FF / 0 ERAM / 0 DSP
- `camera_to_dsi_display.bit` 1789539 B `md5 FF811C1A27A9B86DBDAC5187F666AE32`
- `compile_check` 42/43（唯一失败是 ph1p35_ddr 黑盒保护，既有）
- `HDL-8007` = 0

## 回滚
上一版 `proj\releases\2026-10-17_contour\camera_to_dsi_display.bit`。