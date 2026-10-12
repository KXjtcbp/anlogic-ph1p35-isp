//=============================================================================
// 文件      : isp/awb/awb.v
// 模块      : awb
// 功能      : 自动白平衡(AWB)。按行统计 4 路像素的 R/G/B 累加和，用除法器求 G/R、G/B 比值作为 R、B 通道增益(20bit Q16 定点)，乘回像素后饱和截断到 8bit 输出，使画面三通道均值趋于一致。
// 数据通路  : I_tdata(96bit = 4 像素 × RGB888) → 打 3 拍寄存 → 拆 4 组 RGB888 → 按行累加 sum_r/sum_g/sum_b[0:3] → 4 组 × (G/R、G/B) divider IP 求 Q16 商 → 20bit 增益寄存器 in_r_rX/in_b_rX → signal_delay 缓存 50 拍把像素对齐到增益 → R/B 增益乘法(28bit) → 饱和截断回 8bit → 拼回 96bit。
// 时钟/复位 : 单时钟 I_clk；I_rst_n 低电平异步复位(所有时序块为 posedge I_clk or negedge I_rst_n)；I_tuser(帧首)在统计与增益块中作同步清零，用于按行重开统计窗。
// 依赖      : divider（TD 生成的除法器网表，定义在 isp/awb/divider/divider_gate.v，参数 PIPLE=50 即流水 50 拍）、signal_delay（本目录内，内部用 blk_mem_gen_awb_delay_signal）。
// 综合/实现 : generate for 展开 4 组、共 8 个除法器实例；本模块自身不含 BRAM。默认参数 IMG_HEIGHT=1080/IMG_WIDTH=1920，本工程由 isp_top.v:144 例化为 IMG_HEIGHT=720、IMG_WIDTH=1280。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
/*****************************************************************
Company : MiLianKe Electronic Technology Co., Ltd.
WebSite:https://www.milianke.com
TechWeb:https://www.uisrc.com
tmall-shop:https://milianke.tmall.com
jd-shop:https://milianke.jd.com
taobao-shop: https://milianke.taobao.com
Description: 
The reference demo provided by Milianke is only used for learning. 
We cannot ensure that the demo itself is free of bugs, so users 
should be responsible for the technical problems and consequences
caused by the use of their own products.
@Author      :   XiaoQingquan 
@Time        :   2024/10 
version:     :   
@Description :   在原基础上删去了一些赘余的代码，并且优化了时序，加入BRAM IP核，
                 让从除法器出来的每一个数据都可以对上相应的像素数据进行增益，使
                 得它的适用行更加广泛了。
*****************************************************************/
module awb  #(   
    parameter IMG_HEIGHT = 1080,   // 图像高度参数，默认值为1080
    parameter IMG_WIDTH  = 1920    // 图像宽度参数，默认值为1920
) 
(
    input                   I_clk  ,    // 输入时钟信号
    input                   I_rst_n,    // 输入复位信号，低电平有效

    input                   I_tlast  ,  // 行结束信号
    input                   I_tuser  ,  // 帧开始信号
    input [95:0]            I_tdata  ,  // 输入数据，总共包含4个像素的RGB值，每个像素24位，4*24=96位
    input                   I_tvalid ,  // 输入数据有效信号
    output                  I_tready ,  // 输入数据准备好信号

    output                  O_tlast  ,  // 输出行结束信号
    output                  O_tuser  ,  // 输出帧开始信号
    output [95:0]           O_tdata  ,  // 输出数据
    output                  O_tvalid ,  // 输出数据有效信号
    input                   O_tready    // 输出数据准备好信号
);

/*****************************************************************
                          RGB565转RGB888（未使用部分）                                        
*****************************************************************/

// //RGB565转RGB888的代码（此部分代码被注释掉，未使用）
// wire [4:0]  rgb565_r   = I_st_data[11+:5];
// wire [5:0]  rgb565_g   = I_st_data[5+:6];
// wire [4:0]  rgb565_b   = I_st_data[0+:5];

