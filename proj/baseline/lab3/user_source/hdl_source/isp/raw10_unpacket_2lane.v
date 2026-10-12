//=============================================================================
// 文件      : isp/raw10_unpacket_2lane.v
// 模块      : raw10_unpacket_2lane
// 功能      : 把 CSI 字节流(2 lane、32bit/拍)按 RAW10 的“4 像素 / 5 字节”打包规则重新拼装为 40bit(=4×10bit 像素)输出，并同步给出帧首/帧尾/有效。★重要：黑电平减法与 10bit→8bit 右移截位、RAW8 输出、FIFO 读写控制那一整段位于 /* 块注释内(本文件 :141-:233)，未参与综合；因此本模块当前实际只输出 O_raw10_*，并不产生 RAW8，也不做任何黑电平修正。
// 数据通路  : I_csi_data(32bit/拍) 与 I_csi_valid → 各打 2 拍 → S_phase_cnt(0..4) 相位机 → case 按相位把相邻两拍的字节与 lane 尾部 2bit 拼成 4 个 10bit → S_raw10_wr_data[39:30]/[29:20]/[19:10]/[9:0] → 输出寄存器 O_raw10_data 时把 4 个字段次序反转后送出。
// 时钟/复位 : 只有 I_clk，本文件内全部为同步时序、无复位逻辑；I_rst_n 端口存在但在本文件内未被引用。
// 依赖      : 无子模块被例化（w40_d40_fifo 的例化位于注释区内，未生效）。
// 综合/实现 : 本文件没有 `timescale；关键信号带 //synthesis keep 属性。每 5 拍为一个相位循环、其中 4 拍出数据共 16 个像素，第 5 拍为空拍。I_camera_black_level 端口在本工程 design_top_wrapper.v:571 例化时未连接（悬空按 0 处理），且使用它的逻辑本身处于注释区内。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
/*******************************MILIANKE*******************************
*Company : MiLianKe Electronic Technology Co., Ltd.
*WebSite:https://www.milianke.com
*TechWeb:https://www.uisrc.com
*tmall-shop:https://milianke.tmall.com
*jd-shop:https://milianke.jd.com
*taobao-shop1: https://milianke.taobao.com
*Create Date: 2023/03/23
*Module Name:
*File Name:
*Description: 
*The reference demo provided by Milianke is only used for learning. 
*We cannot ensure that the demo itself is free of bugs, so users 
*should be responsible for the technical problems and consequences
*caused by the use of their own products.
*Copyright: Copyright (c) MiLianKe
*All rights reserved.
*Revision: 1.0
*Signal description
*1) I_ input
*2) O_ output
*3) IO_ input output
*4) S_ system internal signal
*5) _n activ low
*6) _dg debug signal 
*7) _r delay or register
*8) _s state mechine
*********************************************************************/
/*********raw10_unpacket_2lane RAW���ݸ�ʽתΪRAW10,֮������λ��ʵ��RAW8***********
--�汾��1.0
*********************************************************************/

module raw10_unpacket_2lane (
    input wire I_clk,
    input wire I_rst_n,

    input wire        I_csi_frame_start,  //synthesis keep
    input wire        I_csi_frame_end,    //synthesis keep
    input wire        I_csi_valid,        //synthesis keep
    input wire [31:0] I_csi_data,         //synthesis keep

    input wire [9:0] I_camera_black_level,  // 黑电平基座输入；本工程 design_top_wrapper.v:571 例化时未连接（悬空=0）

    output reg        O_raw10_frame_start,
    output reg        O_raw10_frame_end,
    output reg        O_raw10_valid,
    output reg [39:0] O_raw10_data
);

//---- 内部信号 ----
  reg         S_csi_valid_1d;  //synthesis keep
  reg         S_csi_valid_2d;  //synthesis keep
  reg  [31:0] S_csi_data_1d;  //synthesis keep
  reg  [31:0] S_csi_data_2d;  //synthesis keep
  reg  [ 2:0] S_phase_cnt;  //synthesis keep  // 3bit 相位：0..3 出数据，4 为空拍
  reg         S_raw10_wr_en;  //synthesis keep
  reg  [39:0] S_raw10_wr_data;  //synthesis keep
  wire [ 9:0] S_fifo_rd_num;  //synthesis keep
  reg         S_fifo_rd_en;  //synthesis keep
  wire        S_fifo_empty;  //synthesis keep
  reg         S_raw8_valid;  //synthesis keep
  reg  [39:0] S_raw8_data;  //synthesis keep
  wire [39:0] S_fifo_rd_data;  //synthesis keep


