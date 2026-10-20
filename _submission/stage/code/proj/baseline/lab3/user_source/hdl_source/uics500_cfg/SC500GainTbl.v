//=============================================================================
// [HDR-2026-10-09] 文件      : SC500GainTbl.v
// 模块      : SC500GainTbl
// 功能      : 把自动曝光/增益算法给出的增益档位索引（0..73）翻译成 SC500CS 的模拟增益寄存器编码（16bit，高 8bit 写在 0x3e08、低 8bit 写在 0x3e09）。
// 数据通路  : I_gain_idx(7bit 档位) → 查表 → O_gain_code(16bit 寄存器编码)
// 时钟/复位 : I_clk 上升沿同步输出；I_rstn 低有效。
// 依赖      : 被 uics500_cfg/uicfgcs500_720p.v:124-130 与 uics500_cfg/uicfgcs500.v:154 例化
// 综合/实现 : ■ 表内三段阶梯 0x0320 / 0x0720 / 0x0F20 = 粗调 ×1 / ×2 / ×4；每段内低字节 0x20..0x3F 是细调。
//           ■ ★表只到索引 73（0x0F29），因此把 RTL 自动增益路径封顶在约 4.28×；而手册表2-4 允许到 15.750×。想用更高模拟增益只能改 init 表（uics500reg_720p60.v 索引 112/113），按键调不上去。
//-----------------------------------------------------------------------------
// 修改记录  :
//   2026-09-27  [230f479] 导入官方 lab3 基线
//   2026-10-09  （未提交）端口改名 I → I_gain_idx、O → O_gain_code（原名无语义），同步更新 2 处例化
//-----------------------------------------------------------------------------
// 2026-10-09 全树做过一次标识符改名（只改名字不改逻辑，见 E:\FPGA\_analysis\rename_report.txt）
//=============================================================================
`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Create Date:    01:32:02 06/12/2023 
// Module Name:    SC500GainTbl 
//////////////////////////////////////////////////////////////////////////////////
module SC500GainTbl(
	input 			I_clk,
	input 			I_rstn,
	input 	[6:0] 	I_gain_idx,
	output reg	[15:0] 	O_gain_code
);

	always @(posedge I_clk) begin
		O_gain_code <= 0; 
		case (I_gain_idx)
			0:O_gain_code<=16'h0320; 1:O_gain_code<=16'h0321; 2:O_gain_code<=16'h0322; 3:O_gain_code<=16'h0323; 4:O_gain_code<=16'h0324; 5:O_gain_code<=16'h0325; 6:O_gain_code<=16'h0326; 7:O_gain_code<=16'h0327; 8:O_gain_code<=16'h0328; 9:O_gain_code<=16'h0329; 10:O_gain_code<=16'h032A; 11:O_gain_code<=16'h032B; 12:O_gain_code<=16'h032C; 13:O_gain_code<=16'h032D; 14:O_gain_code<=16'h032E; 15:O_gain_code<=16'h032F; 
			16:O_gain_code<=16'h0330; 17:O_gain_code<=16'h0331; 18:O_gain_code<=16'h0332; 19:O_gain_code<=16'h0333; 20:O_gain_code<=16'h0334; 21:O_gain_code<=16'h0335; 22:O_gain_code<=16'h0336; 23:O_gain_code<=16'h0337; 24:O_gain_code<=16'h0338; 25:O_gain_code<=16'h0339; 26:O_gain_code<=16'h033A; 27:O_gain_code<=16'h033B; 28:O_gain_code<=16'h033C; 29:O_gain_code<=16'h033D; 30:O_gain_code<=16'h033E; 31:O_gain_code<=16'h033F; 
			32:O_gain_code<=16'h0720; 33:O_gain_code<=16'h0721; 34:O_gain_code<=16'h0722; 35:O_gain_code<=16'h0723; 36:O_gain_code<=16'h0724; 37:O_gain_code<=16'h0725; 38:O_gain_code<=16'h0726; 39:O_gain_code<=16'h0727; 40:O_gain_code<=16'h0728; 41:O_gain_code<=16'h0729; 42:O_gain_code<=16'h072A; 43:O_gain_code<=16'h072B; 44:O_gain_code<=16'h072C; 45:O_gain_code<=16'h072D; 46:O_gain_code<=16'h072E; 47:O_gain_code<=16'h072F; 
			48:O_gain_code<=16'h0730; 49:O_gain_code<=16'h0731; 50:O_gain_code<=16'h0732; 51:O_gain_code<=16'h0733; 52:O_gain_code<=16'h0734; 53:O_gain_code<=16'h0735; 54:O_gain_code<=16'h0736; 55:O_gain_code<=16'h0737; 56:O_gain_code<=16'h0738; 57:O_gain_code<=16'h0739; 58:O_gain_code<=16'h073A; 59:O_gain_code<=16'h073B; 60:O_gain_code<=16'h073C; 61:O_gain_code<=16'h073D; 62:O_gain_code<=16'h073E; 63:O_gain_code<=16'h073F; 
			64:O_gain_code<=16'h0F20; 65:O_gain_code<=16'h0F21; 66:O_gain_code<=16'h0F22; 67:O_gain_code<=16'h0F23; 68:O_gain_code<=16'h0F24; 69:O_gain_code<=16'h0F25; 70:O_gain_code<=16'h0F26; 71:O_gain_code<=16'h0F27; 72:O_gain_code<=16'h0F28; 73:O_gain_code<=16'h0F29; 
		endcase
	end

endmodule
