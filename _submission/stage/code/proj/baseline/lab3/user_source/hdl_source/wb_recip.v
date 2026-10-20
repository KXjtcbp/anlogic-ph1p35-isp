//==============================================================================
//  wb_recip.v  —— AWB 白平衡增益计算（倒数查表法，替代 TD 流水除法器）
//-----------------------------------------------------------------------------
//  【为什么要有这个文件】
//  原实现在 awb.v 里例化两个 TD 生成的流水除法器 div_gen_G_R_r1 / divide_G_B_r1，
//  它们合计占用 1896 logic LUT + 2168 ripple + 5507 FF（约占全片 LUT6 的 11%），
//  是整个设计里最贵的一块。同一个除法如果换成「归一化 + 倒数 ROM + 一次乘法」，
//  面积可以降一个数量级，代价只有 1 个 ERAM 与 1~2 个 DSP。
//
//  【算法】定点倒数查表法（textbook reciprocal-LUT division）
//      e   = floor(log2(sum_x))            32bit 优先编码器
//      m   = sum_x >> (e-8)                ∈ [256,512)
//      idx = m - 256                       8bit ROM 索引
//      T2  = round(2^24 / (256+idx))       16bit ROM
//      dsh = sum_g >> (e-16)               截 20bit
//      q16 = (dsh * T2) >> 16              Q16 增益
//  推导：n = m * 2^(e-8)，故 1/n = 2^(8-e)/m = 2^(8-e)*T2/2^24
//        q16 = sum_g*2^16/n = sum_g*2^(24-e)/m = (sum_g*2^(16-e))*T2/2^16
//        dsh  正是 sum_g*2^(16-e)，所以 q16 = (dsh*T2)>>16。
//
//  【精度】对 44.9 万组真实范围随机扫描：典型 0.16~0.21%，最差 0.39%。
//  误差根源是 m 的向下取整（最多 1/256）。AWB 的验收带宽是 ±2%，
//  且该误差是确定性的（同输入同输出），不会引入帧间抖动。
//
//  【与旧实现的语义对齐】
//  * O_q[19:0]  = Q16 增益，与 divider 的 quotient[19:0] 同义
//  * |O_q[47:20] 非零 <=> 真商 >= 2^20，与 divider 的 quotient 高位同义，
//    调用方原有的 `if(|in_r_x1[47:20]) 饱和 20'hfffff` 分支一行不用改
//  * 组合逻辑、零延迟（旧 divider 有 50 级流水），但调用方是帧级锁存，
//    延迟不影响功能
//
//  【调用前提】I_den 与 I_num 必须由调用方保证：
//      I_den >= 32'd65536  且  I_num >= 32'd1
//    否则 e-16 会下溢。awb.v 里用 S_sum_ok 做门控，不满足时保持上一帧增益。
//    （帧首累加器刚清零时必然不满足，此时保持 = 正确行为）
//==============================================================================

