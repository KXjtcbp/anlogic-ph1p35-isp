//=============================================================================
// [HDR-2026-10-09] 文件      : uicfgcs500_720p.v
// 模块      : uicfgcs500_720p
// 功能      : SC500CS 的 I2C 配置状态机：上电后按 init 表逐条写寄存器，配置完成后转为按 AE 表下发曝光/增益，并产生 O_cfg_done / O_ae_cfg_done 握手信号。
// 数据通路  : init 表(上电) 或 ae 表(运行时) → I2C 时序(uii2c) → O_cam_scl / IO_cam_sda 两条线到传感器
// 时钟/复位 : I_clk（24MHz 域）；I_rst_n 低有效。I2C 分频由 parameter CLK_DIV 决定（16'd239）。
// 依赖      : uics500reg_720p60（init 表）/ SC500GainTbl（增益编码）/ uics500regAE（AE 表）/ uii2c（I2C 主机）
// 综合/实现 : ■ (:56) 延时分支只按 `reg_index == 9'd115` 触发（stream on 之后延时 POST_STREAM_DELAY=240000 拍 ≈ 10ms @24MHz）；因此往 init 表**追加索引**只需改 REG_SIZE 与 case，不必改状态机。
//           ■ (:32-33) 用 O_cfg_done 选择当前下发的是 init 表还是 ae 表。
//-----------------------------------------------------------------------------
// 修改记录  :
//   2026-09-27  [230f479] 导入官方 lab3 基线
//   2026-10-09  （未提交）标识符改名 8 处：I_ae/I_ag → I_exposure_time/I_analog_gain，SC500GainTbl 例化的 .I/.O → .I_gain_idx/.O_gain_code
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑，见 E:\FPGA\_analysis\rename_report.txt）
//=============================================================================
`timescale 1ns / 1ns

module uicfgcs500_720p #(
    parameter CLK_DIV = 16'd239
)(
    input  wire        I_clk,
    input  wire        I_rst_n,
    input  wire        I_ae_req,
    input  wire [15:0] I_exposure_time,
    input  wire [15:0] I_analog_gain,
    input  wire        I_test_pattern,   // [2026-10-10d] ★自检用★：1 = 运行时表把 0x4501 写成 0xbc（灰度测试图）。顶层只在"四开关全拨上"时为 1
    input  wire        I_gain_high,      // SW4：1 = 模拟增益 15.750×；0 = 4.000×
    input  wire        I_gain_digital,   // SW3：1 = 数字增益 ×2.000；0 = ×1.000（复位默认）
    output wire        O_cam_scl,
    inout  wire        IO_cam_sda,
    output reg         O_cfg_done,
    output reg         O_ae_cfg_done
);

localparam CAM_ID = 8'h6c;
localparam [17:0] POST_STREAM_DELAY = 18'd240000;

reg [7:0]  rst_cnt = 8'd0;
reg        iic_req;
wire       iic_busy;
reg [31:0] wr_data;
reg [1:0]  state;
reg [8:0]  reg_index;
reg [17:0] delay_cnt;

wire [23:0] init_data;
wire [8:0]  init_size;
wire [23:0] ae_data;
wire [8:0]  ae_size;
wire [23:0] selected_data = O_cfg_done ? ae_data : init_data;
wire [8:0]  selected_size = O_cfg_done ? ae_size : init_size;

always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n)
        rst_cnt <= 8'd0;
    else if (!rst_cnt[7])
        rst_cnt <= rst_cnt + 1'b1;
end

always @(posedge I_clk) begin
    if (!rst_cnt[7]) begin
        reg_index     <= 9'd0;
        iic_req       <= 1'b0;
        wr_data       <= 32'd0;
        O_cfg_done    <= 1'b0;
        O_ae_cfg_done <= 1'b0;
        delay_cnt     <= 18'd0;
        state         <= 2'd0;
    end else begin
        case (state)
            2'd0: begin
                iic_req <= 1'b0;
                if (!O_cfg_done) begin
                    if ((reg_index == 9'd115) && (delay_cnt < POST_STREAM_DELAY))
                        delay_cnt <= delay_cnt + 1'b1;
                    else if (reg_index == init_size) begin
                        O_cfg_done    <= 1'b1;
                        O_ae_cfg_done <= 1'b1;
                        reg_index     <= 9'd0;
                    end else
                        state <= 2'd1;
                end else if (I_ae_req) begin
                    O_ae_cfg_done <= 1'b0;
                    reg_index     <= 9'd0;
                end else if (!O_ae_cfg_done) begin
                    if (reg_index == ae_size)
                        O_ae_cfg_done <= 1'b1;
                    else
                        state <= 2'd1;
                end
            end
            2'd1: begin
                if (!iic_busy) begin
                    iic_req        <= 1'b1;
                    wr_data[7:0]   <= CAM_ID;
                    wr_data[15:8]  <= selected_data[23:16];
                    wr_data[23:16] <= selected_data[15:8];
                    wr_data[31:24] <= selected_data[7:0];
                    state          <= 2'd2;
                end
            end
            2'd2: begin
                if (iic_busy) begin
                    iic_req <= 1'b0;
                    state   <= 2'd3;
                end
            end
            2'd3: begin
                if (!iic_busy) begin
                    reg_index <= reg_index + 1'b1;
                    state     <= 2'd0;
                end
            end
        endcase
    end
end

uii2c #(
    .WMEN_LEN (4),
    .RMEN_LEN (1),
    .CLK_DIV  (CLK_DIV)
) u_i2c (
    .I_clk      (I_clk),
    .I_rstn     (rst_cnt[7]),
    .O_iic_scl  (O_cam_scl),
    .IO_iic_sda (IO_cam_sda),
    .I_wr_data  (wr_data),
    .I_wr_cnt   (8'd4),
    .O_rd_data  (),
    .I_rd_cnt   (8'd0),
    .I_iic_mode (1'b0),
    .I_iic_req  (iic_req),
    .O_iic_busy (iic_busy)
);

uics500reg_720p60 u_init_table (
    .REG_INDEX (reg_index),
    .REG_DATA  (init_data),
    .REG_SIZE  (init_size),
    .I_test_pattern (I_test_pattern),
    .I_gain_high    (I_gain_high),
    .I_gain_digital (I_gain_digital)
);

// [2026-10-10d] 运行时增益表（AE 表）的输入改成"开关直接给出的寄存器原始字节"，
//   不再经过 SC500GainTbl —— 该表只有索引 0..73（封顶 ≈4.28×，见 SC500GainTbl.v），
//   会把 15.750×/31.500× 截回去，这正是"增益上不去"的隐藏瓶颈之一。
//
// ★[HDR-2026-10-12] AE 算法（ae_ctrl.v）已落地 ⇒ 曝光与模拟增益改为真正使用模块输入端口★
//   改前这两根是硬编码 wire，把同名输入端口完全屏蔽掉了：AE 表拿到的一直是常数
//   0x07C6 / 0x1F3F，无论上游 AE 算法算出什么都不会生效。这是"原厂已预置 90% AE 通路、
//   但唯一真正断掉的那一根线"。
//   数字增益仍由 SW3 手动选择（×1.000/×2.000），作为 AE 模拟增益之外的粗档位；
//   模拟增益本身覆盖 {3e08,3e09} = 1.000× ~ 15.750×，乘 SW3 后总范围 1.000× ~ 31.500×。
wire [15:0] rt_exposure     = I_exposure_time;                       // 来自 ae_ctrl.v（固定 1990）
wire [15:0] rt_analog_gain  = I_analog_gain;                         // 来自 ae_ctrl.v（{3e08,3e09} 原始字节对）
wire [15:0] rt_digital_gain = I_gain_digital ? 16'h0180 : 16'h0080;  // ×2.000  / ×1.000（SW3）

// SC500GainTbl 例化保留给将来的 AE 算法用（当前不再驱动 AE 表，输出悬空无害）
wire [15:0] gain_value;
SC500GainTbl u_gain_table (
    .I_clk  (I_clk),
    .I_rstn (rst_cnt[7]),
    .I_gain_idx      (I_analog_gain - 16),
    .O_gain_code      (gain_value)
);

uics500regAE u_ae_table (
    .REG_INDEX (reg_index),
    .REG_DATA  (ae_data),
    .REG_SIZE  (ae_size),
    .I_analog_gain      (rt_analog_gain),
    .I_exposure_time    (rt_exposure),
    .I_digital_gain     (rt_digital_gain),
    .I_test_pattern     (I_test_pattern)
);

endmodule
