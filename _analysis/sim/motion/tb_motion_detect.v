`timescale 1ns/1ps
// motion_detect 逐拍喂帧：16 块列 x 9 块行，块 80x80 像素 = 20 beat x 80 行
module tb_motion_detect;
    reg clk=0, rstn=0, tvalid=0, tuser=0, tlast=0, bypass=0;
    reg [95:0] tdata=0;
    wire [143:0] mask; wire [7:0] cnt, dc, dp; wire any;
    integer errors=0, i, y, b;

    motion_detect #(.STRICT2(1'b0)) dut (
        .I_clk(clk), .I_rst_n(rstn), .I_bypass(bypass),
        .I_tdata(tdata), .I_tvalid(tvalid), .I_tuser(tuser), .I_tlast(tlast),
        .O_blk_mask(mask), .O_blk_cnt(cnt), .O_motion_any(any),
        .O_dbg_cur(dc), .O_dbg_prev(dp));

    always #5 clk = ~clk;

    function [95:0] pack4(input [7:0] v);
        begin pack4 = {v,v,v, v,v,v, v,v,v, v,v,v}; end
    endfunction

    task send_frame(input [7:0] base, input [7:0] base2);
        integer yy, bx;
        begin
            for (yy = 0; yy < 720; yy = yy + 1) begin
                for (bx = 0; bx < 320; bx = bx + 1) begin
                    @(negedge clk);
                    tvalid = 1'b1;
                    tuser  = (yy==0 && bx==0);
                    tlast  = (bx==319);
                    tdata  = pack4((bx < 40) ? base2 : base);
                    @(posedge clk);
                end
            end
        end
    endtask

    initial begin
        rstn = 0; #40 rstn = 1; #20;
        // 帧 1：全帧恒定亮度 100 建立基线（无运动）
        send_frame(8'd100, 8'd100);
        @(negedge clk); tvalid=0; tlast=0; tuser=0; @(posedge clk);
        $display("[%0t] frame1 cnt=%0d any=%0b", $time, cnt, any);
        if (cnt != 0) begin $display("*** FAIL frame1 cnt=%0d (expect 0)", cnt); errors=errors+1; end

        // 帧 2：同样亮度 ⇒ 仍无运动
        send_frame(8'd100, 8'd100);
        @(negedge clk); tvalid=0; @(posedge clk);
        $display("[%0t] frame2 cnt=%0d", $time, cnt);
        if (cnt != 0) begin $display("*** FAIL frame2 cnt=%0d (expect 0)", cnt); errors=errors+1; end

        // 帧 3：块列 0..1 变亮到 160，其余 100 ⇒ 每块行 2 块，共 9*2=18
        send_frame(8'd100, 8'd160);
        @(negedge clk); tvalid=0; @(posedge clk);
        $display("[%0t] frame3 cnt=%0d any=%0b", $time, cnt, any);
        if (cnt != 18) begin $display("*** FAIL frame3 cnt=%0d (expect 18)", cnt); errors=errors+1; end
        if (any !== 1'b1) begin $display("*** FAIL frame3 any!=1"); errors=errors+1; end
        for (i = 0; i < 9; i = i + 1) begin
            if (mask[i*16+0] !== 1'b1 || mask[i*16+1] !== 1'b1)
                begin $display("*** FAIL mask blkrow %0d bx0/1 not set", i); errors=errors+1; end
            if (mask[i*16+5] !== 1'b0)
                begin $display("*** FAIL mask blkrow %0d bx5 wrongly set", i); errors=errors+1; end
        end

        // 帧 4：回到全 100 ⇒ 块列 0..1 又变化 ⇒ 仍应报 18
        send_frame(8'd100, 8'd100);
        @(negedge clk); tvalid=0; @(posedge clk);
        $display("[%0t] frame4 cnt=%0d", $time, cnt);
        if (cnt != 18) begin $display("*** FAIL frame4 cnt=%0d (expect 18)", cnt); errors=errors+1; end

        // 帧 5：仍全 100 ⇒ 与帧 4 相同 ⇒ 无运动
        send_frame(8'd100, 8'd100);
        @(negedge clk); tvalid=0; @(posedge clk);
        $display("[%0t] frame5 cnt=%0d", $time, cnt);
        if (cnt != 0) begin $display("*** FAIL frame5 cnt=%0d (expect 0)", cnt); errors=errors+1; end

        if (errors == 0) $display("*** ALL PASS, errors=0 ***");
        else             $display("*** FAILED, errors=%0d ***", errors);
        $finish;
    end
endmodule
