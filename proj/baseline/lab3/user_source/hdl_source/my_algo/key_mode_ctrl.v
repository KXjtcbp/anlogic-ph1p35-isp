//-----------------------------------------------------------------------------
//  修改记录 :
//    2026-09-27  [6440c52] 新建本模块（按键切换算法模式）
//    2026-10-03  [364d1bf] 模式值改为单 bit 翻转跨域协议，修掉残留 0.085ns 时序违例
//    2026-10-06  （未提交）模式数由 4 改为 5，增加第二根翻转线 O_mode_wrap，
//                循环改为 0→1→2→3→4→0；复位默认模式 = MODE 2（伪彩热力图）
//    2026-10-09  （未提交）标识符改名，无逻辑改动
//    2026-10-10  （未提交）★按键语义改成 K1-K4 直选 MODE0-MODE3★
//                - 端口 I_key_n 由 1 bit 扩成 4 bit（bit0=K1/D5, bit1=K2/A9,
//                  bit2=K3/B9, bit3=K4/C7），四个键各自消抖；
//                - K1/K2/K3/K4 → MODE 0/1/2/3，不再循环切换；
//                - 复位默认模式由 MODE 2 改为 MODE 0（原图直通）；
//                - ★跨域协议一个字没改★：仍只走 O_mode_tgl / O_mode_wrap 两根
//                  单 bit 翻转线。本模块按「从当前模式前进几步能到目标模式」
//                  发出对应个数的步进脉冲（0~4 个），接收端照旧"数脉冲"即可，
//                  所以 hdmi_mixer.v 的接收逻辑完全不用动（只改了它的复位值）。
//                - 脉冲间隔 16 拍 @24MHz ≈ 667ns，而接收端 3 级同步只需要
//                  <42ns 就能看到稳定电平，余量 16 倍，绝不会漏计数。
//                - 代价：MODE 4（卡通化）不再有按键入口。
//    2026-10-10  （未提交）★按 m02742 要求恢复卡通化一键入口（评分细则硬要求）★
//                - K4 短按由 MODE 3 改为 ★MODE 4（卡通化）★，一键直达；
//                - 长按任意键 >=1s -> MODE 3（5 段彩条诊断模式，原诊断能力保留）；
//                - 依据：选题指南 2.6 评分标准「（一）基础扩展项（1）视频图像
//                  风格化处理或视觉增强」，在《赛题解析二》里点名为「边缘提取与
//                  区域填充（卡通化处理）」；my_algo.v 的 MODE 4（f_cart 区域
//                  填充 + edg 描边）正是该实现，属于计分功能，不能只藏在长按里。
//                  同时满足 2.5 加分项（1）多算法切换与状态显示。
//                - 同步修掉 hdmi_mixer.v 的 MODE 4 OSD 显示 bug（字形库补 '4'）。
//-----------------------------------------------------------------------------
//===========================================================================
//  key_mode_ctrl.v  --  按键算法模式切换控制器（K1-K4 直选版）
//
//  项目：2026 全国大学生嵌入式芯片与系统设计竞赛 选题二
//
//  作用：把开发板上的 4 个按键变成「算法模式直选键」，5 个模式全部可达：
//            K1 → MODE 0(原图直通)     K2 → MODE 1(灰度)
//            K3 → MODE 2(伪彩热力图)   K4 → MODE 4(★卡通化★)
//            长按任意键 >=1s           → MODE 3(5 段彩条诊断模式)
//        上电默认 MODE 0。
//        ★为什么 MODE 4 必须放在短按上：卡通化是评分细则「基础扩展项（1）
//          视频图像风格化处理」点名的功能（见《赛题解析二》），属于计分项，
//          一键直达比藏在长按里更稳妥；而 MODE 3 彩条在本工程里是诊断工具
//          （my_algo.v 的注释写着「诊断用看得见的直方图」），放长按合适。★
//        ★hdmi_mixer.v 的字形库原来没有数字 '4' 的字形，MODE 4 会被显示成
//          「MODE 0」（与真正的 MODE 0 无法区分，直接违反评分项「状态显示」），
//          本次已补字形并改成统一索引。★
//
//  ---------------------------------------------------------------------
//  按键硬件事实（来自 user_source/constraints_source/pin.adc 与开发板手册
//  《HX1P35B 开发板引脚分配汇总》"十三、4 组按键"）
//  ---------------------------------------------------------------------
//    KEY1 = D5  → I_button[0]      KEY2 = A9 → I_button[1]
//    KEY3 = B9  → I_button[2]      KEY4 = C7 → I_button[3]
//    均带内部上拉、按下为低电平（active-low）。
//    （改版前 I_button[0] 被约束到 N2，那是 GPIOA_19 扩展口第 22 脚，
//      不是按键，所以当时实际只有 KEY1 可用。）
//
//  ---------------------------------------------------------------------
//  为什么单独例化 4 份消抖而不是复用现成的
//  ---------------------------------------------------------------------
//   工程里 key_remove_shakes 只被 hdmi_tx.v 内部使用（它的 I_key_in 在
//   design_top_wrapper.v 被接成 1'b0，等于没用）。本模块自己例化 4 份，
//   互不干扰，不会改变 hdmi_tx 的任何既有行为。单份约 14 LUT / 24 FF。
//
//  ---------------------------------------------------------------------
//  时钟域
//  ---------------------------------------------------------------------
//   必须用 24 MHz（S_24m_clk）等慢时钟：key_remove_shakes 内部固定计数到
//   100000，在 24 MHz 下约 4.2ms（正常消抖），在 100MHz 下只有 1ms（偏短）。
//
//  资源消耗估计：4 份消抖 + 一个步进发生器 ≈ 60 LUT / 120 FF（可忽略）
//===========================================================================

