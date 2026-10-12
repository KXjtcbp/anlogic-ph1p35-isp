//=============================================================================
// æ–‡ä»¶      : isp/csi_unpacket_2lane.v
// æ¨¡å—      : csi_unpacket_2lane
// åŠŸèƒ½      : è§£æ MIPI CSI-2 RX æ ¸è¾“å‡ºçš„ 16bit(2 lane Ã— 1 byte)æ•°æ®æµï¼šç”¨ valid ä¸Šå‡æ²¿å®šä½åŒ…å¤´ï¼ŒæŒ‰ DT è¯†åˆ«å¸§é¦–(0x00)ã€å¸§å°¾(0x01)ä¸ RAW10 æ•°æ®é•¿åŒ…(0x2B)ï¼Œä»åŒ…å¤´å–å‡ºå­—è®¡æ•°å¹¶åœˆå‡ºæ•°æ®åŒºï¼ŒæŠŠ 2 æ‹ 16bit æ‹¼æˆ 32bit è¾“å‡ºã€‚
// æ•°æ®é€šè·¯  : I_hs_valid/I_hs_data â†’ æ‰“ 1 æ‹ â†’ S_head_en(= æœ¬æ‹ valid ä¸”ä¸Šä¸€æ‹ !valid) â†’ DT åˆ¤å®š â†’ S_data_length(å­—èŠ‚æ•° >> 1ï¼Œå•ä½æ¢ç®—æˆ 2lane çš„æ‹æ•°) â†’ S_data_en / S_data_en_cnt åœˆå‡ºæ•°æ®åŒº â†’ csi_valid_r æ¯æ‹ç¿»è½¬äº§ç”Ÿ 2 æ‹ä¸€æ¬¡çš„ O_csi_valid â†’ O_csi_data ç”± {æ—§ [15:0], I_hs_data} ç§»ä½æ‹¼æ¥ã€‚
// æ—¶é’Ÿ/å¤ä½ : å•æ—¶é’Ÿ I_clkï¼›I_rst_n ä½ç”µå¹³å¼‚æ­¥å¤ä½(ä»… S_data_en å—ä½¿ç”¨)ï¼›å…¶ä½™æ—¶åºå—åªå« posedge I_clkã€‚
// ä¾èµ–      : æ— å­æ¨¡å—ä¾‹åŒ–ã€‚
// ç»¼åˆ/å®ç° : `timescale 1ns/1nsï¼›å…³é”®ä¿¡å·å¸¦ //synthesis keep å±æ€§ã€‚FRAME_DATA_DT é€‰ 0x2B(RAW10)ï¼Œ0x2A(RAW8) é‚£ä¸€è¡Œè¢«æ³¨é‡Šæ‰ï¼›å¯¹å¸§é¦–/å¸§å°¾åªåšè¾“å‡ºæŒ‡ç¤ºï¼Œå¹¶ä¸æˆªæ–­æ•°æ®åŒºã€‚
//-----------------------------------------------------------------------------
// ä¿®æ”¹è®°å½•  :
//   <æ—¥æœŸä¸è¯¦>  è‡ªå®˜æ–¹ lab3 åŸºçº¿å¯¼å…¥åæœ¬å·¥ç¨‹æœªè§é’ˆå¯¹æœ¬æ–‡ä»¶çš„ä¿®æ”¹
//-----------------------------------------------------------------------------
// 2026-10-09 å…¨æ ‘åšè¿‡ä¸€æ¬¡æ ‡è¯†ç¬¦æ”¹åï¼ˆåªæ”¹åå­—ä¸æ”¹é€»è¾‘ï¼‰ï¼Œå¯¹ç…§è§ E:\FPGA\_analysis\rename_report.txt
//=============================================================================
/*******************************MILIANKE*******************************
*Company : MiLianKe Electronic Technology Co., Ltd.
*WebSite:https://www.milianke.com
*TechWeb:https://www.uisrc.com
*tmall-shop:https://milianke.tmall.com
*jd-shop:https://milianke.jd.com
*taobao-shop1: https://milianke.taobao.com
*Create Date: 2023/03/23
*Module Name:
*File Name:
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
/*********csi_unpacket_2lane MIPI CSI½âÂë***********
--°æ±¾ºÅ1.0
--MIPI IPÊı¾İ½âÂëÎª32bitÊı¾İÊä³ö¸øÏÂÒ»¼¶Ê¹ÓÃ£¬ÕâÀïĞèÒªÁË½âMIPIĞ­ÒéµÄÊı¾İ¸ñÊ½
*********************************************************************/

