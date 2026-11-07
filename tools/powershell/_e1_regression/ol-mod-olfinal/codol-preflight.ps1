#Requires -Version 5.1
<#
codol-preflight.ps1  (schemaVersion 2)

Non-destructive readiness check for the OLMod CODOL local battle server.
It never builds, launches the game, starts a packet capture or modifies the
repository or the host. Its only writes are the report files.

Guiding rule: a token is only true when the EVIDENCE named by the token is
actually present. A filename match, a readable container header or a command
on PATH is never by itself proof of an asset set or of a toolchain.

Exit codes: 0 = no blocking failure, 1 = BLOCKED, 2 = script error.
#>
[CmdletBinding()]
param(
    [string]   $RepoPath = ".",
    [string]   $ClientPath = "",
    [string]   $GamePath = "",
    [string]   $ExpectedClientSha256 = "",
    [string]   $ExpectedAssetBuildAssociation = "",
    [string[]] $RequiredMapFastfiles = @(),
    [long]     $MinMapFastfileBytes = 262144,
    [string]   $OutFile = "preflight.json",
    [string]   $StableOut = ""
)

$ErrorActionPreference = "Stop"
$script:Checks = New-Object System.Collections.ArrayList
$script:MapManifest = $null

function Add-Check {
    param([string]$Id, [string]$Name, [string]$Status, $Expected, $Actual, $Evidence)
    [void]$script:Checks.Add([ordered]@{
        id = $Id; name = $Name; status = $Status; expected = $Expected; actual = $Actual; evidence = $Evidence })
}
function Get-Sha256OrNull { param([string]$Path)
    try { return (Get-FileHash -LiteralPath $Path -Algorithm SHA256 -ErrorAction Stop).Hash } catch { return $null } }
function Test-CommandExists { param([string]$Name)
    $c = Get-Command $Name -ErrorAction SilentlyContinue; if ($null -eq $c) { return $null }; return $c.Source }
function Get-FirstBytes { param([string]$Path, [int]$Count = 16)
    try { $fs = [System.IO.File]::OpenRead($Path); try { $b = New-Object byte[] $Count; $n = $fs.Read($b,0,$Count);
        if ($n -le 0) { return $null }; if ($n -lt $Count) { $b = $b[0..($n-1)] }; return $b } finally { $fs.Dispose() } }
    catch { return $null } }

# A fastfile is a MAP candidate only when its name matches a map pattern AND it
# is not one of the known non-map families. The denylist is evaluated first, so
# mp_playlists.ff and code_/common_/ui_/localized_/marketplace/loadscreen files
# can never be promoted to a map by the pattern alone.
function Get-FastfileClass { param([string]$Name)
    $l = $Name.ToLowerInvariant()
    if ($l -match "playlist")      { return "playlists" }
    if ($l -match "^localized_")   { return "localized" }
    if ($l -match "^code_")        { return "code" }
    if ($l -match "^common_")      { return "common" }
    if ($l -match "^ui_")          { return "ui" }
    if ($l -match "^development")  { return "development" }
    if ($l -match "marketplace")   { return "marketplace" }
    if ($l -match "loadscreen")    { return "loadscreen" }
    if ($l -match "^(mp|zm|coop|sp)_") { return "MAP" }
    return "other" }

$runGeneratedAt = (Get-Date).ToUniversalTime().ToString("o")
$repoFull = $null
if (Test-Path -LiteralPath $RepoPath) { $repoFull = (Resolve-Path -LiteralPath $RepoPath).Path }

