# CODOL 固化启动链快照

本快照只包含启动链，不包含 `COD OL\IIPS` 的 22 GiB 资源，
也不包含游戏本体 junction 目标、历史运行日志或内存转储。

包含：

- `golden/CODOL_VERIFIED_GOLDEN_20261019`：完整 Golden 启动套件。
- `entry/run_frozen_chain_once.py`：单次启动入口。
- `entry/verify_frozen_chain.py`：只读核心校验。
- `entry/harden_frozen_core_acl.ps1`：ACL 加固。
- `sandbox_config/iips.ini`：IIPS 配置。
- `sandbox_config/dwauth.ini`：Auth/大厅配置。
- `sandbox_config/players`：玩家本地文件。
- `ref_manifest/_golden_hashes.json`：保护清单。
- `evidence`：最后成功轮次摘要、postflight、data manifest、
  Auth/Lobby 日志和恢复文档。

自检：

```powershell
$root = $PSScriptRoot
$manifest = Get-Content (Join-Path $root 'BACKUP_MANIFEST.json') -Raw | ConvertFrom-Json
$bad = @()
foreach ($row in $manifest) {
  $path = Join-Path $root ($row.RelativePath -replace '/', '\')
  if (-not (Test-Path -LiteralPath $path)) { $bad += "missing: $($row.RelativePath)"; continue }
  $hash = (Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash
  if ($hash -ne $row.SHA256) { $bad += "hash: $($row.RelativePath)" }
}
if ($bad) { $bad; exit 1 }
'backup OK'
```
