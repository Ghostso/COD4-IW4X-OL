# -*- coding: utf-8 -*-
"""找出是谁在不断重启 codoMP_client_shipRetail.exe。"""
import ctypes
import ctypes.wintypes as wt
import sys

k32 = ctypes.WinDLL("kernel32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
MAX_PATH = 260


def main():
    import subprocess
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process | Where-Object { $_.Name -match "
         "'codoMP|python|cmd|conhost' } | ForEach-Object { "
         "Write-Output ($_.ProcessId.ToString() + '|' + $_.ParentProcessId.ToString() "
         "+ '|' + $_.Name + '|' + $_.CommandLine) }"],
        capture_output=True, text=True, errors="replace").stdout
    for line in out.splitlines():
        if line.strip():
            print(line.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
