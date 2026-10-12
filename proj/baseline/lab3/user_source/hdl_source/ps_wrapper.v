//=============================================================================
// 文件      : ps_wrapper.v
// 模块      : ps_wrapper
// 功能      : MCU（软核处理器）子系统包装：把 MCU 的 JTAG 调试口、APB 外设总线、两路 UART 和 8 路 GPIO 引到端口上，
//             并把 GPIO 做成三态双向口；本工程未使用的 AHB 主口全部空置。
//             注意：gpio3 / gpio4 的方向控制被改接成 S_gpio5_out / S_gpio6_out（见正文），与其余 GPIO 的写法不同。
// 数据通路  : JTAG（I_jtag_tck/tms/tdi -> O_jtag_tdo）与 APB（paddr/psel/penable/pwrite/pwdata/pstrobe/pprot/prdata/pready/pslverr）
//             以及 uart0/uart1 直达 MCU 端口；GPIO 通过 S_gpioN_out / S_gpioN_dir / S_gpioN_in 三根线完成三态双向连接。
//             本工程未使用的 AHB 主接口全部悬空，只把 hrdata/hresp/hready 接常量以保持接口电平确定。
// 时钟/复位 : I_core_clk 为 MCU 内核时钟，I_timer_clk 为定时器时钟，I_apb_clk 为 APB 总线时钟；
//             I_rst 高有效，同时驱动 core_reset 与 por_reset；I_apb_rst 单独复位 APB 从机侧。
//             本文件内部没有时序逻辑，只做端口连接与三态描述，故不存在跨时钟域处理。
// 依赖      : MCU（安路软核，定义见 ip_source/MCU/MCU.v）；无其他子模块。
// 综合/实现 : 纯端口连接 + 三态 assign，可综合。未被 td_project/camera_to_dsi_display.al 收录，
//             全树也未搜索到 ps_wrapper 的例化点，疑似未接入本工程（未能确认是否被例化）。
//-----------------------------------------------------------------------------
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================




//---- 模块说明 ----
// 本文件是 MCU 子系统的外壳：内部把安路软核 MCU 例化一次，把它的调试口、总线口、串口和 GPIO 引出到顶层；
// GPIO 采用 in / out / dir 三根内部线 + 一条三态 assign 的标准接法，方向由 MCU 自己决定。
module ps_wrapper (
    input wire        I_core_clk,
    input wire        I_timer_clk,
    input wire        I_rst,

    input wire        I_jtag_tck,
    input wire        I_jtag_tms,
    input wire        I_jtag_tdi,
    output wire       O_jtag_tdo,

    input wire        I_apb_clk,
    input wire        I_apb_rst,
    output wire[19:0] O_apb_paddr,
    output wire       O_apb_psel,
    output wire       O_apb_penable,
    output wire       O_apb_pwrite,
    output wire[31:0] O_apb_pwdata,
    output wire[3:0]  O_apb_pstrobe,
    output wire[2:0]  O_apb_pprot,
    input wire[31:0]  I_apb_prdata,
    input wire        I_apb_pready,
    input wire        I_apb_pslverr,

    output wire       O_uart0_tx,
    input wire        I_uart0_rx,

    output wire       O_uart1_tx,
    input wire        I_uart1_rx,

    inout wire        IO_gpio0,
    inout wire        IO_gpio1,
    inout wire        IO_gpio2,
    inout wire        IO_gpio3,
    inout wire        IO_gpio4,
    inout wire        IO_gpio5,
    inout wire        IO_gpio6,
    inout wire        IO_gpio7
);
    

//---- GPIO 内部连线声明 ----
// 每路 GPIO 三根线：S_gpioN_out 输出值、S_gpioN_dir 方向（1 = 输入/高阻）、S_gpioN_in 回读值。
    wire S_gpio0_in;
    wire S_gpio0_out;
    wire S_gpio0_dir;

    wire S_gpio1_in;
    wire S_gpio1_out;
    wire S_gpio1_dir;

    wire S_gpio2_in;
    wire S_gpio2_out;
    wire S_gpio2_dir;

    wire S_gpio3_in; 
    wire S_gpio3_out;
    wire S_gpio3_dir;

    wire S_gpio4_in; 
    wire S_gpio4_out;
    wire S_gpio4_dir;

    wire S_gpio5_in;
    wire S_gpio5_out;
    wire S_gpio5_dir;

    wire S_gpio6_in;
    wire S_gpio6_out;
    wire S_gpio6_dir;

    wire S_gpio7_in;
    wire S_gpio7_out;
    wire S_gpio7_dir;


//---- GPIO 三态双向驱动（标准接法） ----
// dir 有效时把引脚置为高阻以便外部驱动，否则把 out 值驱动到引脚；
// 同时把引脚电平回读进 S_gpioN_in 交给 MCU。gpio0 / 1 / 2 / 5 / 6 / 7 都是这种标准写法。
    assign IO_gpio0 = S_gpio0_dir ? 1'bz : S_gpio0_out;
    assign S_gpio0_in = IO_gpio0;

    assign IO_gpio1 = S_gpio1_dir ? 1'bz : S_gpio1_out;
    assign S_gpio1_in = IO_gpio1;

    assign IO_gpio2 = S_gpio2_dir ? 1'bz : S_gpio2_out;
    assign S_gpio2_in = IO_gpio2;

