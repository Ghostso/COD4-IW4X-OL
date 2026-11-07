# OfflineServer\repair_sandbox.ps1
# 仅从 COD OL 完整安装目录把沙箱缺失的资源文件硬链接/复制过去
# 绝不修改 launch.ps1、不动 WeGame、纯离线

$ROOT   = 'D:\BaiduNetdiskDownload\使命召唤OL'
$SRC    = Join-Path $ROOT 'COD OL'
$SBX    = Join-Path $ROOT 'run_codol_001\sandbox_ifs1_20260923'

$CriticalDirs = @(
    'zone',
    'main',
    'scripts',
    'video',
    'sound',
    'localization',
    'materials',
    'images'
)

foreach ($dir in $CriticalDirs) {
    $srcDir = Join-Path $SRC $dir
    $dstDir = Join-Path $SBX $dir
    if (-not (Test-Path $srcDir)) { continue }
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir | Out-Null }

    $files = Get-ChildItem -Recurse -File $srcDir
    foreach ($f in $files) {
        $rel = $f.FullName.Substring($srcDir.Length + 1)
        $dst = Join-Path $dstDir $rel
        if (-not (Test-Path $dst)) {
            $dstParent = Split-Path -Parent $dst
            if (-not (Test-Path $dstParent)) { New-Item -ItemType Directory -Path $dstParent | Out-Null }
            # 优先硬链接（节省空间、极快），失败则复制
            $result = cmd /c mklink /H "$dst" "$($f.FullName)" 2>$null
            if ($LASTEXITCODE -ne 0) {
                Copy-Item -LiteralPath $f.FullName -Destination $dst -Force
            }
        }
    }
    Write-Host "[OK] $dir 同步完成"
}

# 确保 dwauth.ini / cacert.pem 已就绪（若被覆盖则恢复）
$dwauth = Join-Path $SBX 'dwauth.ini'
if (-not (Test-Path $dwauth)) {
    @('127.0.0.1','0','127.0.0.1','443','0','0','0') | Set-Content -Encoding ASCII $dwauth
}
$ca = Join-Path $ROOT 'OfflineServer\lobby_server\ca_append.pem'
$cacert = Join-Path $SBX 'cacert.pem'
if (Test-Path $ca -and (Get-Content $cacert -Raw) -notmatch 'CODOL Local Lobby CA') {
    Add-Content -Path $cacert -Value ("`n" + (Get-Content $ca -Raw)) -Encoding ASCII
}
Write-Host "[===] 沙箱修复完成，可直接跑 launch.ps1 验证"