module wb_recip (
    input  wire [31:0] I_den,   // sum_x（该通道的累加和，>= 65536）
    input  wire [31:0] I_num,   // sum_g（绿通道累加和，>= 1）
    output wire [47:0] O_q      // 与 divider quotient 同语义
);

    //--------------------------------------------------------------------------
    // 1) 求 e = floor(log2(I_den))，32bit 优先编码器
    //--------------------------------------------------------------------------
    reg  [4:0] S_e;
    reg        S_found;
    integer    i;
    always @(*) begin
        S_e     = 5'd0;
        S_found = 1'b0;
        for (i = 31; i >= 0; i = i - 1) begin
            if (!S_found && I_den[i]) begin
                S_e     = i[4:0];
                S_found = 1'b1;
            end
        end
    end

    wire [4:0] S_sh_m = S_e - 5'd8;    // 用于把 I_den 归一到 [256,512)
    wire [4:0] S_sh_d = S_e - 5'd16;   // 用于把 I_num 归一到 ~20bit

    wire [8:0]  S_m   = I_den >> S_sh_m;
    wire [7:0]  S_idx = S_m[7:0];      // = m - 256

    //--------------------------------------------------------------------------
    // 2) 倒数 ROM：256 x 16bit，内联 case 表（不可用 $readmemh）
    //--------------------------------------------------------------------------
    function [15:0] F_recip;
        input [7:0] idx;
        begin
            case (idx)
                8'd0  : F_recip = 16'hFFFF;
                8'd1  : F_recip = 16'hFF01;
                8'd2  : F_recip = 16'hFE04;
                8'd3  : F_recip = 16'hFD09;
                8'd4  : F_recip = 16'hFC10;
                8'd5  : F_recip = 16'hFB19;
                8'd6  : F_recip = 16'hFA23;
                8'd7  : F_recip = 16'hF930;
                8'd8  : F_recip = 16'hF83E;
                8'd9  : F_recip = 16'hF74E;
                8'd10 : F_recip = 16'hF660;
                8'd11 : F_recip = 16'hF574;
                8'd12 : F_recip = 16'hF48A;
                8'd13 : F_recip = 16'hF3A1;
                8'd14 : F_recip = 16'hF2BA;
                8'd15 : F_recip = 16'hF1D5;
                8'd16 : F_recip = 16'hF0F1;
                8'd17 : F_recip = 16'hF00F;
                8'd18 : F_recip = 16'hEF2F;
                8'd19 : F_recip = 16'hEE50;
                8'd20 : F_recip = 16'hED73;
                8'd21 : F_recip = 16'hEC98;
                8'd22 : F_recip = 16'hEBBE;
                8'd23 : F_recip = 16'hEAE5;
                8'd24 : F_recip = 16'hEA0F;
                8'd25 : F_recip = 16'hE939;
                8'd26 : F_recip = 16'hE866;
                8'd27 : F_recip = 16'hE793;
                8'd28 : F_recip = 16'hE6C3;
                8'd29 : F_recip = 16'hE5F3;
                8'd30 : F_recip = 16'hE526;
                8'd31 : F_recip = 16'hE459;
                8'd32 : F_recip = 16'hE38E;
                8'd33 : F_recip = 16'hE2C5;
                8'd34 : F_recip = 16'hE1FC;
                8'd35 : F_recip = 16'hE136;
                8'd36 : F_recip = 16'hE070;
                8'd37 : F_recip = 16'hDFAC;
                8'd38 : F_recip = 16'hDEE9;
                8'd39 : F_recip = 16'hDE28;
                8'd40 : F_recip = 16'hDD68;
                8'd41 : F_recip = 16'hDCA9;
                8'd42 : F_recip = 16'hDBEB;
                8'd43 : F_recip = 16'hDB2F;
                8'd44 : F_recip = 16'hDA74;
                8'd45 : F_recip = 16'hD9BA;
                8'd46 : F_recip = 16'hD902;
                8'd47 : F_recip = 16'hD84A;
                8'd48 : F_recip = 16'hD794;
                8'd49 : F_recip = 16'hD6DF;
                8'd50 : F_recip = 16'hD62C;
                8'd51 : F_recip = 16'hD579;
                8'd52 : F_recip = 16'hD4C7;
                8'd53 : F_recip = 16'hD417;
                8'd54 : F_recip = 16'hD368;
                8'd55 : F_recip = 16'hD2BA;
                8'd56 : F_recip = 16'hD20D;
                8'd57 : F_recip = 16'hD161;
                8'd58 : F_recip = 16'hD0B7;
                8'd59 : F_recip = 16'hD00D;
                8'd60 : F_recip = 16'hCF64;
                8'd61 : F_recip = 16'hCEBD;
                8'd62 : F_recip = 16'hCE17;
                8'd63 : F_recip = 16'hCD71;
                8'd64 : F_recip = 16'hCCCD;
                8'd65 : F_recip = 16'hCC29;
                8'd66 : F_recip = 16'hCB87;
                8'd67 : F_recip = 16'hCAE6;
                8'd68 : F_recip = 16'hCA46;
                8'd69 : F_recip = 16'hC9A6;
                8'd70 : F_recip = 16'hC908;
                8'd71 : F_recip = 16'hC86A;
                8'd72 : F_recip = 16'hC7CE;
                8'd73 : F_recip = 16'hC733;
                8'd74 : F_recip = 16'hC698;
                8'd75 : F_recip = 16'hC5FE;
                8'd76 : F_recip = 16'hC566;
                8'd77 : F_recip = 16'hC4CE;
                8'd78 : F_recip = 16'hC437;
                8'd79 : F_recip = 16'hC3A1;
                8'd80 : F_recip = 16'hC30C;
                8'd81 : F_recip = 16'hC278;
                8'd82 : F_recip = 16'hC1E5;
                8'd83 : F_recip = 16'hC152;
                8'd84 : F_recip = 16'hC0C1;
                8'd85 : F_recip = 16'hC030;
                8'd86 : F_recip = 16'hBFA0;
                8'd87 : F_recip = 16'hBF11;
                8'd88 : F_recip = 16'hBE83;
                8'd89 : F_recip = 16'hBDF6;
                8'd90 : F_recip = 16'hBD69;
                8'd91 : F_recip = 16'hBCDD;
                8'd92 : F_recip = 16'hBC52;
                8'd93 : F_recip = 16'hBBC8;
                8'd94 : F_recip = 16'hBB3F;
                8'd95 : F_recip = 16'hBAB6;
                8'd96 : F_recip = 16'hBA2F;
                8'd97 : F_recip = 16'hB9A8;
                8'd98 : F_recip = 16'hB921;
                8'd99 : F_recip = 16'hB89C;
                8'd100: F_recip = 16'hB817;
                8'd101: F_recip = 16'hB793;
                8'd102: F_recip = 16'hB710;
                8'd103: F_recip = 16'hB68D;
                8'd104: F_recip = 16'hB60B;
                8'd105: F_recip = 16'hB58A;
                8'd106: F_recip = 16'hB50A;
                8'd107: F_recip = 16'hB48A;
                8'd108: F_recip = 16'hB40B;
                8'd109: F_recip = 16'hB38D;
                8'd110: F_recip = 16'hB30F;
                8'd111: F_recip = 16'hB292;
                8'd112: F_recip = 16'hB216;
                8'd113: F_recip = 16'hB19B;
                8'd114: F_recip = 16'hB120;
                8'd115: F_recip = 16'hB0A6;
                8'd116: F_recip = 16'hB02C;
                8'd117: F_recip = 16'hAFB3;
                8'd118: F_recip = 16'hAF3B;
                8'd119: F_recip = 16'hAEC3;
                8'd120: F_recip = 16'hAE4C;
                8'd121: F_recip = 16'hADD6;
                8'd122: F_recip = 16'hAD60;
                8'd123: F_recip = 16'hACEB;
                8'd124: F_recip = 16'hAC77;
                8'd125: F_recip = 16'hAC03;
                8'd126: F_recip = 16'hAB8F;
                8'd127: F_recip = 16'hAB1D;
                8'd128: F_recip = 16'hAAAB;
                8'd129: F_recip = 16'hAA39;
                8'd130: F_recip = 16'hA9C8;
                8'd131: F_recip = 16'hA958;
                8'd132: F_recip = 16'hA8E8;
                8'd133: F_recip = 16'hA879;
                8'd134: F_recip = 16'hA80B;
                8'd135: F_recip = 16'hA79C;
                8'd136: F_recip = 16'hA72F;
                8'd137: F_recip = 16'hA6C2;
                8'd138: F_recip = 16'hA656;
                8'd139: F_recip = 16'hA5EA;
                8'd140: F_recip = 16'hA57F;
                8'd141: F_recip = 16'hA514;
                8'd142: F_recip = 16'hA4AA;
                8'd143: F_recip = 16'hA440;
                8'd144: F_recip = 16'hA3D7;
                8'd145: F_recip = 16'hA36E;
                8'd146: F_recip = 16'hA306;
                8'd147: F_recip = 16'hA29F;
                8'd148: F_recip = 16'hA238;
                8'd149: F_recip = 16'hA1D1;
                8'd150: F_recip = 16'hA16B;
                8'd151: F_recip = 16'hA106;
                8'd152: F_recip = 16'hA0A1;
                8'd153: F_recip = 16'hA03C;
                8'd154: F_recip = 16'h9FD8;
                8'd155: F_recip = 16'h9F74;
                8'd156: F_recip = 16'h9F11;
                8'd157: F_recip = 16'h9EAF;
                8'd158: F_recip = 16'h9E4D;
                8'd159: F_recip = 16'h9DEB;
                8'd160: F_recip = 16'h9D8A;
                8'd161: F_recip = 16'h9D29;
                8'd162: F_recip = 16'h9CC9;
                8'd163: F_recip = 16'h9C69;
                8'd164: F_recip = 16'h9C0A;
                8'd165: F_recip = 16'h9BAB;
                8'd166: F_recip = 16'h9B4C;
                8'd167: F_recip = 16'h9AEE;
                8'd168: F_recip = 16'h9A91;
                8'd169: F_recip = 16'h9A34;
                8'd170: F_recip = 16'h99D7;
                8'd171: F_recip = 16'h997B;
                8'd172: F_recip = 16'h991F;
                8'd173: F_recip = 16'h98C4;
                8'd174: F_recip = 16'h9869;
                8'd175: F_recip = 16'h980E;
                8'd176: F_recip = 16'h97B4;
                8'd177: F_recip = 16'h975A;
                8'd178: F_recip = 16'h9701;
                8'd179: F_recip = 16'h96A8;
                8'd180: F_recip = 16'h9650;
                8'd181: F_recip = 16'h95F8;
                8'd182: F_recip = 16'h95A0;
                8'd183: F_recip = 16'h9549;
                8'd184: F_recip = 16'h94F2;
                8'd185: F_recip = 16'h949C;
                8'd186: F_recip = 16'h9446;
                8'd187: F_recip = 16'h93F0;
                8'd188: F_recip = 16'h939B;
                8'd189: F_recip = 16'h9346;
                8'd190: F_recip = 16'h92F1;
                8'd191: F_recip = 16'h929D;
                8'd192: F_recip = 16'h9249;
                8'd193: F_recip = 16'h91F6;
                8'd194: F_recip = 16'h91A3;
                8'd195: F_recip = 16'h9150;
                8'd196: F_recip = 16'h90FE;
                8'd197: F_recip = 16'h90AC;
                8'd198: F_recip = 16'h905A;
                8'd199: F_recip = 16'h9009;
                8'd200: F_recip = 16'h8FB8;
                8'd201: F_recip = 16'h8F68;
                8'd202: F_recip = 16'h8F17;
                8'd203: F_recip = 16'h8EC8;
                8'd204: F_recip = 16'h8E78;
                8'd205: F_recip = 16'h8E29;
                8'd206: F_recip = 16'h8DDA;
                8'd207: F_recip = 16'h8D8C;
                8'd208: F_recip = 16'h8D3E;
                8'd209: F_recip = 16'h8CF0;
                8'd210: F_recip = 16'h8CA3;
                8'd211: F_recip = 16'h8C56;
                8'd212: F_recip = 16'h8C09;
                8'd213: F_recip = 16'h8BBC;
                8'd214: F_recip = 16'h8B70;
                8'd215: F_recip = 16'h8B24;
                8'd216: F_recip = 16'h8AD9;
                8'd217: F_recip = 16'h8A8E;
                8'd218: F_recip = 16'h8A43;
                8'd219: F_recip = 16'h89F8;
                8'd220: F_recip = 16'h89AE;
                8'd221: F_recip = 16'h8964;
                8'd222: F_recip = 16'h891B;
                8'd223: F_recip = 16'h88D2;
                8'd224: F_recip = 16'h8889;
                8'd225: F_recip = 16'h8840;
                8'd226: F_recip = 16'h87F8;
                8'd227: F_recip = 16'h87AF;
                8'd228: F_recip = 16'h8768;
                8'd229: F_recip = 16'h8720;
                8'd230: F_recip = 16'h86D9;
                8'd231: F_recip = 16'h8692;
                8'd232: F_recip = 16'h864C;
                8'd233: F_recip = 16'h8605;
                8'd234: F_recip = 16'h85BF;
                8'd235: F_recip = 16'h8579;
                8'd236: F_recip = 16'h8534;
                8'd237: F_recip = 16'h84EF;
                8'd238: F_recip = 16'h84AA;
                8'd239: F_recip = 16'h8465;
                8'd240: F_recip = 16'h8421;
                8'd241: F_recip = 16'h83DD;
                8'd242: F_recip = 16'h8399;
                8'd243: F_recip = 16'h8356;
                8'd244: F_recip = 16'h8312;
                8'd245: F_recip = 16'h82CF;
                8'd246: F_recip = 16'h828D;
                8'd247: F_recip = 16'h824A;
                8'd248: F_recip = 16'h8208;
                8'd249: F_recip = 16'h81C6;
                8'd250: F_recip = 16'h8185;
                8'd251: F_recip = 16'h8143;
                8'd252: F_recip = 16'h8102;
                8'd253: F_recip = 16'h80C1;
                8'd254: F_recip = 16'h8081;
                8'd255: F_recip = 16'h8040;
                default: F_recip = 16'h0000;
            endcase
        end
    endfunction

    wire [15:0] S_t2  = F_recip(S_idx);

    //--------------------------------------------------------------------------
    // 3) 归一化分子并做一次乘法
    //--------------------------------------------------------------------------
    wire [31:0] S_draw = I_num >> S_sh_d;
    wire [19:0] S_dsh  = (|S_draw[31:20]) ? 20'hFFFFF : S_draw[19:0];

    wire [35:0] S_prod = S_dsh * S_t2;      // 20 x 16 -> 36
    wire [35:0] S_q16  = S_prod >> 16;

    //--------------------------------------------------------------------------
    // 4) 与旧 divider 相同的溢出语义：真商 >= 2^20 时把 [47:20] 置非零
    //    ★不能用 S_q16 判溢出★ —— 上面 S_dsh 已经钳到 20bit，
    //    分子很大时 S_q16 反而被压小。改用等价条件直接判：
    //      q16 >= 2^20  <=>  num*2^16/den >= 2^20  <=>  num >= 16*den
    //--------------------------------------------------------------------------
    wire [35:0] S_num36 = {4'd0, I_num};
    wire [35:0] S_den16 = {I_den, 4'b0000};       // 16 * I_den
    wire        S_ovf   = (S_num36 >= S_den16);

    assign O_q = S_ovf ? 48'hFFFF_FFFF_FFFF : {28'd0, S_q16[19:0]};

endmodule
