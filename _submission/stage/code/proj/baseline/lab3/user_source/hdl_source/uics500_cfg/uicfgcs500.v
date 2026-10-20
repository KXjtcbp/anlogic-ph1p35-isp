//=============================================================================
// 文件      : uics500_cfg/uicfgcs500.v
// 模块      : uicfgcs500 #( parameter CLK_DIV = 16d999 )
// 功能      : SC500 摄像头 I2C 配置控制：上电后按寄存器表逐条写配置，配置完成后再按 AE 请求更新曝光与模拟增益。★未被 camera_to_dsi_display.al 编译：本文件与 uics500_cfg/uicfgcs500_720p.v 同族但不是 720p 版本，全树无例化；本工程当前在用的是 uicfgcs500_720p.v。
// 数据通路  : 端口 I_clk/I_rst_n/I_ae_req/I_exposure_time[15:0]/I_analog_gain[15:0] -> O_cam_scl/IO_cam_sda/O_cfg_done/O_ae_cfg_done。localparam CAM_ID = 8h6C（7bit 器件地址 + 写位）。reg[7:0] rst_cnt 上电自增到 bit7=1 作为内部延时复位，等 I2C 与寄存器表稳定后再启动状态机。TS_S 是 2bit 状态机：0=取当前 REG_INDEX 对应的寄存器数据，1=总线不忙时把 4 字节组装进 wr_data 并置 iic_req，2=等 iic_busy 起来后清 iic_req，3=等 iic_busy 落下后 reg_index 加 1 回到 0（写完一轮即 O_cfg_done）。wr_data 组装（大端，寄存器地址在前、数据在后）：wr_data[7:0]<=CAM_ID、[15:8]<=REG_DATA[23:16]、[23:16]<=REG_DATA[15:8]、[31:24]<=REG_DATA[7:0]。assign REG_DATA = (O_cfg_done == 0) ? REG_DATA_REG : REG_DATA_AE，即先走配置表、配置完成后再走 AE 表。
// 时钟/复位 : I_clk 为系统时钟，I_rst_n 异步复位、低电平有效；I2C 的 SCL 分频常数 CLK_DIV 由参数给出（默认 16d999，例化 uii2c 时透传）。
// 依赖      : 例化 uii2c#(.WMEN_LEN(4),.RMEN_LEN(1),.CLK_DIV(CLK_DIV)) uii2c_inst（I_wr_cnt=8d4、I_rd_cnt=8d0、I_iic_mode=1b0，即每次写 4 字节）、uics500reg uics500reg_inst（第 146 行）、SC500GainTbl gain_tbl（.I_gain_idx(I_analog_gain - 16)）、uics500regAE uics500regAE_inst。
// 综合/实现 : ★未被 camera_to_dsi_display.al 引用、未参与综合实现。本文件为 GB18030 编码，本次插入的注释按 GB18030 写回，原有字节未改动。
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
*Create Date: 2019/12/17
*Module Name:uicfg7611
*File Name:uicfg7611.v
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

/*******************************uicfg7611***************************
--1.ADV7611芯片配置驱动程序
*********************************************************************/

