//=============================================================================
// 文件      : awb.v
// 模块      : awb #( parameter IMG_HEIGHT = 1080, IMG_WIDTH = 1920 )
// 功能      : 自动白平衡增益：按 R/G/B 三通道累加和算出 R、B 相对 G 的增益，再对延时对齐后的 96bit（4 像素 x 24bit）数据逐像素施加增益。★与 isp\awb\awb.v 同名但内容不同（本文件 383 行、那份 490 行，属另一版本）。核实结论：本文件在 .al 编译清单中，被 isp_top.v:126 例化为 awb，是本工程当前在用的白平衡实现（isp/awb/ 下的同名文件不在 .al 中）。
// 数据通路  : 输入 I_tdata[95:0]（每 24bit 一个像素：[23:16]=R、[15:8]=G、[7:0]=B）、I_tvalid/I_tuser/I_tlast；输出 O_tdata[95:0] 及 O_tvalid/O_tuser/O_tlast，另有 output I_tready 与 input O_tready（方向命名沿用原作者写法，实际是同一对握手）。①累加区：rgb_sum[0] = r+g+b（注释说“削弱白色”，即用亮度阈值排除过亮像素），sum_r/sum_g/sum_b 在 I_tuser 或复位时置 1（避免除零），在 I_tvalid_r0 && (rgb_sum[0] < 720) 时累加（720 是经验阈值）；②除法区：[HDR-2026-10-15a] 已由两个 TD 流水 divider 改为 wb_recip.v（归一化+倒数ROM+一次乘法），.I_den(sum_r[0])/(sum_b[0])、.I_num(sum_g[0])，输出 48bit in_r_x1/in_b_x1；③延时区：例化 signal_delay #(.IMG_HEIGHT,.IMG_WIDTH,.DATA_WIDTH(96),.DELAY_CYCLE(50))，用 BRAM 把像素流延后若干行，等增益算完再对齐；④增益寄存器 in_r_r1/in_b_r1 复位与 I_tuser 时为 20h10000（=1.0 的定点表示），done[0] 时若 |in_r_x1[47:20] 非零则饱和到 20hfffff，否则取 in_r_x1[19:0]；⑤增益乘：R_new_rN <= in_r_r1 * rgb888_r_d1[N-1]，G 不乘，B 乘 in_b_r1；⑥输出饱和 assign R_new_xN = (R_new_rN[27:24]) ? 255 : R_new_rN[23:16]（G 直接取），最后把 4 像素拼回 96bit；O_tlast = (valid_d1==0)&&(valid_d2==1)（在 valid 下降沿产生行结束），O_tuser = I_tuser，O_tvalid = valid_d2，I_tready = O_tready。
// 时钟/复位 : I_clk 上升沿同步；I_rst_n 异步复位、低电平有效；内部有 r0/r1/d1/d2 多级流水与 signal_delay 的整行延时，所以输出相对输入整体延后若干行。
// 依赖      : [HDR-2026-10-15a] wb_recip.v（倒数查表除法，替代原两个 TD divider）与 signal_delay（本目录 signal_delay.v，内部再例化 BRAM blk_mem_gen_awb_delay_signal）。第 46~55 行有被 // 注释掉的 RGB565->RGB888 代码，仅作历史保留。
// 综合/实现 : 本文件在 camera_to_dsi_display.al 的编译清单中，参与本工程综合实现；用到除法器与 BRAM，是本工程资源占用较大的模块之一。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
//---- kuai 1: duan-kou sheng-ming (96bit RGB888 liu-shui + tvalid/tuser/tlast shou-wo) ----
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
    parameter IMG_HEIGHT = 1080,
    parameter IMG_WIDTH  = 1920
) 
(
    input                   I_clk  ,
    input                   I_rst_n,


    input                   I_tlast  ,
    input                   I_tuser  ,
    input [95:0]            I_tdata  ,
    input                   I_tvalid , 
    output                  I_tready ,

    output                  O_tlast  ,
    output                  O_tuser  ,
    output [95:0]           O_tdata  ,
    output                  O_tvalid ,
    input                   O_tready ,

    // [HDR-2026-10-12k] 遥测输出：当前生效的 R/B 白平衡增益（20bit Q16，0x10000 = 1.000x）
    //   为什么要引出来：本模块的增益每一帧都被 I_tuser 复位成 1.000x，之后由 done[0]
    //   用「本帧到当前行为止的累加比」持续覆盖。屏幕上那点固定偏色到底是
    //   "增益没算对" 还是 "算对了但没真正作用到像素上"，只有把 in_r_r1 / in_b_r1
    //   拿出来看才能区分 —— 光看画面永远分不清。
    //   纯组合直通，不增加任何时序级、不占额外资源。
    output [19:0]           O_gain_r ,
    output [19:0]           O_gain_b
);

