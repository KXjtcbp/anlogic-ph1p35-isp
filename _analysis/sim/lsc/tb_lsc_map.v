//=============================================================================
//  tb_lsc_map.v  ——  只做一件事：把整帧恒定灰度喂进 lsc.v，把每拍的
//  (S_bx, S_y, S_kr_r, S_kb_r, 输出 R 码) 打出来。
//  目的：直接量出 RTL 在 (beat,line) 上实际施加的增益，不经过 AWB / AE / 采集链。
//  运行：vsim -c -do "run -all; quit -f" tb_lsc_map
//=============================================================================
`timescale 1ns / 1ps

module tb_lsc_map;
    reg         clk = 0;
    reg         rst_n = 0;
    reg  [95:0] i_data = 0;
    reg         i_valid = 0, i_user = 0, i_last = 0;
    wire [95:0] o_data;
    wire        o_valid, o_user, o_last;

    localparam [11:0] H_BEATS = 12'd320;
    localparam [11:0] V_LINES = 12'd720;
    localparam [7:0]  VIN     = 8'd100;

    integer    file_map;
    integer    y, b;

    always #5 clk = ~clk;

    lsc #(
        .LSC_ENABLE(1'b1),
        .H_BEATS   (H_BEATS),
        .V_LINES   (V_LINES),
        .K_MAX     (10'd1023)
    ) dut (
        .I_clk(clk), .I_rst_n(rst_n), .I_bypass(1'b0),
        .I_tdata(i_data), .I_tvalid(i_valid), .I_tuser(i_user), .I_tlast(i_last),
        .O_tdata(o_data), .O_tvalid(o_valid), .O_tuser(o_user), .O_tlast(o_last)
    );

    // 输入位置打一拍（S_kr_r 是相对输入晚 1 拍登记的组合 S_kr）
    reg [8:0]  d_bx;
    reg [11:0] d_y;

    wire [95:0] pat = {VIN, VIN, VIN,  VIN, VIN, VIN,  VIN, VIN, VIN,  VIN, VIN, VIN};

    always @(posedge clk) begin
        d_bx <= dut.S_bx;
        d_y  <= dut.S_y;
        if (o_valid === 1'b1)
            $fwrite(file_map, "%0d %0d %0d %0d %0d %0d %0d\n",
                    d_bx, d_y, dut.S_kr_r, dut.S_kb_r,
                    o_data[23:16], o_data[15:8], o_data[7:0]);
    end

    initial begin
        file_map = $fopen("lsc_gain_map.txt", "w");
        repeat (6) @(negedge clk);
        rst_n = 1;
        repeat (2) @(negedge clk);

        for (y = 0; y < 720; y = y + 1) begin
            for (b = 0; b < 320; b = b + 1) begin
                i_data  = pat;
                i_valid = 1'b1;
                i_user  = (y == 0 && b == 0);
                i_last  = (b == 319);
                @(negedge clk);
            end
        end
        i_valid = 0; i_user = 0; i_last = 0;
        repeat (8) @(negedge clk);
        $fclose(file_map);
        $display("*** map done ***");
        $finish;
    end
endmodule
