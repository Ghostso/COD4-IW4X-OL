$ErrorActionPreference='Continue'
$roots=@(
 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\Logs',
 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TimeLog',
 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TenproxyLog',
 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\TGuard',
 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts',
 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\docs',
 'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\_ptrfix'
)
foreach($root in $roots){
  Write-Output "===== $root ====="
  if(Test-Path -LiteralPath $root){
    Get-ChildItem -LiteralPath $root -Recurse -Force -File -ErrorAction SilentlyContinue |
      Sort-Object LastWriteTime -Descending |
      Select-Object -First 100 FullName,Length,LastWriteTime |
      Format-Table -AutoSize | Out-String -Width 300
  } else { Write-Output 'MISSING' }
}
