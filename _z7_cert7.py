# -*- coding: utf-8 -*-
import subprocess
ps = r'''
$out = @()
foreach ($store in @("Cert:\LocalMachine\Root","Cert:\CurrentUser\Root")) {
  Get-ChildItem $store -ErrorAction SilentlyContinue | Where-Object { $_.Subject -like "*CODOL*" } | ForEach-Object {
    $out += [pscustomobject]@{ Store=$store; Subject=$_.Subject; Thumbprint=$_.Thumbprint; NotAfter=$_.NotAfter }
  }
}
if ($out.Count -eq 0) { "NO CODOL CA IN ANY ROOT STORE" } else { $out | Format-List | Out-String }
'''
r = subprocess.run(["powershell","-NoProfile","-Command",ps], capture_output=True, text=True)
print(r.stdout); print(r.stderr[:500])
