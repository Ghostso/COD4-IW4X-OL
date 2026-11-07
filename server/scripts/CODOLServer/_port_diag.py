#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Read-only diagnosis of the CODOL harness UDP ports."""

import subprocess


def show(cmd):
    print('=== ' + cmd)
    try:
        o = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        text = o.decode('gbk', 'replace')
    except subprocess.CalledProcessError as exc:
        text = exc.output.decode('gbk', 'replace')
    for line in text.splitlines():
        if any((':' + p) in line or (' ' + p + ' ') in line
               for p in ('8000', '8081', '3074', '28960')):
            print(line)


def main():
    show('netstat -ano')
    show('netsh int ipv4 show excludedportrange protocol=udp')
    show('netsh int ipv4 show excludedportrange protocol=tcp')


if __name__ == '__main__':
    main()
