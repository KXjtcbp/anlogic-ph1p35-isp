`timescale 1ns / 1ps
// ============================================================================
//  tb_obj_detect.v — obj_detect 功能回归
//  场景：1280x720，左半（x<640，即块列 0..7）像素为红 (200,40,40)，
//        右半（块列 8..15）像素为黑 (10,10,10)。
//  期望：掩码从左 8 列全 1、右 8 列全 0；块数 = 8 列 x 9 行 = 72。
// ============================================================================
module tb_obj_detect;

    function integer popcount(input [143:0] v);
        integer k;
        begin
            popcount = 0;
            for (k = 0; k < 144; k = k + 1) if (v[k]) popcount = popcount + 1;
        end
    endfunction


    localparam OSD_X0 = 0;      // 不做 OSD 剔除，整帧参与

    reg         clk = 1'b0;
    reg         rst_n = 1'b0;
    reg  [95:0] tdata = 96'd0;
    reg         tvalid = 1'b0;
    reg         tuser  = 1'b0;
    reg         tlast  = 1'b0;

    wire [143:0] blk_mask;
    wire [7:0]   blk_cnt;
    wire         obj_any;
    wire [15:0]  hit_sum;

    always #8.333 clk = ~clk;      // 60 MHz

    obj_detect #(
        .H_BEATS       (9'd320 ),
        .V_LINES       (12'd720),
        .BEATS_PER_BLK (5'd20  ),
        .LINES_PER_BLK (7'd80  ),
        .LUM_MIN       (8'd80  ),
        .CHR_MIN       (8'd35  ),
        .HIT_MIN       (13'd40 )
    ) dut (
        .I_clk      (clk     ),
        .I_rst_n    (rst_n   ),
        .I_bypass   (1'b0    ),
        .I_tdata    (tdata   ),
        .I_tvalid   (tvalid  ),
        .I_tuser    (tuser   ),
        .I_tlast    (tlast   ),
        .O_blk_mask (blk_mask),
        .O_blk_cnt  (blk_cnt ),
        .O_obj_any  (obj_any ),
        .O_hit_sum  (hit_sum )
    );

    reg [7:0] RED  [0:3];
    reg [7:0] BLK  [0:3];

    integer errors = 0;
    integer x, y, b, nchk;

    task chk(input [255:0] nm, input integer got, input integer exp);
        begin
            nchk = nchk + 1;
            if (got !== exp) begin
                errors = errors + 1;
                $display("*** FAIL %0s : got %0d  exp %0d ***", nm, got, exp);
            end
        end
    endtask

    // 一帧
    task send_frame(input integer is_red_left);
        integer beat, px;
        begin
            for (y = 0; y < 720; y = y + 1) begin
                for (beat = 0; beat < 320; beat = beat + 1) begin
                    tvalid = 1'b1;
                    tuser  = (y == 0 && beat == 0);
                    tlast  = (beat == 319);
                    // 4 个像素：beat*4 + 0..3
                    for (px = 0; px < 4; px = px + 1) begin
                        if ((beat*4 + px) < 640) begin
                            tdata[px*24 +: 8]  = 8'd40;    // B
                            tdata[px*24+8 +: 8] = 8'd40;   // G
                            tdata[px*24+16+: 8] = 8'd200;  // R
                        end else begin
                            tdata[px*24 +: 8]  = 8'd10;
                            tdata[px*24+8 +: 8] = 8'd10;
                            tdata[px*24+16+: 8] = 8'd10;
                        end
                    end
                    @(posedge clk);
                    #1;
                end
                tvalid = 1'b0; tuser = 1'b0; tlast = 1'b0;
                repeat (2) @(posedge clk);
                #1;
            end
        end
    endtask

    integer i, one_cnt, left_cnt, right_cnt;

    initial begin
        nchk = 0;
        $display("=== tb_obj_detect start ===");
        repeat (5) @(posedge clk);
        rst_n = 1'b1;
        repeat (5) @(posedge clk);

        send_frame(1);          // 第 1 帧：建立 S_prev
        repeat (5) @(posedge clk);
        #1;
        send_frame(1);          // 第 2 帧：两帧确认后才输出（fix5 的行为）
        repeat (5) @(posedge clk);
        #1;

        // 统计
        one_cnt = 0; left_cnt = 0; right_cnt = 0;
        for (i = 0; i < 144; i = i + 1) begin
            if (blk_mask[i]) begin
                one_cnt = one_cnt + 1;
                if ((i % 16) < 8) left_cnt = left_cnt + 1;
                else              right_cnt = right_cnt + 1;
            end
        end

        $display("  掩码 1 的个数 = %0d  (左半 %0d / 右半 %0d)", one_cnt, left_cnt, right_cnt);
        $display("  块计数 blk_cnt = %0d   hit_sum = %0d   obj_any = %0b", blk_cnt, hit_sum, obj_any);

        chk("left  72", left_cnt, 72);
        chk("right  0", right_cnt, 0);
        chk("cnt  72",  blk_cnt,  72);
        chk("any   1",  obj_any,  1);

        // 第二帧：全黑 ⇒ 掩码应全 0
        for (b = 0; b < 63; b = b + 1) begin   // [A2] 2 帧清 S_prev + 61 帧让 60 帧保持过期   // [A2] 前 2 帧清 S_prev，再 9 帧让 8 帧保持过期后再判 0
            for (i = 0; i < 720; i = i + 1) begin
                for (x = 0; x < 320; x = x + 1) begin
                    tvalid = 1'b1;
                    tuser  = (i == 0 && x == 0);
                    tlast  = (x == 319) && (i == 719);
                    tdata  = {4{24'h0A0A0A}};
                    @(posedge clk); #1;
                end
                tvalid = 1'b0; tuser = 1'b0; tlast = 1'b0;
                repeat (2) @(posedge clk); #1;
            end
            repeat (5) @(posedge clk);
            // [A2-PERSIST] 打印暗段每帧的掩码位数，验证 60 帧保持
            if (b < 3 || b == 30 || b == 58 || b == 59 || b == 60 || b == 61 || b == 62)
                $display("   [persist] dark frame b=%0d  mask_popcount=%0d", b, popcount(blk_mask));
        end
        repeat (5) @(posedge clk); #1;
        one_cnt = 0;
        for (i = 0; i < 144; i = i + 1) if (blk_mask[i]) one_cnt = one_cnt + 1;
        $display("  全黑帧后掩码 1 的个数 = %0d  blk_cnt = %0d", one_cnt, blk_cnt);
        chk("dark 0", one_cnt, 0);
        chk("dark cnt 0", blk_cnt, 0);

        if (errors == 0) $display("*** ALL PASS, errors=0 (n_chk=%0d) ***", nchk);
        else             $display("*** FAILED, errors=%0d ***", errors);
        $finish;
    end

    initial begin
        #20_000_000;
        $display("*** TIMEOUT ***");
        $finish;
    end

endmodule
