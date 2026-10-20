$ErrorActionPreference = 'Continue'
$VLIB = "E:\modelsim\modelsim_ase\win32aloem\vlib.exe"
$VLOG = "E:\modelsim\modelsim_ase\win32aloem\vlog.exe"
$W    = $args[0]      # work dir
$MODE = $args[1]      # 'orig' | 'new'
$BASE = if ($MODE -eq 'orig') { "E:\FPGA\_analysis\orig_copy\hdl_source" } else { "E:\FPGA\proj\baseline\lab3\user_source\hdl_source" }

Remove-Item -Recurse -Force $W -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $W | Out-Null
Push-Location $W
& $VLIB work | Out-Null
$files = @(
  "$BASE\video_in.v",
  "$BASE\video_out.v",
  "$BASE\vtc\uivtc.v",
  "$BASE\hdmi_tx.v",
  "$BASE\hdmi_phy_wrapper.v",
  "$BASE\pll_hdmi.v",
  "$BASE\lane_lvds_10_1.v",
  "$BASE\mipi_rx_error_detect.v",
  "$BASE\key_remove_shakes.v",
  "$BASE\video_cuttting.v",
  "$BASE\ps_wrapper.v",
  "$BASE\mc_to_user_interface.v",
  "$BASE\I2S_receiver.v",
  "$BASE\audio_arc_calculate.v",
  "E:\FPGA\_analysis\stubs_D.v"
)
$out = & $VLOG -quiet -sv -work work @files 2>&1
$code = $LASTEXITCODE
Pop-Location
$out | Out-String
"===== MODE=$MODE  VLOG EXIT CODE = $code ====="
exit $code
