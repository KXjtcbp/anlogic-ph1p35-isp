//=============================================================================
// 文件      : raw10_unpacket.v
// 模块      : raw10_unpacket
// 功能      : RAW10 拆包：把 32bit 的 CSI 数据流里的 8bit 主数据与 2bit LSB 重新拼成 10bit 像素。★疑似历史遗留副本：全树没有任何模块例化它，也未列入 .al 编译清单；本工程 RAW10 拆包实际由 isp/raw10_unpacket_2lane.v 承担（未逐一比对两者差异，未能确认）。本文件后半段还留着大段被 // 注释掉的旧实现。
// 数据通路  : 输入 I_csi_data[31:0]（2lane 拼成的 32bit）与 I_camera_black_level[9:0]；输出 O_raw10_data[39:0]（=4 像素 x 10bit，字段 [9:0]/[19:10]/[29:20]/[39:30]）。现役逻辑：先把 frame_start/frame_end/valid/data 打两拍同步；S_phase_cnt 的推进条件是 {S_csi_valid_2d,S_csi_valid_1d,I_csi_valid} == 3b101（即 valid 按 1/0/1 的节奏出现，说明 MIPI 输入不连续），在 0->4 之间循环；case(S_phase_cnt) 的 d0~d3 每拍把 4 个 32bit 字里的 8bit 主数据与 2bit LSB 拼成 4 个 10bit 像素（d0->P0~P3、d1->P4~P7、d2->P8~P11、d3->P12~P15），d4 清 0 并置 wr_en=0；最后 O_raw10_data <= {S_raw10_wr_data[9:0],[19:10],[29:20],[39:30]}（相对 P0~P15 做了一次字序翻转），O_raw10_valid <= S_raw10_wr_en。
// 时钟/复位 : I_clk 上升沿同步；I_rst_n 只作端口保留，现役逻辑中未见使用。
// 依赖      : 无模块例化它；现役代码只用自身寄存器，不依赖 IP。第 112~259 行的旧实现里例化过 w40_d512_fifo（FIFO 已随旧代码一起被注释掉，本工程 .al 中也没有该 IP），旧实现还包含黑电平 (x - I_camera_black_level) >> 2 的处理。
// 综合/实现 : ★未被 camera_to_dsi_display.al 引用、未参与综合实现。文件内已有的 // 旧注释按要求原样保留，未做改动。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
//---- kuai 1: duan-kou sheng-ming (32bit CSI shu-ru -> 40bit RAW10 shu-chu) ----


