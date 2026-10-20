//=============================================================================
// 文件      : uics500_cfg/uii2c.v
// 模块      : uii2c #( parameter integer WMEN_LEN = 8d0, RMEN_LEN = 8d0, CLK_DIV = 16d499 )
// 功能      : 通用 I2C 主机（MASTER）：按请求发起一次写或读传输，支持 WMEN_LEN 字节写、RMEN_LEN 字节读，用于配置 SC500 摄像头寄存器。本工程实际使用的就是这一份。
// 数据通路  : 端口：I_clk/I_rstn、O_iic_scl、inout IO_iic_sda、I_wr_data[WMEN_LEN*8-1:0]、I_wr_cnt[7:0]、O_rd_data[RMEN_LEN*8-1:0]、I_rd_cnt[7:0]、I_iic_req、I_iic_mode（1=连续读、0=当前寄存器地址读）、O_iic_busy、O_iic_bus_error、IO_iic_sda_dg。时序：SCL 由 scl_clk 分频得到，localparam SCL_DIV = CLK_DIV/2 是半个 SCL 周期的计数；localparam OFFSET = SCL_DIV - SCL_DIV/4 让外部 SCL 相对内部节拍延后 3/4 个半周期，以拉开 SCL 与 SDA 的建立/保持时间。状态机 localparam：IDLE=4d0、START=1、W_WAIT=2、W_ACK=3、R_WAIT=4、R_ACK=5、STOP1=6、STOP2=7（声明为 reg [2:0] IIC_S 却赋 4d 常量，位宽偏紧但 0~7 都能表示，本次只加注释未改代码）。SDA 是开漏输出：assign IO_iic_sda = (sda_o == 1b0) ? 1b0 : 1bz（0 拉低、否则高阻靠外部上拉），assign sda_i = IO_iic_sda 回读。发送在 always @(posedge scl_clk)、接收在 always @(negedge scl_clk)，读回数据按字节存放 O_rd_data[((rcnt-1b1)*8) +: 8] <= sda_i_r[7:0]；在 W_ACK 状态若 sda_i == 1b1（从机未应答）则置 O_iic_bus_error。
// 时钟/复位 : I_clk 为系统时钟，I_rstn 异步复位、低电平有效；SCL 频率 = I_clk / CLK_DIV（本文件默认 CLK_DIV=499，实际分频常数由上层 uicfgcs500_720p.v 传入，例化时取 999）。
// 依赖      : 第 94~107 行是注释掉的 //PULLUP PULLUP_inst 与整段 Xilinx IOBUF #(...) IOBUF_inst (.O(sda_i), ... .I(sda_o), .T(sda_o));（端口名全在注释中），仅供历史参考，本次未改动注释内任何名字。被 uics500_cfg/uicfgcs500_720p.v:100 例化为 uii2c_inst（WMEN_LEN=4/RMEN_LEN=1）。
// 综合/实现 : 本文件在 camera_to_dsi_display.al 的编译清单中；SCL 与 SDA 走普通 IO（无专用 IOBUF 例化），无其它 IP 依赖。本文件为 GB18030 编码，本次插入的注释按 GB18030 写回，原有字节未改动。
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
*Create Date: 2022/12/23
*Module Name:uii2c
*File Name:uii2c.v
*Description: 
*The reference demo provided by Milianke is only used for learning. 
*We cannot ensure that the demo itself is free of bugs, so users 
*should be responsible for the technical problems and consequences
*caused by the use of their own products.
*Copyright: Copyright (c) MiLianKe
*All rights reserved.
*Revision: 1.1
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

/*******************************I2C控制器 MASTER*********************
--以下是米联客设计的I2C总线MASTER控制器
--1.代码简洁，占用极少逻辑资源，代码结构清晰，逻辑设计严谨
--2.使用方便，只需要把发送的数据放入寄存器，就可以自动支持任意长度的写数据
--3.使用方便，只需要把读的数据告知控制器，就可以自动支持任意长度的读数据
--4.1.1版本，升级了O_iic_bus_error标志信号，当总线写操作没有ACK返回，设置O_iic_bus_error，可以通过观察O_iic_bus_error查看总线是否有错误
*********************************************************************/

