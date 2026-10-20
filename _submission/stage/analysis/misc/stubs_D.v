//=============================================================================
// 文件      : _analysis/stubs_D.v   (分析用桩文件，不属于工程源码)
// 模块      : 若干空桩模块
// 功能      : 为 ModelSim 语法自验补齐工程中由 TD 原语/加密 IP/未接入模块提供的
//             被例化单元，使 vlog 不再报 "Module 'xxx' is not defined"。
//             端口列表按源码中的例化连接核对，只做语法级占位。
// 数据通路  : 无
// 时钟/复位 : 无
// 依赖      : 无
// 综合/实现 : 不参与综合，仅供仿真器解析
//-----------------------------------------------------------------------------
// 修改记录  :
//   2026-10-09  新建，用于 video 通路注释任务的编译自验
//-----------------------------------------------------------------------------
//=============================================================================

//---- TD 原语：时钟缓冲 / 混合时钟 / PLL 包装 / ODDR ----
module PH1P_LOGIC_BUFG (input i, output o); endmodule
module PH1P_PHY_MLCLK (input ce, input clkin, output clkout); endmodule

module ph1p_phy_pll_wrapper_27c53fedd344 #(
    parameter FBKCLK = "CLKC0_EXT", parameter FBKCLK_INT = "VCO_PHASE0",
    parameter FIN = "100.0", parameter REFCLK_DIV = 1, parameter FBCLK_DIV = 1,
    parameter CLKC0_ENABLE = "DISABLE", parameter CLKC0_DIV = 1, parameter CLKC0_CPHASE = 0,
    parameter CLKC0_FPHASE = 0, parameter CLKC0_FPHASE_RSTSEL = 0,
    parameter CLKC0_DUTY50 = "ENABLE", parameter CLKC0_DUTY_INT = 1,
    parameter CLKC1_ENABLE = "DISABLE", parameter CLKC1_DIV = 1, parameter CLKC1_CPHASE = 0,
    parameter CLKC1_FPHASE = 0, parameter CLKC1_FPHASE_RSTSEL = 0,
    parameter CLKC1_DUTY50 = "ENABLE", parameter CLKC1_DUTY_INT = 1,
    parameter CLKC2_ENABLE = "DISABLE", parameter CLKC2_DIV = 1, parameter CLKC2_CPHASE = 0,
    parameter CLKC2_FPHASE = 0, parameter CLKC2_FPHASE_RSTSEL = 0,
    parameter CLKC2_DUTY50 = "ENABLE", parameter CLKC2_DUTY_INT = 1,
    parameter CLKC3_ENABLE = "DISABLE", parameter CLKC3_DIV = 1, parameter CLKC3_CPHASE = 0,
    parameter CLKC3_FPHASE = 0, parameter CLKC3_FPHASE_RSTSEL = 0,
    parameter CLKC3_DUTY50 = "ENABLE", parameter CLKC3_DUTY_INT = 1,
    parameter PLL_USR_RST = "DISABLE", parameter PLL_FEED_TYPE = "EXTERNAL",
    parameter PLL_FASTLOOP = "ENABLE", parameter LPF_RES = 0, parameter LPF_CAP = 0,
    parameter ICP_CUR = 0, parameter PHASE_PATH_SEL = 0,
    parameter DYN_PHASE_PATH_SEL = "DISABLE", parameter DYN_FPHASE_EN = "DISABLE",
    parameter PI_OUT_SEL = "NORMAL", parameter PI_FRAC_EN = "DISABLE",
    parameter CLKC0_PI_SHIFT_EN = "DISABLE", parameter FEEDBK_MODE = "NORMAL",
    parameter DYN_CPHASE_EN = "DISABLE"
) (
    input clk4_en, output clk4_out, output clkb4_out,
    input clk5_en, output clk5_out, output clkb5_out,
    input clk6_en, output clk6_out, output clkb6_out,
    input refclk, input drp_clk, input drp_rstn, input drp_sel, input drp_rd, input drp_wr,
    input [7:0] drp_addr, input [7:0] drp_wdata, output drp_err, output drp_rdy,
    output [7:0] drp_rdata, input psclk, input [2:0] psclksel, input psstep, input psdown,
    input cps_step, output psdone, input ssc_reset, input [1:0] clkc_rst, input pllpd,
    input reset, input fbclk, input wakeup, input refclk_rst,
    input clk0_en, output clkb0_out, output clk0_out,
    input clk1_en, output clkb1_out, output clk1_out,
    input clk2_en, output clkb2_out, output clk2_out,
    input clk3_en, output clkb3_out, output clk3_out,
    output lock
);
endmodule

