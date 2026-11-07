#Requires -Version 5.1
<#
inspect-artifact.ps1  (read-only)

Computes identity metadata for files the USER explicitly names. It never starts
the file, never writes to it, never walks other directories and never touches
any expected-hash configuration. It uses only what ships with PowerShell/.NET,
so it needs no installation.

Usage:
  .\inspect-artifact.ps1 -Path D:\somewhere\out.exe
  .\inspect-artifact.ps1 -Path D:\install\main\mp_crash_tropical.ff,D:\somewhere\out.exe

Exit codes: 0 = all inputs inspected, 1 = at least one input unreadable.
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string[]] $Path,
    [string] $OutFile = ""
)
$ErrorActionPreference = "Stop"
$results = New-Object System.Collections.ArrayList

# 'powershell -File' binds every argument as a single string, so a list passed
# as "a,b" arrives as one element. Expand by comma only when the literal path
# does not exist, so a real filename containing a comma still wins.
$expanded = New-Object System.Collections.ArrayList
foreach ($raw in $Path) {
    if (Test-Path -LiteralPath $raw) { [void]$expanded.Add($raw) }
    elseif ($raw -match ',') {
        foreach ($piece in ($raw -split ',')) {
            if (-not [string]::IsNullOrWhiteSpace($piece)) { [void]$expanded.Add($piece.Trim()) }
        }
    } else { [void]$expanded.Add($raw) }
}
$Path = @($expanded)
$anyFailure = $false

function Read-At { param([System.IO.FileStream]$Stream, [long]$Offset, [int]$Count)
    if ($Offset + $Count -gt $Stream.Length) { return $null }
    $Stream.Position = $Offset
    $buf = New-Object byte[] $Count
    $n = $Stream.Read($buf, 0, $Count)
    if ($n -lt $Count) { return $null }
    return $buf
}

foreach ($item in $Path) {
    $entry = [ordered]@{
        path = $item; exists = $false; bytes = $null; sha256 = $null
        peMachine = $null; peMachineName = $null; imageBase = $null; sizeOfImage = $null
        sections = @(); fileVersion = $null; productVersion = $null; companyName = $null
        fastfileMagic = $null; fastfileVersion = $null; kind = "unknown"; errors = @()
    }
    if (-not (Test-Path -LiteralPath $item -PathType Leaf)) {
        $entry.errors += "not found"
        $anyFailure = $true
        [void]$results.Add($entry)
        continue
    }
    $entry.exists = $true
    $fi = Get-Item -LiteralPath $item
    $entry.bytes = $fi.Length
    $entry.sha256 = (Get-FileHash -LiteralPath $item -Algorithm SHA256).Hash
    $entry.fileVersion = $fi.VersionInfo.FileVersion
    $entry.productVersion = $fi.VersionInfo.ProductVersion
    $entry.companyName = $fi.VersionInfo.CompanyName

    $ext = [System.IO.Path]::GetExtension($item).ToLowerInvariant()
    $stream = $null
    try {
        $stream = [System.IO.File]::Open($item, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::ReadWrite)
        if ($ext -eq ".ff") {
            $entry.kind = "fastfile"
            $hdr = Read-At $stream 0 12
            if ($hdr) {
                $entry.fastfileMagic = [System.Text.Encoding]::ASCII.GetString($hdr, 0, 8)
                $entry.fastfileVersion = [System.BitConverter]::ToUInt32($hdr, 8)
            } else { $entry.errors += "fastfile header unreadable" }
        } else {
            $entry.kind = "pe"
            $eLfanew = Read-At $stream 0x3C 4
            if ($eLfanew) {
                $peOff = [System.BitConverter]::ToInt32($eLfanew, 0)
                $sig = Read-At $stream $peOff 4
                if ($sig -and [System.BitConverter]::ToUInt32($sig, 0) -eq 0x00004550) {
                    $coff = Read-At $stream ($peOff + 4) 20
                    $machine = [System.BitConverter]::ToUInt16($coff, 0)
                    $nSections = [System.BitConverter]::ToUInt16($coff, 2)
                    $sizeOpt = [System.BitConverter]::ToUInt16($coff, 16)
                    $entry.peMachine = ("0x" + $machine.ToString("X4"))
                    switch ($machine) { 0x014C { $entry.peMachineName = "x86" } 0x8664 { $entry.peMachineName = "x64" } default { $entry.peMachineName = "unknown" } }
                    $optOff = $peOff + 24
                    $opt = Read-At $stream $optOff 60
                    if ($opt) {
                        $entry.imageBase = ("0x" + [System.BitConverter]::ToUInt32($opt, 28).ToString("X8"))
                        $entry.sizeOfImage = ("0x" + [System.BitConverter]::ToUInt32($opt, 56).ToString("X8"))
                    }
                    $secOff = $optOff + $sizeOpt
                    for ($i = 0; $i -lt $nSections; $i++) {
                        $s = Read-At $stream ($secOff + $i * 40) 40
                        if (-not $s) { break }
                        $nm = [System.Text.Encoding]::ASCII.GetString($s, 0, 8).TrimEnd([char]0)
                        $entry.sections += [ordered]@{ name = $nm;
                            virtualSize = ("0x" + [System.BitConverter]::ToUInt32($s, 8).ToString("X"));
                            virtualAddress = ("0x" + [System.BitConverter]::ToUInt32($s, 12).ToString("X"));
                            rawSize = ("0x" + [System.BitConverter]::ToUInt32($s, 16).ToString("X"));
                            rawPtr = ("0x" + [System.BitConverter]::ToUInt32($s, 20).ToString("X")) }
                    }
                } else { $entry.errors += "PE signature not found" }
            } else { $entry.errors += "DOS header unreadable" }
        }
    } catch { $entry.errors += ("read failed: " + $_.Exception.Message) }
    finally { if ($stream) { $stream.Dispose() } }

    [void]$results.Add($entry)
}

$payload = [ordered]@{ schemaVersion = 1; kind = "codol-artifact-inspection"; generatedAt = (Get-Date).ToUniversalTime().ToString("o"); files = $results }
$json = ($payload | ConvertTo-Json -Depth 8).Replace([string][char]13 + [string][char]10, [string][char]10)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
if (-not [string]::IsNullOrWhiteSpace($OutFile)) { [System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($OutFile), $json, $utf8NoBom) }

foreach ($e in $results) {
    Write-Host ("--- " + $e.path)
    if (-not $e.exists) { Write-Host "    NOT FOUND"; continue }
    Write-Host ("    bytes        = " + $e.bytes)
    Write-Host ("    sha256       = " + $e.sha256)
    if ($e.kind -eq "pe") {
        Write-Host ("    peMachine    = " + $e.peMachine + " (" + $e.peMachineName + ")")
        Write-Host ("    imageBase    = " + $e.imageBase + "   sizeOfImage = " + $e.sizeOfImage)
        Write-Host ("    sections     = " + (($e.sections | ForEach-Object { $_.name }) -join ", "))
    }
    if ($e.kind -eq "fastfile") { Write-Host ("    fastfile     = magic=" + $e.fastfileMagic + " version=" + $e.fastfileVersion) }
    Write-Host ("    fileVersion  = " + $e.fileVersion + "  (METADATA ONLY - never identity)")
    if ($e.errors.Count) { Write-Host ("    errors       = " + ($e.errors -join "; ")) }
}
if ($anyFailure) { exit 1 } else { exit 0 }
