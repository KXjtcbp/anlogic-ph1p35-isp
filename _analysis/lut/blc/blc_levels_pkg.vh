// ===================================================================
// blc_levels_pkg.vh —— 模块 A（黑电平校正）参数包
// 由 _analysis/scripts/gen_blc_module_a.py 生成，请勿手改
// 生成规则：level = 40 + 2 * index  （index 0..15）
// 默认 index = 8 -> level = 56 （10-09 ChipWatcher 实测基座下限 57 减 1）
// ===================================================================
`ifndef BLC_LEVELS_PKG_VH
`define BLC_LEVELS_PKG_VH

localparam [9:0] BLC_LEVEL_00 = 10'd40 ;
localparam [9:0] BLC_LEVEL_01 = 10'd42 ;
localparam [9:0] BLC_LEVEL_02 = 10'd44 ;
localparam [9:0] BLC_LEVEL_03 = 10'd46 ;
localparam [9:0] BLC_LEVEL_04 = 10'd48 ;
localparam [9:0] BLC_LEVEL_05 = 10'd50 ;
localparam [9:0] BLC_LEVEL_06 = 10'd52 ;
localparam [9:0] BLC_LEVEL_07 = 10'd54 ;
localparam [9:0] BLC_LEVEL_08 = 10'd56 ;  // <= 默认
localparam [9:0] BLC_LEVEL_09 = 10'd58 ;
localparam [9:0] BLC_LEVEL_10 = 10'd60 ;
localparam [9:0] BLC_LEVEL_11 = 10'd62 ;
localparam [9:0] BLC_LEVEL_12 = 10'd64 ;
localparam [9:0] BLC_LEVEL_13 = 10'd66 ;
localparam [9:0] BLC_LEVEL_14 = 10'd68 ;
localparam [9:0] BLC_LEVEL_15 = 10'd70 ;

localparam [3:0] BLC_DEFAULT_IDX = 4'd8;
localparam [9:0] BLC_DEFAULT_LEVEL = BLC_LEVEL_08;

// 4bit index -> 10bit level
function [9:0] blc_level_of;
    input [3:0] idx;
    begin
        case (idx)
            4'd0  : blc_level_of = 10'd40;
            4'd1  : blc_level_of = 10'd42;
            4'd2  : blc_level_of = 10'd44;
            4'd3  : blc_level_of = 10'd46;
            4'd4  : blc_level_of = 10'd48;
            4'd5  : blc_level_of = 10'd50;
            4'd6  : blc_level_of = 10'd52;
            4'd7  : blc_level_of = 10'd54;
            4'd8  : blc_level_of = 10'd56;
            4'd9  : blc_level_of = 10'd58;
            4'd10 : blc_level_of = 10'd60;
            4'd11 : blc_level_of = 10'd62;
            4'd12 : blc_level_of = 10'd64;
            4'd13 : blc_level_of = 10'd66;
            4'd14 : blc_level_of = 10'd68;
            4'd15 : blc_level_of = 10'd70;
            default: blc_level_of = BLC_DEFAULT_LEVEL;
        endcase
    end
endfunction

`endif