//  ---------------------------------------------------------------------
//  跨时钟域协议（重要，别改回 2 bit 直连）
//  ---------------------------------------------------------------------
//   本模块跑在 24 MHz 慢时钟域；算法模式要送给 hdmi_mixer（74.25MHz 像素域）
//   和 my_algo（csi_rx_clk 域）。**只把 2 bit 模式值直接送过去会被时序工具
//   当成跨域组合路径**，实测代价：
//     - 直连进 hdmi_mixer 组合云：Setup WNS 由 +0.103ns 掉到 -4.416ns（29 个违例端点）
//     - 只加同步器送电平：      仍有 -0.085ns / 2 个违例端点
//   因此改为标准做法：**只跨 1 bit 的"翻转"信号**。
//   两个接收域各自维护 3 bit 计数器：
//     收到 tgl  边沿 → mode = (mode == 4) ? 0 : mode + 1
//     收到 wrap 边沿 → mode = 0
//   本模块发出步进脉冲时必须与自己的 O_mode 严格同步地翻转 tgl；
//   只有当这一步恰好是 4→0 时，才同时翻转 wrap（并把 O_mode 置 0）。
//   注意：O_mode / O_mode_chg 只供同域使用；算法模式值由各目标域各自计数得到
//         （my_algo 走的是 3 bit 直连 + 2 级同步，见 my_algo.v 的 I_mode）。
//===========================================================================

