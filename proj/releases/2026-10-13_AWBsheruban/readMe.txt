AWB 舍入版 —— 2026-10-13 21:29

=== 相对 2026-10-13_AWB帧锁存版 改了什么 ===
并入 B 的 feat/awb-robust，唯一净 RTL 改动是 awb.v 输出端四舍五入：
  原: assign R_new_x1 = (R_new_r1[27:24])?255:R_new_r1[23:16];      // 截断
  新: wire [8:0] R_rnd1 = {1'b0,R_new_r1[23:16]} + {8'd0,R_new_r1[15]};
      assign R_new_x1 = (R_new_r1[27:24] || R_rnd1[8])?255:R_rnd1[7:0];
R/B 各 4 路，共 8 个 9bit 加法器，不新增乘法器/除法器。
意义：截断是向下取整，只作用在 R/B 两路（G 不乘增益）=> 一个与亮度、与增益都
无关的"只压 R 和 B、不压 G"的加性偏置。B 的门级 TB 实测均匀场 B-G 由 -1.00 码
变 0.00 码。

=== 本版 RTL 组成 ===
A 的 AWB 帧锁存（in_r_hold/in_b_hold，整帧一个常数增益）
+ B 的输出端四舍五入
+ A 的 AE 两行遥测
+ A 的 AE 闭环（ae_stat.v + ae_ctrl.v）

=== QoR ===
Setup WNS +103ps / TNS 0 / 违例 0 ; Hold WNS +20ps / TNS 0 / 违例 0
Wire length 4986320 ; #slices 18202 (85.79%) ; #RAMs 60 ; #DSPs 8
black box 检查：0 条 HDL-8007

=== 文件 ===
camera_to_dsi_display.bit            1789539 B  md5 2d08fae1ab265754650edf0556331890
camera_to_dsi_display_compress.bit   1443057 B  md5 6c6d0e88cf0c9b4264cc22a568c5bcab

=== 回滚 ===
proj/releases/2026-10-13_AWB帧锁存版/  md5 f933199d6defb46a4e7c9cc6a13c00d8