if ($null -eq $repoFull) {
    Add-Check "repo.path" "repository path exists" "FAIL" "a directory" "not found: $RepoPath" $RepoPath
} else {
    Add-Check "repo.path" "repository path exists" "PASS" "a directory" $repoFull $repoFull
    foreach ($f in @("xmake.lua", "vcpkg.json", "config\codol-game-dir.txt")) {
        $p = Join-Path $repoFull $f; $ok = Test-Path -LiteralPath $p
        $st = "FAIL"; if ($ok) { $st = "PASS" }
        $ac = "missing"; if ($ok) { $ac = "present" }
        Add-Check ("repo.file." + $f) ("repo file present: " + $f) $st "present" $ac $p }
    if ($null -eq (Test-CommandExists "git")) {
        Add-Check "repo.git" "git available" "FAIL" "git" "not found" "" }
    else {
        $head = (& git -C $repoFull rev-parse HEAD 2>$null)
        $branch = (& git -C $repoFull rev-parse --abbrev-ref HEAD 2>$null)
        $porc = @(& git -C $repoFull status --porcelain 2>$null)
        $wst = "WARN"; if ($porc.Count -eq 0) { $wst = "PASS" }
        Add-Check "repo.head" "git HEAD" "PASS" "a commit" $head $head
        Add-Check "repo.branch" "git branch" "PASS" "a branch" $branch $branch
        Add-Check "repo.worktree" "worktree clean" $wst "0 changes" "$($porc.Count) change(s)" ($porc -join "; ") }
}

if ([string]::IsNullOrWhiteSpace($ClientPath)) {
    Add-Check "client.path" "client executable path supplied" "FAIL" "a path" "not supplied" ""
} else {
    Add-Check "client.path" "client executable path supplied" "PASS" "a path" $ClientPath $ClientPath
    if (-not (Test-Path -LiteralPath $ClientPath -PathType Leaf)) {
        Add-Check "client.exists" "client executable exists" "FAIL" "an existing file" "not found" $ClientPath
    } else {
        $ci = Get-Item -LiteralPath $ClientPath
        Add-Check "client.exists" "client executable exists" "PASS" "an existing file" "$($ci.Length) bytes" $ClientPath
        $actualSha = Get-Sha256OrNull $ClientPath
        if ([string]::IsNullOrWhiteSpace($ExpectedClientSha256)) {
            Add-Check "client.sha256" "client SHA-256 is the approved target" "FAIL" "(no approved hash supplied)" "not comparable" $ClientPath
        } else {
            $exp = $ExpectedClientSha256.Trim().ToUpperInvariant()
            $act = "<unreadable>"; if ($null -ne $actualSha) { $act = $actualSha.ToUpperInvariant() }
            $cst = "FAIL"; if ($act -eq $exp) { $cst = "PASS" }
            Add-Check "client.sha256" "client SHA-256 is the approved target" $cst $exp $act $ClientPath }
        $vi = $ci.VersionInfo
        Add-Check "client.fileversion" "client file version (METADATA ONLY - never identity)" "INFO" "(informational)" ("FileVersion=" + $vi.FileVersion + "; ProductVersion=" + $vi.ProductVersion) $ClientPath
        $arch = "unknown"
        try { $fs = [System.IO.File]::OpenRead($ClientPath)
            try { $br = New-Object System.IO.BinaryReader($fs)
                $fs.Position = 0x3C; $pe = $br.ReadInt32(); $fs.Position = $pe + 4; $m = $br.ReadUInt16()
                if ($m -eq 0x14c) { $arch = "x86" } elseif ($m -eq 0x8664) { $arch = "x64" } else { $arch = "0x" + $m.ToString("x") } } finally { $fs.Dispose() } } catch {}
        Add-Check "client.arch" "client PE architecture" "INFO" "informational" $arch $ClientPath } }

