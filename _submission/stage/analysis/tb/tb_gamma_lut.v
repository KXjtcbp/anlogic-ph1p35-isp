//=============================================================================
// [自动生成] 不要手改：由 E:\FPGA\_analysis\gen_tb_gamma.py 从 isp_gamma.v 的
//   内联表 mem_b00[0..255] 逐条导出期望值生成。
// 验证内容：
//   1) 旁路 I_gamma_bypass=1：8bit 原样通过（仍是 2 拍延迟）
//   2) 启用   I_gamma_bypass=0：输入 i 的输出必须 == 表[i]（256 条全查）
//   3) 12 个字节通道（4 像素 x RGB）逐拍严格相等（验证 12 张表复制循环）
//=============================================================================
`timescale 1ns/1ns
module tb_gamma_lut;
    reg         clk = 1'b0;
    always #5   clk = ~clk;
    reg         rst_n = 1'b0;
    reg  [95:0] td = 96'd0;
    reg         tvalid = 1'b0, tlast = 1'b0, tuser = 1'b0;
    reg         bypass = 1'b1, o_ready = 1'b1;
    wire [95:0] od;
    wire        ol, ou, ov, iready;

    isp_gamma dut (
        .I_clk(clk), .I_rst_n(rst_n), .I_tlast(tlast), .I_tuser(tuser),
        .I_tdata(td), .I_tvalid(tvalid), .I_tready(iready),
        .I_gamma_bypass(bypass),
        .O_tdata(od), .O_tlast(ol), .O_tuser(ou), .O_tvalid(ov), .O_tready(o_ready)
    );

    reg  [7:0] exp_tbl [0:255];
    reg  [7:0] got     [0:1023];
    integer n_got = 0, errors = 0, lane_err = 0, i, k;

    initial begin
        exp_tbl[  0] = 8'h00; exp_tbl[  1] = 8'h0d; exp_tbl[  2] = 8'h12; exp_tbl[  3] = 8'h16; exp_tbl[  4] = 8'h19; exp_tbl[  5] = 8'h1c; exp_tbl[  6] = 8'h1f; exp_tbl[  7] = 8'h21;
        exp_tbl[  8] = 8'h24; exp_tbl[  9] = 8'h26; exp_tbl[ 10] = 8'h28; exp_tbl[ 11] = 8'h2a; exp_tbl[ 12] = 8'h2c; exp_tbl[ 13] = 8'h2e; exp_tbl[ 14] = 8'h2f; exp_tbl[ 15] = 8'h31;
        exp_tbl[ 16] = 8'h33; exp_tbl[ 17] = 8'h34; exp_tbl[ 18] = 8'h36; exp_tbl[ 19] = 8'h37; exp_tbl[ 20] = 8'h39; exp_tbl[ 21] = 8'h3a; exp_tbl[ 22] = 8'h3b; exp_tbl[ 23] = 8'h3d;
        exp_tbl[ 24] = 8'h3e; exp_tbl[ 25] = 8'h3f; exp_tbl[ 26] = 8'h40; exp_tbl[ 27] = 8'h42; exp_tbl[ 28] = 8'h43; exp_tbl[ 29] = 8'h44; exp_tbl[ 30] = 8'h45; exp_tbl[ 31] = 8'h46;
        exp_tbl[ 32] = 8'h48; exp_tbl[ 33] = 8'h49; exp_tbl[ 34] = 8'h4a; exp_tbl[ 35] = 8'h4b; exp_tbl[ 36] = 8'h4c; exp_tbl[ 37] = 8'h4d; exp_tbl[ 38] = 8'h4e; exp_tbl[ 39] = 8'h4f;
        exp_tbl[ 40] = 8'h50; exp_tbl[ 41] = 8'h51; exp_tbl[ 42] = 8'h52; exp_tbl[ 43] = 8'h53; exp_tbl[ 44] = 8'h54; exp_tbl[ 45] = 8'h55; exp_tbl[ 46] = 8'h56; exp_tbl[ 47] = 8'h57;
        exp_tbl[ 48] = 8'h58; exp_tbl[ 49] = 8'h59; exp_tbl[ 50] = 8'h59; exp_tbl[ 51] = 8'h5a; exp_tbl[ 52] = 8'h5b; exp_tbl[ 53] = 8'h5c; exp_tbl[ 54] = 8'h5d; exp_tbl[ 55] = 8'h5e;
        exp_tbl[ 56] = 8'h5f; exp_tbl[ 57] = 8'h5f; exp_tbl[ 58] = 8'h60; exp_tbl[ 59] = 8'h61; exp_tbl[ 60] = 8'h62; exp_tbl[ 61] = 8'h63; exp_tbl[ 62] = 8'h64; exp_tbl[ 63] = 8'h64;
        exp_tbl[ 64] = 8'h65; exp_tbl[ 65] = 8'h66; exp_tbl[ 66] = 8'h67; exp_tbl[ 67] = 8'h68; exp_tbl[ 68] = 8'h68; exp_tbl[ 69] = 8'h69; exp_tbl[ 70] = 8'h6a; exp_tbl[ 71] = 8'h6b;
        exp_tbl[ 72] = 8'h6b; exp_tbl[ 73] = 8'h6c; exp_tbl[ 74] = 8'h6d; exp_tbl[ 75] = 8'h6e; exp_tbl[ 76] = 8'h6e; exp_tbl[ 77] = 8'h6f; exp_tbl[ 78] = 8'h70; exp_tbl[ 79] = 8'h70;
        exp_tbl[ 80] = 8'h71; exp_tbl[ 81] = 8'h72; exp_tbl[ 82] = 8'h73; exp_tbl[ 83] = 8'h73; exp_tbl[ 84] = 8'h74; exp_tbl[ 85] = 8'h75; exp_tbl[ 86] = 8'h75; exp_tbl[ 87] = 8'h76;
        exp_tbl[ 88] = 8'h77; exp_tbl[ 89] = 8'h77; exp_tbl[ 90] = 8'h78; exp_tbl[ 91] = 8'h79; exp_tbl[ 92] = 8'h79; exp_tbl[ 93] = 8'h7a; exp_tbl[ 94] = 8'h7b; exp_tbl[ 95] = 8'h7b;
        exp_tbl[ 96] = 8'h7c; exp_tbl[ 97] = 8'h7d; exp_tbl[ 98] = 8'h7d; exp_tbl[ 99] = 8'h7e; exp_tbl[100] = 8'h7e; exp_tbl[101] = 8'h7f; exp_tbl[102] = 8'h80; exp_tbl[103] = 8'h80;
        exp_tbl[104] = 8'h81; exp_tbl[105] = 8'h82; exp_tbl[106] = 8'h82; exp_tbl[107] = 8'h83; exp_tbl[108] = 8'h83; exp_tbl[109] = 8'h84; exp_tbl[110] = 8'h85; exp_tbl[111] = 8'h85;
        exp_tbl[112] = 8'h86; exp_tbl[113] = 8'h86; exp_tbl[114] = 8'h87; exp_tbl[115] = 8'h88; exp_tbl[116] = 8'h88; exp_tbl[117] = 8'h89; exp_tbl[118] = 8'h89; exp_tbl[119] = 8'h8a;
        exp_tbl[120] = 8'h8b; exp_tbl[121] = 8'h8b; exp_tbl[122] = 8'h8c; exp_tbl[123] = 8'h8c; exp_tbl[124] = 8'h8d; exp_tbl[125] = 8'h8d; exp_tbl[126] = 8'h8e; exp_tbl[127] = 8'h8f;
        exp_tbl[128] = 8'h8f; exp_tbl[129] = 8'h90; exp_tbl[130] = 8'h90; exp_tbl[131] = 8'h91; exp_tbl[132] = 8'h91; exp_tbl[133] = 8'h92; exp_tbl[134] = 8'h92; exp_tbl[135] = 8'h93;
        exp_tbl[136] = 8'h94; exp_tbl[137] = 8'h94; exp_tbl[138] = 8'h95; exp_tbl[139] = 8'h95; exp_tbl[140] = 8'h96; exp_tbl[141] = 8'h96; exp_tbl[142] = 8'h97; exp_tbl[143] = 8'h97;
        exp_tbl[144] = 8'h98; exp_tbl[145] = 8'h98; exp_tbl[146] = 8'h99; exp_tbl[147] = 8'h99; exp_tbl[148] = 8'h9a; exp_tbl[149] = 8'h9a; exp_tbl[150] = 8'h9b; exp_tbl[151] = 8'h9b;
        exp_tbl[152] = 8'h9c; exp_tbl[153] = 8'h9c; exp_tbl[154] = 8'h9d; exp_tbl[155] = 8'h9d; exp_tbl[156] = 8'h9e; exp_tbl[157] = 8'h9e; exp_tbl[158] = 8'h9f; exp_tbl[159] = 8'h9f;
        exp_tbl[160] = 8'ha0; exp_tbl[161] = 8'ha1; exp_tbl[162] = 8'ha1; exp_tbl[163] = 8'ha2; exp_tbl[164] = 8'ha2; exp_tbl[165] = 8'ha3; exp_tbl[166] = 8'ha3; exp_tbl[167] = 8'ha4;
        exp_tbl[168] = 8'ha4; exp_tbl[169] = 8'ha5; exp_tbl[170] = 8'ha5; exp_tbl[171] = 8'ha6; exp_tbl[172] = 8'ha6; exp_tbl[173] = 8'ha7; exp_tbl[174] = 8'ha7; exp_tbl[175] = 8'ha8;
        exp_tbl[176] = 8'ha8; exp_tbl[177] = 8'ha9; exp_tbl[178] = 8'ha9; exp_tbl[179] = 8'haa; exp_tbl[180] = 8'hab; exp_tbl[181] = 8'hab; exp_tbl[182] = 8'hac; exp_tbl[183] = 8'hac;
        exp_tbl[184] = 8'had; exp_tbl[185] = 8'had; exp_tbl[186] = 8'hae; exp_tbl[187] = 8'haf; exp_tbl[188] = 8'haf; exp_tbl[189] = 8'hb0; exp_tbl[190] = 8'hb0; exp_tbl[191] = 8'hb1;
        exp_tbl[192] = 8'hb2; exp_tbl[193] = 8'hb2; exp_tbl[194] = 8'hb3; exp_tbl[195] = 8'hb4; exp_tbl[196] = 8'hb4; exp_tbl[197] = 8'hb5; exp_tbl[198] = 8'hb5; exp_tbl[199] = 8'hb6;
        exp_tbl[200] = 8'hb7; exp_tbl[201] = 8'hb7; exp_tbl[202] = 8'hb8; exp_tbl[203] = 8'hb9; exp_tbl[204] = 8'hb9; exp_tbl[205] = 8'hba; exp_tbl[206] = 8'hbb; exp_tbl[207] = 8'hbb;
        exp_tbl[208] = 8'hbc; exp_tbl[209] = 8'hbd; exp_tbl[210] = 8'hbe; exp_tbl[211] = 8'hbe; exp_tbl[212] = 8'hbf; exp_tbl[213] = 8'hc0; exp_tbl[214] = 8'hc1; exp_tbl[215] = 8'hc1;
        exp_tbl[216] = 8'hc2; exp_tbl[217] = 8'hc3; exp_tbl[218] = 8'hc4; exp_tbl[219] = 8'hc5; exp_tbl[220] = 8'hc5; exp_tbl[221] = 8'hc6; exp_tbl[222] = 8'hc7; exp_tbl[223] = 8'hc8;
        exp_tbl[224] = 8'hc9; exp_tbl[225] = 8'hca; exp_tbl[226] = 8'hcb; exp_tbl[227] = 8'hcb; exp_tbl[228] = 8'hcc; exp_tbl[229] = 8'hcd; exp_tbl[230] = 8'hce; exp_tbl[231] = 8'hcf;
        exp_tbl[232] = 8'hd0; exp_tbl[233] = 8'hd1; exp_tbl[234] = 8'hd2; exp_tbl[235] = 8'hd3; exp_tbl[236] = 8'hd5; exp_tbl[237] = 8'hd6; exp_tbl[238] = 8'hd7; exp_tbl[239] = 8'hd8;
        exp_tbl[240] = 8'hd9; exp_tbl[241] = 8'hdb; exp_tbl[242] = 8'hdc; exp_tbl[243] = 8'hdd; exp_tbl[244] = 8'hdf; exp_tbl[245] = 8'he0; exp_tbl[246] = 8'he2; exp_tbl[247] = 8'he3;
        exp_tbl[248] = 8'he5; exp_tbl[249] = 8'he7; exp_tbl[250] = 8'he9; exp_tbl[251] = 8'hec; exp_tbl[252] = 8'hee; exp_tbl[253] = 8'hf1; exp_tbl[254] = 8'hf5; exp_tbl[255] = 8'hff;
    end

    // 采集输出（ov 高时抓一拍）；同时检查 12 个字节通道是否严格相等
    always @(posedge clk) begin
        if (ov) begin
            got[n_got] = od[7:0];
            if (od !== {12{od[7:0]}}) lane_err = lane_err + 1;
            n_got = n_got + 1;
        end
    end

    task drive(input [7:0] val);
    begin
        td = {12{val}};
        tvalid = 1'b1;
        @(posedge clk);
    end
    endtask

    task idle(input integer n);
    begin
        tvalid = 1'b0;
        td = 96'd0;
        for (i = 0; i < n; i = i + 1) @(posedge clk);
    end
    endtask

    integer t0;
    initial begin
        @(posedge clk);
        rst_n = 1'b0; @(posedge clk); @(posedge clk);
        rst_n = 1'b1; @(posedge clk);

        // ---- 用例 1：旁路直通 ----
        bypass = 1'b1;
        n_got = 0;
        drive(8'h00); drive(8'h2a); drive(8'hec); drive(8'hff); drive(8'h12); drive(8'h55);
        idle(4);
        $display("[1] bypass=1 收到 %0d 拍", n_got);
        if (n_got != 6) begin
            $display("  FAIL: 期望 6 拍直通"); errors = errors + 1;
        end
        for (i = 0; i < 6; i = i + 1) begin
            t0 = (i == 0) ? 8'h00 : (i == 1) ? 8'h2a : (i == 2) ? 8'hec :
                 (i == 3) ? 8'hff : (i == 4) ? 8'h12 : 8'h55;
            if (got[i] !== t0[7:0]) begin
                $display("  FAIL 直通[%0d]: got %02x exp %02x", i, got[i], t0[7:0]);
                errors = errors + 1;
            end
        end
        if (errors == 0) $display("  PASS: 000 2a ec ff 12 55 原样通过");

        // ---- 用例 2：256 条查表全覆盖 ----
        bypass = 1'b0;
        n_got = 0;
        for (k = 0; k < 256; k = k + 1) drive(k[7:0]);
        idle(4);
        $display("[2] bypass=0 收到 %0d 拍", n_got);
        if (n_got != 256) begin
            $display("  FAIL: 期望 256 拍"); errors = errors + 1;
        end
        for (i = 0; i < 256; i = i + 1) begin
            if (got[i] !== exp_tbl[i]) begin
                if (errors < 12) $display("  FAIL 查表[%0d]: got %02x exp %02x", i, got[i], exp_tbl[i]);
                errors = errors + 1;
            end
        end
        $display("  查表逐条比对错误数 = %0d", errors);
        $display("  12 通道不一致拍数   = %0d", lane_err);
        errors = errors + lane_err;

        // ---- 锚点 ----
        $display("  锚点: 0->%02x 4->%02x 8->%02x 42->%02x 64->%02x 118->%02x 160->%02x 200->%02x 236->%02x 255->%02x",
                 exp_tbl[0], exp_tbl[4], exp_tbl[8], exp_tbl[42], exp_tbl[64],
                 exp_tbl[118], exp_tbl[160], exp_tbl[200], exp_tbl[236], exp_tbl[255]);

        if (errors == 0) $display("==== ALL PASS ====");
        else             $display("==== FAIL: %0d ====", errors);
        $finish;
    end
endmodule
