#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix the local IIPS chain in the run sandbox.

Root cause of [100] / 初始化IIPS错误 8189fec (from iips.dll strings):
    ResourceManagerII::Initialize()
      -> LaunchIIPSHostApp  (/mode iipslaunch)
      -> m_iipsClient.Start() -> "failed to conncet pipe" (IIPSERR_PIPE_INIT)
      -> named pipe  \\.\Pipe\...   keyed by IIPS\\HostPid

The sandbox has an empty IIPS\\HostPid and an iips.ini that enables IIPS with
an unreachable intranet URL (10.231.2.181), so the whole chain fails before any
lobby/GDP traffic.

This tool:
  1. restores iips.ini to the shipped value (enable_iips=0) or a local one
  2. reports the HostPid state
  3. optionally starts IIPSHostApp.exe so it writes its own PID
"""

import argparse
import os
import subprocess
import sys
import time

ROOT = r'D:\BaiduNetdiskDownload\使命召唤OL'
SANDBOX = os.path.join(ROOT, 'run_codol_001', 'sandbox_ifs1_20260923')
REAL = os.path.join(ROOT, 'COD OL')


def read(path):
    try:
        return open(path, 'rb').read()
    except OSError:
        return None


def write(path, data):
    with open(path, 'wb') as fh:
        fh.write(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--enable-iips', type=int, choices=(0, 1), default=0)
    ap.add_argument('--iips-url', default='')
    ap.add_argument('--start-host', action='store_true')
    args = ap.parse_args()

    sb_ini = os.path.join(SANDBOX, 'iips.ini')
    sb_pid = os.path.join(SANDBOX, 'IIPS', 'HostPid')
    real_ini = os.path.join(REAL, 'iips.ini')

    print('sandbox iips.ini   :', (read(sb_ini) or b'').decode('gbk', 'replace').strip())
    print('sandbox HostPid    :', (read(sb_pid) or b'').decode('ascii', 'replace').strip())
    print('original iips.ini  :', (read(real_ini) or b'').decode('gbk', 'replace').strip())

    if args.enable_iips == 0:
        payload = b'enable_iips=0'
    else:
        url = args.iips_url or 'http://127.0.0.1/'
        payload = ('enable_iips=1\r\niips_url="%s"' % url).encode('ascii')
    write(sb_ini, payload)
    print('wrote %s -> %r' % (sb_ini, payload))

    if args.start_host:
        host = os.path.join(SANDBOX, 'IIPS', 'IIPSHostApp.exe')
        if os.path.isfile(host):
            subprocess.Popen([host, '/mode', 'iipslaunch'], cwd=os.path.dirname(host))
            time.sleep(3)
            print('HostPid now:', (read(sb_pid) or b'').decode('ascii', 'replace').strip())
        else:
            print('IIPSHostApp.exe not found at', host)
    return 0


if __name__ == '__main__':
    sys.exit(main())
