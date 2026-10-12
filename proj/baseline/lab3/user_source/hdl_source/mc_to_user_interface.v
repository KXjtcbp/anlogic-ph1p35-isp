//=============================================================================
// 文件      : mc_to_user_interface.v
// 模块      : mc_to_user_interface
// 功能      : DDR 用户接口与 DDR 控制器接口之间的命令/数据转换桥。
//             用户侧只给出“写使能/读使能 + 地址 + 写数据”，本模块把它们打包进 FIFO，
//             再按 DDR 控制器的 app 接口时序翻译成 read/write 命令、地址与写数据。
// 数据通路  : 用户侧 (wr_en, rd_en, addr, wdata) 拼成 155 bit 记录写入 w155_d512_fifo；
//             从 FIFO 读出后按位段拆分：bit[154]=写标志、bit[153]=读标志、bit[152:128]=地址、bit[127:0]=写数据；
//             读回通路 I_mc_app_rd_data -> O_ddr_user_rd_data 为直通，读有效也直接透传。
// 时钟/复位 : 单一时钟 I_clk；I_rst_n 低有效，FIFO 的 rst 端接 ~I_rst_n（即高有效复位）。
//             本文件只有这一个时钟域。
// 依赖      : 例化 w155_d512_fifo（155 bit 宽、512 深的软 FIFO，来自 ip_source），无其他子模块。
// 综合/实现 : 纯 RTL + FIFO IP，可综合；已收录于 td_project/camera_to_dsi_display.al，
//             并在 design_top_wrapper.v:687 以 u_mc_to_user_interface 例化。
//-----------------------------------------------------------------------------
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================



//---- 模块说明 ----
// 用户侧看到的是一个“可读可写的 DDR 窗口”：给地址与数据、拉一下使能即可；
// 本模块把这些请求排队（FIFO 起缓冲和跨模块握手的作用），再按 DDR 控制器 app 接口的要求逐拍发出。
module mc_to_user_interface (
    input wire          I_clk,
    input wire          I_rst_n,

    /*
        ddr user interface
        当I_ddr_user_ready拉低时，还能写入8个长度数据
    */
    input wire          I_ddr_user_wr_en,
    input wire          I_ddr_user_rd_en,  //synthesis keep
    input wire[24:0]    I_ddr_user_addr,
    input wire[127:0]   I_ddr_user_wr_data,
    output wire         O_ddr_user_ready,
    output wire         O_ddr_user_rd_valid,
    output wire[127:0]  O_ddr_user_rd_data,

    /*
        ddr memory controller interface
    */
    output  wire        O_mc_app_en,
    output  wire [24:0] O_mc_app_addr,
    output  wire [2:0]  O_mc_app_cmd,
    input  wire         I_mc_app_rdy,
    output wire         O_mc_app_wdf_wren,
    output wire [127:0] O_mc_app_wdf_data,
    output wire         O_mc_app_wdf_end,
    output wire [31:0]  O_mc_app_wdf_mask,
    input wire          I_mc_app_wdf_rdy,
    input wire [127:0]  I_mc_app_rd_data,
    input wire          I_mc_app_rd_data_end,
    input wire          I_mc_app_rd_data_valid
);

//---- 内部信号声明 ----
// S_fifo_wr_en：FIFO 写使能，读或写请求都要入队；
// S_fifo_wr_data：入队的 155 bit 记录；
// S_fifio_pro_full：FIFO 的 almost full（原文拼写多一个 i，保留不改），用于反压用户侧；
// S_fifo_empty：FIFO 空标志，空时不向控制器发命令。
    wire        S_fifo_wr_en;    
    wire[154:0] S_fifo_wr_data;
    wire        S_fifio_pro_full;
    wire        S_fifo_rd_en;    
    wire[154:0] S_fifo_rd_data;
    wire        S_fifo_rd_valid;
    wire        S_fifo_empty;   

//---- 请求入队打包 ----
// 读、写请求共用一条 FIFO，所以写使能是两者的“或”。
    assign S_fifo_wr_en = I_ddr_user_wr_en | I_ddr_user_rd_en;

// 155 bit 记录的字段分配（高位在前）：
//   bit[154]    = 写使能 I_ddr_user_wr_en；
//   bit[153]    = 读使能 I_ddr_user_rd_en；
//   bit[152:128]= 25 bit 地址 I_ddr_user_addr；
//   bit[127:0]  = 128 bit 写数据 I_ddr_user_wr_data。
    assign S_fifo_wr_data = {I_ddr_user_wr_en,I_ddr_user_rd_en,I_ddr_user_addr,I_ddr_user_wr_data};

//---- 向控制器发起一次传输 ----
// 控制器命令通道与写数据通道都 ready、且队列非空时才弹出记录，保证不会丢命令。
    assign S_fifo_rd_en = I_mc_app_rdy & I_mc_app_wdf_rdy & (~S_fifo_empty);

//---- 用户侧反压 ----
// FIFO 接近满时把 ready 拉低，提示用户侧“还能再写 8 个长度的数据”（见端口处原注释）。
    assign O_ddr_user_ready = ~S_fifio_pro_full;

//---- 命令译码：地址 / 命令 / 写数据 ----
// 取记录的地址字段送控制器；
    assign O_mc_app_en = S_fifo_rd_en;

    assign O_mc_app_addr = O_mc_app_en ? S_fifo_rd_data[152:128] : 'd0;

// 命令编码：3'd1 = 读、3'd0 = 写；由记录的读标志 bit[153] 决定（读优先，读写不会同时有效）。
    assign O_mc_app_cmd = O_mc_app_en && S_fifo_rd_data[153] ? 3'd1 : 3'd0;

// 写数据有效只在“写”请求时拉起，由记录的写标志 bit[154] 决定。
    assign O_mc_app_wdf_wren = O_mc_app_en & S_fifo_rd_data[154];

    assign O_mc_app_wdf_end = O_mc_app_wdf_wren;

// 掩码全 0 表示 128 bit 全部字节有效（不做字节选通）。
    assign O_mc_app_wdf_mask = 'd0;

// 只有写请求时把 128 bit 写数据推上总线，其余时刻给 0 避免无用翻转。
    assign O_mc_app_wdf_data = O_mc_app_wdf_wren ? S_fifo_rd_data[127:0] : 'd0;

//---- 读回通路（纯直通） ----
// 控制器的读数据有效与读数据原样转给用户侧，本模块不额外打拍、不做缓冲。
    assign O_ddr_user_rd_valid = I_mc_app_rd_data_valid;
    
    assign O_ddr_user_rd_data = I_mc_app_rd_data;

//---- 请求队列 FIFO ----
// 155 bit 宽、512 深的单时钟 FIFO：位宽刚好容纳一条打包记录；
// rst 接 ~I_rst_n 是因为 FIFO IP 的 rst 为高有效，而本模块复位是低有效；
// full_flag / wrusedw / aempty / rdusedw 不使用（留空），只用 afull 做反压、empty_flag 判空。
    w155_d512_fifo U_w155_d512_fifo(
        .clk        ( I_clk            ),     
        .rst        ( ~I_rst_n         ),     

        .we         ( S_fifo_wr_en     ),
        .di         ( S_fifo_wr_data   ),
        .afull      ( S_fifio_pro_full ),
        .full_flag  (),
        .wrusedw    (),
 
        .re         ( S_fifo_rd_en     ), 
        .valid      ( S_fifo_rd_valid  ), 
        .dout       ( S_fifo_rd_data   ),  
        .empty_flag ( S_fifo_empty     ),
        .aempty     (),
        .rdusedw    ()
    );
    
endmodule