// wire [23:0] rgb888     = {{rgb565_r[4:0],rgb565_r[2:0]},{rgb565_g[5:0],rgb565_g[1:0]},{rgb565_b[4:0],rgb565_b[2:0]}};

// wire [7:0]  rgb888_r   = rgb888[16+:8];
// wire [7:0]  rgb888_g   = rgb888[8+:8] ;
// wire [7:0]  rgb888_b   = rgb888[0+:8] ;

/*****************************************************************
                          中间信号                                        
*****************************************************************/

//---- 输入数据/有效信号打拍（3 级流水） ----
  reg         I_tvalid_r0,I_tvalid_r1;			// 输入有效信号的寄存
  reg  [95:0] I_tdata_d0,I_tdata_d1,I_tdata_d2; // 输入数据的寄存


//---- 白平衡统计累加器（4 通道并行，按行清零） ----
  // 累加RGB通道的数值，用于计算平均值
  reg  [31:0]         sum_r[0:3];
  reg  [31:0]         sum_g[0:3];
  reg  [31:0]         sum_b[0:3];

  
  wire  [95:0]        data_d0 ;		// 延时后的数据
  wire                valid_d0;     // 延时后的有效信号
  wire                I_tuser_r0;   // 延时后的帧开始信号 
                                    
  reg                 I_tuser_r1;   // 帧开始信号的寄存
                                    
  reg   [95:0]        data_d1 ;     // 再次延时后的数据
  reg                 valid_d1;     // 再次延时后的有效信号

  /*****************************************************************
                            平均值计算                                      
*****************************************************************/

	// 对输入数据和有效信号进行寄存，形成流水线
  always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n) begin
        I_tdata_d0  <= 0;
        I_tdata_d1  <= 0;
        I_tdata_d2  <= 0;
        {I_tvalid_r0,I_tvalid_r1} <= 0;  // I_tvalid_r0/r1 两级有效信号一并清零
    end else begin
        I_tdata_d0  <= I_tdata   ;  // d0 = 当前输入，与 I_tvalid_r0 同拍
        I_tdata_d1  <= I_tdata_d0;  // d1 = 上一拍数据
        I_tdata_d2  <= I_tdata_d1;  // d2 在本文件内未见其它引用（仅此处移位）
        I_tvalid_r0 <= I_tvalid;
        I_tvalid_r1 <= I_tvalid_r0;
    end
  end
  
//---- 96bit 拆 4×RGB888（每组 24bit：R@[23:16] G@[15:8] B@[7:0]） ----
  // 将输入数据拆分为4个像素的RGB分量
    wire [7:0] rgb888_r_d0[0:3];
    wire [7:0] rgb888_g_d0[0:3];
    wire [7:0] rgb888_b_d0[0:3];

    assign  rgb888_r_d0[0] = I_tdata_d0[16+:8];  // 像素0 R = bit[23:16]
    assign  rgb888_g_d0[0] = I_tdata_d0[8+:8];
    assign  rgb888_b_d0[0] = I_tdata_d0[0+:8];
  
    assign  rgb888_r_d0[1] = I_tdata_d0[40+:8];  // 像素1 R = bit[47:40]
    assign  rgb888_g_d0[1] = I_tdata_d0[32+:8];
    assign  rgb888_b_d0[1] = I_tdata_d0[24+:8];
  
    assign  rgb888_r_d0[2] = I_tdata_d0[64+:8];  // 像素2 R = bit[71:64]
    assign  rgb888_g_d0[2] = I_tdata_d0[56+:8];
    assign  rgb888_b_d0[2] = I_tdata_d0[48+:8];
  
    assign  rgb888_r_d0[3] = I_tdata_d0[88+:8];  // 像素3 R = bit[95:88]
    assign  rgb888_g_d0[3] = I_tdata_d0[80+:8];
    assign  rgb888_b_d0[3] = I_tdata_d0[72+:8];