$mapCandidates = @(); $allFf = @()
if ([string]::IsNullOrWhiteSpace($GamePath)) {
    Add-Check "game.path" "game directory supplied" "FAIL" "a directory" "not supplied" ""
} else {
    Add-Check "game.path" "game directory supplied" "PASS" "a directory" $GamePath $GamePath
    if (-not (Test-Path -LiteralPath $GamePath -PathType Container)) {
        Add-Check "game.exists" "game directory exists" "FAIL" "an existing directory" "not found" $GamePath
    } else {
        $gFull = (Resolve-Path -LiteralPath $GamePath).Path
        Add-Check "game.exists" "game directory exists" "PASS" "an existing directory" $gFull $gFull
        $mainDir = Join-Path $gFull "main"
        $mainOk = Test-Path -LiteralPath $mainDir -PathType Container
        $mst = "FAIL"; $mac = "missing"; if ($mainOk) { $mst = "PASS"; $mac = "present" }
        Add-Check "game.main" "main/ directory present" $mst "present" $mac $mainDir
        try { $allFf = @(Get-ChildItem -LiteralPath $gFull -Recurse -File -Filter "*.ff" -Depth 6 -ErrorAction SilentlyContinue) } catch { $allFf = @() }
        $fcSt = "FAIL"; if ($allFf.Count -gt 0) { $fcSt = "PASS" }
        Add-Check "game.ff_count" "fastfiles found" $fcSt ">=1 .ff" "$($allFf.Count) .ff" $gFull
        $mapCandidates = @($allFf | Where-Object { (Get-FastfileClass $_.Name) -eq "MAP" })
        $mSt = "FAIL"; if ($mapCandidates.Count -gt 0) { $mSt = "PASS" }
        Add-Check "game.map_ff" "map fastfiles present (strict classification)" $mSt ">=1 map .ff" "$($mapCandidates.Count) map .ff" (($mapCandidates | Select-Object -First 12 | ForEach-Object { $_.Name }) -join ", ")
        $badHeader = @(); $tooSmall = @(); $manifest = @()
        foreach ($f in $mapCandidates) {
            $bytes = Get-FirstBytes $f.FullName 16
            $magic = ""; $ver = 0
            if ($null -ne $bytes -and $bytes.Length -ge 12) { $magic = [System.Text.Encoding]::ASCII.GetString($bytes,0,8); $ver = [System.BitConverter]::ToUInt32($bytes,8) }
            if ($magic -ne "IWff0100") { $badHeader += $f.Name }
            if ($f.Length -lt $MinMapFastfileBytes) { $tooSmall += $f.Name }
            $manifest += [ordered]@{ name = $f.Name; bytes = $f.Length; magic = $magic; version = $ver; sha256 = (Get-Sha256OrNull $f.FullName) } }
        if ($mapCandidates.Count -gt 0) { $script:MapManifest = $manifest }
        $hSt = "FAIL"; $hAc = $badHeader -join ", "; if ($mapCandidates.Count -gt 0 -and $badHeader.Count -eq 0) { $hSt = "PASS"; $hAc = "all readable" }
        Add-Check "game.map_headers" "every map candidate has a readable IWff0100 header" $hSt "all readable" $hAc "$($mapCandidates.Count) probed"
        $sSt = "FAIL"; $sAc = $tooSmall -join ", "; if ($mapCandidates.Count -gt 0 -and $tooSmall.Count -eq 0) { $sSt = "PASS"; $sAc = "all plausible" }
        Add-Check "game.map_sizes" "every map candidate is plausibly a map" $sSt ">= $MinMapFastfileBytes bytes" $sAc "heuristic size floor"
        $unhashed = @($manifest | Where-Object { [string]::IsNullOrWhiteSpace($_.sha256) })
        $hhSt = "FAIL"; $hhAc = "missing: " + (($unhashed | ForEach-Object { $_.name }) -join ", "); if ($mapCandidates.Count -gt 0 -and $unhashed.Count -eq 0) { $hhSt = "PASS"; $hhAc = "all hashed" }
        Add-Check "game.map_hashes" "every map candidate has a SHA-256" $hhSt "all hashed" $hhAc "$($manifest.Count) entries"
        $req = @($RequiredMapFastfiles | Where-Object { -not [string]::IsNullOrWhiteSpace($_) })
        if ($req.Count -eq 0) {
            Add-Check "game.map_completeness" "required map set defined and complete" "FAIL" "an explicit -RequiredMapFastfiles list" "not supplied" "completeness standard is undefined"
        } else {
            $missingReq = @()
            foreach ($r0 in $req) { $rn = $r0.Trim().ToLowerInvariant(); if ($rn -notmatch "\.ff$") { $rn = $rn + ".ff" }
                $hit = @($manifest | Where-Object { $_.name.ToLowerInvariant() -eq $rn })
                if ($hit.Count -eq 0) { $missingReq += $rn } }
            $cSt = "FAIL"; $cAc = "missing: " + ($missingReq -join ", "); if ($missingReq.Count -eq 0) { $cSt = "PASS"; $cAc = "all present" }
            Add-Check "game.map_completeness" "required map set defined and complete" $cSt ($req -join ", ") $cAc "completeness standard" }
        if ([string]::IsNullOrWhiteSpace($ExpectedAssetBuildAssociation)) {
            Add-Check "game.build_association" "asset set associated with the approved client build" "FAIL" "an explicit association statement" "not supplied" "the tool cannot prove build association itself"
        } else {
            Add-Check "game.build_association" "asset set associated with the approved client build" "PASS" "explicit declaration" $ExpectedAssetBuildAssociation "caller-declared; recorded verbatim, not independently provable" } } }

