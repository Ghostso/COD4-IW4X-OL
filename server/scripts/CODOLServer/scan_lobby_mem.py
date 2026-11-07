# -*- coding: utf-8 -*-
"""Scan a live CODOL game process for lobby/host address evidence.

Run elevated. Usage:
    python scan_lobby_mem.py [pid] [--out FILE]

It searches committed readable regions for:
  - lobby / blaze / demonware dvar names
  - hostname-like tokens (with dots, ending in .com/.net/.cn/.qq.com)
  - IPv4 literals followed by :port
and dumps the surrounding ASCII context so we can see the value assigned to
each name (CoD keeps dvars as name/value strings near each other).
"""

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'COD OL', 'scripts'))

import procmem as PM  # noqa: E402


NAMES = [
    'dwlobbyhost', 'dwlobbyip', 'blazehost', 'blazeip', 'lobbyhost', 'lobbyip',
    'loginserver', 'accountserver', 'matchmakingserver', 'titleserver',
    'onlinegame', 'title_id', 'demonware', 'dwlogon', 'lobby', 'blaze',
    'stun.', 'natserver', 'bdLobby', 'umbrella',
]

HOST_RE = re.compile(rb'[A-Za-z0-9\-]{2,63}(?:\.[A-Za-z0-9\-]{2,63}){1,4}')
IP_RE = re.compile(rb'\b(?:\d{1,3}\.){3}\d{1,3}\b')
IPPORT_RE = re.compile(rb'\b(?:\d{1,3}\.){3}\d{1,3}:\d{1,5}\b')


def interesting_host(s):
    low = s.lower()
    return any(k in low for k in (
        'demonware', 'callofduty', 'activision', 'qq.com', 'blaze', 'lobby',
        'gamesafe', 'tencent', 'stun', 'codo',
    ))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pid', nargs='?', type=int, default=0)
    ap.add_argument('--out', default=os.path.join(HERE, 'lobby_mem_scan.json'))
    args = ap.parse_args()

    pid = args.pid
    if not pid:
        # fall back to scanning the process list via tasklist
        import subprocess
        out = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq codoMP_client_shipRetail.exe',
                              '/FO', 'CSV', '/NH'], capture_output=True, text=True).stdout
        for line in out.splitlines():
            parts = [x.strip('"') for x in line.split('","')]
            if len(parts) >= 2 and parts[1].isdigit():
                pid = int(parts[1])
                break
    if not pid:
        raise SystemExit('game process not found')
    print('scanning pid=%d' % pid, flush=True)

    result = {'pid': pid, 'names': {}, 'hosts': [], 'ipports': [], 'ips': []}

    hits = PM.cmd_scan_multi(pid, [(k, t) for t in NAMES for k in ('ascii', 'utf16')],
                             maxhits=8)
    for key, addrs in hits.items():
        if addrs:
            result['names'][key] = [hex(a) for a in addrs]

    h = PM.k32.OpenProcess(PM.PROCESS_QUERY_INFORMATION | PM.PROCESS_VM_READ, False, pid)
    if not h:
        raise SystemExit('OpenProcess failed: %d' % ctypes.get_last_error())
    try:
        seen_hosts = {}
        seen_ips = {}
        seen_ipports = {}
        for base, size in PM._regions(h):
            data = PM._read(h, base, min(size, 32 * 1024 * 1024))
            if not data:
                continue
            for m in HOST_RE.finditer(data):
                s = m.group()
                if b'.' not in s or len(s) < 6:
                    continue
                if not interesting_host(s.decode('ascii', 'replace')):
                    continue
                key = s.decode('ascii', 'replace')
                if key in seen_hosts:
                    continue
                seen_hosts[key] = base + m.start()
            for m in IPPORT_RE.finditer(data):
                key = m.group().decode('ascii')
                if key in seen_ipports:
                    continue
                seen_ipports[key] = base + m.start()
            for m in IP_RE.finditer(data):
                key = m.group().decode('ascii')
                if key in seen_ips:
                    continue
                seen_ips[key] = base + m.start()
        result['hosts'] = sorted(
            ({'value': k, 'va': hex(v)} for k, v in seen_hosts.items()),
            key=lambda d: d['value'])
        result['ipports'] = sorted(
            ({'value': k, 'va': hex(v)} for k, v in seen_ipports.items()),
            key=lambda d: d['value'])
        result['ips'] = sorted(
            ({'value': k, 'va': hex(v)} for k, v in seen_ips.items()),
            key=lambda d: d['value'])
    finally:
        PM.k32.CloseHandle(h)

    with open(args.out, 'w', encoding='utf-8') as fh:
        json.dump(result, fh, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2)[:8000])
    print('written', args.out)


if __name__ == '__main__':
    main()