//---- CSI 输入打拍：valid/data 各 2 级 ----
  //ͬ��������MIPI���������I_csi_valid����������ÿ��I_csi_valid ����1��
  always @(posedge I_clk) begin
    O_raw10_frame_start <= I_csi_frame_start;
    O_raw10_frame_end   <= I_csi_frame_end;

    S_csi_valid_1d      <= I_csi_valid;
    S_csi_valid_2d      <= S_csi_valid_1d;

    S_csi_data_1d       <= I_csi_data;
    S_csi_data_2d       <= S_csi_data_1d;
  end

//---- 相位计数器 S_phase_cnt：0..4，每 5 拍一个循环 ----
  always @(posedge I_clk) begin
    if({S_csi_valid_2d,S_csi_valid_1d,I_csi_valid}==3'b101)begin//��S_csi_valid_2d��I_csi_validͬʱ��Ч��S_csi_valid_2d����ǰһ����Ч32Bit I_csi_valid���������µ�32bit  // 只有相隔 1 拍的两个 valid 同时有效(3'b101)才推进相位（CSI valid 不连续）
      if (S_phase_cnt == 3'd4)  //һ�����ڽ���
        S_phase_cnt <= 3'd0;
      else S_phase_cnt <= S_phase_cnt + 3'd1;
    end else if ({S_csi_valid_2d, S_csi_valid_1d, I_csi_valid} == 3'b000) S_phase_cnt <= 3'd0;
  end


//---- 40bit 拆 4×10bit：按相位把两拍字节与 lane 尾部 2bit 拼装 ----
  always @(posedge I_clk) begin
    if ({S_csi_valid_2d, S_csi_valid_1d, I_csi_valid} == 3'b101) begin
      case (S_phase_cnt)
        3'd0: begin
          S_raw10_wr_en          <= 1'b1;
          S_raw10_wr_data[39:30] <= {S_csi_data_2d[31:24], I_csi_data[25:24]};  ///P0  // 每个 10bit = 高 8bit + 跨字节的 2 个低位 bit
          S_raw10_wr_data[29:20] <= {S_csi_data_2d[23:16], I_csi_data[27:26]};  ///P1
          S_raw10_wr_data[19:10] <= {S_csi_data_2d[15 : 8], I_csi_data[29:28]};  ///P2
          S_raw10_wr_data[9:0]   <= {S_csi_data_2d[7 : 0], I_csi_data[31:30]};  ///P3
        end
        3'd1: begin
          S_raw10_wr_en          <= 1'b1;
          S_raw10_wr_data[39:30] <= {S_csi_data_2d[23:16], I_csi_data[17:16]};  ///P4
          S_raw10_wr_data[29:20] <= {S_csi_data_2d[15 : 8], I_csi_data[19:18]};  ///P5
          S_raw10_wr_data[19:10] <= {S_csi_data_2d[7 : 0], I_csi_data[21:20]};  ///P6
          S_raw10_wr_data[9:0]   <= {I_csi_data[31:24], I_csi_data[23:22]};  ///P7
        end
        3'd2: begin
          S_raw10_wr_en          <= 1'b1;
          S_raw10_wr_data[39:30] <= {S_csi_data_2d[15 : 8], I_csi_data[9:8]};  ///P8
          S_raw10_wr_data[29:20] <= {S_csi_data_2d[7 : 0], I_csi_data[11:10]};  ///P9
          S_raw10_wr_data[19:10] <= {I_csi_data[31:24], I_csi_data[13:12]};  ///P10
          S_raw10_wr_data[9:0]   <= {I_csi_data[23:16], I_csi_data[15:14]};  ///P11
        end
        3'd3: begin
          S_raw10_wr_en          <= 1'b1;
          S_raw10_wr_data[39:30] <= {S_csi_data_2d[7 : 0], I_csi_data[1:0]};  ///P12
          S_raw10_wr_data[29:20] <= {I_csi_data[31:24], I_csi_data[3:2]};  ///P13
          S_raw10_wr_data[19:10] <= {I_csi_data[23:16], I_csi_data[5:4]};  ///P14
          S_raw10_wr_data[9:0]   <= {I_csi_data[15 : 8], I_csi_data[7:6]};  ///P15
        end
        3'd4: begin
          S_raw10_wr_en          <= 1'b0;
          S_raw10_wr_data[39:30] <= 'd0;  // 相位 4：空拍，输出全 0
          S_raw10_wr_data[29:20] <= 'd0;
          S_raw10_wr_data[19:10] <= 'd0;
          S_raw10_wr_data[9:0]   <= 'd0;
        end
      endcase
    end else begin
      S_raw10_wr_en          <= 1'b0;
      S_raw10_wr_data[39:30] <= 'd0;
      S_raw10_wr_data[29:20] <= 'd0;
      S_raw10_wr_data[19:10] <= 'd0;
      S_raw10_wr_data[9:0]   <= 'd0;
    end
  end

//---- 输出寄存器：字段次序反转后送出 ----
  always @(posedge I_clk) begin
    O_raw10_data <= {
      S_raw10_wr_data[9:0], S_raw10_wr_data[19:10], S_raw10_wr_data[29:20], S_raw10_wr_data[39:30]  // 注意：与写入时字段次序相反，原 [39:30] 落到输出的最低位
    };
    O_raw10_valid <= S_raw10_wr_en;  // 写使能打 1 拍即 O_raw10_valid
  end

//---- 以下整段(:141-:233)处于块注释区内、未参与综合：黑电平减法 + 10bit→8bit 右移截位 + FIFO 读写控制 + RAW8 输出 ----
  /*
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n)
            S_fifo_rd_en <= 1'b0;
        else
            if(S_fifo_empty)
                S_fifo_rd_en <= 1'b0;
            else if(S_fifo_rd_num == 'd310)
                S_fifo_rd_en <= 1'b1;
            else
                S_fifo_rd_en <= S_fifo_rd_en;
    end

    always @(posedge I_clk) begin
        S_raw8_valid       <= S_fifo_rd_en & (~S_fifo_empty);
        O_raw8_valid       <= S_raw8_valid;

        S_raw8_data[39:30] <= (S_fifo_rd_data[39:30] - I_camera_black_level) >> 2;  // 先减黑电平基座、再右移 2 位（10bit→8bit，即除以 4）；整段当前处于注释区内，未综合
        S_raw8_data[29:20] <= (S_fifo_rd_data[29:20] - I_camera_black_level) >> 2;
        S_raw8_data[19:10] <= (S_fifo_rd_data[19:10] - I_camera_black_level) >> 2;
        S_raw8_data[9:0]   <= (S_fifo_rd_data[9:0]   - I_camera_black_level) >> 2;  // 四个 10bit 字段同构处理
    end

reg [11:0]line_cnt;//synthesis keep

    always @(posedge I_clk ) begin
        if((O_raw8_valid==1'b0)&(S_raw8_valid == 1'b1))
            line_cnt <= line_cnt + 1'b1;
        else if(I_csi_frame_start)
            line_cnt <=0;
    end

    assign O_raw8_data = {S_raw8_data[37:30],S_raw8_data[27:20],S_raw8_data[17:10],S_raw8_data[7:0]};


  always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n) begin
      raw10_wr_fifo_en <= 1'b0;
    end else if (raw10_frame_start == 1'b1) begin
      raw10_wr_fifo_en <= 1'b1;
    end else if (raw10_frame_end == 1'b1) begin
      raw10_wr_fifo_en <= 1'b0;
    end else begin
      raw10_wr_fifo_en <= raw10_wr_fifo_en;
    end
  end

  always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n) begin
      raw10_wr_cunt <= 20'b0;
    end else if (raw10_wr_fifo_en && raw10_valid) begin
      raw10_wr_cunt <= raw10_wr_cunt + 1;
    end else if (raw10_wr_fifo_en == 'b0) begin
      raw10_wr_cunt <= 20'b0;
    end else begin
      raw10_wr_cunt <= raw10_wr_cunt;
    end
  end



  always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n || raw10_wr_fifo_en) begin
      raw10_rd_cunt <= 20'b0;
      raw10_rd_en   <= 1'b0;
    end else if (raw10_rd_cunt == 20'd270) begin
      raw10_rd_cunt <= 20'b0;
      raw10_rd_en   <= 1'b0;
    end else begin
      raw10_rd_cunt <= raw10_rd_cunt + 1;
      raw10_rd_en   <= 1'b1;
    end
  end
  always @(posedge I_clk) begin
    raw10_rd_en_r <= raw10_rd_en;
  end

  w40_d40_fifo u_w40_d40_fifo (
      .clk (I_clk),
      .wrst(I_csi_frame_start),
      .rrst(I_csi_frame_start),
      .we  (raw10_wr_fifo_en && raw10_valid),
      .di  (raw10_data),
      // .full_flag(),
      // .wrusedw  (),

      .re  (raw10_rd_en),
      .dout(S_fifo_rd_data)
      // .empty_flag(S_fifo_empty),
      // .rdusedw   (S_fifo_rd_num)
  );

*/

endmodule
