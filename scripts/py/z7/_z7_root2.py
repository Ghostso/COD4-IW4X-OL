# -*- coding: utf-8 -*-
import subprocess
ps = r'''
$rows = @()
foreach ($s in @("Cert:\LocalMachine\Root","Cert:\CurrentUser\Root")) {
  Get-ChildItem $s -ErrorAction SilentlyContinue | Where-Object { $_.Subject -like "*CODOL*" } | ForEach-Object {
    $rows += ("{0}`t{1}`t{2}" -f $s, $_.Subject, $_.Thumbprint)
  }
}
if ($rows.Count -eq 0) { "NONE" } else { $rows -join "`n" }
'''
r = subprocess.run(["powershell","-NoProfile","-Command",ps], capture_output=True)
print(r.stdout.decode("utf-8","replace"))
print("ERR:", r.stderr.decode("utf-8","replace")[:400])
