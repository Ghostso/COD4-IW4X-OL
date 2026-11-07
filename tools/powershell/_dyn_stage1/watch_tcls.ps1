param(
    [string]$Target = 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TCLS\Client.exe',
    [string]$WorkingDirectory = 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TCLS',
    [string]$LogFile = 'D:\BaiduNetdiskDownload\使命召唤OL\_dyn_stage1\tcls_launch.log',
    [int]$DurationSeconds = 90
)
$ErrorActionPreference = 'Continue'
function W([string]$Text) {
    $line = '{0} {1}' -f (Get-Date).ToString('yyyy-MM-dd HH:mm:ss.fff'), $Text
    $line | Tee-Object -FilePath $LogFile -Append
}
W 'OBSERVER_BEGIN'
W ("TARGET={0}" -f $Target)
W ("WORKDIR={0}" -f $WorkingDirectory)
$before = @(Get-Process -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id)
$p = Start-Process -FilePath $Target -WorkingDirectory $WorkingDirectory -PassThru
W ("CREATE_RETURN PID={0}" -f $p.Id)
$seen = @{}
$deadline = (Get-Date).AddSeconds($DurationSeconds)
do {
    $procs = @(Get-Process -ErrorAction SilentlyContinue | Where-Object { $_.ProcessName -match 'Client|launcher|codoMP|TQMCenter|Tenio|tgp|WeGame|wegame_env|tcls|TPSvc' })
    foreach ($proc in $procs) {
        $id = $proc.Id
        if (-not $seen.ContainsKey($id)) {
            $seen[$id] = $true
            $isNewAfterLaunch = -not ($before -contains $id)
            $cmd = ''
            try { $cmd = (Get-CimInstance Win32_Process -Filter ("ProcessId={0}" -f $id) -ErrorAction Stop).CommandLine } catch { $cmd = '<unavailable>' }
            W ("PROC PID={0} PPID={1} NAME={2} NEW={3} START={4} CMD={5}" -f $id, $proc.Parent.Id, $proc.ProcessName, $isNewAfterLaunch, $proc.StartTime.ToString('yyyy-MM-dd HH:mm:ss.fff'), $cmd)
            try {
                foreach ($m in @($proc.Modules | Sort-Object ModuleName)) {
                    W ("MODULE PID={0} NAME={1} BASE={2} SIZE={3} PATH={4}" -f $id, $m.ModuleName, ('0x{0:X8}' -f [uint32]$m.BaseAddress.ToInt64()), $m.ModuleMemorySize, $m.FileName)
                }
            } catch { W ("MODULE PID={0} ERROR={1}" -f $id, $_.Exception.Message) }
        }
    }
    Start-Sleep -Milliseconds 500
} while ((Get-Date) -lt $deadline)
W 'OBSERVER_END'