$clVer = $null; $clArch = $null
if ($null -ne (Test-CommandExists "cl")) {
    try { $banner = (& cl 2>&1 | Select-Object -First 3) -join " "
        if ($banner -match "Version\s+([0-9]+\.[0-9]+\.[0-9]+(\.[0-9]+)?)") { $clVer = $Matches[1] }
        if ($banner -match "for\s+(x86|x64)") { $clArch = $Matches[1] } } catch {} }
$clSt = "FAIL"; if ($clVer) { $clSt = "PASS" }
Add-Check "tool.cl" "MSVC cl.exe on PATH" $clSt "cl present" $(if ($clVer) { $clVer } else { "not found" }) ""
$clvSt = "FAIL"; if ($clVer) { $clvSt = "PASS" }
Add-Check "tool.cl_version" "MSVC compiler version parsed" $clvSt "a parsed version" $(if ($clVer) { $clVer } else { "unparsed" }) "banner parse"
$claSt = "FAIL"; if ($clArch -eq "x86") { $claSt = "PASS" }
Add-Check "tool.cl_arch" "MSVC target architecture" $claSt "x86" $(if ($clArch) { $clArch } else { "unparsed" }) "CODOL is a 32-bit title"
$xmVer = $null
if ($null -ne (Test-CommandExists "xmake")) {
    try { $o = (& xmake --version 2>&1 | Select-Object -First 2) -join " "; if ($o -match "v?([0-9]+\.[0-9]+\.[0-9]+)") { $xmVer = $Matches[1] } } catch {} }
$xmSt = "FAIL"; if ($xmVer) { $xmSt = "PASS" }
Add-Check "tool.xmake" "xmake on PATH" $xmSt "xmake present" $(if ($xmVer) { $xmVer } else { "not found" }) ""
$xmOk = $false; if ($xmVer) { try { if ([version]$xmVer -ge [version]"3.0.9") { $xmOk = $true } } catch {} }
$xmvSt = "FAIL"; if ($xmOk) { $xmvSt = "PASS" }
Add-Check "tool.xmake_version" "xmake version >= 3.0.9 (README.md:31)" $xmvSt ">= 3.0.9" $(if ($xmVer) { $xmVer } else { "not found" }) "banner parse"
$vcRoot = $env:VCPKG_ROOT
$vcRootOk = $false; if ((-not [string]::IsNullOrWhiteSpace($vcRoot)) -and (Test-Path -LiteralPath $vcRoot)) { $vcRootOk = $true }
$vcrSt = "FAIL"; if ($vcRootOk) { $vcrSt = "PASS" }
Add-Check "tool.vcpkg_root" "VCPKG_ROOT set and valid" $vcrSt "a valid directory" $(if ([string]::IsNullOrWhiteSpace($vcRoot)) { "empty" } else { $vcRoot }) ""
$vcVer = $null
if ($null -ne (Test-CommandExists "vcpkg")) {
    try { $o2 = (& vcpkg version 2>&1 | Select-Object -First 2) -join " "; if ($o2 -match "([0-9]{4}-[0-9]{2}-[0-9]{2})") { $vcVer = $Matches[1] } } catch {} }
