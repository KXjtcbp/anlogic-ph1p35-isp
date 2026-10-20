//=============================================================================
// 文件      : isp/data128_96/data128_96.v
// 模块      : data128_96
// 功能      : 位宽重切：把 128bit 截成 96bit —— 按 32bit 一组分成 4 组，丢掉每组高 8bit，保留每组的低 24bit（一个像素）后按原顺序拼起来。
// 数据通路  : 输入 I_tdata[127:0]，输出 O_tdata[95:0]；O_tdata = {I_tdata[23:0], I_tdata[55:32], I_tdata[87:64], I_tdata[119:96]}，即组 0(bit23:0)->O[95:72]、组 1(bit55:32)->O[71:48]、组 2(bit87:64)->O[47:24]、组 3(bit119:96)->O[23:0]。96bit = 4 像素 x 24bit，[23:16]=R、[15:8]=G、[7:0]=B。每 128bit 的 4 个高 8bit 被丢弃，所以是单向、不可逆的缩位。
// 时钟/复位 : 无时钟、无复位：纯组合 assign。
// 依赖      : 被 isp/isp_top.v:121 例化为 u_data128_96。第 17 行是注释掉的另一种写法（把 I_tdata 重复使用的那种），仅作历史保留。
// 综合/实现 : 本文件在 camera_to_dsi_display.al 的编译清单中，纯组合、无资源问题。
//-----------------------------------------------------------------------------
// 修改记录  :
//   <日期不详>  自官方 lab3 基线导入后本工程未见针对本文件的修改
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑），对照见 E:\FPGA\_analysis\rename_report.txt
//=============================================================================
/*****************************************************************
Company : Nanjing Weiku Robot Technology Co., Ltd.
Brand   : VLKUS
Technical forum:www.uisrc.com
@Author      :   XiaoQingquan 
@Time        :   2024/09/18 
@Description :   
*****************************************************************/

//---- kuai 1: duan-kou sheng-ming (128bit shu-ru -> 96bit shu-chu) ----
module data128_96 (

    input  wire [127:0] I_tdata,
    output wire [ 95:0] O_tdata
);

  //---- kuai 2: shai-jian pin-jie (diu diao mei 32bit de gao 8bit, liu xia 4 x 24bit) ----
  assign O_tdata = {I_tdata[23:0], I_tdata[55:32], I_tdata[87:64], I_tdata[119:96]};
  //assign O_tdata = {I_tdata, I_tdata, I_tdata[55:32], I_tdata[23:0]};

endmodule
