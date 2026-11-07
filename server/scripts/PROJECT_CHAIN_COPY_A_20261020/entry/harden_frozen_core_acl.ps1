param([string]$Root)
$ErrorActionPreference = 'Stop'
$files = @(
  (Join-Path $Root 'CODOL_VERIFIED_GOLDEN_20261019\run_all.py'),
  (Join-Path $Root 'CODOL_VERIFIED_GOLDEN_20261019\nt10.py')
)
$backupDir = Join-Path $Root 'run_codol_001\runs\ACL_BACKUP_20261020'
New-Item -ItemType Directory -Path $backupDir -Force | Out-Null
foreach ($p in $files) {
  if (-not (Test-Path -LiteralPath $p)) { throw "missing protected file: $p" }
  $name = Split-Path -Leaf $p
  $backup = Get-Acl -LiteralPath $p
  $backup | Export-Clixml -LiteralPath (Join-Path $backupDir ($name + '.acl.xml'))
  $acl = Get-Acl -LiteralPath $p
  $acl.SetAccessRuleProtection($true, $false)
  $acl.Access | Where-Object {
    $_.AccessControlType -eq 'Allow' -and
    $_.IdentityReference -ne 'BUILTIN\Administrators' -and
    $_.IdentityReference -ne 'NT AUTHORITY\SYSTEM' -and
    $_.IdentityReference -ne 'BUILTIN\Users'
  } | ForEach-Object { [void]$acl.RemoveAccessRuleSpecific($_) }
  Set-Acl -LiteralPath $p -AclObject $acl
}
