//=============================================================================
// tb_awb_live_ratio.v
//   活档 AWB「每个有效像素都启动一次除法器」缺陷实测台。
//
//   被测模块 : proj/baseline/lab3/user_source/hdl_source/awb.v  (模块名 awb)
//              —— camera_to_dsi_display.al:54 指向的唯一在综合链里的 AWB。
//              本 TB 一个字符都不改 RTL，只做激励 + 统计。
//
//   激励      : 真实像素流 1,1,0 valid 图案（2/3 占空比），每拍 4 像素打包，
//               96bit = {P3,P2,P1,P0}，每像素 {R[23:16],G[15:8],B[7:0]}。
//               每行 320 个有效拍（=1280 像素 = IMG_WIDTH），共 8 行（4 行中性 +
//               4 行偏绿，见 CASE 定义），每个 CASE 跑 1 帧，帧间空转 1200 拍排空流水。
//
//   CASE A : 均匀场        R=80  G=100 B=90                 （期望 R/G≈1.000）
//   CASE B : 空间不均匀场  前半 4 行 100/100/100（中性）
//                          后半 4 行  60/100/ 90（偏绿 R/G=0.6）
//                          整帧 ΣR/ΣG 与 ΣB/ΣG 与 CASE A 相同（帧均值 80/100/90）
//   CASE C : 均匀场但增益不可精确表示  R=81 G=100 B=91
//                          gain_r = floor(100/81*65536) = 80909，
//                          R_out = 81*80909>>16 = 99.9999 ⇒ 截断得 99。
//                          用来量化输出端 [23:16] 截断造成的 −0.5 码系统性偏置。
//
//   统计      : 对「输出帧」累加 ΣR_out/ΣG_out/ΣB_out、像素数、Σ(R-G)/Σ(B-G)，
//               帧末按固定格式打印一行。
//
//   注        : 若 divider_gate.v 门级网表跑不动，脚本改用同目录
//               divider_behav.v（行为级 divider，端口/流水完全一致，level_nu=50），
//               用了就必须在报告里声明「行为级替换」。
//=============================================================================
`timescale 1ns/1ps

//=============================================================================
// tb_awb_live_ratio_2f.v  —— tb_awb_live_ratio.v 的两帧变体（2026-10-12）
//   双缓冲补丁在帧边界原子切换 ⇒ 第 0 帧仍用 1.0000x、第 1 帧才用上整帧比值。
//   所以每个 CASE 跑 2 帧，丢弃第 0 帧、统计第 1 帧。
//   除"每 CASE 两帧 + module 改名"外与母本逐字相同。
//=============================================================================
module tb_awb_live_ratio_2f;

  localparam W     = 1280;      // 图像宽度（像素）
  localparam H     = 8;         // 图像高度（行）
  localparam BPL   = W/4;       // 每行有效拍数 = 320
  localparam NCASE = 3;         // CASE A / B / C
  localparam GAP   = 2;         // 行间空闲拍数
  localparam DRAIN = 2000;      // 帧末流水排空拍数（须大于 signal_delay+除法器总延迟）

  reg clk = 0;
  always #8.3335 clk = ~clk;    // ~60 MHz

  reg         rst_n  = 0;
  reg         tuser  = 0;
  reg         tlast  = 0;
  reg         tvalid = 0;
  reg  [95:0] tdata  = 0;
  wire        tready;
  wire        o_tlast, o_tuser, o_tvalid;
  wire [95:0] o_tdata;
  wire [19:0] o_gain_r, o_gain_b;
  reg         o_tready = 1;

  awb #(.IMG_HEIGHT(H), .IMG_WIDTH(W)) dut (
      .I_clk (clk),    .I_rst_n(rst_n), .I_tlast(tlast), .I_tuser(tuser),
      .I_tdata(tdata), .I_tvalid(tvalid), .I_tready(tready),
      .O_tlast(o_tlast), .O_tuser(o_tuser), .O_tdata(o_tdata),
      .O_tvalid(o_tvalid), .O_tready(o_tready),
      .O_gain_r(o_gain_r), .O_gain_b(o_gain_b)
  );

  //---------------------------------------------------------------- CASE 定义
  // 当前 CASE 号（0=A, 1=B, 2=C）；前 H/2 行用 _n 组，后 H/2 行用 _l 组。
  integer ci = 0;

  reg [7:0] A_rn, A_gn, A_bn, A_rl, A_gl, A_bl;   // CASE A
  reg [7:0] B_rn, B_gn, B_bn, B_rl, B_gl, B_bl;   // CASE B
  reg [7:0] C_rn, C_gn, C_bn, C_rl, C_gl, C_bl;   // CASE C

  task set_case;
    input integer n;
    begin
      ci = n;
      case (n)
        0: begin A_rn=8'd80;  A_gn=8'd100; A_bn=8'd90;
                 A_rl=8'd80;  A_gl=8'd100; A_bl=8'd90;  end
        1: begin B_rn=8'd100; B_gn=8'd100; B_bn=8'd100;
                 B_rl=8'd60;  B_gl=8'd100; B_bl=8'd90;  end
        2: begin C_rn=8'd81;  C_gn=8'd100; C_bn=8'd91;
                 C_rl=8'd81;  C_gl=8'd100; C_bl=8'd91;  end
      endcase
    end
  endtask

  function [7:0] px_r; input integer row; begin
    case (ci)
      0: px_r = (row < H/2) ? A_rn : A_rl;
      1: px_r = (row < H/2) ? B_rn : B_rl;
      2: px_r = (row < H/2) ? C_rn : C_rl;
    endcase
  end endfunction

  function [7:0] px_g; input integer row; begin
    case (ci)
      0: px_g = (row < H/2) ? A_gn : A_gl;
      1: px_g = (row < H/2) ? B_gn : B_gl;
      2: px_g = (row < H/2) ? C_gn : C_gl;
    endcase
  end endfunction

  function [7:0] px_b; input integer row; begin
    case (ci)
      0: px_b = (row < H/2) ? A_bn : A_bl;
      1: px_b = (row < H/2) ? B_bn : B_bl;
      2: px_b = (row < H/2) ? C_bn : C_bl;
    endcase
  end endfunction

  //---------------------------------------------------------------- 统计累加器
  integer inR, inG, inB, in_npx;   // 输入帧
  integer ouR, ouG, ouB, npx;      // 输出帧
  integer dRG, dBG;                // Σ(R-G), Σ(B-G)
  integer j, k, f;

  // ---- 按输出行分桶，用来定位偏差出现在帧内哪一段 ------------------------
  integer row_sumR [0:15];
  integer row_sumG [0:15];
  integer row_sumB [0:15];
  integer row_npx  [0:15];
  integer row_idx;
  integer row_beat;                // 当前输出行内已收的拍数
  reg     row_first;               // 本行第一拍
  reg [19:0] gainr_snap [0:15];
  reg [19:0] gainb_snap [0:15];

  task reset_rows;
    integer p;
    begin
      for (p = 0; p < 16; p = p + 1) begin
        row_sumR[p]=0; row_sumG[p]=0; row_sumB[p]=0;
        row_npx[p]=0; gainr_snap[p]=0; gainb_snap[p]=0;
      end
      row_idx = 0;
      row_beat = 0;
      row_first = 1;
    end
  endtask

  // divider 的 done 观测（层级引用，不驱动、不修改 RTL）
  integer done_hi, done_rise;
  integer vld_cyc;
  reg     done_d;
  always @(posedge clk) begin
    done_d <= dut.done[0];
    if (rst_n) begin
      if (tvalid)    vld_cyc   = vld_cyc   + 1;
      if (dut.done[0]) done_hi = done_hi   + 1;
      if (dut.done[0] & ~done_d) done_rise = done_rise + 1;
    end
  end

  always @(posedge clk) if (tvalid) begin
    for (j = 0; j < 4; j = j + 1) begin
      inR = inR + tdata[24*j+16 +: 8];
      inG = inG + tdata[24*j+ 8 +: 8];
      inB = inB + tdata[24*j    +: 8];
    end
    in_npx = in_npx + 4;
  end

  always @(posedge clk) if (o_tvalid) begin
    if (o_tuser || row_first) begin        // 行首：换桶并抓一次增益快照
      if (!row_first) row_idx = row_idx + 1;
      row_first = 0;
      row_beat  = 0;
      if (row_idx > 15) row_idx = 15;
      gainr_snap[row_idx] = dut.in_r_r1;
      gainb_snap[row_idx] = dut.in_b_r1;
    end
    for (j = 0; j < 4; j = j + 1) begin
      ouR = ouR + o_tdata[24*j+16 +: 8];
      ouG = ouG + o_tdata[24*j+ 8 +: 8];
      ouB = ouB + o_tdata[24*j    +: 8];
      dRG = dRG + ($signed({1'b0,o_tdata[24*j+16 +: 8]})
                 - $signed({1'b0,o_tdata[24*j+ 8 +: 8]}));
      dBG = dBG + ($signed({1'b0,o_tdata[24*j    +: 8]})
                 - $signed({1'b0,o_tdata[24*j+ 8 +: 8]}));
      if (row_beat < 320) begin            // 每桶 1280 像素（320 拍）
        row_sumR[row_idx] = row_sumR[row_idx] + o_tdata[24*j+16 +: 8];
        row_sumG[row_idx] = row_sumG[row_idx] + o_tdata[24*j+ 8 +: 8];
        row_sumB[row_idx] = row_sumB[row_idx] + o_tdata[24*j    +: 8];
        row_npx [row_idx] = row_npx [row_idx] + 1;
      end
    end
    row_beat = row_beat + 1;
    // 行内像素数恰好 1280（320 拍）⇒ 到点就换桶
    if (row_beat >= 320) begin
      row_idx   = row_idx + 1;
      row_first = 1;
      row_beat  = 0;
    end
    npx = npx + 4;
  end

  task reset_acc; begin
    inR=0; inG=0; inB=0; in_npx=0;
    ouR=0; ouG=0; ouB=0; npx=0; dRG=0; dBG=0;
    vld_cyc=0; done_hi=0; done_rise=0;
  end endtask

  task report;
    integer srg, sbg;
    reg [8*12:1] trg, tbg;
    begin
      srg = (dRG >= 0) ? 1 : -1;
      sbg = (dBG >= 0) ? 1 : -1;
      $sformat(trg, "%0s%0d.%0.2d", (srg>=0)?"+":"-",
               (srg*dRG*100/npx)/100, ((srg*dRG*100/npx)%100));
      $sformat(tbg, "%0s%0d.%0.2d", (sbg>=0)?"+":"-",
               (sbg*dBG*100/npx)/100, ((sbg*dBG*100/npx)%100));
      $display("CASE %0s: R/G=%.4f B/G=%.4f mean R-G=%0s B-G=%0s (meanG=%0d.%0.2d)",
               (ci==0) ? "A" : (ci==1) ? "B" : "C",
               ouR*1.0/ouG, ouB*1.0/ouG, trg, tbg,
               ouG/npx, ((ouG*100/npx)%100));
      $display("         raw: inR=%0d inG=%0d inB=%0d inN=%0d | ouR=%0d ouG=%0d ouB=%0d outN=%0d | gainR=%h gainB=%h",
               inR, inG, inB, in_npx, ouR, ouG, ouB, npx,
               dut.in_r_r1, dut.in_b_r1);
      $display("         div: vld_cyc=%0d done_hi=%0d done_rise=%0d  (done per valid=%0d.0)",
               vld_cyc, done_hi, done_rise, done_hi/vld_cyc);
      // 按输出行分桶，看偏差出现在帧内哪一段
      for (k = 0; k < 8; k = k + 1) begin
        if (row_npx[k] != 0)
          $display("         row%0d: npx=%0d sumR=%0d sumG=%0d sumB=%0d | R/G=%.4f B/G=%.4f | gainR_at_rowstart=%h",
                   k, row_npx[k], row_sumR[k], row_sumG[k], row_sumB[k],
                   row_sumR[k]*1.0/row_sumG[k], row_sumB[k]*1.0/row_sumG[k],
                   gainr_snap[k]);
      end
    end
  endtask

  //---------------------------------------------------------------- 驱动
  task drive_frame; begin
    for (k = 0; k < H; k = k + 1) begin
      repeat (GAP) @(negedge clk);
      tdata  = { {px_r(k),px_g(k),px_b(k)}, {px_r(k),px_g(k),px_b(k)},
                 {px_r(k),px_g(k),px_b(k)}, {px_r(k),px_g(k),px_b(k)} };
      tvalid = 1;
      tuser  = (k == 0);
      tlast  = 0;
      repeat (BPL-1) @(negedge clk);
      tlast  = 1;
      @(negedge clk);
      tlast  = 0;
      tvalid = 0;
      tuser  = 0;
    end
    repeat (DRAIN) @(negedge clk);
  end endtask

  //---------------------------------------------------------------- 主流程
  initial begin
    reset_acc;
    rst_n = 0;
    repeat (10) @(negedge clk);
    rst_n = 1;
    repeat (5)  @(negedge clk);

    for (f = 0; f < NCASE; f = f + 1) begin
      set_case(f);
      reset_acc;
      reset_rows;
      $display("--- warm-up frame 0  CASE %0s (discarded) ---",
               (f==0)?"A":(f==1)?"B":"C");
      drive_frame;                       // 帧 0：双缓冲尚未收敛，丢弃
      reset_acc;
      reset_rows;
      $display("--- MEASURED frame 1  CASE %0s ---",
               (f==0)?"A":(f==1)?"B":"C");
      drive_frame;                       // 帧 1：已用整帧比值，统计这一帧
      report;
    end

    $display("======== DONE ========");
    $finish;
  end

  initial begin
    #4000000;
    $display("*** TIMEOUT ***");
    $finish;
  end

endmodule