/*****************************************************************
                          RGB565תRGB888                                        
*****************************************************************/

//---- kuai 2: bei // zhu-shi diao de RGB565 -> RGB888 dai-ma (jin bao-liu) ----
    // //RGB565??????888
    // wire [4:0]  rgb565_r   = I_st_data[11+:5];
    // wire [5:0]  rgb565_g   = I_st_data[5+:6];
    // wire [4:0]  rgb565_b   = I_st_data[0+:5];
    
    // wire [23:0] rgb888     = {{rgb565_r[4:0],rgb565_r[2:0]},{rgb565_g[5:0],rgb565_g[1:0]},{rgb565_b[4:0],rgb565_b[2:0]}};
    
    // wire [7:0]  rgb888_r   = rgb888[16+:8];
    // wire [7:0]  rgb888_g   = rgb888[8+:8] ;
    // wire [7:0]  rgb888_b   = rgb888[0+:8] ;
//---- kuai 3: R/G/B lei-jia (ji suan zeng-yi yi-ju; sum_* fu-zhi 1 yi bi-mian chu-ling) ----
    
  /*****************************************************************
                          中间信号                                        
*****************************************************************/


  reg         I_tvalid_r0,I_tvalid_r1;
  reg  [95:0] I_tdata_d0,I_tdata_d1;


  //累加RGB通道的�??
  reg  [31:0]         sum_r[0:3];
  reg  [31:0]         sum_g[0:3];
  reg  [31:0]         sum_b[0:3];

  
  wire  [95:0]        data_d0 ;
  wire                valid_d0;
  wire                I_tuser_r0;    

  reg                 I_tuser_r1;

  reg   [95:0]        data_d1 ;
  reg                 valid_d1;
  reg   [9:0]         rgb_sum[0:3];//每个像素点RGB的和
  /*****************************************************************
                            平均值计�??                                      
*****************************************************************/

// 对输入数据和有效信号进行寄存，形成流水线
always @(posedge I_clk or negedge I_rst_n) begin
    if (!I_rst_n) begin
        I_tdata_d0  <= 0;
        I_tdata_d1  <= 0;
        {I_tvalid_r0,I_tvalid_r1} <= 0;
    end else begin
        I_tdata_d0  <= I_tdata   ;
        I_tdata_d1  <= I_tdata_d0;
        I_tvalid_r0 <= I_tvalid;
        I_tvalid_r1 <= I_tvalid_r0;
    end
end

// 将输入数据拆分为4个像素的RGB分量
wire [7:0] rgb888_r_d[0:3];
wire [7:0] rgb888_g_d[0:3];
wire [7:0] rgb888_b_d[0:3];

assign  rgb888_r_d[0] = I_tdata[16+:8];
assign  rgb888_g_d[0] = I_tdata[8+:8];
assign  rgb888_b_d[0] = I_tdata[0+:8];
// [HDR-2026-10-12k] 补上第 1~3 路。原文件这两个 4 元素数组只赋了 [0]，
// 其余三路是悬空 wire；白平衡要按整帧统计，不能只取 1/4 的像素。
assign  rgb888_r_d[1] = I_tdata[40+:8];
assign  rgb888_g_d[1] = I_tdata[32+:8];
assign  rgb888_b_d[1] = I_tdata[24+:8];
assign  rgb888_r_d[2] = I_tdata[64+:8];
assign  rgb888_g_d[2] = I_tdata[56+:8];
assign  rgb888_b_d[2] = I_tdata[48+:8];
assign  rgb888_r_d[3] = I_tdata[88+:8];
assign  rgb888_g_d[3] = I_tdata[80+:8];
assign  rgb888_b_d[3] = I_tdata[72+:8];


