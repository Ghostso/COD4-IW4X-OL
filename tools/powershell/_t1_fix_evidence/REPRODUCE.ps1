# REPRODUCE.ps1 - T-1 verified baseline: forced build + test, with hash assertions.
#
# Never runs a bare `xmake` or `xmake build`: ol_deploy is set_default(true) and
# config/codol-game-dir.txt is non-empty, so a default build would attempt a
# deployment. Every invocation below names its target explicitly.
#
# Usage:  powershell -NoProfile -ExecutionPolicy Bypass -File REPRODUCE.ps1

[CmdletBinding()]
param(
    [string] $Repository = "F:\桌面\ol\ol-mod-olfinal",
    [string] $LogDirectory = ""
)

$ErrorActionPreference = "Continue"
if ([string]::IsNullOrWhiteSpace($LogDirectory)) {
    $LogDirectory = Join-Path $PSScriptRoot "."
}
New-Item -ItemType Directory -Force -Path $LogDirectory | Out-Null
$log = Join-Path $LogDirectory ("reproduce_" + (Get-Date -Format "yyyyMMdd_HHmmss") + ".log")
function L($m) { $m | Out-File -FilePath $log -Encoding utf8 -Append }

# --- the frozen baseline -------------------------------------------------
$Expected = [ordered]@{
    "src\game_server\server_mp\sv_network_mp.cpp"              = "EF4E209BDD9EFDCD5A1F7F69B3789E77852FD98C1371D7C1154677EEBFF19B60"
    "src\game_server\server_mp\sv_network_mp.hpp"              = "53E5907AE4AFD9251A2192DB2634D88223F6037DB57D772DCC7A081D4E8612C1"
    "src\game_server\win32\win_net.cpp"                        = "3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14"
    "src\game_server\win32\win_net.hpp"                        = "8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1"
    "tests\game_server\TransportLifecycleTests.cpp"             = "FA67AE5B9C6D222CB3B8630D0EEA3D143A860A5E4C55753EB0951A7650A4C8AD"
    "src\game_server\EngineBindings.hpp"                        = "9ACE87313419DB58DC41EE6F4F38612A0970525BAF24CBF924462AD1BA88C72E"
    "src\game_server\ClientProcessPatches.cpp"                  = "E81D760A6B362076C346471EAC89F6841BF43B369BDA360E5E9180378C09B885"
}
$ExpectedHead = "2a75bdd8872bb9f54006382a924c3006ec9affc2"

L "=== T-1 REPRODUCE ==="
L ("started=" + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))
L ("repository=" + $Repository)

$head = (& git -C $Repository rev-parse HEAD)
L ("HEAD=" + $head + " expected=" + $ExpectedHead)
if ($head -ne $ExpectedHead) {
    L "STOP: HEAD does not match the frozen baseline."
    Write-Error "HEAD $head != $ExpectedHead"; exit 2
}
$mismatch = @()
foreach ($rel in $Expected.Keys) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $Repository $rel) -Algorithm SHA256).Hash
    $ok = ($actual -eq $Expected[$rel])
    L ("{0}  {1}  {2}" -f $(if ($ok) { "OK  " } else { "DRIFT" }), $actual, $rel)
    if (-not $ok) { $mismatch += $rel }
}
if ($mismatch.Count -gt 0) {
    L ("STOP: drifted files: " + ($mismatch -join ", "))
    Write-Error ("Source drift: " + ($mismatch -join ", ")); exit 2
}
L "baseline hashes all match"

Push-Location $Repository
try {
    L "=== configure ==="
    & xmake f 2>&1 | Out-File -FilePath $log -Encoding utf8 -Append
    L ("CONFIGURE exit=" + $LASTEXITCODE)

    L "=== forced rebuild ol_transport_lifecycle_tests ==="
    & xmake build -r ol_transport_lifecycle_tests 2>&1 | Out-File -FilePath $log -Encoding utf8 -Append
    L ("BUILD exit=" + $LASTEXITCODE)

    $exe = Join-Path $Repository "build\bin\release\ol_transport_lifecycle_tests.exe"
    $run = & $exe 2>&1
    $rc = $LASTEXITCODE
    $run | Out-File -FilePath $log -Encoding utf8 -Append
    L ("ol_transport_lifecycle_tests run exit=" + $rc)
    $run | Select-String -Pattern "^checks=" | ForEach-Object { L ("  " + $_.Line) }

    foreach ($t in @("ol_game_server_tests", "ol_lua_runtime_tests")) {
        L ("=== build+run " + $t + " ===")
        & xmake build $t 2>&1 | Out-File -FilePath $log -Encoding utf8 -Append
        L ("BUILD exit=" + $LASTEXITCODE)
        $e = Join-Path $Repository ("build\bin\release\" + $t + ".exe")
        if (Test-Path $e) {
            $o = & $e 2>&1
            $o | Out-File -FilePath $log -Encoding utf8 -Append
            L ($t + " run exit=" + $LASTEXITCODE)
        }
    }

    L "=== build ol_game_server (production plugin; compile+link only) ==="
    & xmake build ol_game_server 2>&1 | Out-File -FilePath $log -Encoding utf8 -Append
    L ("BUILD ol_game_server exit=" + $LASTEXITCODE)

    L "=== git diff --check ==="
    & git diff --check 2>&1 | Out-File -FilePath $log -Encoding utf8 -Append
    L ("diff-check exit=" + $LASTEXITCODE)

    L "=== deploy guard: build\stage must be untouched ==="
    L ("stage mtime=" + (Get-Item -LiteralPath (Join-Path $Repository "build\stage")).LastWriteTime.ToString("yyyy-MM-dd HH:mm:ss"))
} finally { Pop-Location }

L ("finished=" + (Get-Date).ToString("yyyy-MM-dd HH:mm:ss"))
Write-Host ("REPRODUCE log: " + $log)