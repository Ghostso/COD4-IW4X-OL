param([string]$Exe)
$ErrorActionPreference = 'Stop'
$dir = [IO.Path]::GetDirectoryName($Exe)
$p = Start-Process -FilePath $Exe -WorkingDirectory $dir -PassThru
$rows = @()
try {
  foreach ($delay in @(200,800,2000,5000)) {
    Start-Sleep -Milliseconds $delay
    try { $p.Refresh() } catch {}
    if ($p.HasExited) {
      $rows += [pscustomobject]@{ delay_ms=$delay; pid=$p.Id; state='exited'; exitcode=$p.ExitCode; modules=@() }
      break
    }
    $mods = @()
    try {
      foreach ($m in $p.Modules) { $mods += [pscustomobject]@{ name=$m.ModuleName; path=$m.FileName; base=('0x{0:X8}' -f $m.BaseAddress.ToInt64()); size=$m.ModuleMemorySize } }
      $rows += [pscustomobject]@{ delay_ms=$delay; pid=$p.Id; state='alive'; exitcode=$null; modules=$mods }
    } catch {
      $rows += [pscustomobject]@{ delay_ms=$delay; pid=$p.Id; state='module_enum_error'; error=$_.Exception.ToString(); modules=@() }
    }
  }
} finally {
  try { if (-not $p.HasExited) { $p.CloseMainWindow() | Out-Null; Start-Sleep -Milliseconds 200; if (-not $p.HasExited) { Stop-Process -Id $p.Id -Force } } } catch {}
}
$rows | ConvertTo-Json -Depth 6