// 将输入数据拆分为4个像素的RGB分量
wire [7:0] rgb888_r_d0[0:3];
wire [7:0] rgb888_g_d0[0:3];
wire [7:0] rgb888_b_d0[0:3];

assign  rgb888_r_d0[0] = I_tdata_d0[16+:8];
assign  rgb888_g_d0[0] = I_tdata_d0[8+:8];
assign  rgb888_b_d0[0] = I_tdata_d0[0+:8];
// [HDR-2026-10-12k] 同上，补第 1~3 路（偏移与 data_d1 的拆法一致）
assign  rgb888_r_d0[1] = I_tdata_d0[40+:8];
assign  rgb888_g_d0[1] = I_tdata_d0[32+:8];
assign  rgb888_b_d0[1] = I_tdata_d0[24+:8];
assign  rgb888_r_d0[2] = I_tdata_d0[64+:8];
assign  rgb888_g_d0[2] = I_tdata_d0[56+:8];
assign  rgb888_b_d0[2] = I_tdata_d0[48+:8];
assign  rgb888_r_d0[3] = I_tdata_d0[88+:8];
assign  rgb888_g_d0[3] = I_tdata_d0[80+:8];
assign  rgb888_b_d0[3] = I_tdata_d0[72+:8];


        ///削弱白色
