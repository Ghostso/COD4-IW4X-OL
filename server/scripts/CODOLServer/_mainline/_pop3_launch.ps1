$ErrorActionPreference = 'Stop'
# Derive the project root from this script's own path so the file stays pure ASCII
# (PowerShell 5.1 reads .ps1 as GBK, so a literal CJK path here would be mangled).
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent (Split-Path -Parent $here)
$out  = Join-Path $root 'CODOLServer\_mainline\_pop3_agent.log'
$last = Join-Path $root 'CODOLServer\_mainline\_pop3_agent_last.txt'
$task = Join-Path $root 'CODOLServer\_mainline\_pop3_task.txt'
$node = 'C:\Program Files\nodejs\node.exe'
$js   = 'C:\Users\Z7-CT5N1\AppData\Roaming\npm\node_modules\@openai\codex\bin\codex.js'

$prompt = [System.IO.File]::ReadAllText($task, [System.Text.Encoding]::UTF8)

$err = $out -replace '\.log$', '.err.log'
$argList = @(
    '"' + $js + '"', 'exec',
    '-m', 'deepseek-v4.1-flash',
    '-s', 'danger-full-access',
    '-C', '"' + $root + '"',
    '--skip-git-repo-check',
    '--json',
    '-o', '"' + $last + '"',
    '-'
)
# Start-Process redirects the prompt file byte-for-byte, avoiding the
# stdin encoder that previously corrupted the UTF-8 CJK prompt.
Start-Process -FilePath $node -ArgumentList $argList `
    -RedirectStandardInput $task -RedirectStandardOutput $out -RedirectStandardError $err `
    -WindowStyle Hidden -Wait
