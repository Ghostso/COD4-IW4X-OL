$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_openssl7.log'
$done = Join-Path $ws '_install_openssl7.done'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-OPENSSL7' -Encoding UTF8
$rc = 1
try {
    $vc = 'E:\vcpkg'
    $env:VCPKG_ROOT = $vc
    $env:VCPKG_DEFAULT_TRIPLET = 'x86-windows-static'
    $env:VCPKG_VISUAL_STUDIO_PATH = 'E:\BuildTools'
    $env:VCPKG_MAX_CONCURRENCY = '8'
    $env:Path = 'C:\Program Files\Git\cmd;E:\BuildTools\Common7\IDE\CommonExtensions\Microsoft\CMake\CMake\bin;' + $env:Path
    L ('admin=' + ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
    $dl = Join-Path $vc 'downloads'
    New-Item -ItemType Directory -Force -Path $dl | Out-Null
    $msysFile = Join-Path $vc 'scripts\cmake\vcpkg_acquire_msys.cmake'
    $pairs = New-Object System.Collections.ArrayList
    $pending = $null
    foreach ($ln in (Get-Content $msysFile)) {
        if ($ln -match 'URL\s+"(https://[^"]+)"') { $pending = $Matches[1]; continue }
        if ($pending -and $ln -match 'SHA512\s+([0-9a-fA-F]{128})') {
            [void]$pairs.Add([pscustomobject]@{ url = $pending; sha = $Matches[1].ToLower() })
            $pending = $null
        }
    }
    L ('msys packages declared: ' + $pairs.Count)
    $need = 0; $got = 0; $fail = 0
    foreach ($p in $pairs) {
        $bn = [System.IO.Path]::GetFileName($p.url)
        $dst = Join-Path $dl ('msys2-' + $bn)
        $okHash = $false
        if (Test-Path $dst) { $okHash = ((Get-FileHash $dst -Algorithm SHA512).Hash.ToLower() -eq $p.sha) }
        if (-not $okHash) {
            $need++
            & curl.exe -sS -L --proxy 'http://127.0.0.1:10090' --max-time 300 -o $dst $p.url 2>&1 | Out-Null
            $okHash = ((Get-FileHash $dst -Algorithm SHA512).Hash.ToLower() -eq $p.sha)
        }
        if ($okHash) { $got++ } else { $fail++; L ('  HASH/FAIL: ' + $bn) }
    }
    L ('msys seeded ok=' + $got + ' failed=' + $fail + ' downloaded=' + $need)
    L '--- vcpkg install openssl ---'
    & (Join-Path $vc 'vcpkg.exe') install 'openssl:x86-windows-static' 2>&1 | ForEach-Object { L ('  ' + $_) }
    $irc = $LASTEXITCODE
    L ('vcpkg install exit=' + $irc)
    $inst = Join-Path $vc 'installed\x86-windows-static'
    L ('ssl.h      = ' + (Test-Path (Join-Path $inst 'include\openssl\ssl.h')))
    L ('libcrypto  = ' + (Test-Path (Join-Path $inst 'lib\libcrypto.lib')))
    L ('libssl     = ' + (Test-Path (Join-Path $inst 'lib\libssl.lib')))
    L ('mhook.lib  = ' + (Test-Path (Join-Path $inst 'lib\mhook.lib')))
    if ($irc -eq 0) { $rc = 0 }
} catch { L ('EXCEPTION: ' + $_.Exception.Message); $rc = 99 }
Set-Content -LiteralPath $done -Value ('EXIT=' + $rc) -Encoding UTF8
L ('DONE rc=' + $rc)