$vcSt = "FAIL"; if ($vcVer) { $vcSt = "PASS" }
Add-Check "tool.vcpkg" "vcpkg on PATH" $vcSt "vcpkg present" $(if ($vcVer) { $vcVer } else { "not found" }) ""
$tripletFile = ""; if (-not [string]::IsNullOrWhiteSpace($vcRoot)) { $tripletFile = Join-Path $vcRoot "triplets\x86-windows-static.cmake" }
$trOk = $false; if ($tripletFile -and (Test-Path -LiteralPath $tripletFile)) { $trOk = $true }
$trSt = "FAIL"; if ($trOk) { $trSt = "PASS" }
Add-Check "tool.vcpkg_triplet" "vcpkg triplet x86-windows-static available" $trSt "x86-windows-static" $(if ($trOk) { "present" } else { "not found" }) $tripletFile
$sslHeader = ""; $sslVer = $null
if (-not [string]::IsNullOrWhiteSpace($vcRoot)) {
    $sslHeader = Join-Path $vcRoot "installed\x86-windows-static\include\openssl\ssl.h"
    if (Test-Path -LiteralPath $sslHeader) { try { $l0 = Get-Content -LiteralPath $sslHeader -ErrorAction Stop | Select-String "OPENSSL_VERSION_TEXT" | Select-Object -First 1; if ($l0) { $sslVer = $l0.Line.Trim() } } catch {} } }
$sslOk = $false; if ($sslHeader -and (Test-Path -LiteralPath $sslHeader)) { $sslOk = $true }
$sslState = "not found"; if ($sslOk) { $sslState = "header present"; if ($sslVer) { $sslState = $sslVer } }
$sslSt = "FAIL"; if ($sslOk) { $sslSt = "PASS" }
Add-Check "tool.openssl" "OpenSSL present for x86-windows-static" $sslSt "installed x86-windows-static OpenSSL" $sslState $sslHeader
$pf86 = [Environment]::GetEnvironmentVariable("ProgramFiles(x86)")
$vswhere = ""; if ($pf86) { $vswhere = Join-Path $pf86 "Microsoft Visual Studio\Installer\vswhere.exe" }
$vsOk = $false; if ($vswhere -and (Test-Path -LiteralPath $vswhere)) { $vsOk = $true }
$vsSt = "FAIL"; if ($vsOk) { $vsSt = "PASS" }
Add-Check "tool.vswhere" "vswhere present (Visual Studio installed)" $vsSt "present" $(if ($vsOk) { $vswhere } else { "not found" }) ""
foreach ($t in @("cmake", "ninja")) {
    $tp = Test-CommandExists $t
    Add-Check ("tool." + $t) ($t + " on PATH (not required by this project)") "INFO" "informational" $(if ($tp) { "present" } else { "absent" }) "" }
$pk = Test-CommandExists "pktmon"
$pkSt = "WARN"; if ($pk) { $pkSt = "PASS" }
Add-Check "tool.pktmon" "pktmon available for packet capture" $pkSt "pktmon" $(if ($pk) { $pk } else { "not found" }) ""

function Check-Status { param([string]$Id) $c = $script:Checks | Where-Object { $_.id -eq $Id }; if ($null -eq $c) { return "SKIP" }; return $c.status }
$clientHashOk = ((Check-Status "client.sha256") -eq "PASS")
$assetsOk = (((Check-Status "game.map_ff") -eq "PASS") -and ((Check-Status "game.map_headers") -eq "PASS") -and ((Check-Status "game.map_sizes") -eq "PASS") -and ((Check-Status "game.map_hashes") -eq "PASS") -and ((Check-Status "game.map_completeness") -eq "PASS") -and ((Check-Status "game.build_association") -eq "PASS"))
$toolchainOk = (((Check-Status "tool.cl") -eq "PASS") -and ((Check-Status "tool.cl_version") -eq "PASS") -and ((Check-Status "tool.cl_arch") -eq "PASS") -and ((Check-Status "tool.xmake") -eq "PASS") -and ((Check-Status "tool.xmake_version") -eq "PASS") -and ((Check-Status "tool.vcpkg") -eq "PASS") -and ((Check-Status "tool.vcpkg_root") -eq "PASS") -and ((Check-Status "tool.vcpkg_triplet") -eq "PASS") -and ((Check-Status "tool.openssl") -eq "PASS"))
$tokens = [ordered]@{
    CLIENT_HASH_VERIFIED          = $clientHashOk
    ASSET_SET_VERIFIED            = $assetsOk
    TOOLCHAIN_READY               = $toolchainOk
    BUILD_CONFIRMED               = $false
    PROTOCOL_TESTS_PASSED         = $false
    CLIENT_CONNECT_CONFIRMED      = $false
    GAMESTATE_ACCEPTED_CONFIRMED  = $false
    WORLD_SPAWN_CONFIRMED         = $false
    SNAPSHOT_FLOW_CONFIRMED       = $false
    TWO_CLIENT_GAMEPLAY_CONFIRMED = $false }
