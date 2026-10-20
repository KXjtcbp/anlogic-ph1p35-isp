安路选题二 —— 基于安路 PH1P35 的实时数字图像处理系统
代码与工程提交说明
================================================================

一、目录说明
  code\proj\baseline\lab3\user_source\   Verilog 源码（自研模块 + 改造过的官方模块）
  code\proj\baseline\lab3\td_project\    TangDynasty 工程定义（.al 工程文件 / .sdc 时序约束 / .prj 综合文件列表）
  code\proj\releases\2026-10-18_a2_hold60\  最终交付比特流 + 综合时序与面积报告
  analysis\                              分析、拟合、仿真与统计脚本（Python / Verilog Testbench / 生成的 LUT）
  docs\                                  团队协作文档
  tools\                                 图像与视频统计工具
  raw_exports\                           板上 ChipWatcher 抓取的原始数据
  根目录 *.docx                          比赛报告、演示视频脚本、心得体会模板、成员上手指南
  根目录 系统框图_FPGA数据通路.png        系统整体框图
  WORKSPACE_MAP.md                       模块台账 / 资源与指标 / 风险清单
  HISTORY.md                             开发过程中的问题与结论记录

二、自研 RTL 模块（全部在 code\proj\baseline\lab3\user_source\hdl_source\）
  isp\lsc.v              镜头色彩暗角校正（二维 20x12 增益表 + 双线性插值，自行实验定位问题并自拟合）
  isp\awb.v              自动白平衡（灰世界 + 128 次倒数查表替代除法器 + 帧锁存 + 输出舍入）
  isp\wb_recip.v         白平衡用的归一化倒数查表模块
  isp\ae_stat.v          帧亮度与高光/暗部统计（纯移位加法，零 DSP）
  isp\ae_ctrl.v          自动曝光闭环状态机（60MHz 域做统计，24MHz 域写传感器寄存器）
  isp\isp_gamma.v        色调曲线 LUT（真 S 曲线 + 黑位软复位，12 路并行 ROM）
  isp\obj_detect.v       硬件颜色目标检测（16x9 分块 + 两帧确认 + 孤立块滤除 + 帧级跟踪保持）
  isp\motion_detect.v    硬件运动目标检测（块级帧差，只占 144 字节块均值存储，无帧缓存）
  my_algo\my_algo.v      五模式风格化算法层（直通 / 灰度 / 伪彩 / 彩条 / 卡通化）
  my_algo\key_mode_ctrl.v 按键去抖与模式切换（含跨时钟域步进发生器）

三、改造过的官方模块（同样在 user_source\hdl_source\，改动处均带 [HDR-日期] 注释）
  design_top_wrapper.v   顶层：拨码同步、AE 与运动检测接线、参数行 OSD 数据汇聚
  isp\isp_top.v          ISP 链路拼接与旁路观察者取数
  hdmi_mixer.v           7 层 OSD 叠加（Logo / 帧计数 / MODE / 两行遥测 / 参数行 / 运动框 / 目标框）
  isp\demosaic_4x_2_0\mipi_to_raw_converter.v   黑电平扣除（BLACK_LEVEL=56，由盖镜头实测标定）
  uics500_cfg\uicfgcs500_720p.v                 传感器配置：曝光与模拟增益改由 AE 模块驱动

四、构建方式
  1) TangDynasty V6.2.168116，打开 code\proj\baseline\lab3\td_project\camera_to_dsi_display.al
  2) 综合 + 布局布线 + 生成比特流，烧录到 PH1P35MDG324（HX1P35A 开发板）
  3) 烧录后拔电 5 秒重新上电（不要按复位键），让摄像头初始化表重新下发

五、各项功能的现场验证方式（四位数拨码 + K1~K4 按键）
  SW1 拨上 = 启用镜头暗角校正，拨下 = 旁路
  SW2 拨上 = 启用 S 曲线，拨下 = 旁路
  SW3 拨上 = 启用颜色目标检测，拨下 = 关闭
  SW4 拨上 = 检测灵敏度严格档，拨下 = 宽松档
  K1 = 直通，K2 = 灰度，K3 = 伪彩，K4 = 卡通化，长按任一键 ≥1 秒 = 五段彩条
  画面左上两行橙色文字为实时遥测：第 1 行 AE 增益档位 / 状态 / 帧亮度 / 白平衡增益，第 2 行 AE 决策中间变量

六、注意事项
  - 所有 .bit 文件大小都恰好是 1 789 539 字节，大小对不能证明版本对，请核对 md5。
    交付版 md5 = DB39A5CE50591330A6D6E9C0CFCFB2E3
  - 工程中用到的官方 IP（MIPI D-PHY、DDR2 控制器、HDMI 1.4b 发送器、PLL、块 RAM 生成器）
    为安路官方提供，未包含在本压缩包的源码中，需从官方例程 lab_ex_3_osd_SC500_720P 中获取。
  - analysis\ 目录下的脚本路径中有硬编码的 E:\FPGA 前缀，迁移到其它路径运行前需自行替换。
