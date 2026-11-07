[CmdletBinding()]
param(
  [string]$Repo = 'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-Combat-Server-v0.1',
  [string]$OutputRoot = 'D:\BaiduNetdiskDownload\使命召唤OL\CODOL-BATTLE-SERVER-INTEGRATION-FREEZE-005',
  [int]$QuiescenceSeconds = 30,
  [int]$Attempt = 1
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$src = Join-Path $Repo 'src'
$exe = Join-Path $Repo 'build\bin\CODOLCombatServer.exe'
$buildScript = Join-Path $Repo 'build\build.ps1'
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$attemptDir = Join-Path $OutputRoot (('attempt_{0:D2}_{1}' -f $Attempt, $stamp))
$evidence = Join-Path $attemptDir 'evidence'
$artifacts = Join-Path $attemptDir 'artifacts'
New-Item -ItemType Directory -Force -Path $evidence, $artifacts | Out-Null
$utf8 = New-Object System.Text.UTF8Encoding($false)
$result = [ordered]@{
  attempt = $Attempt
  started_at = (Get-Date).ToString('o')
  repo = $Repo
  output_root = $OutputRoot
  attempt_dir = $attemptDir
  status = 'RUNNING'
  errors = @()
}

function Write-Utf8([string]$Path, [string]$Text) {
  [System.IO.File]::WriteAllText($Path, $Text, $utf8)
}
function Write-Json([string]$Path, $Object) {
  Write-Utf8 $Path (($Object | ConvertTo-Json -Depth 12) + "`n")
}
function Write-ExitCode([string]$Path, [int]$Code) {
  Write-Utf8 $Path ("$Code`n")
}
function Invoke-Captured([string]$FilePath, [string[]]$Arguments, [string]$OutFile, [string]$ErrFile, [string]$CodeFile) {
  $p = Start-Process -FilePath $FilePath -ArgumentList $Arguments -WorkingDirectory $Repo -RedirectStandardOutput $OutFile -RedirectStandardError $ErrFile -WindowStyle Hidden -PassThru
  $p.WaitForExit()
  Write-ExitCode $CodeFile $p.ExitCode
  return $p.ExitCode
}
function Get-SourceRows {
  $rows = New-Object System.Collections.Generic.List[object]
  foreach ($f in (Get-ChildItem -LiteralPath $src -Recurse -File -Filter '*.cs' -ErrorAction Stop)) {
    $bytes = [System.IO.File]::ReadAllBytes($f.FullName)
    $sha = [System.Security.Cryptography.SHA256]::Create()
    try { $hash = (($sha.ComputeHash($bytes) | ForEach-Object { $_.ToString('x2') }) -join '') } finally { $sha.Dispose() }
    $rows.Add([pscustomobject]@{
      relative_path = $f.FullName.Substring($src.Length + 1).Replace('\','/')
      bytes = [int64]$f.Length
      last_write_utc = $f.LastWriteTimeUtc.ToString('o')
      sha256 = $hash
    }) | Out-Null
  }
  $map = @{}
  foreach ($r in $rows) { $map[$r.relative_path] = $r }
  $keys = [string[]]$map.Keys
  [Array]::Sort($keys, [System.StringComparer]::Ordinal)
  $ordered = New-Object System.Collections.Generic.List[object]
  foreach ($k in $keys) { $ordered.Add($map[$k]) | Out-Null }
  return ,$ordered.ToArray()
}
function Get-SourceFingerprint([object[]]$Rows) {
  $map = @{}
  foreach ($r in $Rows) { $map[$r.relative_path] = $r }
  $keys = [string[]]$map.Keys
  [Array]::Sort($keys, [System.StringComparer]::Ordinal)
  $sha = [System.Security.Cryptography.SHA256]::Create()
  try {
    foreach ($k in $keys) {
      $name = [System.Text.Encoding]::UTF8.GetBytes($k)
      $null = $sha.TransformBlock($name, 0, $name.Length, $null, 0)
      $nul = [byte[]](0)
      $null = $sha.TransformBlock($nul, 0, 1, $null, 0)
      $body = [System.IO.File]::ReadAllBytes((Join-Path $src $k.Replace('/','\')))
      $null = $sha.TransformBlock($body, 0, $body.Length, $null, 0)
    }
    $null = $sha.TransformFinalBlock([byte[]]@(), 0, 0)
    return (($sha.Hash | ForEach-Object { $_.ToString('x2') }) -join '')
  } finally { $sha.Dispose() }
}
function Export-Rows([object[]]$Rows, [string]$Path) {
  $Rows | Export-Csv -LiteralPath $Path -Delimiter "`t" -NoTypeInformation -Encoding utf8
}
function Get-FileSha256([string]$Path) {
  return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Get-Line([string]$Text, [string]$Pattern) {
  $m = [regex]::Match($Text, $Pattern, [System.Text.RegularExpressions.RegexOptions]::Multiline)
  if ($m.Success) { return $m.Value.Trim() }
  return $null
}
function Drain-Queue($Queue) {
  $items = New-Object System.Collections.Generic.List[string]
  $item = $null
  while ($Queue.TryDequeue([ref]$item)) { $items.Add([string]$item) | Out-Null; $item = $null }
  return ,$items.ToArray()
}

$lockStreams = New-Object System.Collections.Generic.List[System.IO.FileStream]
$watcher = $null
$global:Freeze005WatcherEvents = New-Object 'System.Collections.Concurrent.ConcurrentQueue[string]'
$changedHandler = $null
$createdHandler = $null
$deletedHandler = $null
$renamedHandler = $null
$status = 'INVALID'
$failure = $null

try {
  Write-Json (Join-Path $evidence 'environment.json') ([ordered]@{
    captured_at = (Get-Date).ToString('o')
    powershell = $PSVersionTable.PSVersion.ToString()
    os = [System.Environment]::OSVersion.VersionString
    repo = $Repo
    source_dir = $src
    compiler = 'C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe'
    working_directory_for_commands = $Repo
  })

  $watcher = New-Object System.IO.FileSystemWatcher
  $watcher.Path = $src
  $watcher.Filter = '*.cs'
  $watcher.IncludeSubdirectories = $true
  $watcher.NotifyFilter = [System.IO.NotifyFilters]'FileName, DirectoryName, LastWrite, Size, CreationTime'
  $changedHandler = [System.IO.FileSystemEventHandler]{ param($sender,$e) $global:Freeze005WatcherEvents.Enqueue("$((Get-Date).ToString('o'))`tCHANGED`t$($e.FullPath)") }
  $createdHandler = [System.IO.FileSystemEventHandler]{ param($sender,$e) $global:Freeze005WatcherEvents.Enqueue("$((Get-Date).ToString('o'))`tCREATED`t$($e.FullPath)") }
  $deletedHandler = [System.IO.FileSystemEventHandler]{ param($sender,$e) $global:Freeze005WatcherEvents.Enqueue("$((Get-Date).ToString('o'))`tDELETED`t$($e.FullPath)") }
  $renamedHandler = [System.IO.RenamedEventHandler]{ param($sender,$e) $global:Freeze005WatcherEvents.Enqueue("$((Get-Date).ToString('o'))`tRENAMED`t$($e.OldFullPath)`t$($e.FullPath)") }
  $watcher.add_Changed($changedHandler)
  $watcher.add_Created($createdHandler)
  $watcher.add_Deleted($deletedHandler)
  $watcher.add_Renamed($renamedHandler)
  $watcher.EnableRaisingEvents = $true

  $sourceFiles = Get-ChildItem -LiteralPath $src -Recurse -File -Filter '*.cs' -ErrorAction Stop
  foreach ($f in $sourceFiles) {
    $stream = [System.IO.File]::Open($f.FullName, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::Read)
    $lockStreams.Add($stream)
  }
  Write-Utf8 (Join-Path $evidence 'source_lock.txt') ("LOCKED_FILES=$($lockStreams.Count)`nLOCK_MODE=FileAccess.Read,FileShare.Read (denies external write/delete)`nLOCKED_AT=$((Get-Date).ToString('o'))`n")

  Start-Sleep -Seconds $QuiescenceSeconds
  $preEvents = Drain-Queue $global:Freeze005WatcherEvents
  if ($preEvents.Count -gt 0) {
    Write-Utf8 (Join-Path $evidence 'source_watcher_events_pre.tsv') ($preEvents -join "`n")
    throw "source watcher observed events during quiescence: $($preEvents.Count)"
  }

  $preRows = Get-SourceRows
  $preFp = Get-SourceFingerprint $preRows
  Export-Rows $preRows (Join-Path $evidence 'source_inventory_pre.tsv')
  Write-Json (Join-Path $evidence 'source_fingerprint_pre.json') ([ordered]@{
    algorithm = 'SHA256(per source file: UTF-8 relative_path + 0x00 + raw content; ordinal path sort)'
    scope = 'src/**/*.cs'
    included = @('*.cs under src recursively')
    ignored = @('build/**','logs/**','docs/**','config/**','tests/**','binaries','delivery directory')
    count = $preRows.Count
    source_sha256 = $preFp
  })

  $buildOut = Join-Path $evidence 'build.stdout.log'
  $buildErr = Join-Path $evidence 'build.stderr.log'
  $buildCodePath = Join-Path $evidence 'build.exitcode.txt'
  $pwshPath = (Get-Process -Id $PID).Path
  $buildCode = Invoke-Captured $pwshPath @('-NoProfile','-ExecutionPolicy','Bypass','-File',$buildScript) $buildOut $buildErr $buildCodePath
  $buildText = ((Get-Content -LiteralPath $buildOut -Raw -ErrorAction SilentlyContinue) + "`n" + (Get-Content -LiteralPath $buildErr -Raw -ErrorAction SilentlyContinue))
  if ($buildCode -ne 0 -or $buildText -notmatch 'BUILD OK') { throw "release build failed, exit=$buildCode" }
  Copy-Item -LiteralPath (Join-Path $Repo 'build\bin\BUILD_MANIFEST.txt') -Destination (Join-Path $evidence 'BUILD_MANIFEST.snapshot.txt') -Force
  Copy-Item -LiteralPath $exe -Destination (Join-Path $artifacts 'CODOLCombatServer.exe') -Force
  Copy-Item -LiteralPath (Join-Path $Repo 'build\bin\BUILD_MANIFEST.txt') -Destination (Join-Path $artifacts 'BUILD_MANIFEST.txt') -Force
  $exeHash = Get-FileSha256 $exe
  Write-Utf8 (Join-Path $evidence 'artifact.sha256') ("$exeHash *CODOLCombatServer.exe`n")

  $selftestOut = Join-Path $evidence 'selftest.stdout.log'
  $selftestErr = Join-Path $evidence 'selftest.stderr.log'
  $selftestCodePath = Join-Path $evidence 'selftest.exitcode.txt'
  $selftestCode = Invoke-Captured $exe @('--selftest') $selftestOut $selftestErr $selftestCodePath
  $selftestText = ((Get-Content -LiteralPath $selftestOut -Raw -ErrorAction SilentlyContinue) + "`n" + (Get-Content -LiteralPath $selftestErr -Raw -ErrorAction SilentlyContinue))
  $selftestSummary = Get-Line $selftestText '通过\s+\d+\s+项，失败\s+\d+\s+项。'
  if ($selftestCode -ne 0 -or $selftestText -notmatch '全绿。') { throw "selftest failed, exit=$selftestCode" }

  $fpOut = Join-Path $evidence 'fingerprint.stdout.log'
  $fpErr = Join-Path $evidence 'fingerprint.stderr.log'
  $fpCodePath = Join-Path $evidence 'fingerprint.exitcode.txt'
  $fpCode = Invoke-Captured $exe @('--fingerprint') $fpOut $fpErr $fpCodePath
  if ($fpCode -ne 0) { throw "fingerprint command failed, exit=$fpCode" }
  $fpText = Get-Content -LiteralPath $fpOut -Raw
  $fpExe = Get-Line $fpText 'SOURCE_SHA256=[0-9a-fA-F]{64}'
  $fpCountLine = Get-Line $fpText 'SOURCE_FILES=\d+'
  $fpExeHash = if ($fpExe) { $fpExe.Substring('SOURCE_SHA256='.Length) } else { $null }
  $fpExeCount = if ($fpCountLine) { [int]$fpCountLine.Substring('SOURCE_FILES='.Length) } else { -1 }
  $manifestText = Get-Content -LiteralPath (Join-Path $Repo 'build\bin\BUILD_MANIFEST.txt') -Raw
  $manifestHashLine = Get-Line $manifestText 'source_sha256:\s*[0-9a-fA-F]{64}'
  $manifestHash = if ($manifestHashLine) { ($manifestHashLine -split ':',2)[1].Trim() } else { $null }
  if ($fpExeHash -ne $preFp -or $manifestHash -ne $preFp -or $fpExeCount -ne $preRows.Count) {
    throw "source fingerprint mismatch pre=$preFp exe=$fpExeHash manifest=$manifestHash exe_count=$fpExeCount"
  }

  $runOut = Join-Path $evidence 'run_maxseconds.stdout.log'
  $runErr = Join-Path $evidence 'run_maxseconds.stderr.log'
  $runCodePath = Join-Path $evidence 'run_maxseconds.exitcode.txt'
  $runStart = Get-Date
  $runProc = Start-Process -FilePath $exe -ArgumentList @('--run','--max-seconds','3') -WorkingDirectory $Repo -RedirectStandardOutput $runOut -RedirectStandardError $runErr -WindowStyle Hidden -PassThru
  $bound = $null
  $deadline = (Get-Date).AddSeconds(10)
  while (-not $runProc.HasExited -and (Get-Date) -lt $deadline) {
    $bound = Get-NetUDPEndpoint -LocalPort 28960 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -eq $runProc.Id } | Select-Object -First 1
    if ($bound) { break }
    Start-Sleep -Milliseconds 50
  }
  if (-not $bound) {
    try { $runProc.Kill() } catch { }
    throw 'did not observe UDP 28960 bound by the run process'
  }
  $runProc.WaitForExit()
  $runCode = $runProc.ExitCode
  Write-ExitCode $runCodePath $runCode
  Start-Sleep -Milliseconds 300
  $afterBind = Get-NetUDPEndpoint -LocalPort 28960 -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -eq $runProc.Id }
  $runText = ((Get-Content -LiteralPath $runOut -Raw -ErrorAction SilentlyContinue) + "`n" + (Get-Content -LiteralPath $runErr -Raw -ErrorAction SilentlyContinue))
  $bindLine = Get-Line $runText '已监听 UDP\s+[^\r\n]+'
  $autoLine = Get-Line $runText '达到 max-seconds=[^\r\n]+'
  $cleanupLine = Get-Line $runText '停机清理自检通过:\s*sessions=0\s+entities=0'
  $runObservation = [ordered]@{
    command = "$exe --run --max-seconds 3"
    pid = $runProc.Id
    started_at = $runStart.ToString('o')
    exited_at = (Get-Date).ToString('o')
    exit_code = $runCode
    udp_bind_observed = ($null -ne $bound)
    observed_local_address = if ($bound) { $bound.LocalAddress.ToString() } else { $null }
    observed_local_port = if ($bound) { [int]$bound.LocalPort } else { $null }
    observed_owning_process = if ($bound) { [int]$bound.OwningProcess } else { $null }
    bind_log_line = $bindLine
    auto_stop_log_line = $autoLine
    cleanup_log_line = $cleanupLine
    endpoint_after_exit = @($afterBind).Count -eq 0
  }
  Write-Json (Join-Path $evidence 'run_observation.json') $runObservation
  if ($runCode -ne 0 -or $null -eq $bindLine -or $null -eq $autoLine -or $null -eq $cleanupLine -or @($afterBind).Count -ne 0) {
    throw "limited run validation failed exit=$runCode bind=$($null -ne $bindLine) auto=$($null -ne $autoLine) cleanup=$($null -ne $cleanupLine) endpoint_released=$(@($afterBind).Count -eq 0)"
  }

  $postRows = Get-SourceRows
  $postFp = Get-SourceFingerprint $postRows
  Export-Rows $postRows (Join-Path $evidence 'source_inventory_post.tsv')
  Write-Json (Join-Path $evidence 'source_fingerprint_post.json') ([ordered]@{
    algorithm = 'SHA256(per source file: UTF-8 relative_path + 0x00 + raw content; ordinal path sort)'
    scope = 'src/**/*.cs'
    count = $postRows.Count
    source_sha256 = $postFp
  })
  $watcherEvents = Drain-Queue $global:Freeze005WatcherEvents
  Write-Utf8 (Join-Path $evidence 'source_watcher.log') ("WINDOW_START=$($result.started_at)`nWINDOW_END=$((Get-Date).ToString('o'))`nEVENT_COUNT=$($watcherEvents.Count)`n" + (($watcherEvents -join "`n")) + "`n")

  $preMap = @{}; foreach ($r in $preRows) { $preMap[$r.relative_path] = $r }
  $postMap = @{}; foreach ($r in $postRows) { $postMap[$r.relative_path] = $r }
  $keyList = New-Object System.Collections.Generic.List[string]
  $seen = New-Object 'System.Collections.Generic.HashSet[string]' ([System.StringComparer]::Ordinal)
  foreach ($k in $preMap.Keys) { if ($seen.Add([string]$k)) { $keyList.Add([string]$k) | Out-Null } }
  foreach ($k in $postMap.Keys) { if ($seen.Add([string]$k)) { $keyList.Add([string]$k) | Out-Null } }
  $allKeys = $keyList.ToArray()
  [Array]::Sort($allKeys, [System.StringComparer]::Ordinal)
  [Array]::Sort($allKeys, [System.StringComparer]::Ordinal)
  $diffs = New-Object System.Collections.Generic.List[string]
  foreach ($k in $allKeys) {
    if (-not $preMap.ContainsKey($k)) { $diffs.Add("ADDED`t$k"); continue }
    if (-not $postMap.ContainsKey($k)) { $diffs.Add("REMOVED`t$k"); continue }
    $a = $preMap[$k]; $b = $postMap[$k]
    if ($a.sha256 -ne $b.sha256 -or $a.bytes -ne $b.bytes -or $a.last_write_utc -ne $b.last_write_utc) {
      $diffs.Add("CHANGED`t$k`t$a.sha256`t$b.sha256`t$a.last_write_utc`t$b.last_write_utc")
    }
  }
  Write-Utf8 (Join-Path $evidence 'inventory_comparison.txt') ("PRE_FINGERPRINT=$preFp`nPOST_FINGERPRINT=$postFp`nPRE_FILES=$($preRows.Count)`nPOST_FILES=$($postRows.Count)`nDIFF_COUNT=$($diffs.Count)`nWATCHER_EVENT_COUNT=$($watcherEvents.Count)`n" + (($diffs -join "`n")) + "`n")
  if ($preFp -ne $postFp -or $preRows.Count -ne $postRows.Count -or $diffs.Count -ne 0 -or $watcherEvents.Count -ne 0) {
    throw "source changed during validation pre=$preFp post=$postFp diffs=$($diffs.Count) watcher=$($watcherEvents.Count)"
  }

  $buildManifest = Get-Content -LiteralPath (Join-Path $Repo 'build\bin\BUILD_MANIFEST.txt') -Raw
  $buildConfig = Get-Line $buildManifest 'configuration:\s*release'
  if (-not $buildConfig) { throw 'build manifest does not record release configuration' }
  $manifestSizeLine = Get-Line $buildManifest 'size:\s*\d+'
  $manifestSize = if ($manifestSizeLine) { [int64](($manifestSizeLine -split ':',2)[1].Trim()) } else { -1 }
  $manifestBinaryHash = Get-Line $buildManifest 'sha256:\s*[0-9a-fA-F]{64}'
  $manifestBinaryHash = if ($manifestBinaryHash) { ($manifestBinaryHash -split ':',2)[1].Trim().ToLowerInvariant() } else { $null }
  if ($manifestBinaryHash -ne $exeHash -or $manifestSize -ne (Get-Item $exe).Length) { throw 'build manifest binary hash/size mismatch' }

  $fingerprintEvidence = [ordered]@{
    pre_source_sha256 = $preFp
    post_source_sha256 = $postFp
    exe_reported_source_sha256 = $fpExeHash
    build_manifest_source_sha256 = $manifestHash
    source_file_count = $preRows.Count
    exe_reported_source_files = $fpExeCount
    all_equal = ($preFp -eq $postFp -and $preFp -eq $fpExeHash -and $preFp -eq $manifestHash)
    artifact_sha256 = $exeHash
    artifact_bytes = (Get-Item $exe).Length
    build_configuration = 'release'
  }
  Write-Json (Join-Path $evidence 'fingerprint_evidence.json') $fingerprintEvidence

  $descriptorDir = Join-Path $Repo 'build\bin\session_descriptor'
  if (Test-Path -LiteralPath $descriptorDir) {
    New-Item -ItemType Directory -Force -Path (Join-Path $artifacts 'session_descriptor') | Out-Null
    Copy-Item -Path (Join-Path $descriptorDir '*') -Destination (Join-Path $artifacts 'session_descriptor') -Recurse -Force
  }
  $internalLog = Join-Path $Repo 'logs\combat_server.log'
  if (Test-Path -LiteralPath $internalLog) { Copy-Item -LiteralPath $internalLog -Destination (Join-Path $artifacts 'combat_server.internal.log') -Force }
  Copy-Item -LiteralPath (Join-Path $Repo 'config\combat_server.cfg') -Destination (Join-Path $artifacts 'combat_server.cfg.snapshot') -Force

  $status = 'PASS'
  $result.status = $status
  $result.selftest_summary = $selftestSummary
  $result.source_sha256 = $preFp
  $result.source_files = $preRows.Count
  $result.artifact_sha256 = $exeHash
  $result.run_observation = $runObservation
  $result.ended_at = (Get-Date).ToString('o')
  Write-Json (Join-Path $attemptDir 'attempt_result.json') $result
  Write-Utf8 (Join-Path $attemptDir 'VALID' ) "PASS`n"
  Write-Host "FREEZE005_RESULT=PASS"
  Write-Host "ATTEMPT_DIR=$attemptDir"
  Write-Host "SOURCE_SHA256=$preFp"
  Write-Host "ARTIFACT_SHA256=$exeHash"
  Write-Host "SELFTEST=$selftestSummary"
}
catch {
  $failure = $_.Exception.ToString()
  $result.status = 'INVALID'
  $result.errors = @($failure)
  $result.ended_at = (Get-Date).ToString('o')
  Write-Json (Join-Path $attemptDir 'attempt_result.json') $result
  try {
    $events = Drain-Queue $global:Freeze005WatcherEvents
    Write-Utf8 (Join-Path $evidence 'source_watcher.log') ("EVENT_COUNT=$($events.Count)`n" + (($events -join "`n")) + "`n")
  } catch { }
  Write-Utf8 (Join-Path $attemptDir 'INVALID') ($failure + "`n")
  Write-Host "FREEZE005_RESULT=INVALID"
  Write-Host "ATTEMPT_DIR=$attemptDir"
  Write-Host "ERROR=$($_.Exception.Message)"
  exit 1
}
finally {
  if ($watcher) {
    $watcher.EnableRaisingEvents = $false
    try { if ($changedHandler) { $watcher.remove_Changed($changedHandler) } } catch { }
    try { if ($createdHandler) { $watcher.remove_Created($createdHandler) } } catch { }
    try { if ($deletedHandler) { $watcher.remove_Deleted($deletedHandler) } } catch { }
    try { if ($renamedHandler) { $watcher.remove_Renamed($renamedHandler) } } catch { }
    $watcher.Dispose()
  }
  foreach ($stream in $lockStreams) { try { $stream.Dispose() } catch { } }
}
