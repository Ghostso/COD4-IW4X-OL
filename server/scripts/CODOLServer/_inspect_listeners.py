#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List UDP listeners on the CODOL harness ports and their owning PIDs."""

import re
import subprocess


def main():
    out = subprocess.check_output('netstat -ano', shell=True)
    text = out.decode('gbk', 'replace')
    pids = set()
    for line in text.splitlines():
        if ':8000 ' in line or ':8081 ' in line or ':3074 ' in line \
                or ':28960 ' in line:
            cols = line.split()
            if len(cols) >= 5:
                print(line)
                pids.add(cols[-1])
    print('PIDs:', sorted(pids))
    if pids:
        w = subprocess.check_output(
            'wmic process get ProcessId,Name,CommandLine /format:csv',
            shell=True)
        wtxt = w.decode('gbk', 'replace')
        for line in wtxt.splitlines():
            if any((' ' + p + ' ' in line or ',' + p + ',' in line or
                    line.rstrip().endswith(',' + p)) for p in pids):
                print('PROC', line[:1000])


if __name__ == '__main__':
    main()
