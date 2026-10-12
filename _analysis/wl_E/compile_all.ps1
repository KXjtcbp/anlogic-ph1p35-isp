$ErrorActionPreference = 'Continue'
$vlog = "E:\modelsim\modelsim_ase\win32aloem\vlog.exe"
Set-Location E:\FPGA\_analysis\wl_E

$files = @(
 'osd_char_lib.v',
 'isp\data96_128\data96_128.v',
 'isp\data128_96\data128_96.v',
 'data_96bit_to_128bit.v',
 'raw10_unpacket.v',
 'csi_unpacket.v',
 'raw8_to_rgb888.v',
 'auto_white_balance.v',
 'image_correction.v',
 'awb.v',
 'signal_delay.v',
 'uics500_cfg\uii2c.v',
 'uics500_cfg\uics500reg.v',
 'uics500_cfg\uicfgcs500.v'
)
$base = 'E:\FPGA\proj\baseline\lab3\user_source\hdl_source'
$outdir = 'E:\FPGA\_analysis\wl_E\vlog_out'
New-Item -ItemType Directory -Force $outdir | Out-Null

foreach ($f in $files) {
  $full = Join-Path $base $f
  $log  = Join-Path $outdir (($f -replace '[\\/]','__') + '.log')
  $o = & $vlog -quiet -sv -work work $full 2>&1
  $code = $LASTEXITCODE
  $o | Out-File -Encoding utf8 $log
  $errs = @($o | Where-Object { $_ -match '^\*\* Error' })
  $warns = @($o | Where-Object { $_ -match '^\*\* Warning' })
  Write-Output ("=== $f  exit=$code  errors=$($errs.Count) warnings=$($warns.Count)")
  $errs | Select-Object -First 6 | ForEach-Object { Write-Output ("    " + $_) }
}
