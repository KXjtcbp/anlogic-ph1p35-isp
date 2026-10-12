import os
base = r'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
files = ['video_in.v','video_out.v','hdmi_tx.v','hdmi_phy_wrapper.v','pll_hdmi.v',
         'lane_lvds_10_1.v','mipi_rx_error_detect.v','key_remove_shakes.v',
         'video_cuttting.v','ps_wrapper.v','mc_to_user_interface.v','I2S_receiver.v',
         'audio_arc_calculate.v','vtc/uivtc.v']
tests = '视频数据时钟复位信号模块注释：，。（）帧像素亮度色度消抖计数器行场同步有效窗口串并转换时序产生器'
for f in files:
    p = os.path.join(base, f.replace('/', os.sep))
    b = open(p, 'rb').read()
    try:
        t = b.decode('utf-8'); enc = 'utf-8'
    except Exception:
        t = b.decode('gbk'); enc = 'gbk'
    fail = []
    for c in tests:
        try:
            c.encode(enc)
        except Exception:
            fail.append(c)
    print('%-28s enc=%-6s reenc_fail=%s ends_CRLF=%s' % (f, enc, ''.join(fail) if fail else 'none', b.endswith(b'\r\n')))
