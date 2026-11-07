#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""List python/codo processes and parent PIDs (read-only)."""

import subprocess


def main():
    out = subprocess.check_output(
        'wmic process get ProcessId,ParentProcessId,Name,CommandLine /format:csv',
        shell=True)
    for line in out.decode('gbk', 'replace').splitlines():
        low = line.lower()
        if ('python' in low or 'codo' in low or 'elevated' in low
                or 'suspend' in low or 'fake_tqos' in low
                or 'early_handle' in low or 'aes_key' in low
                or 'tqmc' in low or 'iips' in low or 'tp3' in low):
            print(line[:2000])


if __name__ == '__main__':
    main()