`timescale 1ns / 1ns

module csi_unpacket_2lane 
(
input wire          I_clk,  //À´×ÔMIPI ºËµÄÊ±ÖÓ
input wire          I_rst_n,//Òì²½¸´Î»

input wire          I_hs_valid,//synthesis keep //À´×ÔMIPIºËµÄÊı¾İÓĞĞ§ĞÅºÅ,ÆäÖĞÒ²°üº¬µÄÊı¾İÀàĞÍ
input wire[15: 0]   I_hs_data, //synthesis keep //À´×ÔMIPIºËµÄÊı¾İ,ÆäÖĞÒ²°üº¬µÄÊı¾İÀàĞÍÊı¾İ£¬ÕâÀï¶¨Òå2LANE£¬1BYTEÄ£Ê½

output reg           O_csi_frame_start, //Ö¡ÆğÊ¼£¬1¸öÖÜÆÚÓĞĞ§
output reg           O_csi_frame_end,   //Ö¡½áÊø£¬1¸öÖÜÆÚÓĞĞ§
output reg           O_csi_valid, //synthesis keep      //ÓĞĞ§Êı¾İÊä³ö
output reg           O_csi_hs,
output reg  [31: 0]  O_csi_data   //synthesis keep      //ÓĞĞ§Êı¾İ£¬ÕâÀï¶¨Òå2LANE£¬1BYTEÄ£Ê½
);


//MIPIÊı¾İÀàĞÍ
//DT 00 Ö¡ÆğÊ¼°ü
//DT 01 Ö¡½áÊø°ü
//DT 02 ĞĞÆğÊ¼°ü
//DT 03 ĞĞ½áÊø°ü
//DT 2a 8BITÄ£Ê½ÏÂµÄÊı¾İ³¤°ü
//DT 2b 10BITÄ£Ê½ÏÂµÄÊı¾İ³¤°ü

//---- é•¿åŒ…æ•°æ®ç±»å‹å®šä¹‰ï¼ˆDTï¼‰ ----
localparam FRAME_DATA_DT  = 8'h2B;   //RAW10  // RAW10 é•¿åŒ…ï¼›RAW8 å¯¹åº” 0x2Aï¼ˆè§ä¸‹ä¸€è¡Œè¢«æ³¨é‡Šçš„å®šä¹‰ï¼‰
//localparam FRAME_DATA_DT  = 8'h2A;     //RAW8
localparam FRAME_START_DT = 8'h00;
localparam FRAME_END_DT   = 8'h01;

//---- å†…éƒ¨ä¿¡å· ----
reg        S_hs_valid_1d;      //synthesis keep   
reg [15:0] S_hs_data_1d;       //synthesis keep   
wire       S_head_en;          //synthesis keep   
reg        S_head_en_1d;       //synthesis keep      
reg [15:0] S_data_length;      //synthesis keep      
reg        S_data_en;          //synthesis keep        
reg [15:0] S_data_en_cnt;      //synthesis keep      

//---- å¸§å¤´ä½¿èƒ½ï¼švalid ä¸Šå‡æ²¿ï¼ˆæ¯ä¸ªåŒ…çš„é¦–å­—èŠ‚ï¼‰ ----
assign  S_head_en  = ~S_hs_valid_1d & I_hs_valid;//Ö¡Í·Ê¹ÄÜ  // ä¸Šä¸€æ‹æ— æ•ˆã€æœ¬æ‹æœ‰æ•ˆ â†’ åŒ…å¤´é¦–å­—èŠ‚

//---- è¾“å…¥æ‰“ 1 æ‹ ----
//I_hs_valid ºÍ I_hs_data ¸÷´ò1ÅÄ
always @(posedge I_clk) begin 
    S_hs_valid_1d        <= I_hs_valid;
    S_hs_data_1d         <= I_hs_data;
    S_head_en_1d         <= S_head_en;//Ö¡Í·Ê¹ÄÜ
end

//---- å¸§èµ·å§‹åˆ¤æ–­ï¼šåŒ…å¤´ DT = 0x00 ----
//Ö¡ÆğÊ¼ÅĞ¶Ï
always @(posedge I_clk) 
    O_csi_frame_start <= (S_head_en_1d && S_hs_data_1d[15:8] == FRAME_START_DT);  // åŒ…å¤´é¦–å­—èŠ‚çš„é«˜ 8bit å³ DT


//---- å¸§ç»“æŸåˆ¤æ–­ï¼šåŒ…å¤´ DT = 0x01 ----
//Ö¡½áÊøÅĞ¶Ï
always @(posedge I_clk) 
    O_csi_frame_end  <= (S_head_en_1d && S_hs_data_1d[15:8] == FRAME_END_DT);  // åŒä¸Šï¼ŒDT=0x01 è¡¨ç¤ºå¸§ç»“æŸ

//---- æ•°æ®é•¿åŒ…ï¼šå–å­—è®¡æ•° WCï¼Œæ¢ç®—æˆ 2lane çš„æ‹æ•° ----
//»ñÈ¡Êı¾İ³¤¶È
always @(posedge I_clk) begin 
    if(I_hs_valid)begin
        if(S_head_en_1d && S_hs_data_1d[15:8] == FRAME_DATA_DT)
            S_data_length <= {I_hs_data[15:8],S_hs_data_1d[7:0]} >> 1;  // WC ä¸ºå­—èŠ‚æ•°ï¼Œ2 lane æ¯æ‹ 2 å­—èŠ‚ï¼Œæ•…å³ç§» 1 å¾—æ‹æ•°
        else    
            S_data_length <= S_data_length;
    end
    else    
        S_data_length <= 'd0;
end


//---- æ•°æ®æœ‰æ•ˆçª—å£ï¼ˆS_data_enï¼‰ ----
//Êı¾İÓĞĞ§Ê¹ÄÜ
always @(posedge I_clk or negedge I_rst_n) begin
    if(!I_rst_n)
        S_data_en <= 1'b0;
    else    
        if(S_head_en_1d && S_hs_data_1d[15:8] == FRAME_DATA_DT)
            S_data_en <= 1'b1;
        else if(S_data_en_cnt == S_data_length-1)  // è®¡æ»¡é•¿åº¦å³å…³é—­æ•°æ®çª—å£
            S_data_en <= 1'b0;
        else    
            S_data_en <= S_data_en;
end

//---- æ•°æ®é•¿åº¦è®¡æ•°å™¨ ----
//Êı¾İ³¤¶È¼ÆÊıÆ÷
always @(posedge I_clk) begin
    if(S_data_en)
        S_data_en_cnt <= S_data_en_cnt + 'd1;  // æ•°æ®çª—å£å†…é€æ‹ç´¯åŠ 
    else
        S_data_en_cnt <= 'd0;
end

//---- 16bitâ†’32bit æ‹¼æ¥ä¸è¾“å‡ºæœ‰æ•ˆä¿¡å· ----
//ÓĞĞ§Êı¾İÍ¬²½Êä³ö,°Ñ2LANEµÄ16bitÊı¾İ×ªÎª32bitÊı¾İ
reg  csi_valid_r;//synthesis keep

always @(posedge I_clk) begin
    csi_valid_r   <= S_data_en ? ~csi_valid_r : 0;   // çª—å£å†…æ¯æ‹ç¿»è½¬ â†’ 2 æ‹ä¸€æ¬¡çš„ 32bit æœ‰æ•ˆæŒ‡ç¤º
    O_csi_valid   <= csi_valid_r;
    O_csi_hs      <= I_hs_valid;   // HS çŠ¶æ€é€ä¼ 
end

always @(posedge I_clk) begin
    O_csi_data    <= S_data_en ? {O_csi_data[15:0],I_hs_data} : 0;  // æ–°æ•°æ®è¿›ä½ä½ï¼Œ2 æ‹å‡‘æ»¡ 32bit
end

    
endmodule