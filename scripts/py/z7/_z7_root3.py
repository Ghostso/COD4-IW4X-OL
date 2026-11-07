# -*- coding: utf-8 -*-
import subprocess
ps = r'''
foreach ($s in @("Cert:\LocalMachine\Root","Cert:\CurrentUser\Root","Cert:\LocalMachine\CA","Cert:\LocalMachine\TrustedPublisher")) {
  $n = @(Get-ChildItem $s -ErrorAction SilentlyContinue | Where-Object { $_.Subject -like "*CODOL*" }).Count
  "{0} CODOL={1}" -f $s, $n
}
"--- thumbprint search ---"
foreach ($s in @("Cert:\LocalMachine\Root","Cert:\CurrentUser\Root")) {
  Get-ChildItem $s -ErrorAction SilentlyContinue | Where-Object { $_.Thumbprint -eq "84CAEFFBB8E63F5146D4DB72849491267772B920" } | ForEach-Object { "HIT {0} {1}" -f $s, $_.Subject }
}
"--- whoami ---"
whoami
'''
r = subprocess.run(["powershell","-NoProfile","-Command",ps], capture_output=True)
print("=== NON-ELEVATED ===")
print(r.stdout.decode("utf-8","replace"))
