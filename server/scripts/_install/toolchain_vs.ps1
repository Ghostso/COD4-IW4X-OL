$ErrorActionPreference = 'Continue'
$ws = 'D:\BaiduNetdiskDownload\使命召唤OL'
$log = Join-Path $ws '_install_vs.log'
$done = Join-Path $ws '_install_vs.done'
$dir = Join-Path $ws '_install'
$boot = Join-Path $dir 'vs_BuildTools.exe'
function L($m) { Add-Content -LiteralPath $log -Value ((Get-Date -Format 'HH:mm:ss') + '  ' + $m) -Encoding UTF8 }
Remove-Item $done -ErrorAction SilentlyContinue
Set-Content -LiteralPath $log -Value 'START-ELEVATED' -Encoding UTF8
$rc = 1
try {
    L ('whoami=' + (whoami))
    L ('admin=' + ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator))
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    L ('install dir ready: ' + (Test-Path $dir))
    $pl = $false
    try { $pl = (Test-NetConnection -ComputerName 127.0.0.1 -Port 10090 -InformationLevel Quiet -WarningAction SilentlyContinue) } catch {}
    L ('proxy 127.0.0.1:10090 listening = ' + $pl)
    $env:TEMP = 'E:\_vstemp'; $env:TMP = 'E:\_vstemp'
    New-Item -ItemType Directory -Force -Path 'E:\_vstemp' | Out-Null
    L ('E:\_vstemp created = ' + (Test-Path 'E:\_vstemp'))
    $url = 'https://aka.ms/vs/17/release/vs_BuildTools.exe'
    $ok = $false
    $attempts = @(
        @{n='curl-noproxy'; a={ & curl.exe -sS -L --noproxy '*' --max-time 240 -o $boot $url 2>&1 }},
        @{n='curl-proxy';   a={ & curl.exe -sS -L --proxy 'http://127.0.0.1:10090' --max-time 240 -o $boot $url 2>&1 }},
        @{n='iwr-default';  a={ Invoke-WebRequest -Uri $url -OutFile $boot -UseBasicParsing -TimeoutSec 240 }},
        @{n='iwr-proxy';    a={ Invoke-WebRequest -Uri $url -OutFile $boot -UseBasicParsing -Proxy 'http://127.0.0.1:10090' -TimeoutSec 240 }}
    )
    foreach ($att in $attempts) {
        if ($ok) { break }
        L ('--- download attempt: ' + $att.n)
        try { $out = & $att.a; if ($out) { L ('    out: ' + (($out | Out-String).Trim() -replace '\s+',' ').Substring(0, [Math]::Min(300, (($out | Out-String).Trim()).Length))) } } catch { L ('    threw: ' + $_.Exception.Message) }
        if ((Test-Path $boot) -and ((Get-Item $boot).Length -gt 500000)) { $ok = $true; L ('    OK bytes=' + (Get-Item $boot).Length) }
        else { L ('    failed, size=' + (if (Test-Path $boot) { (Get-Item $boot).Length } else { -1 })) }
    }
    if ($ok) {
        L ('bootstrapper sha256=' + (Get-FileHash $boot -Algorithm SHA256).Hash)
        $vsArgs = @('--quiet','--wait','--norestart','--nocache','--installPath','E:\BuildTools','--add','Microsoft.VisualStudio.Workload.VCTools','--add','Microsoft.VisualStudio.Component.VC.Tools.x86.x64','--includeRecommended')
        L ('launching vs installer: ' + ($vsArgs -join ' '))
        $p = Start-Process -FilePath $boot -ArgumentList $vsArgs -Wait -PassThru
        L ('vs_BuildTools exit=' + $p.ExitCode)
        $rc = $p.ExitCode
    } else { L 'DOWNLOAD FAILED (all transports)'; $rc = 98 }
    $vcvars = 'E:\BuildTools\VC\Auxiliary\Build\vcvarsall.bat'
    L ('vcvarsall.bat exists = ' + (Test-Path $vcvars))
    L ('MSVC versions = ' + ((Get-ChildItem 'E:\BuildTools\VC\Tools\MSVC' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name) -join ','))
    if (Test-Path $vcvars) {
        $inner = [char]34 + $vcvars + [char]34 + ' x86 >nul 2>&1 && cl 2>&1 && link 2>&1'
        $clOut = (& cmd.exe /c $inner | Out-String)
        L ('cl/link output: ' + ($clOut.Trim() -replace '\r?\n',' | ').Substring(0,[Math]::Min(400,$clOut.Trim().Length)))
    }
    L ('SDK Include = ' + ((Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\Include' -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Name) -join ','))
} catch { L ('EXCEPTION: ' + $_.Exception.Message); $rc = 99 }
Set-Content -LiteralPath $done -Value ('EXIT=' + $rc) -Encoding UTF8
L ('DONE rc=' + $rc)