module EF2_LOGIC_ODDR (input clk, input rst, input d1, input d0, output q); endmodule
module EF3_LOGIC_ODDR (input clk, input rst, input d1, input d0, output q); endmodule
module EF4_LOGIC_ODDR (input clk, input rst, input d1, input d0, output q); endmodule
module SF1_LOGIC_ODDR (input clk, input rst, input d1, input d0, output q); endmodule
module EG_LOGIC_ODDR  (input clk, input rst, input d1, input d0, output q); endmodule
module PH1_LOGIC_ODDR (input clk, input rst, input d1, input d0, output q); endmodule
module PH1P_LOGIC_ODDR(input clk, input rst, input d1, input d0, output q); endmodule
module DR1_LOGIC_ODDR (input clk, input rst, input d1, input d0, output q); endmodule

//---- IP：宽度 128 / 155 的 512 深异步 FIFO（真实实现由 TD 生成，此处只留端口）----
module w128_d512_fifo (
    input rst, input clkw, input clkr, input we, input [127:0] di, input re,
    output [127:0] dout, output valid, output full_flag, output empty_flag,
    output afull, output aempty, output [8:0] wrusedw, output [8:0] rdusedw
);
endmodule

module w155_d512_fifo (
    input rst, input clk, input we, input [154:0] di, input re,
    output [154:0] dout, output valid, output full_flag, output empty_flag,
    output afull, output aempty, output [8:0] wrusedw, output [8:0] rdusedw
);
endmodule

//---- MCU 软核（ps_wrapper 例化；本工程 .al 未收录 ps_wrapper.v）----
module MCU (
    input core_clk, input timer_clk, input core_reset, input por_reset,
    input nmi, input [22:0] clic_irq,
    input jtag_tck, input jtag_tms, input jtag_tdi, output jtag_tdo,
    input apb_clk, input apb_rst,
    output [19:0] paddr, output psel, output penable, output pwrite,
    output [31:0] pwdata, output [3:0] pstrobe, output [2:0] pprot,
    input [31:0] prdata, input pready, input pslverr,
    output ahb_clk, output htrans, output hwrite, output haddr, output hsize,
    output hburst, output hprot, output hmastlock, output hwdata,
    input [31:0] hrdata, input [1:0] hresp, input hready,
    output uart0_tx, input uart0_rx, output uart1_tx, input uart1_rx,
    input gpio0_in, output gpio0_out, output gpio0_dir,
    input gpio1_in, output gpio1_out, output gpio1_dir,
    input gpio2_in, output gpio2_out, output gpio2_dir,
    input gpio3_in, output gpio3_out, output gpio3_dir,
    input gpio4_in, output gpio4_out, output gpio4_dir,
    input gpio5_in, output gpio5_out, output gpio5_dir,
    input gpio6_in, output gpio6_out, output gpio6_dir,
    input gpio7_in, output gpio7_out, output gpio7_dir
);
endmodule

//---- HDMI 1.4b 发送核（源码为 TD 加密文件 .enc.v，参数/端口可读，加密体不被 ModelSim 接受，此处用桩）----
module hdmi_1_4b_transmitter_core_wrapper #(
    parameter DEVICE = "EG", parameter HTOTAL = 2200, parameter HSA = 44,
    parameter HFP = 88, parameter HBP = 148, parameter HACTIVE = 1920,
    parameter VTOTAL = 1125, parameter VSA = 5, parameter VFP = 4,
    parameter VBP = 36, parameter VACTIVE = 1080, parameter VIDEO_TPG = "Enable",
    parameter VIDEO_FORMAT = "RGB", parameter VIDEO_VIC = 16,
    parameter AUDIO_SAMPLE_RATE = "48K", parameter IIC_SCL_DIV = 125
) (
    input wire I_pixel_clk, input wire I_rst,
    input wire I_edid_read_trig, output wire O_edid_read_valid, output wire [7:0] O_edid_read_data,
    input wire I_axis_s_user, input wire I_axis_s_valid, input wire I_axis_s_last,
    input wire [23:0] I_axis_s_data, output wire O_axis_s_ready,
    input wire I_audio_valid, input wire [23:0] I_audio_left_data, input wire [23:0] I_audio_right_data,
    input wire I_acr_valid, input wire [19:0] I_acr_cts, input wire [19:0] I_acr_n,
    output wire O_video_locked, output wire O_ddc_scl, inout wire IO_ddc_sda,
    output wire [9:0] O_ch0_tmds_data, output wire [9:0] O_ch1_tmds_data,
    output wire [9:0] O_ch2_tmds_data, output wire [9:0] O_clk_tmds_data
);
endmodule

//---- ChipWatcher 调试核（mipi_rx_error_detect 中为草稿引用，工程中无此定义）----
module cwc1 (
    input probe0, input probe1, input probe2, input probe3,
    input [11:0] probe4, input [11:0] probe5, input probe6, input probe7,
    input [11:0] probe8, input [11:0] probe9, input clk
);
endmodule
