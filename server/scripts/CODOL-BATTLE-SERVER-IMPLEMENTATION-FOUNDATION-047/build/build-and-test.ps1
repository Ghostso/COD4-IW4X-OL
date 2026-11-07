# CODOL 047 reproducible build + test entry point.
# Writes logs under build/logs and build/test-results. Never touches the client or 040-046.
param(
    [ValidateSet('Release','Debug')]
    [string]$Configuration = 'Release'
)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$stamp = Get-Date -Format 'yyyyMMdd_HHmmss'
$logDir = Join-Path $root 'build\logs'
$resultDir = Join-Path $root 'build\test-results'
New-Item -ItemType Directory -Force -Path $logDir, $resultDir | Out-Null
$buildLog = Join-Path $logDir ("build_$stamp.log")
$testLog = Join-Path $resultDir ("tests_$stamp.log")

Push-Location $root
try {
    Write-Host "== dotnet --version =="
    dotnet --version | Tee-Object -FilePath $buildLog
    Write-Host "== dotnet build ($Configuration) =="
    $buildOutput = dotnet build "CODOL.BattleServer.Foundation.sln" -c $Configuration --nologo 2>&1
    $buildCode = $LASTEXITCODE
    $buildOutput | Tee-Object -FilePath $buildLog -Append
    if ($buildCode -ne 0) { throw "build failed with exit code $buildCode (log: $buildLog)" }

    Write-Host "== dotnet test-runner =="
    $testOutput = dotnet run --project "tests\Codol.BattleServer.Tests\Codol.BattleServer.Tests.csproj" -c $Configuration --no-build 2>&1
    $testCode = $LASTEXITCODE
    $testOutput | Tee-Object -FilePath $testLog
    if ($testCode -ne 0) { throw "tests failed with exit code $testCode (log: $testLog)" }

    $exe = Join-Path $root ("tests\Codol.BattleServer.Tests\bin\$Configuration\net8.0\Codol.BattleServer.Tests.dll")
    $lib = Join-Path $root ("src\Codol.BattleServer\bin\$Configuration\net8.0\Codol.BattleServer.dll")
    $manifest = Join-Path $root 'build\BUILD_MANIFEST.txt'
    @(
        "configuration=$Configuration",
        "built_at=$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
        "dotnet=$(dotnet --version)",
        "test_assembly=$exe",
        "test_assembly_sha256=$((Get-FileHash -Algorithm SHA256 -LiteralPath $exe).Hash)",
        "library_assembly=$lib",
        "library_assembly_sha256=$((Get-FileHash -Algorithm SHA256 -LiteralPath $lib).Hash)",
        "build_log=$buildLog",
        "test_log=$testLog"
    ) | Set-Content -LiteralPath $manifest -Encoding utf8
    Write-Host "BUILD_AND_TEST_OK manifest=$manifest"
}
finally {
    Pop-Location
}
