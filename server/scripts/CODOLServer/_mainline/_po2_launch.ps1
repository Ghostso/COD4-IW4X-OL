$ErrorActionPreference = 'Stop'
$root = 'D:\BaiduNetdiskDownload\使命召唤OL'
$task = Join-Path $root 'CODOLServer\_mainline\_po2_task.txt'
$node = 'C:\Program Files\nodejs\node.exe'
$js = 'C:\Users\Z7-CT5N1\AppData\Roaming\npm\node_modules\@openai\codex\bin\codex.js'
Get-Content -LiteralPath $task -Raw -Encoding UTF8 |
    & $node $js exec -m deepseek-v4.1-flash -s danger-full-access -C $root --skip-git-repo-check -