$blockers = @($script:Checks | Where-Object { $_.status -eq "FAIL" } | ForEach-Object { "$($_.id): expected $($_.expected), got $($_.actual)" })
$verdict = "BLOCKED"; if ($clientHashOk -and $assetsOk -and $toolchainOk) { $verdict = "READY_TO_BUILD" }
$missingEvidence = @($script:Checks | Where-Object { ($_.id -like "game.*" -or $_.id -like "tool.*") -and $_.status -eq "FAIL" } | ForEach-Object { $_.id })
$assetEvidence = [ordered]@{
    mapCandidateCount = $mapCandidates.Count
    associationDeclaration = $ExpectedAssetBuildAssociation
    requiredMapFastfiles = @($RequiredMapFastfiles)
    minMapFastfileBytes = $MinMapFastfileBytes
    missingEvidence = $missingEvidence }
$toolchainEvidence = [ordered]@{ msvcVersion = $clVer; msvcArch = $clArch; xmakeVersion = $xmVer; vcpkgVersion = $vcVer; vcpkgRoot = $vcRoot; triplet = "x86-windows-static"; openssl = $sslVer }

$results = [ordered]@{
    checks = $script:Checks
    tokens = $tokens
    verdict = $verdict
    blockerCount = $blockers.Count
    blockers = $blockers
    assetEvidence = $assetEvidence
    toolchainEvidence = $toolchainEvidence
    mapFastfileManifest = $script:MapManifest }
$report = [ordered]@{
    schemaVersion = 2
    kind = "codol-preflight"
    reproducibility = [ordered]@{
        byteReproducible = @("results")
        runMetadataOnly = @("runMetadata")
        method = "Two runs with identical arguments and an identical filesystem produce a byte-identical results object. runMetadata necessarily differs because it carries a timestamp and host identity." }
    runMetadata = [ordered]@{
        generatedAt = $runGeneratedAt
        host = [ordered]@{ computerName = $env:COMPUTERNAME; os = [System.Environment]::OSVersion.VersionString; psVersion = $PSVersionTable.PSVersion.ToString() }
        inputs = [ordered]@{ repoPath = $repoFull; clientPath = $ClientPath; gamePath = $GamePath; expectedClientSha256 = $ExpectedClientSha256; expectedAssetBuildAssociation = $ExpectedAssetBuildAssociation; requiredMapFastfiles = @($RequiredMapFastfiles) } }
    note = "BUILD_CONFIRMED and every runtime token are always false here: they require an actual build, actual test execution and an actual session. A PASS in this report is never a claim that the server works."
    results = $results }
$crlf = [string][char]13 + [string][char]10
$json = ($report | ConvertTo-Json -Depth 12).Replace($crlf, [string][char]10)
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($OutFile), $json, $utf8NoBom)
if (-not [string]::IsNullOrWhiteSpace($StableOut)) {
    $stable = ($results | ConvertTo-Json -Depth 12).Replace($crlf, [string][char]10)
    [System.IO.File]::WriteAllText([System.IO.Path]::GetFullPath($StableOut), $stable, $utf8NoBom) }

Write-Host "=== codol-preflight (schemaVersion 2) ==="
foreach ($c in $script:Checks) { Write-Host ("{0,-6} {1,-58} {2}" -f $c.status, $c.name, $c.actual) }
Write-Host ""
Write-Host ("VERDICT : " + $verdict)
Write-Host ("BLOCKERS: " + $blockers.Count)
foreach ($b in $blockers) { Write-Host ("  - " + $b) }
Write-Host ("REPORT  : " + [System.IO.Path]::GetFullPath($OutFile))
if ($verdict -eq "READY_TO_BUILD") { exit 0 } else { exit 1 }
