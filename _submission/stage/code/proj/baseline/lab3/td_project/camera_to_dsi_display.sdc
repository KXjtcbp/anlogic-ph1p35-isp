create_clock -name {sys_clk_50m} -period 20.000 -waveform {0.000 10.000} [get_ports {I_sys_clk}]
create_clock -name {mipi_rx_ck_pad} -period 4.167 -waveform {0.000 2.083} [get_nets {IO_rx_clk_pad_p}]

derive_clocks

rename_clock -name {pll_clk_100m} [get_clocks {u_PLL/ph1p_phy_pll_wrapper_25a56e5ce2f9_Inst/u_PH1P_PHY_PLL.clkc[0]}]
rename_clock -name {pll_clk_24m} [get_clocks {u_PLL/ph1p_phy_pll_wrapper_25a56e5ce2f9_Inst/u_PH1P_PHY_PLL.clkc[1]}]
rename_clock -name {HDMI_PIXEL_CLK} [get_clocks {u_PLL/ph1p_phy_pll_wrapper_25a56e5ce2f9_Inst/u_PH1P_PHY_PLL.clkc[4]}]
rename_clock -name {HDMI_SERIAL_CLK} [get_clocks {u_PLL/ph1p_phy_pll_wrapper_25a56e5ce2f9_Inst/u_PH1P_PHY_PLL.clkc[5]}]

rename_clock -name {MIPI_RX_BYTE_CLK} [get_clocks {u_mipi_dphy_rx_ph1p_mipiio_wrapper/u_ph1p_mipiio_rx_wrapper/u_PH1P_LOGIC_DPHY_MIPI_RX.o_fabric_div4_8_clk}]


set_clock_groups -asynchronous \
    -group [get_clocks {mipi_rx_ck_pad MIPI_RX_BYTE_CLK}] \
    -group [get_clocks {sys_clk_50m pll_clk_100m pll_clk_24m HDMI_PIXEL_CLK HDMI_SERIAL_CLK}] \
    -group [get_clocks {u_ph1p35_324_ddr_wrapper/u_ddr2/ddr_clk u_ph1p35_324_ddr_wrapper/u_ddr2/usr_clk}]

# ============================================================
# [CDC-FIX 2026-10-04] 24MHz key domain -> HDMI pixel domain, single-bit toggle CDC
# Sole remaining setup violation: u_key_mode_ctrl/O_mode_reg[*] ->
#   u_hdmi_mixer/S_algo_tgl_sync{1,2}_reg, Slack -0.020ns, Logic Level = 0,
#   Data Path Delay 0.444ns (cell 0.204 + net 0.240).
# Cause: the 24MHz launch edge happens to fall 0.653ns before a pixel-clock
#   capture edge, so the tool uses that edge pair as the setup budget
#   (0.653ns) -- smaller than the macro's intrinsic clk-to-Q + setup.
#   Source flop -> first sync flop is metastability-tolerant by design and
#   must not be checked as a single-cycle synchronous path.
# Fix: -datapath_only drops clock jitter/skew/pessimism and constrains only
#   Clk-to-Q + net delay + setup. 8.000ns is a deliberate bound (24MHz period
#   41.667ns, pixel period 13.333ns): it clears the false violation while
#   still flagging any real long routing detour.
#   -datapath_only is supported only by set_max_delay (SWUG105 4.4.21).
# ============================================================
set_max_delay -datapath_only -from [get_clocks {pll_clk_24m}] -to [get_clocks {HDMI_PIXEL_CLK}] 8.000

# ============================================================
# [AE 2026-10-12] ae_stat(60MHz ISP 域) -> ae_ctrl(24MHz) 准静态多 bit CDC
# ae_stat 挂在 isp_top 里 awb 的输入侧，输出 5 组信号：
#   O_luma_sum[39:0] / O_pix_cnt[31:0] / O_hi_cnt[31:0] / O_lo_cnt[31:0] / O_frame_tgl
# 每帧只更新一次、之后保持约 16.7ms（60Hz）不变，属于准静态总线；
# ae_ctrl 用 O_frame_tgl 的单 bit 翻转沿（内部 2 级同步 + 边沿检测）去采样数据，
# 采样时刻比数据变化晚 3 个 24MHz 周期（125ns），远小于 16.7ms 的保持时间。
# 这里只用 set_max_delay 给这条跨域总线一个上界（20ns），避免出现超长绕线；
# 两组时钟已在上面 set_clock_groups -asynchronous 里声明互不相关，故不再做单周期检查。
# ============================================================
set_max_delay -datapath_only -from [get_clocks {MIPI_RX_BYTE_CLK}] -to [get_clocks {pll_clk_24m}] 20.000

