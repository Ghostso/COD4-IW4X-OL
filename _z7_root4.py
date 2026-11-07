# -*- coding: utf-8 -*-
import subprocess
ps = r'''
$p = "HKLM:\SOFTWARE\Microsoft\SystemCertificates\Root\Certificates"
"--- HKLM Root subkeys ---"
$ks = Get-ChildItem $p -ErrorAction SilentlyContinue
"count = " + @($ks).Count
$target = "84CAEFFBB8E63F5146D4DB72849491267772B920"
$hit = $null
foreach ($k in $ks) {
  if ($k.PSChildName -eq $target) { $hit = $k.PSChildName }
}
if ($hit) { "THUMBPRINT FOUND IN HKLM ROOT: $hit" } else { "THUMBPRINT NOT FOUND IN HKLM ROOT" }
"--- HKCU Root ---"
$q = "HKCU:\SOFTWARE\Microsoft\SystemCertificates\Root\Certificates"
$kh = Get-ChildItem $q -ErrorAction SilentlyContinue
"count = " + @($kh).Count
if ($kh) { foreach ($k in $kh) { if ($k.PSChildName -eq $target) { "FOUND IN HKCU: " + $k.PSChildName } } }
'''
r = subprocess.run(["powershell","-NoProfile","-Command",ps], capture_output=True)
print(r.stdout.decode("utf-8","replace"))
print("ERR:", r.stderr.decode("utf-8","replace")[:300])