//---- 行内累加：统计窗 = 一整行 ----
// 对每个通道的值进行累加，用于计算平均值
  always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n || I_tuser) begin  // 帧首(I_tuser)同步清零：统计窗按行重开
	  // 复位或行开始信号有效时，清零累加器
      sum_r[0] <= 0;
      sum_g[0] <= 0;
      sum_b[0] <= 0;

      sum_r[1] <= 0;
      sum_g[1] <= 0;
      sum_b[1] <= 0;

      sum_r[2] <= 0;
      sum_g[2] <= 0;
      sum_b[2] <= 0;

      sum_r[3] <= 0;
      sum_g[3] <= 0;
      sum_b[3] <= 0;
    end else if (I_tvalid_r0) begin  // 仅在数据有效拍累加
	  // 当输入有效时，累加RGB分量的值
      sum_r[0] <= sum_r[0] + rgb888_r_d0[0];
      sum_g[0] <= sum_g[0] + rgb888_g_d0[0];
      sum_b[0] <= sum_b[0] + rgb888_b_d0[0];

      sum_r[1] <= sum_r[1] + rgb888_r_d0[1];
      sum_g[1] <= sum_g[1] + rgb888_g_d0[1];
      sum_b[1] <= sum_b[1] + rgb888_b_d0[1];

      sum_r[2] <= sum_r[2] + rgb888_r_d0[2];
      sum_g[2] <= sum_g[2] + rgb888_g_d0[2];
      sum_b[2] <= sum_b[2] + rgb888_b_d0[2];

      sum_r[3] <= sum_r[3] + rgb888_r_d0[3];
      sum_g[3] <= sum_g[3] + rgb888_g_d0[3];
      sum_b[3] <= sum_b[3] + rgb888_b_d0[3];
    end
  end



  /*****************************************************************
                           除法运算                                        
*****************************************************************/
//---- 除法器输出与增益来源 ----
  // 定义除法器的输出信号
  wire [47:0] dout_R[3:0];
  wire [47:0] dout_B[3:0];

  wire done[3:0];
  // 提取除法器的输出数据，用于后续增益计算
  wire [47:0] in_r_x1;
  wire [47:0] in_b_x1;
  assign in_r_x1 = dout_R[0][47:0];  // 通道0：G/R 商（Q16 定点）
  assign in_b_x1 = dout_B[0][47:0];  // 通道0：G/B 商（Q16 定点）


  wire [47:0] in_r_x2;
  wire [47:0] in_b_x2;
  assign in_r_x2 = dout_R[1][47:0];
  assign in_b_x2 = dout_B[1][47:0];


  wire [47:0] in_r_x3;
  wire [47:0] in_b_x3;
  assign in_r_x3 = dout_R[2][47:0];
  assign in_b_x3 = dout_B[2][47:0];


  wire [47:0] in_r_x4;
  wire [47:0] in_b_x4;
  assign in_r_x4 = dout_R[3][47:0];
  assign in_b_x4 = dout_B[3][47:0];
    

