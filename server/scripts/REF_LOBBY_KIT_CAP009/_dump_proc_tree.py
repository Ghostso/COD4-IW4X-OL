# -*- coding: utf-8 -*-
"""打印 python / 游戏 进程树(含命令行), 找出反复拉起游戏的那个。"""
import os
import subprocess
import sys


def main():
    # 用 tasklist + wmic 拿命令行
    out = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "Get-CimInstance Win32_Process -Filter \"Name like '%python%' or "
         "Name like '%codoMP%' or Name like '%nt10%' or Name like '%run_all%'\" | "
         "ForEach-Object { [Console]::WriteLine(('{0}|{1}|{2}|{3}' -f "
         "$_.ProcessId,$_.ParentProcessId,$_.Name,$_.CommandLine)) }"],
        capture_output=True, text=True, errors="replace")
    print("stdout:")
    for line in (out.stdout or "").splitlines():
        if line.strip():
            print("  " + line.strip())
    if out.stderr:
        print("stderr:", out.stderr[:800])
    return 0


if __name__ == "__main__":
    sys.exit(main())