//---- timescale (shi-jian dan-wei / jing-du) ----
`timescale 1ns / 1ns

//---- kuai 1: can-shu CLK_DIV (I2C SCL fen-pin xi-shu, mo-ren 16d999, tou-chuan gei uii2c) ----
module uicfgcs500#
(
parameter	 CLK_DIV  = 16'd999
)
(
//---- kuai 2: duan-kou sheng-ming (AE qing-qiu + bao-guang/zeng-yi ru -> I2C SCL/SDA yu pei-zhi wan-cheng biao-zhi) ----
input  wire             I_clk,  //系统时钟输入
input  wire             I_rst_n,  //系统复位输入
input  wire             I_ae_req,//摄像头AE控制
input  wire	 [15:0] 	I_exposure_time,
input  wire	 [15:0] 	I_analog_gain,
output wire             O_cam_scl, //I2C总线，SCL时钟
inout  wire             IO_cam_sda, //I2C总线，SDA数据
output reg              O_cfg_done, //配置完成
output reg              O_ae_cfg_done
);	

//---- kuai 3: she-bei di-zhi CAM_ID = 8h6C (SC500 de I2C cong-ji di-zhi + xie wei) ----
localparam CAM_ID = 8'h6C;
//---- kuai 4: nei-bu yan-shi fu-wei rst_cnt (shang-dian zi-zeng dao bit7=1 cai qi-dong zhuang-tai-ji) ----
//内部计数器产生一个延迟复位
reg[7:0] rst_cnt =0;
always@(posedge I_clk or negedge I_rst_n)  
    if(I_rst_n == 1'b0) //复位初始化寄存器
        rst_cnt<= 8'd0; 
    else if(rst_cnt[7] == 1'b0)
       rst_cnt <= rst_cnt + 1'b1; 
    else 
       rst_cnt <= rst_cnt; 

reg  iic_req;//请求操作I2C控制器信号
wire ic_busy; //I2C控制器忙信号 
reg  [31:0] wr_data;     //写数据寄存器
reg  [1 :0] TS_S = 2'd0; //状态机寄存器
reg  [8 :0] reg_index;   //寄存索引
wire [23:0] REG_DATA;    //寄存器数据
wire [23:0] REG_DATA_REG;    //寄存器数据
wire [23:0] REG_DATA_AE;    //寄存器数据
wire [8 :0] REG_SIZE;    //寄存器数量
wire [8 :0] REG_SIZE_REG;    //寄存器数量
wire [8 :0] REG_SIZE_AE;    //寄存器数量

always@(posedge I_clk ) begin 
    if(rst_cnt[7] == 1'b0)begin //复位初始化寄存器
        reg_index  <= 9'd0;
        iic_req    <= 1'b0;
        wr_data    <= 32'd0;
        O_cfg_done <= 1'b0;
        O_ae_cfg_done <= 1'b0;
        TS_S     <= 2'd0;    
    end
    else begin
        case(TS_S)
        0:if(reg_index == REG_SIZE && O_cfg_done == 1'b0) begin//如果配置完成
            O_cfg_done <= 1'b1;       //设置 cfg_done标准
        end 
//---- kuai 5: zhuang-tai-ji TS_S (0=qu biao, 1=zu-zhuang wr_data bing fa qi iic_req, 2=deng busy qi lai hou qing req, 3=deng busy luo-xia hou reg_index+1) ----
        else if(reg_index == REG_SIZE && O_ae_cfg_done == 1'b0) begin//如果配置完成
            O_ae_cfg_done <= 1'b1;       //设置 cfg_done标准
        end 
        else if(I_ae_req)begin
            O_ae_cfg_done <= 0;
            reg_index   <= 0;
        end
        else if((O_cfg_done&O_ae_cfg_done) == 1'b0)
            TS_S <= 2'd1;           //下一个状态
        1:if(!iic_busy)begin        //当总线非忙，才可以操作I2C控制器
            iic_req  <= 1'b1;       //请求操作I2C控制器
			wr_data[7  :0] <= CAM_ID;           //器件地址   
			wr_data[15 :8] <= REG_DATA[23:16];  //寄存器地址-高8bit    
			wr_data[23:16] <= REG_DATA[15: 8];  //寄存器地址-低8bit  
            wr_data[31:24] <= REG_DATA[7 : 0];  //寄存器数据
            TS_S      <= 2'd2; //下一个状态
        end    
        2:if(iic_busy)begin
             iic_req  <= 1'b0;  //重置 iic_req =0
             TS_S     <= 2'd3;  //下一个状态
//---- kuai 6: wr_data zu-zhuang (da-duan: CAM_ID -> di-zhi gao/di zi-jie -> shu-ju gao/di zi-jie) ----
        end
        3:if(!iic_busy)begin  //当总线非忙，才可以操作I2C控制器 
			reg_index<= reg_index + 1'b1;//寄存器索引加1
			TS_S    <= 2'd0;//回到初始状态
        end 
        endcase
   end
end

assign REG_DATA = (O_cfg_done == 0) ? REG_DATA_REG : REG_DATA_AE;
assign REG_SIZE = (O_cfg_done == 0) ? REG_SIZE_REG : REG_SIZE_AE;

//例化I2C控制模块
//---- kuai 7: uii2c shi-li-hua (mei ci xie 4 zi-jie: WMEN_LEN=4, RMEN_LEN=1) ----
uii2c#
(
.WMEN_LEN(4),     //最大支持一次写入4BYTE(包含器件地址)
.RMEN_LEN(1),     //最大支持一次读出1BYTE
.CLK_DIV(CLK_DIV) //100KHZ I2C总线时钟
)
uii2c_inst
(
.I_clk(I_clk),//系统时钟
.I_rstn(rst_cnt[7]),//系统复位
.O_iic_scl(O_cam_scl),//I2C SCL总线时钟
.IO_iic_sda(IO_cam_sda),//I2C SDA数据总线
.I_wr_data(wr_data),//写数据寄存器
.I_wr_cnt(8'd4),//需要写的数据BYTES
.O_rd_data(),   //读数据寄存器
.I_rd_cnt(8'd0),//需要读的数据BYTES
.I_iic_mode(1'b0),//读模式设置
//---- kuai 8: pei-zhi biao / AE biao xuan-ze (O_cfg_done==0 shi zou pei-zhi biao, fou-ze zou AE biao) ----
.I_iic_req(iic_req),//I2C控制器请求
.O_iic_busy(iic_busy)//I2C控制器忙
);


//例化CAM的寄存器配置表
uics500reg uics500reg_inst
(
.REG_SIZE(REG_SIZE_REG),  //寄存器数量
.REG_INDEX(reg_index),    //寄存索引
.REG_DATA(REG_DATA_REG)   //寄存器数据
);  

wire 	[15:0] 	w_gain_val; 
SC500GainTbl gain_tbl (.I_clk(I_clk), .I_rstn(rst_cnt[7]==1'b0), .I_gain_idx(I_analog_gain - 16), .O_gain_code(w_gain_val));
//例化CAM AE的寄存器配置表
uics500regAE uics500regAE_inst
(
.REG_SIZE(REG_SIZE_AE),  //寄存器数量
.REG_INDEX(reg_index),//寄存索引
.REG_DATA(REG_DATA_AE),   //寄存器数据
.I_analog_gain(w_gain_val),
.I_exposure_time(I_exposure_time)
);  




endmodule