//---- timescale (shi-jian dan-wei / jing-du) ----
`timescale 1ns / 1ns //仿真刻度/精度

//---- kuai 1: can-shu (WMEN_LEN xie zi-jie shu / RMEN_LEN du zi-jie shu / CLK_DIV SCL fen-pin xi-shu) ----
module uii2c#
(
parameter integer WMEN_LEN = 8'd0,//写长度，以字节为单位，包含器件地址
parameter integer RMEN_LEN = 8'd0,//读长度，以字节为单位，不包含器件地址
parameter integer CLK_DIV  = 16'd499// I2C时钟分频系数
)
//---- kuai 2: duan-kou sheng-ming (SCL + kai-lou SDA + xie/du shu-ju yu qing-qiu shou-wo) ----
(
input  wire I_clk,//系统时钟输入
input  wire I_rstn,//系统复位，低电平有效
output reg  O_iic_scl = 1'b0,//I2C时钟SCL
inout  wire IO_iic_sda,//I2C 数据总线
input  wire [WMEN_LEN*8-1'b1:0]I_wr_data,//写数据寄存器，其中WMEN_LEN设置了最大支持的数据字节数，越大占用的FPGA资源越多
input  wire [7:0]I_wr_cnt,//写数据计数器，代表写了多少个字节
output reg  [RMEN_LEN*8-1'b1:0]O_rd_data = 0,//读数据寄存器，其中RMEN_LEN设置了最大支持的数据字节数，越大占用的FPGA资源越多
input  wire [7:0]I_rd_cnt,//读数据计数器
input  wire I_iic_req,//I_iic_req == 1 使能I2C传输
input  wire I_iic_mode,//I_iic_mode = 1 随机读   I_iic_mode = 0 读当前寄存器或者页读
output reg  O_iic_busy = 1'b0,//I2C控制器忙
output reg  O_iic_bus_error, //I2C总线，无法读到正确ACK出错
output reg  IO_iic_sda_dg
);

//---- kuai 3: zhuang-tai-bian-liang (IDLE/START/W_WAIT/W_ACK/R_WAIT/R_ACK/STOP1/STOP2) ----
localparam IDLE    = 4'd0;//I2C 总线空闲状态
localparam START   = 4'd1;//I2C 总线启动
localparam W_WAIT  = 4'd2;//I2C 总线等待写完成
localparam W_ACK   = 4'd3;//I2C 总线等待写WACK
localparam R_WAIT  = 4'd4;//I2C 总线等待读完成 
localparam R_ACK   = 4'd5;//I2C 总线等待读RACK 
localparam STOP1   = 4'd6;//I2C 总线产生停止位
//---- kuai 4: SCL fen-pin chang-liang (SCL_DIV = CLK_DIV/2; OFFSET = SCL_DIV - SCL_DIV/4 rang SCL yan-hou 3/4 ge ban-zhou-qi, bao-zheng SCL/SDA jian-li-bao-chi shi-jian) ----
localparam STOP2   = 4'd7;//I2C 总线产生停止位   

//---- kuai 5: SDA kai-lou shu-chu yu hui-du (0 la-di, 1 gao-zu kao wai-bu shang-la) ----
localparam SCL_DIV = CLK_DIV/2;

localparam OFFSET = SCL_DIV - SCL_DIV/4;//设置I2C总线的SCL时钟的偏移，以满足SCL和SDA的时序要求，外部的SCL延迟内部的半周期的四分之三

reg [2:0] IIC_S = 4'd0; //I2C 状态机
//generate  scl
reg [15:0] clkdiv = 16'd0;   //I2C 时钟分频寄存器
reg scl_r 	   = 1'b1;       //I2C控制器的SCL内部时钟
reg sda_o 	   = 1'b0;       //I2C控制器的SDA
reg scl_clk    = 1'b0;       //I2C控制器内部SCL时钟，与外部时钟存在OFFSET参数设置的相位偏移
reg [7:0] sda_r = 8'd0;      //发送寄存器
reg [7:0] sda_i_r = 8'd0;    //接收寄存器
reg [7:0] wcnt = 8'd0;       //发送数据计数器，以byte为单位
reg [7:0] rcnt = 8'd0;       //接收数据计数器，以byte为单位
reg [2:0] bcnt = 3'd0;       //bit计数器
reg  rd_req = 1'b0;          //读请求，当判断到需要读数据，内部状态机中设置1
wire sda_i;                  //sda 输入
wire scl_offset;             //scl 时钟偏移控制

assign  sda_i   = IO_iic_sda ;  //读总线 
assign  IO_iic_sda = (sda_o == 1'b0) ?  1'b0 : 1'bz;    //写总线，1'bz代表高阻，I2C外部通过上拉电阻，实现总线的高电平

//---- kuai 6: bei zhu-shi diao de PULLUP / Xilinx IOBUF shi-li-hua (.I/.O/.T duan-kou ming zi jin zai zhu-shi zhong, ben ci wei dong) ----
//PULLUP PULLUP_inst (.O(iic_sda));

//XILINX I2C 用IOBUF实现控制
//IOBUF #(
//.DRIVE(12), // Specify the output drive strength
//.IBUF_LOW_PWR("TRUE"),  // Low Power - "TRUE", High Performance = "FALSE" 
//.IOSTANDARD("DEFAULT"), // Specify the I/O standard
//.SLEW("SLOW") // Specify the output slew rate
//) IOBUF_inst (
//.O(sda_i),    // Buffer output
//.IO(IO_iic_sda), // Buffer inout port (connect directly to top-level port)
//.I(sda_o),    // Buffer input
//.T(sda_o)     // 3-state enable input, high=input, low=output
//);
//---- kuai 7: shi-zhong fen-pin yu SCL sheng-cheng ----

//scl 时钟分频器
always@(posedge I_clk)
    if(clkdiv < SCL_DIV)    
        clkdiv <= clkdiv + 1'b1;
    else begin
        clkdiv <= 16'd0; 
        scl_clk <= !scl_clk;
    end


assign  scl_offset  = (clkdiv == OFFSET);//设置scl_offset的时间参数
always @(posedge I_clk) O_iic_scl <=  scl_offset ?  scl_r : O_iic_scl; //O_iic_scl延迟scl_offset时间的scl_r

//采集I2C 数据总线sda
always @(posedge I_clk) IO_iic_sda_dg <= sda_i;  

//当IIC_S状态机处于，同时空闲状态，设置SCL为高电平，同时也是空闲，停止状态，用于产生起始位和停止位时序，否则寄存scl_clk时钟
always @(*) 
    if(IIC_S == IDLE || IIC_S == STOP1 || IIC_S == STOP2)
        scl_r <= 1'b1;
    else 
        scl_r <= scl_clk;
  

//当进入IIC_S状态为启动、停止设置sda=0，结合scl产生起始位，或者(IIC_S == R_ACK && (rcnt != I_rd_cnt) sda=0，用于产生读操作的ACK
always @(*) 
    if(IIC_S == START || IIC_S == STOP1 || (IIC_S == R_ACK && (rcnt != I_rd_cnt)))
        sda_o <= 1'b0;
    else if(IIC_S == W_WAIT)
        sda_o <= sda_r[7]; 
    else  sda_o <= 1'b1; //否则其他状态都为1，当(IIC_S == R_ACK && (rcnt == I_rd_cnt) 产生一个NACK 

//I2C数据发送模块，所有的写数据都通过此模块发送
always @(posedge scl_clk) 
    if(IIC_S == W_ACK || IIC_S == START)begin//IIC_S=START和W_ACK，把需要发送的数据，寄存到sda_r
        sda_r <= I_wr_data[(wcnt*8) +: 8];//寄存需要发发送的数据到sda_r
        if( rd_req ) sda_r <= {I_wr_data[7:1],1'b1};//对于读操作，rd_req由内部代码产生，当写完第一个数据(器件地址)，后通过判断I_rd_cnt，确认是否数据需要读
    end
    else if(IIC_S == W_WAIT)//当W_WAT状态，通过移位操作，把数据发送到数据总线
        sda_r <= {sda_r[6:0],1'b1};//移位操作
    else 
        sda_r <= sda_r;

//sda data bus read and hold data to O_rd_data register when IIC_S=R_ACK
//I2C数据接收模块，I2C读期间，把数据通过移位操作，移入O_rd_data
always @(negedge scl_clk)begin
    if(IIC_S == R_WAIT ) //当IIC_S == R_WAIT ||IIC_S == W_ACK(如果读操作，第1个BIT是W_ACK这个状态读)启动移位操作
        sda_i_r <= {sda_i_r[6:0],sda_i};
//---- kuai 8: xie-fa shi-xu (always @(posedge scl_clk)) ----
    else if(IIC_S == R_ACK)//当IIC_S == R_ACK,完成一个BYTE读，把数据保存到O_rd_data
        O_rd_data[((rcnt-1'b1)*8) +: 8] <= sda_i_r[7:0];
    else if(IIC_S == IDLE)//空闲状态，重置sda_i_r
        sda_i_r <= 8'd0;
end

//总线忙状态
always @(posedge scl_clk or negedge I_rstn )begin
	if(I_rstn == 1'b0)
    	O_iic_busy <= 1'b0; 
	else begin
    	if((I_iic_req == 1'b1 || rd_req == 1'b1 || O_iic_bus_error))//I_iic_req == 1'b1 || rd_req == 1'b1总线进入忙状态
    	    O_iic_busy <= 1'b1; 
        else if(IIC_S == IDLE)
        	O_iic_busy <= 1'b0;
    end 		
end

//总线忙状态
always @(negedge scl_clk or negedge I_rstn )begin
	if(I_rstn == 1'b0)
    	O_iic_bus_error <= 1'b0;  	
	else begin
    	if(IIC_S  == W_ACK && sda_i == 1'b1)//I_iic_req == 1'b1 || rd_req == 1'b1总线进入忙状态
    	    O_iic_bus_error <= 1'b1; 
        else if(I_iic_req == 0)
        	O_iic_bus_error <= 1'b0;
    end 		
end

//I2C Master控制器状态机
always @(posedge scl_clk or negedge I_rstn )begin
		if(I_rstn == 1'b0)begin //异步复位，复位相关寄存器
           wcnt 	<= 8'd0;
           rcnt 	<= 8'd0;
           rd_req 	<= 1'b0;   
           IIC_S    <= IDLE;
        end
        else begin
        case(IIC_S) //sda = 1 scl =1
//---- kuai 9: jie-shou shi-xu / du hui shu-ju (always @(negedge scl_clk), an zi-jie cun-fang) ----
        IDLE:begin//在空闲状态，sda=1 scl=1 
           if(I_iic_req == 1'b1 || rd_req == 1'b1) //当I_iic_req == 1'b1代表启动传输 当 rd_req == 1'b1 代表读操作需要产生repeated start 重复启动  
              IIC_S  <= START; //进入START状态
           else begin
              wcnt <= 8'd0; //复位计数器
              rcnt <= 8'd0; //复位计数器
           end
        end
        START:begin //这个状态，前面的代码，先设置sda = 0，scl_offset参数设置了scl_clk时钟的偏移，之后 scl_clk =0 即scl =0 产生起始位或者重复起始位
           bcnt <= 3'd7; //设置bcnt的初值         
           IIC_S  <= W_WAIT;//进入发送等待
        end           
        W_WAIT://等待发送完成，这里发送8bits 数据，写器件地址，写寄存器地址，写数据，都在这个状态完成
        begin
           if(bcnt > 3'd0)//如果8bits没发送完，直到发送完
               bcnt  <= bcnt - 1'b1; //bcnt计数器，每发送1bit减1
           else begin //8bits发送完毕
               wcnt <= wcnt + 1'b1; //wcnt计数器，用于记录已经写了多少字节
               IIC_S  <= W_ACK;//进入W_ACK状态
           end
        end 
        W_ACK://等待WACK，此阶段，也判断是否有读操作
        begin 
//---- kuai 10: ACK jian-ce yu zong-xian cuo-wu biao-zhi (W_ACK zhuang-tai sda_i == 1 ze O_iic_bus_error) ----
           if(wcnt < I_wr_cnt)begin //判断是否所有数据发送(写)完成
              bcnt <= 3'd7; //如果没有写完，重置bcnt
              IIC_S <= W_WAIT;//继续回到W_WAIT等待数据发送(写)完成
           end
           else if(I_rd_cnt > 3'd0)begin//I_rd_cnt > 0代表有数据需要读，I_rd_cnt决定了有多少数据需要读
              if(rd_req == 1'b0 && I_iic_mode == 1'b1)begin //对于第一次写完器件地址，如果I_iic_mode==1代表支持随机读
                  rd_req <= 1'b1;//设置rd_req=1，请求读操作
                  IIC_S <= IDLE; //设置状态进入IDLE，根据rd_req的值会重新产生一次为读操作进行的repeated重复start
              end
              else //如果之前已经完成了repeated重复start，那么读操作进入读数据阶段
                  IIC_S <= R_WAIT;//进入读等待
                  bcnt <= 3'd7;//设置bcnt的初值  
           end
           else //如果所有的发送完成，也没数据需要读，进入停止状态
              IIC_S <= STOP1; 
        end  
        R_WAIT://等待读操作完成
        begin
           rd_req <= 1'b0;//重置读请求rd_req=0
           bcnt  <= bcnt - 1'b1; //bit 计数器
           if(bcnt == 3'd0)begin //当8bits数据读完
              rcnt <= (rcnt < I_rd_cnt) ? (rcnt + 1'b1) : rcnt;//判断是否还有数据需要读
              IIC_S  <= R_ACK;//进入R_ACK
           end
        end
        R_ACK://R_ACK状态产生NACK
        begin
           bcnt <= 3'd7;//重置读请求bcnt计数器
           IIC_S <= (rcnt < I_rd_cnt) ? R_WAIT : STOP1; //如果所有数据读完，进入停止状态
        end  
        STOP1:begin//产生停止位 sda = 0 scl = 1
            rd_req 	<= 1'b0;              
            IIC_S <= STOP2;
        end
        STOP2://产生停止位  sda = 1 scl = 1
            IIC_S <= IDLE;          
        default:
            IIC_S <= IDLE;
    	endcase
    end
end

endmodule
