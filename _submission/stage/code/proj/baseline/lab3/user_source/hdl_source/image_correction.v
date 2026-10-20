//=============================================================================
// 文件      : image_correction.v
// 模块      : image_correction #( parameter DATA_WIDTH = 40 )
// 功能      : 图像裁剪/开窗（不是色彩或镜头校正）：只放行画面中 600 行 x 256 列的一块区域，其余数据清零。★全树无例化、不在 .al 编译清单中，属未接入模块；文件名与功能并不完全对应，注释按代码实际行为描述。
// 数据通路  : 输入 I_raw_data[39:0]、I_raw_valid、I_raw_frame_start；输出 O_raw_tdata[39:0]/O_raw_tlast/O_raw_tvalid/O_raw_tuser，另有一个方向相反的 input O_raw_tready（命名沿用了原作者的写法）。I_raw_tvalid_d/I_raw_tdata_r 先把输入打一拍；cnt 在 !I_raw_valid 时自增，wire last = (cnt == 10) 作为行内节拍（常量 10 与 40bit=4 像素的打包粒度有关，具体依据未能从代码确认）；v_cnt 在 last 时 +1、I_raw_frame_start 时清 0，V_valid = (v_cnt >= 0) && (v_cnt <= 599) 只放行 600 行；h_cnt 在 last 或帧起始清 0、I_raw_tvalid_d 时 +1，H_valid = (h_cnt <= 255) && (h_cnt >= 0) 只放行 256 列；tuser = (h_cnt==0)&&(v_cnt==0)&&I_raw_tvalid_d；O_raw_tdata 在 V_valid&&H_valid 时给数据否则给 0；O_raw_tlast = V_valid && (h_cnt==255) && I_raw_tvalid_d；I_raw_tready 直接回连 O_raw_tready。
// 时钟/复位 : I_clk 上升沿同步；I_rst_n 异步复位、低电平有效；h_cnt/v_cnt 都是 15bit 计数器，行首节拍由 last 产生。
// 依赖      : 第 79~93 行是注释掉的调试核例化 cwc cwc_inst，本目录无该模块定义（疑似安路调试 IP）；无其它自研依赖。
// 综合/实现 : ★未被 camera_to_dsi_display.al 引用、未参与综合实现。本文件为 GB18030 编码，本次插入的注释按 GB18030 写回，原有字节未改动。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================

module image_correction #(
    parameter DATA_WIDTH   = 40
)(
    input                          	  I_clk   			,
    input                          	  I_rst_n 			,

    input    [DATA_WIDTH - 1:0]       I_raw_data		,       
    input                             I_raw_valid 		,     
    input                             I_raw_frame_start	,
    input                             I_raw_frame_end  	,
    // 输出RAW10数据
    output     [DATA_WIDTH - 1:0]     O_raw_tdata 		,
    output                            O_raw_tlast 		,
    output                            O_raw_tvalid		,
    output                            O_raw_tuser 		,
    input                             O_raw_tready
);

    //---- kuai 1: nei-bu ji-cun qi / xian-wang ----
    reg                        I_raw_tvalid_d; 
    reg    [DATA_WIDTH - 1:0]  I_raw_tdata_r;
    reg    [14:0]              h_cnt,v_cnt;
    wire                       V_valid,H_valid;
    wire                       tuser;

    //---- kuai 2: shu-ru da-pai (I_raw_tvalid_d / I_raw_tdata_r) ----
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n )begin
            I_raw_tvalid_d <= 0;
            I_raw_tdata_r  <= 0;
        end
        else begin
            I_raw_tvalid_d <= I_raw_valid;
            I_raw_tdata_r  <= I_raw_data;
        end
    end
    
    //---- kuai 3: hang-nei jie-pai ji-shu (cnt == 10 wei last) ----
    reg  [7:0] cnt;
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n )begin
            cnt <= 0;
        end
        else if(I_raw_valid)
            cnt <= 0;
        else if(!I_raw_valid)begin
            cnt <= cnt + 1;
        end
    end

    wire last = (cnt == 10);
    //---- kuai 4: chui-zhi fang-xiang kai-chuang (v_cnt 0~599, ji 600 hang) ----
    // 计算行数
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n || I_raw_frame_start)
            v_cnt <= 0;
        else if(last)
            v_cnt  <=  v_cnt + 1;
    end

    //---- kuai 5: V_valid (zhi fang-xing 0~599 hang) ----
    assign V_valid = (v_cnt >= 0) && (v_cnt <= 599);

    //---- kuai 6: shui-ping fang-xiang kai-chuang (h_cnt 0~255, ji 256 lie) ----
    // 计算每行像素个数
    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n || I_raw_frame_start) 
            h_cnt <= 0;
        else if(last)
            h_cnt <= 0;
        else if(I_raw_tvalid_d)
            h_cnt <=  h_cnt + 1;
    end
    assign H_valid = (h_cnt <= 255) && (h_cnt >= 0);
    
    assign tuser = (h_cnt == 0) && (v_cnt == 0) && I_raw_tvalid_d;
    
    assign O_raw_tdata  = V_valid && H_valid? I_raw_tdata_r:0;
    assign I_raw_tready = O_raw_tready;
    assign O_raw_tvalid = H_valid && V_valid && I_raw_tvalid_d;
    assign O_raw_tlast  = V_valid && (h_cnt == 255) && I_raw_tvalid_d;
    assign O_raw_tuser  = tuser;

    //---- kuai 7: bei zhu-shi diao de tiao-shi-he cwc (jin zhu-shi bao-liu) ----
//   cwc cwc_inst
// (
// .probe0  (I_raw_data			),
// .probe1  (I_raw_valid 		),
// .probe2  (I_raw_frame_start	),
// .probe3  (I_raw_frame_end  	),
// .probe4  (O_raw_tdata 		),
// .probe5  (O_raw_tlast 		),
// .probe6  (O_raw_tvalid		),
// .probe7  (O_raw_tuser 		),
// .probe8  (h_cnt 				),
// .probe9  (v_cnt 				),
// .probe10 (cnt 				),
// .clk	  (I_clk				)
// );


endmodule