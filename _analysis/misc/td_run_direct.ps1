# Run the TD flow engine directly inside each run directory (what TD's own
# <run>.bat does, minus the trailing `pause`).
#
# Usage:  pwsh -ExecutionPolicy Bypass -File td_run_direct.ps1 [syn_1] [phy_1] ...
#
# NOTE 1 -- this file is deliberately ASCII-ONLY.
#   A previous revision carried Chinese comments; PowerShell then mis-decoded the
#   file (mojibake), a '?' swallowed a quote and the whole script failed with
#   "The string is missing the terminator". Keep this file ASCII.
#
# NOTE 2 -- the Tcl path MUST use forward slashes.
#   $flow is handed to the Tcl interpreter, where a backslash is an escape:
#   E:\TD\doc\scripts\DefaultFlow.tcl  ->  E:TDdocscriptsDefaultFlow.tcl
#
# NOTE 3 -- td_commands_prompt.exe returns exit code 0 EVEN WHEN the Tcl script
#   never ran. The 2026-10-11 14:53 attempt "succeeded" (exit 0) while the log
#   held only:  couldn't read file "E:TDdocscriptsDefaultFlow.tcl": no such file
#   and the .bit timestamp was still the previous 13:38 build.
#   So success is decided here by ARTIFACT MTIMES, not by the exit code.
#
$ErrorActionPreference = 'Continue'

$eng  = 'E:/TD/bin/td_commands_prompt.exe'
$flow = 'E:/TD/doc/scripts/DefaultFlow.tcl'
$base = 'E:/FPGA/proj/baseline/lab3/td_project/camera_to_dsi_display_Runs'
$runs = if ($args.Count -gt 0) { $args } else { @('syn_1', 'phy_1') }

$artifacts = @{
    'syn_1' = @('camera_to_dsi_display_gate.area', 'camera_to_dsi_display_rtl.area')
    'phy_1' = @('camera_to_dsi_display.bit', 'place.qor', 'route.qor')
}

$failed = @()

# NOTE 4 -- TD's command-line flow reads <run>/camera_to_dsi_display.prj, NOT
#   td_project/*.al. Adding a .v file ONLY to the .al makes it a BLACK BOX:
#   the log shows  HDL-8007 ERROR: <mod> is a black box in <file>(<line>)
#   and the flow still finishes, writing a .bit whose QoR is bit-identical to
#   the previous run. 2026-10-12: ae_stat.v / ae_ctrl.v hit exactly this.
#   So sync the .al file list into every run's .prj BEFORE launching.
$syncPy = 'E:/FPGA/_analysis/scripts/sync_al_to_prj.py'
if (Test-Path $syncPy) {
    Write-Host '--- syncing .al file list into run .prj ---'
    & python $syncPy 2>&1 | ForEach-Object { Write-Host ("    " + $_) }
} else {
    Write-Host ("--- WARNING: {0} not found, .prj not synced ---" -f $syncPy) -ForegroundColor Yellow
}

foreach ($r in $runs) {
    $dir = Join-Path $base $r
    $log = "E:/FPGA/_analysis/td_direct_$r.log"
    $t0  = Get-Date
    Write-Host ("=== RUN {0} start {1} ===" -f $r, $t0.ToString('HH:mm:ss'))

    Push-Location $dir
    try {
        & $eng $flow 2>&1 | Tee-Object -FilePath $log
        $code = $LASTEXITCODE
    } finally {
        Pop-Location
    }

    # Real pass/fail: every expected artifact must be newer than this run's start.
    $ts = $t0.AddSeconds(-2)
    $stale = @()
    foreach ($a in $artifacts[$r]) {
        $p = Join-Path $dir $a
        if (-not (Test-Path $p)) {
            $stale += ($a + " MISSING")
        } elseif ((Get-Item $p).LastWriteTime -lt $ts) {
            $stale += ($a + " STALE(" + (Get-Item $p).LastWriteTime.ToString('HH:mm:ss') + ")")
        }
    }

    $badline = Select-String -Path $log -Pattern "couldn't read file|no such file|invalid command name|HDL-8|HDL-3" -ErrorAction SilentlyContinue

    if (($stale.Count -gt 0) -or $badline) {
        $failed += $r
        Write-Host ("=== RUN {0} exit={1} {2}  *** DID NOT ACTUALLY RUN ***" -f $r, $code, (Get-Date).ToString('HH:mm:ss')) -ForegroundColor Red
        foreach ($s in $stale)   { Write-Host ("    STALE: " + $s) }
        foreach ($b in $badline) { Write-Host ("    LOG  : " + $b.Line.Trim()) }
    } else {
        Write-Host ("=== RUN {0} exit={1} {2}  OK (artifacts refreshed) ===" -f $r, $code, (Get-Date).ToString('HH:mm:ss')) -ForegroundColor Green
        foreach ($a in $artifacts[$r]) {
            $it = Get-Item (Join-Path $dir $a)
            Write-Host ("    {0,-40} {1,12} {2}" -f $a, $it.Length, $it.LastWriteTime.ToString('HH:mm:ss'))
        }
    }
}

Write-Host '=== ALL RUNS DONE ==='
if ($failed.Count -gt 0) {
    Write-Host ("!!! FAILED: " + ($failed -join ', ')) -ForegroundColor Red
    exit 1
}