// 下面是 gpio3 / gpio4 原本的标准三态写法，已被注释停用（改用后面的非常规写法）。
//    assign IO_gpio3 = S_gpio3_dir ? 1'bz : S_gpio3_out;
//    assign S_gpio3_in = IO_gpio3;

//    assign IO_gpio4 = S_gpio4_dir ? 1'bz : S_gpio4_out;
//    assign S_gpio4_in = IO_gpio4;

//---- gpio3 / gpio4 的特殊三态写法 ----
// 与标准写法的区别：这里用 S_gpio5_out / S_gpio6_out 的输出值当方向控制，而不是各自的 S_gpioN_dir；
// 即 gpio3 的三态由 gpio5 的输出电平决定、gpio4 的三态由 gpio6 的输出电平决定；
// S_gpio3_dir / S_gpio4_dir 仍然连到 MCU（见下方例化），但在这两条 assign 里没有被使用。
// 按代码字面如实记录，未做任何改动。
    assign IO_gpio3 = S_gpio5_out ? 1'bz : S_gpio3_out;
    assign S_gpio3_in = IO_gpio3;

// gpio4 与 gpio3 采用同样的特殊写法：三态由 S_gpio6_out 决定，回读仍接到 S_gpio4_in。
    assign IO_gpio4 = S_gpio6_out ? 1'bz : S_gpio4_out;
    assign S_gpio4_in = IO_gpio4;


    assign IO_gpio5 = S_gpio5_dir ? 1'bz : S_gpio5_out;
    assign S_gpio5_in = IO_gpio5;

    assign IO_gpio6 = S_gpio6_dir ? 1'bz : S_gpio6_out;
    assign S_gpio6_in = IO_gpio6;

    assign IO_gpio7 = S_gpio7_dir ? 1'bz : S_gpio7_out;
    assign S_gpio7_in = IO_gpio7;

//---- MCU 软核例化 ----
// core_reset 与 por_reset 都接 I_rst，上电即复位；nmi / clic_irq 接地表示本工程不使用中断；
// AHB 主接口不使用：ahb_clk/htrans/hwrite/haddr/hsize/hburst/hprot/hmastlock/hwdata 全部悬空，
// hrdata/hresp/hready 接常量是为了让未使用的从机侧输入电平确定，避免悬空推断出锁存。
    MCU u_MCU(
        .core_clk   ( I_core_clk    ),
        .timer_clk  ( I_timer_clk   ),

        .core_reset ( I_rst         ),
        .por_reset  ( I_rst         ),

        .nmi        ( 1'b0          ),
        .clic_irq   ( 23'd0         ),

        .jtag_tck   ( I_jtag_tck    ),
        .jtag_tms   ( I_jtag_tms    ),
        .jtag_tdi   ( I_jtag_tdi    ),
        .jtag_tdo   ( O_jtag_tdo    ),

        .apb_clk    ( I_apb_clk     ),
        .apb_rst    ( I_apb_rst     ),
        .paddr      ( O_apb_paddr   ),
        .psel       ( O_apb_psel    ),
        .penable    ( O_apb_penable ),
        .pwrite     ( O_apb_pwrite  ),
        .pwdata     ( O_apb_pwdata  ),
        .pstrobe    ( O_apb_pstrobe ),
        .pprot      ( O_apb_pprot   ),
        .prdata     ( I_apb_prdata  ),
        .pready     ( I_apb_pready  ),
        .pslverr    ( I_apb_pslverr ),

        .ahb_clk    (               ),
        .htrans     (               ),
        .hwrite     (               ),
        .haddr      (               ),
        .hsize      (               ),
        .hburst     (               ),
        .hprot      (               ),
        .hmastlock  (               ),
        .hwdata     (               ),
        .hrdata     ( 32'd0         ),
        .hresp      ( 2'b00         ),
        .hready     ( 1'b1          ),

        .uart0_tx   ( O_uart0_tx    ),
        .uart0_rx   ( I_uart0_rx    ),

        .uart1_tx   ( O_uart1_tx    ),
        .uart1_rx   ( I_uart1_rx    ),

        .gpio0_in   ( S_gpio0_in    ),
        .gpio0_out  ( S_gpio0_out   ),
        .gpio0_dir  ( S_gpio0_dir   ),
        .gpio1_in   ( S_gpio1_in    ),
        .gpio1_out  ( S_gpio1_out   ),
        .gpio1_dir  ( S_gpio1_dir   ),
        .gpio2_in   ( S_gpio2_in    ),
        .gpio2_out  ( S_gpio2_out   ),
        .gpio2_dir  ( S_gpio2_dir   ),
        .gpio3_in   ( S_gpio3_in    ),
        .gpio3_out  ( S_gpio3_out   ),
        .gpio3_dir  ( S_gpio3_dir   ),
        .gpio4_in   ( S_gpio4_in    ),
        .gpio4_out  ( S_gpio4_out   ),
        .gpio4_dir  ( S_gpio4_dir   ),
        .gpio5_in   ( S_gpio5_in    ),
        .gpio5_out  ( S_gpio5_out   ),
        .gpio5_dir  ( S_gpio5_dir   ),
        .gpio6_in   ( S_gpio6_in    ),
        .gpio6_out  ( S_gpio6_out   ),
        .gpio6_dir  ( S_gpio6_dir   ),
        .gpio7_in   ( S_gpio7_in    ),
        .gpio7_out  ( S_gpio7_out   ),
        .gpio7_dir  ( S_gpio7_dir   )
    );


endmodule