/*****************************************************************
                   IP 调用                                    
*****************************************************************/
//---- 除法器 IP 例化：4 通道 × (G/R, G/B)，流水 50 拍 ----
    //为了保证合理的延迟，这里使用了除法器

  genvar i;
  generate
    for (i = 0; i < 4; i = i + 1) begin : div_gen
      divider div_gen_G_R_r1 (
          .clk(I_clk),  					// input wire aclk
          .rst(!I_rst_n),                    
          .start(I_tvalid_r1),              // 输入除数有效信号
          .denominator(sum_r[i]),  			// 输入除数数据，R通道的累加值  // 分母 = 本行 R 累加和
          .numerator({sum_g[i],16'd0}),  	// 输入被除数数据，G通道的累加值，扩展16位  // 分子 = G 累加和左移 16 位，使商为 Q16
          .quotient(dout_R[i]),  			// 输出数据，G/R的比值  // quotient ≈ (G/R) × 65536
          .done(done[i])                    // 输出数据有效信号
      );

      divider divide_G_B_r1 (
          .clk(I_clk),  					// input wire aclk
          .rst(!I_rst_n),                    
          .start(I_tvalid_r1),              // 输入除数有效信号
          .denominator(sum_b[i]),  			// 输入除数数据，R通道的累加值
          .numerator({sum_g[i],16'd0}),  	// 输入被除数数据，G通道的累加值，扩展16位  // 分子同为 G 累加和，分母换成 B 累加和
          .quotient(dout_B[i]),  			// 输出数据，G/R的比值  // quotient ≈ (G/B) × 65536
          .done()                           // 输出数据有效信号
      );
    end
  endgenerate
     
//---- 数据延迟 50 拍：与除法器流水(DIVIDER 参数 PIPLE=50)对齐 ----
	// 信号延迟模块，用于同步信号，延迟50个时钟周期
    signal_delay #(
        .IMG_HEIGHT   (IMG_HEIGHT),
        .IMG_WIDTH    (IMG_WIDTH ),
        .DATA_WIDTH   (96  ),	// 数据位宽为96位
        .DELAY_CYCLE  (50)      // 延迟50个时钟周期
    )signal_delay_d (           
         .I_clk  (I_clk  ),     // 输入时钟信号
         .I_rst_n(I_rst_n),     // 输入复位信号
         .I_tuser(I_tuser),  	// 输入帧开始信号
         .I_valid(I_tvalid_r1), // 输入数据有效信号
         .I_data (I_tdata_d1 ), // 输入数据
         .O_valid(valid_d0   ), // 输出数据有效信号
         .O_data (data_d0    ), // 输出数据
         .O_tuser(I_tuser_r0 )  // 输出帧开始信号
    );

/*****************************************************************
                            增益计算                                      
*****************************************************************/

//---- 增益寄存器（20bit Q16 定点；1.0 = 20'h10000） ----
    reg  [19:0]   in_r_r1;
    reg  [19:0]   in_b_r1;

    reg  [19:0]   in_r_r2;
    reg  [19:0]   in_b_r2;

    reg  [19:0]   in_r_r3;
    reg  [19:0]   in_b_r3;

    reg  [19:0]   in_r_r4;
    reg  [19:0]   in_b_r4;

// ================= [HDR-2026-10-11f] 白平衡增益：帧锁存 + 阻尼 + 钳位 =================
// 见 _analysis/scripts/patch_awb_gain.py 与 sim/awb/tb_awb_zones.v
//   WB_GAIN_MIN/MAX  Q16 定点：20'h10000 = 1.000x
//   WB_DAMP_SHIFT    每帧只更新一次，时间常数 ~= 2^WB_DAMP_SHIFT 帧
    localparam [19:0] WB_GAIN_MIN   = 20'h08000;   // 0.500x
    localparam [19:0] WB_GAIN_MAX   = 20'h40000;   // 4.000x
    localparam [4:0]  WB_DAMP_SHIFT = 5'd2;        // ~4 帧时间常数

    reg  [19:0]   in_r_tgt1, in_b_tgt1;            // 自由运行的目标增益（每拍跟踪商）
    reg  [19:0]   in_r_tgt2, in_b_tgt2;
    reg  [19:0]   in_r_tgt3, in_b_tgt3;
    reg  [19:0]   in_r_tgt4, in_b_tgt4;

    // I_tuser 上升沿检测：上游若把 tuser 给成电平（多拍），增益也必须只更新一次
    reg  S_tuser_d;
    wire S_tuser_rise;
    always @(posedge I_clk or negedge I_rst_n)
        if (!I_rst_n) S_tuser_d <= 1'b0;
        else          S_tuser_d <= I_tuser;
    assign S_tuser_rise = I_tuser & ~S_tuser_d;

    // 商 -> 钳位后的 Q16 增益
    function [19:0] wb_clamp_gain;
        input [47:0] q;
        begin
            if (|q[47:20])                  wb_clamp_gain = WB_GAIN_MAX;  // 溢出 => 上限
            else if (q[19:0] < WB_GAIN_MIN) wb_clamp_gain = WB_GAIN_MIN;  // 下限兜底
            else                            wb_clamp_gain = q[19:0];
        end
    endfunction

    // 阻尼：每帧向目标走 1/2^WB_DAMP_SHIFT，保证至少 1 LSB 以便收敛
    function [19:0] wb_damp_gain;
        input [19:0] cur;
        input [19:0] tgt;
        reg   [19:0] d;
        begin
            d = (tgt > cur) ? (tgt - cur) : (cur - tgt);
            d = d >> WB_DAMP_SHIFT;
            if (d == 20'd0) d = 20'd1;
            wb_damp_gain = (tgt > cur) ? (cur + d) : (cur - d);
        end
    endfunction
// ===================================================================================
	
//---- 增益计算与上限钳位（4 通道同构，仅各自 done 拍更新） ----
	// 计算增益，防止增益过大溢出，限制在0xFFFFF
        // [HDR-2026-10-11f] 通道1：目标增益每拍跟踪（只钳位），实际增益只在帧边界按阻尼更新
    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_tgt1 <= 20'h10000;
            in_b_tgt1 <= 20'h10000;
        end
        else if(done[0])begin
            in_r_tgt1 <= wb_clamp_gain(in_r_x1);
            in_b_tgt1 <= wb_clamp_gain(in_b_x1);
        end
    end

    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_r1 <= 20'h10000;   // R 增益 = 1.0（Q16：65536 = 20'h10000）
            in_b_r1 <= 20'h10000;   // B 增益 = 1.0
        end
        else if(S_tuser_rise)begin   // 只在帧边界（tuser 上升沿）更新 => 帧内严格恒定
            in_r_r1 <= wb_damp_gain(in_r_r1, in_r_tgt1);
            in_b_r1 <= wb_damp_gain(in_b_r1, in_b_tgt1);
        end
    end


        // [HDR-2026-10-11f] 通道2：目标增益每拍跟踪（只钳位），实际增益只在帧边界按阻尼更新
    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_tgt2 <= 20'h10000;
            in_b_tgt2 <= 20'h10000;
        end
        else if(done[1])begin
            in_r_tgt2 <= wb_clamp_gain(in_r_x2);
            in_b_tgt2 <= wb_clamp_gain(in_b_x2);
        end
    end

    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_r2 <= 20'h10000;   // R 增益 = 1.0（Q16：65536 = 20'h10000）
            in_b_r2 <= 20'h10000;   // B 增益 = 1.0
        end
        else if(S_tuser_rise)begin   // 只在帧边界（tuser 上升沿）更新 => 帧内严格恒定
            in_r_r2 <= wb_damp_gain(in_r_r2, in_r_tgt2);
            in_b_r2 <= wb_damp_gain(in_b_r2, in_b_tgt2);
        end
    end




        // [HDR-2026-10-11f] 通道3：目标增益每拍跟踪（只钳位），实际增益只在帧边界按阻尼更新
    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_tgt3 <= 20'h10000;
            in_b_tgt3 <= 20'h10000;
        end
        else if(done[2])begin
            in_r_tgt3 <= wb_clamp_gain(in_r_x3);
            in_b_tgt3 <= wb_clamp_gain(in_b_x3);
        end
    end

    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_r3 <= 20'h10000;   // R 增益 = 1.0（Q16：65536 = 20'h10000）
            in_b_r3 <= 20'h10000;   // B 增益 = 1.0
        end
        else if(S_tuser_rise)begin   // 只在帧边界（tuser 上升沿）更新 => 帧内严格恒定
            in_r_r3 <= wb_damp_gain(in_r_r3, in_r_tgt3);
            in_b_r3 <= wb_damp_gain(in_b_r3, in_b_tgt3);
        end
    end





        // [HDR-2026-10-11f] 通道4：目标增益每拍跟踪（只钳位），实际增益只在帧边界按阻尼更新
    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_tgt4 <= 20'h10000;
            in_b_tgt4 <= 20'h10000;
        end
        else if(done[3])begin
            in_r_tgt4 <= wb_clamp_gain(in_r_x4);
            in_b_tgt4 <= wb_clamp_gain(in_b_x4);
        end
    end

    always @(posedge I_clk or negedge I_rst_n)begin
        if(!I_rst_n)begin
            in_r_r4 <= 20'h10000;   // R 增益 = 1.0（Q16：65536 = 20'h10000）
            in_b_r4 <= 20'h10000;   // B 增益 = 1.0
        end
        else if(S_tuser_rise)begin   // 只在帧边界（tuser 上升沿）更新 => 帧内严格恒定
            in_r_r4 <= wb_damp_gain(in_r_r4, in_r_tgt4);
            in_b_r4 <= wb_damp_gain(in_b_r4, in_b_tgt4);
        end
    end

//---- 延时链再打 1 拍：把 valid/data/tuser 对齐到同一拍 ----
    // 信号同步，延迟一级
    always @(posedge I_clk or negedge I_rst_n) begin
      if (!I_rst_n) begin
          valid_d1 <= 0;
          data_d1  <= 0;
          I_tuser_r1 <= 0;
      end else begin
          valid_d1 <= valid_d0;
          data_d1  <= data_d0 ;
          I_tuser_r1 <= I_tuser_r0;
      end
    end
/*****************************************************************
                           像素值计算                                       
*****************************************************************/

    reg [27:0] R_new_r1;
    reg [27:0] G_new_r1;
    reg [27:0] B_new_r1;

    reg [27:0] R_new_r2;
    reg [27:0] G_new_r2;
    reg [27:0] B_new_r2;

    reg [27:0] R_new_r3;
    reg [27:0] G_new_r3;
    reg [27:0] B_new_r3;

    reg [27:0] R_new_r4;
    reg [27:0] G_new_r4;
    reg [27:0] B_new_r4;


//---- 从延时后的 96bit 中再拆 4×RGB888 ----
    wire   [7:0] rgb888_r_d1[0:3];
    wire   [7:0] rgb888_g_d1[0:3];
    wire   [7:0] rgb888_b_d1[0:3];

    assign  rgb888_r_d1[0] = data_d1[16+:8];
    assign  rgb888_g_d1[0] = data_d1[8+:8];
    assign  rgb888_b_d1[0] = data_d1[0+:8];

    assign  rgb888_r_d1[1] = data_d1[40+:8];
    assign  rgb888_g_d1[1] = data_d1[32+:8];
    assign  rgb888_b_d1[1] = data_d1[24+:8];

    assign  rgb888_r_d1[2] = data_d1[64+:8];
    assign  rgb888_g_d1[2] = data_d1[56+:8];
    assign  rgb888_b_d1[2] = data_d1[48+:8];

    assign  rgb888_r_d1[3] = data_d1[88+:8];
    assign  rgb888_g_d1[3] = data_d1[80+:8];
    assign  rgb888_b_d1[3] = data_d1[72+:8];
	
//---- 增益乘法：R/B 乘增益，G 旁路 ----
	// 计算新的RGB值，应用增益
    always @(posedge I_clk or negedge I_rst_n)begin 
        if(!I_rst_n)begin
            R_new_r1 <= 0;
            G_new_r1 <= 0;
            B_new_r1 <= 0;

            R_new_r2 <= 0;
            G_new_r2 <= 0;
            B_new_r2 <= 0;

            R_new_r3 <= 0;
            G_new_r3 <= 0;
            B_new_r3 <= 0;

            R_new_r4 <= 0;
            G_new_r4 <= 0;
            B_new_r4 <= 0;
        end
        else if(valid_d1) begin
            R_new_r1 <= in_r_r1 * rgb888_r_d1[0];  // 20bit(Q16) × 8bit = 28bit，结果仍为 Q16 → 整数部分在 [27:16]
            G_new_r1 <=           rgb888_g_d1[0];  // G 不乘增益，等价 1.0×
            B_new_r1 <= in_b_r1 * rgb888_b_d1[0];

            R_new_r2 <= in_r_r2 * rgb888_r_d1[1];
            G_new_r2 <=           rgb888_g_d1[1];
            B_new_r2 <= in_b_r2 * rgb888_b_d1[1];

            R_new_r3 <= in_r_r3 * rgb888_r_d1[2];
            G_new_r3 <=           rgb888_g_d1[2];
            B_new_r3 <= in_b_r3 * rgb888_b_d1[2];

            R_new_r4 <= in_r_r4 * rgb888_r_d1[3];
            G_new_r4 <=           rgb888_g_d1[3];
            B_new_r4 <= in_b_r4 * rgb888_b_d1[3];
        end
    end

/*****************************************************************
                            像素值截断                                      
*****************************************************************/

    wire [7:0] R_new_x1;
    wire [7:0] G_new_x1;
    wire [7:0] B_new_x1;

    wire [7:0] R_new_x2;
    wire [7:0] G_new_x2;
    wire [7:0] B_new_x2;

    wire [7:0] R_new_x3;
    wire [7:0] G_new_x3;
    wire [7:0] B_new_x3;

    wire [7:0] R_new_x4;
    wire [7:0] G_new_x4;
    wire [7:0] B_new_x4;
	
//---- 输出截断回 8bit：R/B 饱和，G 直通 ----
	// 对新的像素值进行截断，防止溢出
    assign R_new_x1 = (R_new_r1[27:24])?255:R_new_r1[23:16];  // 整数部分为 [27:16]；若高 4 位 [27:24] 非 0 说明 >255，饱和到 255，否则取 [23:16]
    assign G_new_x1 =  G_new_r1;  // G 已是 8bit（G_new_r1 高 20 位为 0）
    assign B_new_x1 = (B_new_r1[27:24])?255:B_new_r1[23:16];

    assign R_new_x2 = (R_new_r2[27:24])?255:R_new_r2[23:16];
    assign G_new_x2 =  G_new_r2;
    assign B_new_x2 = (B_new_r2[27:24])?255:B_new_r2[23:16];

    assign R_new_x3 = (R_new_r3[27:24])?255:R_new_r3[23:16];
    assign G_new_x3 =  G_new_r3;
    assign B_new_x3 = (B_new_r3[27:24])?255:B_new_r3[23:16];

    assign R_new_x4 = (R_new_r4[27:24])?255:R_new_r4[23:16];
    assign G_new_x4 =  G_new_r4;
    assign B_new_x4 = (B_new_r4[27:24])?255:B_new_r4[23:16];
/*****************************************************************
                           ͬ同步信号                                      
*****************************************************************/

//---- 输出同步信号：valid/tuser 打 1 拍，tlast 取 valid 下降沿 ----
    reg valid_d2,I_tuser_r2;
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n)begin
            valid_d2 <= 0;
            I_tuser_r2 <= 0;
        end
        else begin
            valid_d2 <= valid_d1;
            I_tuser_r2 <= I_tuser_r1;
        end
    end

	// 输出信号的生成
    assign  O_tlast  = (valid_d1 == 0) && (valid_d2 == 1);   // 行结束信号  // valid 的下降沿 = 一行数据结束
    assign  O_tuser  = I_tuser_r2 ;                          // 帧开始信号
    assign  O_tvalid = valid_d2;                             // 输出有效信号
	
	// 输出数据，由四个像素的数据拼接而成
    assign  O_tdata = O_tvalid?{R_new_x4,G_new_x4,B_new_x4,  // 4 个像素合并回 96bit（像素1 位于最低 24bit）
                       R_new_x3,G_new_x3,B_new_x3,
                       R_new_x2,G_new_x2,B_new_x2,
                       R_new_x1,G_new_x1,B_new_x1}:0;
    // assign O_t_data = {R_new[7-:5],G_new[7-:6],B_new[7-:5]};
	// 输入准备好信号，直接连接到输出准备好信号
    assign  I_tready = O_tready;  // 无内部缓存，直接透传反压
 
endmodule



