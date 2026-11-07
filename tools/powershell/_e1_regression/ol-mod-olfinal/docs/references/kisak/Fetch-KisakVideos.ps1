[CmdletBinding()]
param(
    [switch]$Force
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$manifestPath = Join-Path $root "media-manifest.json"
$destination = Join-Path $root "videos"
$manifest = Get-Content -Raw -Encoding UTF8 $manifestPath | ConvertFrom-Json
$videos = $manifest | Where-Object { $_.kind -eq "videos" }

New-Item -ItemType Directory -Force -Path $destination | Out-Null

foreach ($video in $videos) {
    $target = Join-Path $destination $video.name
    $validExisting = $false

    if (Test-Path -LiteralPath $target) {
        $file = Get-Item -LiteralPath $target
        if ($file.Length -eq $video.bytes) {
            $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $target).Hash.ToLowerInvariant()
            $validExisting = $hash -eq $video.sha256
        }
    }

    if ($validExisting -and -not $Force) {
        Write-Host "[skip] $($video.name)"
        continue
    }

    $temporary = "$target.part"
    Remove-Item -Force -ErrorAction SilentlyContinue -LiteralPath $temporary

    Write-Host "[download] $($video.name)"
    Invoke-WebRequest -Uri $video.source_url -OutFile $temporary

    $downloaded = Get-Item -LiteralPath $temporary
    if ($downloaded.Length -ne $video.bytes) {
        Remove-Item -Force -LiteralPath $temporary
        throw "Length mismatch for $($video.name): expected $($video.bytes), got $($downloaded.Length)"
    }

    $hash = (Get-FileHash -Algorithm SHA256 -LiteralPath $temporary).Hash.ToLowerInvariant()
    if ($hash -ne $video.sha256) {
        Remove-Item -Force -LiteralPath $temporary
        throw "SHA-256 mismatch for $($video.name): expected $($video.sha256), got $hash"
    }

    Move-Item -Force -LiteralPath $temporary -Destination $target
}

Write-Host "Kisak article videos are ready in $destination"