//---- kuai 4: chu-fa-qi (suan G/R yu G/B bi-zhi, 48bit shu-chu) ----
        always @(posedge I_clk or negedge I_rst_n) begin
            if(!I_rst_n) begin
                rgb_sum[0] <= 0;
                rgb_sum[1] <= 0;
                rgb_sum[2] <= 0;
                rgb_sum[3] <= 0;
            end
            else if(I_tvalid)begin
                // [HDR-2026-10-12k] 四路各自算 R+G+B（白点排除要逐像素判）
                rgb_sum[0] <= rgb888_r_d[0] + rgb888_g_d[0] + rgb888_b_d[0];
                rgb_sum[1] <= rgb888_r_d[1] + rgb888_g_d[1] + rgb888_b_d[1];
                rgb_sum[2] <= rgb888_r_d[2] + rgb888_g_d[2] + rgb888_b_d[2];
                rgb_sum[3] <= rgb888_r_d[3] + rgb888_g_d[3] + rgb888_b_d[3];
            end
        end

        // [HDR-2026-10-12k] 四路增量（白点排除逐像素判：该像素 R+G+B < 720 才计入）
        wire [31:0] inc_r = ((rgb_sum[0] < 720) ? {24'd0, rgb888_r_d0[0]} : 32'd0)
                          + ((rgb_sum[1] < 720) ? {24'd0, rgb888_r_d0[1]} : 32'd0)
                          + ((rgb_sum[2] < 720) ? {24'd0, rgb888_r_d0[2]} : 32'd0)
                          + ((rgb_sum[3] < 720) ? {24'd0, rgb888_r_d0[3]} : 32'd0);
        wire [31:0] inc_g = ((rgb_sum[0] < 720) ? {24'd0, rgb888_g_d0[0]} : 32'd0)
                          + ((rgb_sum[1] < 720) ? {24'd0, rgb888_g_d0[1]} : 32'd0)
                          + ((rgb_sum[2] < 720) ? {24'd0, rgb888_g_d0[2]} : 32'd0)
                          + ((rgb_sum[3] < 720) ? {24'd0, rgb888_g_d0[3]} : 32'd0);
        wire [31:0] inc_b = ((rgb_sum[0] < 720) ? {24'd0, rgb888_b_d0[0]} : 32'd0)
                          + ((rgb_sum[1] < 720) ? {24'd0, rgb888_b_d0[1]} : 32'd0)
                          + ((rgb_sum[2] < 720) ? {24'd0, rgb888_b_d0[2]} : 32'd0)
                          + ((rgb_sum[3] < 720) ? {24'd0, rgb888_b_d0[3]} : 32'd0);

        // 对每个通道的值进行累加，用于计算平均值
        always @(posedge I_clk or negedge I_rst_n) begin
            if (!I_rst_n || I_tuser) begin
                // 复位或帧起始时清零累加器
                // [HDR-2026-10-12k] 初值由 1 改 0：一帧 92 万个样本，初值 1 数值上
                // 可忽略，但语义上应为 0（原值会让空累加器的比值偏成 1.0）。
                sum_r[0] <= 0;
                sum_g[0] <= 0;
                sum_b[0] <= 0;
            end else if (I_tvalid_r0) begin
                // [HDR-2026-10-12k] ★★ 四路全累加 ★★
                //   原写法只累加 rgb888_*_d0[0]（96bit 字里的第 0 个像素），
                //   等于每 4 个像素只统计 1 个。2026-10-12 21:30~21:49 的 8 张
                //   遥测图反推出：AWB 算出的增益恒定比灰世界需要的低
                //   17.0~17.4%(R) / 8.3~8.9%(B)，与增益大小和场景都无关，
                //   是恒定百分比 => 采样有偏。改成 4 路全进。
                //   ★四路必须先加成一个增量再做一次累加★：同一 always 块里对同一
                //   个 reg 多次非阻塞赋值，只有最后一条生效（会丢掉前三路）。
                sum_r[0] <= sum_r[0] + inc_r;
                sum_g[0] <= sum_g[0] + inc_g;
                sum_b[0] <= sum_b[0] + inc_b;
            end
        end

  /*****************************************************************
                           计算增益                                       
*****************************************************************/

  // [HDR-2026-10-15a] ★优化1：用「归一化 + 倒数查表 + 一次乘法」替换两个 TD 流水除法器★
  //   旧实现 div_gen_G_R_r1 / divide_G_B_r1 合计 1896 logic LUT + 2168 ripple
  //   + 5507 FF（约占全片 LUT6 的 11%）。换成 wb_recip.v 后每通道约
  //   250 LUT + 1 ERAM + 1~2 DSP。
  //   接口与饱和语义【完全不变】：
  //     in_r_x1[19:0] = Q16 增益；|in_r_x1[47:20] 非零 <=> 真商 >= 2^20
  //   于是下面 `if(|in_r_x1[47:20]) 饱和 20'hfffff` 的分支一行都不用改。
  wire [47:0] in_r_x1;
  wire [47:0] in_b_x1;

  // 门控：wb_recip 要求 I_den >= 65536 且 I_num >= 1，否则 e-16 会下溢。
  //   帧首累加器刚被 I_tuser 清零时必然不满足 —— 此时【保持上一帧增益】才是
  //   正确行为（不是清零）。像素实际用的是 I_tuser 拍锁存的 in_*_hold，
  //   而那一拍累加器是满的，所以这个门控对输出画面不可见。
  wire S_sum_ok  = (sum_r[0] >= 32'd65536) && (sum_b[0] >= 32'd65536)
                && (sum_g[0] >= 32'd1);
  // 旧 divider 的 done per valid = 1.0（B 门级 TB 实测），这里用同一拍做写使能
  wire S_gain_we = I_tvalid_r1 && S_sum_ok;



//---- kuai 5: xiang-su liu yan-shi (signal_delay + BRAM, deng zeng-yi suan-wan zai dui-qi) ----
/*****************************************************************
                   IP 调用                                    
*****************************************************************/
    //为了保证合理的延迟，这里使用了除法器

      // [HDR-2026-10-15a] 优化1：倒数查表法（纯组合逻辑，零流水延迟）
      wb_recip u_wb_recip_r (
          .I_den (sum_r[0]),
          .I_num (sum_g[0]),
          .O_q   (in_r_x1)
      );

      wb_recip u_wb_recip_b (
          .I_den (sum_b[0]),
          .I_num (sum_g[0]),
          .O_q   (in_b_x1)
      );

     
//---- kuai 6: di yi ci shi-li-hua signal_delay (yan shi xiang-su liu) ----
    signal_delay #(
        .IMG_HEIGHT   (IMG_HEIGHT),
        .IMG_WIDTH    (IMG_WIDTH ),
        .DATA_WIDTH   (96  ),
        .DELAY_CYCLE  (50)
    )signal_delay_d (
        /*input                       */ .I_clk  (I_clk  ),
        /*input                       */ .I_rst_n(I_rst_n),
        /*input                       */ .I_tuser(I_tuser),  //synthesis keep 
        /*input  wire                 */ .I_valid(I_tvalid_r1),  //synthesis keep 
        /*input  wire [DATA_WIDTH-1:0]*/ .I_data (I_tdata_d1 ),   //synthesis keep 
        /*output wire                 */ .O_valid(valid_d0   ),  //synthesis keep 
        /*output wire [DATA_WIDTH-1:0]*/ .O_data (data_d0    ),   //synthesis keep 
        /*output wire                 */ .O_tuser(I_tuser_r0 )
    );

    

/*****************************************************************
                            ��������                                      
*****************************************************************/

    reg  [19:0]   in_r_r1;
    reg  [19:0]   in_b_r1;
    // [HDR-2026-10-12p] 帧锁存后的"本帧实际使用"的增益
    reg  [19:0]   in_r_hold;
    reg  [19:0]   in_b_hold;
    always @(posedge I_clk or negedge I_rst_n)begin 
        // [HDR-2026-10-12k] ★★ 复位条件去掉 I_tuser ★★
        //   原写法每帧帧首把 R/B 增益打回 1.000x，再靠 done[0] 用"运行中的部分和"
        //   在整帧里慢慢爬回来 => 每帧前半段等于没有白平衡，画面出现纵向色偏，
        //   且帧平均的实际校正量小于除法器算出来的值。白平衡是帧间慢变量，
        //   应当跨帧保持并收敛，只在真复位时回 1.000x。
        if(!I_rst_n)begin
            in_r_r1   <= 20'h10000;
            in_b_r1   <= 20'h10000;
            in_r_hold <= 20'h10000;
            in_b_hold <= 20'h10000;
        end
        else begin
            // [HDR-2026-10-15a] done[0] -> S_gain_we（含累加器就绪门控）
            if(S_gain_we)begin
                if(|in_r_x1[47:20])
                    in_r_r1 <= 20'hfffff;
                else 
                    in_r_r1 <= in_r_x1[19:0];
                if(|in_b_x1[47:20])
                    in_b_r1 <= 20'hfffff;
                else 
                    in_b_r1 <= in_b_x1[19:0];
            end
            // [HDR-2026-10-12p] ★帧锁存★
            //   I_tuser 是帧首那一拍。此刻 in_r_r1/in_b_r1 里放的正是
            //   上一帧跑到帧尾时用满累加器算出来的比值 = 真正的整帧灰世界比值。
            //   把它冻结进 *_hold，整帧所有像素都用这一对常量乘，
            //   于是增益在帧内恒定、帧间一步到位，不再有"帧首从空累加器起算"的抖动。
            if(I_tuser)begin
                in_r_hold <= in_r_r1;
                in_b_hold <= in_b_r1;
            end
        end
//---- kuai 7: di er ci shi-li-hua signal_delay ----
    end


    ////信号同步
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
                           ��������                                       
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


    wire   [7:0] rgb888_r_d1[0:3];
//---- kuai 8: zeng-yi ji-cun qi (fu-wei/tuser shi 20h10000 = 1.0 ding-dian; done shi bao-he) ----
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
            R_new_r1 <= in_r_hold * rgb888_r_d1[0];
            G_new_r1 <=           rgb888_g_d1[0];
            B_new_r1 <= in_b_hold * rgb888_b_d1[0];

            R_new_r2 <= in_r_hold * rgb888_r_d1[1];
            G_new_r2 <=           rgb888_g_d1[1];
            B_new_r2 <= in_b_hold * rgb888_b_d1[1];
//---- kuai 9: zeng-yi cheng-fa (R/B cheng zeng-yi, G bu cheng) + bao-he ----

            R_new_r3 <= in_r_hold * rgb888_r_d1[2];
            G_new_r3 <=           rgb888_g_d1[2];
            B_new_r3 <= in_b_hold * rgb888_b_d1[2];

            R_new_r4 <= in_r_hold * rgb888_r_d1[3];
            G_new_r4 <=           rgb888_g_d1[3];
            B_new_r4 <= in_b_hold * rgb888_b_d1[3];
        end
    end

/*****************************************************************
                            �������???                                      
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

    // [HDR-2026-10-13a] ★输出端四舍五入 (c)★
    //   原写法 (x[27:24])?255:x[23:16] 是"直接截断"：每个像素单独丢掉低 16 bit，
    //   向下取整，平均每像素少 0.5 码；而且只作用在 R/B 两路 —— G 走 G_new_rN
    //   直通、完全不乘增益 —— 于是产生一个与场景亮度、与增益大小都无关的
    //   "只压 R 和 B、不压 G"的加性偏置。门级实测（tb_awb_live_ratio_2f_t1.v）：
    //   CASE A 均匀 80/100/90，截断版 B/G=0.9900，加舍入后 B/G=1.0000。
    //   等价于先 (x + 0x8000) 再 >>16 然后饱和，但只多一个 9 bit 加法器，
    //   不新增乘法器/除法器（HISTORY 第 2 条：本芯片只有 40 个 DSP）。
    wire [8:0] R_rnd1 = {1'b0,R_new_r1[23:16]} + {8'd0,R_new_r1[15]};
    wire [8:0] B_rnd1 = {1'b0,B_new_r1[23:16]} + {8'd0,B_new_r1[15]};
    wire [8:0] R_rnd2 = {1'b0,R_new_r2[23:16]} + {8'd0,R_new_r2[15]};
    wire [8:0] B_rnd2 = {1'b0,B_new_r2[23:16]} + {8'd0,B_new_r2[15]};
    wire [8:0] R_rnd3 = {1'b0,R_new_r3[23:16]} + {8'd0,R_new_r3[15]};
    wire [8:0] B_rnd3 = {1'b0,B_new_r3[23:16]} + {8'd0,B_new_r3[15]};
    wire [8:0] R_rnd4 = {1'b0,R_new_r4[23:16]} + {8'd0,R_new_r4[15]};
    wire [8:0] B_rnd4 = {1'b0,B_new_r4[23:16]} + {8'd0,B_new_r4[15]};

    assign R_new_x1 = (R_new_r1[27:24] || R_rnd1[8])?255:R_rnd1[7:0];
    assign G_new_x1 =  G_new_r1;
    assign B_new_x1 = (B_new_r1[27:24] || B_rnd1[8])?255:B_rnd1[7:0];

    assign R_new_x2 = (R_new_r2[27:24] || R_rnd2[8])?255:R_rnd2[7:0];
    assign G_new_x2 =  G_new_r2;
    assign B_new_x2 = (B_new_r2[27:24] || B_rnd2[8])?255:B_rnd2[7:0];

    assign R_new_x3 = (R_new_r3[27:24] || R_rnd3[8])?255:R_rnd3[7:0];
    assign G_new_x3 =  G_new_r3;
    assign B_new_x3 = (B_new_r3[27:24] || B_rnd3[8])?255:B_rnd3[7:0];

    assign R_new_x4 = (R_new_r4[27:24] || R_rnd4[8])?255:R_rnd4[7:0];
    assign G_new_x4 =  G_new_r4;
    assign B_new_x4 = (B_new_r4[27:24] || B_rnd4[8])?255:B_rnd4[7:0];
//---- kuai 10: shu-chu shou-wo / pin-jie (O_tvalid = valid_d2, O_tdata an 4 xiang-su pin-jie) ----
/*****************************************************************
                           ͬ���ź�                                       
*****************************************************************/

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


    assign  O_tlast  = (valid_d1 == 0) && (valid_d2 == 1);   
    assign  O_tuser  = I_tuser ;   
    assign  O_tvalid = valid_d2;

    assign  O_tdata = O_tvalid?{R_new_x4,G_new_x4,B_new_x4,
                       R_new_x3,G_new_x3,B_new_x3,
                       R_new_x2,G_new_x2,B_new_x2,
                       R_new_x1,G_new_x1,B_new_x1}:0;
    // assign O_t_data = {R_new[7-:5],G_new[7-:6],B_new[7-:5]};
    assign  I_tready = O_tready;

    // [HDR-2026-10-12p] 遥测改成送 in_r_hold / in_b_hold ——
    //   即"本帧真正乘到每个像素上"的那一对常量（帧边界锁存后的值），
    //   而不是 done[0] 那一拍的运行比值。这样屏幕上的 W/B 才等于实际施加的增益。
    assign  O_gain_r = in_r_hold;
    assign  O_gain_b = in_b_hold;
 
endmodule