module raw10_unpacket (
    input wire I_clk,
    input wire I_rst_n,

    input wire        I_csi_frame_start,  //synthesis keep
    input wire        I_csi_frame_end,    //synthesis keep
    input wire        I_csi_valid,        //synthesis keep
    input wire [31:0] I_csi_data,         //synthesis keep

    input wire [9:0] I_camera_black_level,

    output reg        O_raw10_frame_start,
    output reg        O_raw10_frame_end,
    output reg        O_raw10_valid,
    output reg [39:0] O_raw10_data
);

  reg         S_csi_valid_1d;  //synthesis keep
  //---- kuai 2: nei-bu ji-cun qi / xian-wang (S_phase_cnt, S_raw10_wr_data deng) ----
  reg         S_csi_valid_2d;  //synthesis keep
  reg  [31:0] S_csi_data_1d;  //synthesis keep
  reg  [31:0] S_csi_data_2d;  //synthesis keep
  reg  [ 2:0] S_phase_cnt;  //synthesis keep
  reg         S_raw10_wr_en;  //synthesis keep
  reg  [39:0] S_raw10_wr_data;  //synthesis keep
  wire [ 9:0] S_fifo_rd_num;  //synthesis keep
  reg         S_fifo_rd_en;  //synthesis keep
  wire        S_fifo_empty;  //synthesis keep
  reg         S_raw8_valid;  //synthesis keep
  reg  [39:0] S_raw8_data;  //synthesis keep
  wire [39:0] S_fifo_rd_data;  //synthesis keep


  //---- kuai 3: shu-ru da-pai tong-bu (valid/data da liang pai, yu MIPI bu-lian-xu jie-zou dui-qi) ----
  //同步处理，MIPI输入进来后，I_csi_valid不是连续，每个I_csi_valid 打怕1次
  always @(posedge I_clk) begin
    O_raw10_frame_start <= I_csi_frame_start;
    O_raw10_frame_end   <= I_csi_frame_end;

    S_csi_valid_1d      <= I_csi_valid;
    S_csi_valid_2d      <= S_csi_valid_1d;

    S_csi_data_1d       <= I_csi_data;
    S_csi_data_2d       <= S_csi_data_1d;
  end

  //---- kuai 4: xiang-wei ji-shu (tiao-jian = {2d,1d,0d} == 3b101) ----
  always @(posedge I_clk) begin
    if({S_csi_valid_2d,S_csi_valid_1d,I_csi_valid}==3'b101)begin//当S_csi_valid_2d和I_csi_valid同时有效，S_csi_valid_2d代表前一个有效32Bit I_csi_valid代表了最新的32bit
      if (S_phase_cnt == 3'd4)  //一个周期结束
        S_phase_cnt <= 3'd0;
      else S_phase_cnt <= S_phase_cnt + 3'd1;
    //----   (0->4 xun-huan; 3b000 shi qing 0) ----
    end else if ({S_csi_valid_2d, S_csi_valid_1d, I_csi_valid} == 3'b000) S_phase_cnt <= 3'd0;
  end


  //---- kuai 5: RAW10 chai-bao he-xin (mei pai ba 4 ge 32bit zi chai cheng 4 ge 10bit xiang-su) ----
  always @(posedge I_clk) begin
    if ({S_csi_valid_2d, S_csi_valid_1d, I_csi_valid} == 3'b101) begin
        //---- case (S_phase_cnt) ----
      case (S_phase_cnt)
        //---- d0 -> P0~P3 ----
        3'd0: begin
          S_raw10_wr_en          <= 1'b1;
          S_raw10_wr_data[39:30] <= {S_csi_data_2d[31:24], I_csi_data[25:24]};  ///P0
          S_raw10_wr_data[29:20] <= {S_csi_data_2d[23:16], I_csi_data[27:26]};  ///P1
          S_raw10_wr_data[19:10] <= {S_csi_data_2d[15 : 8], I_csi_data[29:28]};  ///P2
          S_raw10_wr_data[9:0]   <= {S_csi_data_2d[7 : 0], I_csi_data[31:30]};  ///P3
        end
        //---- d1 -> P4~P7 ----
        3'd1: begin
          S_raw10_wr_en          <= 1'b1;
          S_raw10_wr_data[39:30] <= {S_csi_data_2d[23:16], I_csi_data[17:16]};  ///P4
          S_raw10_wr_data[29:20] <= {S_csi_data_2d[15 : 8], I_csi_data[19:18]};  ///P5
          S_raw10_wr_data[19:10] <= {S_csi_data_2d[7 : 0], I_csi_data[21:20]};  ///P6
          S_raw10_wr_data[9:0]   <= {I_csi_data[31:24], I_csi_data[23:22]};  ///P7
        end
        //---- d2 -> P8~P11 ----
        3'd2: begin
          S_raw10_wr_en          <= 1'b1;
          S_raw10_wr_data[39:30] <= {S_csi_data_2d[15 : 8], I_csi_data[9:8]};  ///P8
          S_raw10_wr_data[29:20] <= {S_csi_data_2d[7 : 0], I_csi_data[11:10]};  ///P9
          S_raw10_wr_data[19:10] <= {I_csi_data[31:24], I_csi_data[13:12]};  ///P10
          S_raw10_wr_data[9:0]   <= {I_csi_data[23:16], I_csi_data[15:14]};  ///P11
        end
        //---- d3 -> P12~P15 ----
        3'd3: begin
          S_raw10_wr_en          <= 1'b1;
          S_raw10_wr_data[39:30] <= {S_csi_data_2d[7 : 0], I_csi_data[1:0]};  ///P12
          S_raw10_wr_data[29:20] <= {I_csi_data[31:24], I_csi_data[3:2]};  ///P13
          S_raw10_wr_data[19:10] <= {I_csi_data[23:16], I_csi_data[5:4]};  ///P14
          S_raw10_wr_data[9:0]   <= {I_csi_data[15 : 8], I_csi_data[7:6]};  ///P15
        end
        //---- d4 -> qing-ling bing wr_en = 0 ----
        3'd4: begin
          S_raw10_wr_en          <= 1'b0;
          S_raw10_wr_data[39:30] <= 'd0;
          S_raw10_wr_data[29:20] <= 'd0;
          S_raw10_wr_data[19:10] <= 'd0;
          S_raw10_wr_data[9:0]   <= 'd0;
        end
      endcase
    //---- else (shu-ru wu-xiao): shu-chu qing-ling ----
    end else begin
      S_raw10_wr_en          <= 1'b0;
      S_raw10_wr_data[39:30] <= 'd0;
      S_raw10_wr_data[29:20] <= 'd0;
      S_raw10_wr_data[19:10] <= 'd0;
      S_raw10_wr_data[9:0]   <= 'd0;
    end
  end

  //---- kuai 6: shu-chu pin-jie + xie shi-neng (40bit = 4 x 10bit, zi-xu fan-zhuan: [9:0] zai zui gao) ----
  always @(posedge I_clk) begin
    O_raw10_data <= {
      S_raw10_wr_data[9:0], S_raw10_wr_data[19:10], S_raw10_wr_data[29:20], S_raw10_wr_data[39:30]
    };
    O_raw10_valid <= S_raw10_wr_en;
  end

//---- yi-xia wei bei // zhu-shi diao de jiu shi-xian (bao-liu yuan-yang, ben ci wei dong) ----


//    input wire        I_clk,
//    input wire        I_rst_n,
//
//    input wire        I_csi_frame_start,
//    input wire        I_csi_frame_end,
//    input wire        I_csi_valid,
//    input wire[31:0]  I_csi_data,
//
//	input wire[9:0]   I_camera_black_level,
//
//    output reg        O_raw8_frame_start,
//    output reg        O_raw8_frame_end,
//    output reg        O_raw8_valid,
//    output wire[31:0] O_raw8_data
//);
//
//    reg        S_csi_valid_1d;
//    reg[31:0]  S_csi_data_1d;
//    reg[2:0]   S_phase_cnt;
//    reg        S_raw10_wr_en;
//    reg[39:0]  S_raw10_wr_data;
//    wire[8:0]  S_fifo_rd_num;
//    reg        S_fifo_rd_en;
//    wire       S_fifo_empty;
//    reg        S_raw8_valid;
//    reg[39:0]  S_raw8_data;
//    wire[39:0] S_fifo_rd_data;
//
//
//    always @(posedge I_clk) begin
//        O_raw8_frame_start <= I_csi_frame_start;
//        O_raw8_frame_end   <= I_csi_frame_end;
//        S_csi_valid_1d     <= I_csi_valid;
//        S_csi_data_1d      <= I_csi_data;
//    end
//
//
//    always @(posedge I_clk) begin
//        if(S_csi_valid_1d)
//            begin
//                if(S_phase_cnt == 'd4)
//                    S_phase_cnt <= 'd0;
//                else
//                    S_phase_cnt <= S_phase_cnt + 'd1;
//            end
//        else
//            S_phase_cnt <= 'd0;
//    end
//
//
//    always @(posedge I_clk) begin
//        if(S_csi_valid_1d)
//            begin
//                case(S_phase_cnt)
//                    'd0:
//                        begin
//                            S_raw10_wr_en          <= 1'b1;
//                            S_raw10_wr_data[39:30] <= {S_csi_data_1d[31:24],I_csi_data[25:24]}; ///P0
//                            S_raw10_wr_data[29:20] <= {S_csi_data_1d[23:16],I_csi_data[27:26]}; ///P1
//                            S_raw10_wr_data[19:10] <= {S_csi_data_1d[15:8], I_csi_data[29:28]}; ///P2
//                            S_raw10_wr_data[9:0]   <= {S_csi_data_1d[7:0],  I_csi_data[31:30]}; ///P3
//                        end
//                    'd1:
//                        begin
//                            S_raw10_wr_en          <= 1'b1;
//                            S_raw10_wr_data[39:30] <= {S_csi_data_1d[23:16],I_csi_data[17:16]}; ///P4
//                            S_raw10_wr_data[29:20] <= {S_csi_data_1d[15:8], I_csi_data[19:18]}; ///P5
//                            S_raw10_wr_data[19:10] <= {S_csi_data_1d[7:0],  I_csi_data[21:20]}; ///P6
//                            S_raw10_wr_data[9:0]   <= {I_csi_data[31:24],   I_csi_data[23:22]}; ///P7
//                        end
//                    'd2:
//                        begin
//                            S_raw10_wr_en          <= 1'b1;
//                            S_raw10_wr_data[39:30] <= {S_csi_data_1d[15:8],I_csi_data[9:8]};   ///P8
//                            S_raw10_wr_data[29:20] <= {S_csi_data_1d[7:0], I_csi_data[11:10]}; ///P9
//                            S_raw10_wr_data[19:10] <= {I_csi_data[31:24],  I_csi_data[13:12]}; ///P10
//                            S_raw10_wr_data[9:0]   <= {I_csi_data[23:16],  I_csi_data[15:14]}; ///P11
//                        end
//                    'd3:
//                        begin
//                            S_raw10_wr_en          <= 1'b1;
//                            S_raw10_wr_data[39:30] <= {S_csi_data_1d[7:0],I_csi_data[1:0]}; ///P12
//                            S_raw10_wr_data[29:20] <= {I_csi_data[31:24], I_csi_data[3:2]}; ///P13
//                            S_raw10_wr_data[19:10] <= {I_csi_data[23:16], I_csi_data[5:4]}; ///P14
//                            S_raw10_wr_data[9:0]   <= {I_csi_data[15:8],  I_csi_data[7:6]}; ///P15
//                        end
//                    'd4:
//                        begin
//                            S_raw10_wr_en          <= 1'b0;
//                            S_raw10_wr_data[39:30] <= 'd0;
//                            S_raw10_wr_data[29:20] <= 'd0;
//                            S_raw10_wr_data[19:10] <= 'd0;
//                            S_raw10_wr_data[9:0]   <= 'd0;
//                        end
//                endcase
//            end
//        else
//            begin
//                S_raw10_wr_en          <= 1'b0;
//                S_raw10_wr_data[39:30] <= 'd0;
//                S_raw10_wr_data[29:20] <= 'd0;
//                S_raw10_wr_data[19:10] <= 'd0;
//                S_raw10_wr_data[9:0]   <= 'd0;
//            end
//    end
//
//
//    always @(posedge I_clk or negedge I_rst_n) begin
//        if(!I_rst_n)
//            S_fifo_rd_en <= 1'b0;
//        else
//            if(S_fifo_empty)
//                S_fifo_rd_en <= 1'b0;
//            else if(S_fifo_rd_num == 'd250)
//                S_fifo_rd_en <= 1'b1;
//            else
//                S_fifo_rd_en <= S_fifo_rd_en;
//    end
//
//    always @(posedge I_clk) begin
//        S_raw8_valid       <= S_fifo_rd_en & (~S_fifo_empty);
//        O_raw8_valid       <= S_raw8_valid;
//
//        S_raw8_data[39:30] <= (S_fifo_rd_data[39:30] - I_camera_black_level) >> 2;
//        S_raw8_data[29:20] <= (S_fifo_rd_data[29:20] - I_camera_black_level) >> 2;
//        S_raw8_data[19:10] <= (S_fifo_rd_data[19:10] - I_camera_black_level) >> 2;
//        S_raw8_data[9:0]   <= (S_fifo_rd_data[9:0]   - I_camera_black_level) >> 2;
//    end
//
//    assign O_raw8_data = {S_raw8_data[37:30],S_raw8_data[27:20],S_raw8_data[17:10],S_raw8_data[7:0]};
//
//    w40_d512_fifo u_w40_d512_fifo(
//        .clk        ( I_clk             ),
//        .rst        ( I_csi_frame_start ),
//
//        .we         ( S_raw10_wr_en     ),
//        .di         ( S_raw10_wr_data   ),
//        .full_flag  (   ),
//        .wrusedw    (   ),
//
//        .re         ( S_fifo_rd_en      ),
//        .dout       ( S_fifo_rd_data    ),
//        .empty_flag ( S_fifo_empty      ),
//        .rdusedw    ( S_fifo_rd_num     )
//    );
//

    
endmodule