module key_mode_ctrl (
    input  wire       I_clk     ,   // 24 MHz 慢时钟
    input  wire       I_rst_n   ,
    input  wire [3:0] I_key_n   ,   // K1..K4 按键输入，active-low；bit0=K1/D5 … bit3=K4/C7
    output reg  [2:0] O_mode    ,   // 本域当前算法模式 0..4（同域使用）
    output reg        O_mode_chg,   // 模式每前进一步给出 1 个时钟周期的高脉冲（同域使用）
    output reg        O_mode_tgl,   // ★跨域用★：每前进一步翻转 1 次（单 bit）
    output reg        O_mode_wrap   // ★跨域用★：模式由 4 回到 0 时翻转 1 次（单 bit）
);

    //------------------------------------------------------------------
    // 4 份独立消抖：每次有效按下产生 1 个时钟周期的高脉冲
    //------------------------------------------------------------------
    wire [3:0] S_key_trig;

    key_remove_shakes u_key_remove_shakes_mode0 (
        .I_clk          ( I_clk        ),
        .I_rst_n        ( I_rst_n      ),
        .I_key_in       ( I_key_n[0]   ),
        .O_key_trig_out ( S_key_trig[0])
    );

    key_remove_shakes u_key_remove_shakes_mode1 (
        .I_clk          ( I_clk        ),
        .I_rst_n        ( I_rst_n      ),
        .I_key_in       ( I_key_n[1]   ),
        .O_key_trig_out ( S_key_trig[1])
    );

    key_remove_shakes u_key_remove_shakes_mode2 (
        .I_clk          ( I_clk        ),
        .I_rst_n        ( I_rst_n      ),
        .I_key_in       ( I_key_n[2]   ),
        .O_key_trig_out ( S_key_trig[2])
    );

    key_remove_shakes u_key_remove_shakes_mode3 (
        .I_clk          ( I_clk        ),
        .I_rst_n        ( I_rst_n      ),
        .I_key_in       ( I_key_n[3]   ),
        .O_key_trig_out ( S_key_trig[3])
    );

    //------------------------------------------------------------------
    // ★长按检测：任一按键按住 >= T_HOLD 拍 → 置一次长按请求★
    //   按键 active-low（松开=1，按下=0），先做 2 级同步再判断电平。
    //   注：key_remove_shakes 已经把「按下」变成「按住 4.17ms 后仍按住」的单拍
    //       脉冲（见该文件 :76-79 与 :110-111），所以短按动作在按下后约 4ms
    //       就发生；长按只是在这个基础上再叠一次请求，两者互不干扰。
    //   S_long_req 只在本 always 块里写，主 FSM 只读；主 FSM 用自己拥有的
    //   S_long_done 记住「已经消费过」，避免同一个按住期间反复触发。
    //------------------------------------------------------------------
    localparam [24:0] T_HOLD = 25'd24_000_000;   // 1 s @ 24 MHz（本模块挂在 S_24m_clk）

    reg  [3:0]  S_key_sync1;
    reg  [3:0]  S_key_sync2;
    reg  [24:0] S_hold_cnt;
    reg         S_long_req;

    wire S_all_released = &S_key_sync2;     // 4 个键全部松开（active-low ⇒ 全 1）

    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            S_key_sync1 <= 4'hF;
            S_key_sync2 <= 4'hF;
            S_hold_cnt  <= 25'd0;
            S_long_req  <= 1'b0;
        end
        else begin
            S_key_sync1 <= I_key_n;
            S_key_sync2 <= S_key_sync1;

            if(S_all_released) begin
                S_hold_cnt <= 25'd0;        // 全部松开：计时清零，请求作废
                S_long_req <= 1'b0;
            end
            else if(S_hold_cnt < T_HOLD) begin
                S_hold_cnt <= S_hold_cnt + 25'd1;
            end
            else begin
                S_long_req <= 1'b1;         // ★按住满 1s：置一次长按请求★
            end
        end
    end

    //------------------------------------------------------------------
    // 步进发生器
    //   IDLE : 等按键（同一拍多键同时按下时，键号小的优先）
    //   CALC : 算出「还要前进几步」
    //   STEP : 每隔 GAP_MAX+1 拍发一个步进脉冲，直到 S_steps 归零
    //------------------------------------------------------------------
    localparam [1:0] IDLE = 2'd0;
    localparam [1:0] CALC = 2'd1;
    localparam [1:0] STEP = 2'd2;

    localparam [4:0] GAP_MAX = 5'd15;   // 步进脉冲间隔 = 16 拍 @24MHz ≈ 667ns

    reg [1:0] S_state;
    reg [2:0] S_target;                 // 目标模式 0..4（4 = 卡通化）
    reg [4:0] S_gap;                    // 步进间隔计数器
    reg [2:0] S_steps;                  // 剩余步进次数
    reg       S_long_done;              // 本次按住的长按请求是否已被消费

    // 前进步数 = (目标 - 当前) mod 5。用「先加 5 再按需减 5」实现，
    // 避免 Verilog 取模运算；输入范围 S_target∈0..4、O_mode∈0..4，
    // 故 S_diff_w ∈ 0..9（4 bit 足够），减 5 后 ∈ 0..4，不减则 ∈ 1..4。
    // 例：目标 4、当前 0 -> 4+5-0=9 -> 9-5=4 步（0→1→2→3→4）正确。
    wire [3:0] S_diff_w = {1'b0, S_target} + 4'd5 - {1'b0, O_mode};

    always @(posedge I_clk or negedge I_rst_n) begin
        if(!I_rst_n) begin
            O_mode      <= 3'd0;        // ★上电默认 MODE 0（原图直通）★
            O_mode_chg  <= 1'b0;
            O_mode_tgl  <= 1'b0;
            O_mode_wrap <= 1'b0;
            S_state     <= IDLE;
            S_target    <= 3'd0;
            S_gap       <= 5'd0;
            S_steps     <= 3'd0;
            S_long_done <= 1'b0;
        end
        else begin
            O_mode_chg <= 1'b0;         // 默认拉低，只在步进那一拍抬高

            // 全部松手：清掉「本次长按已消费」标志，下一次按住才能再触发一次
            if(S_all_released)
                S_long_done <= 1'b0;

            case(S_state)
                IDLE: begin
                    if(S_key_trig != 4'd0) begin
                        // 多键同时按下：键号小的优先，保证行为确定
                        if(S_key_trig[0])      S_target <= 3'd0;   // K1 -> MODE 0 原图直通
                        else if(S_key_trig[1]) S_target <= 3'd1;   // K2 -> MODE 1 灰度
                        else if(S_key_trig[2]) S_target <= 3'd2;   // K3 -> MODE 2 伪彩热力图
                        else                   S_target <= 3'd4;   // ★K4 -> MODE 4 卡通化★（评分细则点名的计分功能，一键直达）
                        S_state <= CALC;
                    end
                    else if(S_long_req && !S_long_done) begin
                        // ★长按任意键 >=1s -> MODE 3（5 段彩条诊断模式，原诊断能力保留）★
                        S_long_done <= 1'b1;
                        S_target    <= 3'd3;
                        S_state     <= CALC;
                    end
                end

                CALC: begin
                    // 算出步数后就进入发脉冲状态（步数 0 表示已经在该模式，直接回 IDLE）
                    S_steps <= (S_diff_w >= 4'd5) ? (S_diff_w - 4'd5) : S_diff_w[2:0];
                    S_gap   <= 5'd0;
                    S_state <= STEP;
                end

                STEP: begin
                    if(S_steps == 3'd0)
                        S_state <= IDLE;
                    else if(S_gap != GAP_MAX)
                        S_gap <= S_gap + 5'd1;
                    else begin
                        S_gap <= 5'd0;
                        // ---- 发出一步：翻转 tgl；若这一步是 4→0，同时翻转 wrap ----
                        O_mode_tgl <= ~O_mode_tgl;
                        O_mode_chg <= 1'b1;
                        if(O_mode == 3'd4) begin
                            O_mode      <= 3'd0;
                            O_mode_wrap <= ~O_mode_wrap;   // ★只在回卷那一次翻第二根线★
                        end
                        else begin
                            O_mode <= O_mode + 3'd1;
                        end
                        S_steps <= S_steps - 3'd1;
                    end
                end

                default: S_state <= IDLE;
            endcase
        end
    end

endmodule
