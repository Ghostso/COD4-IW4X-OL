#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import subprocess

for cmd in ('netstat -ano', 'netstat -an'):
    print('===', cmd)
    try:
        o = subprocess.check_output(cmd, shell=True)
        print(o.decode('gbk', 'replace')[:8000])
    except Exception as exc:
        print('ERR', repr(exc))
