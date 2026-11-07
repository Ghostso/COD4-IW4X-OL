# -*- coding: utf-8 -*-
"""Extract every IP/hostname literal (ASCII + UTF-16LE) from the CODOL binaries."""

import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
OUT = os.path.join(HERE, '_all_hosts.txt')

FILES = [
    os.path.join(PROJECT, 'COD OL', 'codoMP_client_shipRetail.exe'),
    os.path.join(PROJECT, 'COD OL', 'codoMP_client_shipRetailBase.dll'),
    os.path.join(PROJECT, 'COD OL', 'GameRpcs.dll'),
    os.path.join(PROJECT, 'COD OL', 'TenRpcs.dll'),
    os.path.join(PROJECT, 'COD OL', 'TenProxy.dll'),
    os.path.join(PROJECT, 'COD OL', 'GDPLoader.dll'),
    os.path.join(PROJECT, 'COD OL', 'GDPImpl.dll'),
]

IP_RE = re.compile(r'^(?:\d{1,3}\.){3}\d{1,3}(?::\d{1,5})?$')
HOST_RE = re.compile(r'^[A-Za-z0-9][A-Za-z0-9\-\.]{3,80}$')

NOISE = (
    'w3.org', 'microsoft.com', 'digicert.com', 'verisign.com', 'symantec.com',
    'openssl.org', 'zlib.net', 'gnu.org', 'intel.com', 'nvidia.com',
    'khronos.org', 'python.org', 'sourceforge.net', 'schemas.', 'xmlsoap.org',
    'apache.org', 'mozilla.org', 'webkit.org', 'chromium.org', 'google.com',
    'gstatic.com', 'windows.com', 'msdn.com', 'github.com',
)


def ascii_strings(data, n=4):
    for m in re.finditer(rb'[\x20-\x7e]{%d,}' % n, data):
        yield m.start(), m.group().decode('ascii', 'replace')


def utf16_strings(data, n=4):
    for m in re.finditer(rb'(?:[\x20-\x7e]\x00){%d,}' % n, data):
        yield m.start(), m.group().decode('utf-16le', 'replace')


def is_host(s):
    if not HOST_RE.match(s):
        return False
    if '.' not in s:
        return False
    low = s.lower()
    if any(x in low for x in NOISE):
        return False
    if low.endswith(('.dll', '.exe', '.pdb', '.lib', '.obj', '.cpp', '.h')):
        return False
    return True


def main():
    lines = []
    for path in FILES:
        if not os.path.exists(path):
            continue
        data = open(path, 'rb').read()
        name = os.path.basename(path)
        ips = {}
        hosts = {}
        for kind, gen in (('ascii', ascii_strings(data)), ('utf16', utf16_strings(data))):
            for off, s in gen:
                if IP_RE.match(s):
                    ips.setdefault(s, (kind, off))
                elif is_host(s):
                    hosts.setdefault(s, (kind, off))
        lines.append('=' * 100)
        lines.append('FILE %s size=%d' % (name, len(data)))
        lines.append('-- IPs (%d) --' % len(ips))
        for k, v in sorted(ips.items()):
            lines.append('  %-22s %s off=0x%08X' % (k, v[0], v[1]))
        lines.append('-- hosts (%d) --' % len(hosts))
        # prioritise game-related domains
        prio, rest = [], []
        for k, v in sorted(hosts.items()):
            low = k.lower()
            if any(x in low for x in ('qq.com', 'demonware', 'blaze', 'codol',
                                      'callofduty', 'tencent', 'gamesafe', 'stun')):
                prio.append((k, v))
            else:
                rest.append((k, v))
        for k, v in prio:
            lines.append('  [GAME] %-55s %s off=0x%08X' % (k, v[0], v[1]))
        for k, v in rest[:200]:
            lines.append('  %-62s %s off=0x%08X' % (k, v[0], v[1]))
        if len(rest) > 200:
            lines.append('  ... %d more generic hosts (see file)' % (len(rest) - 200))
        lines.append('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(OUT)
    for ln in lines:
        if ln.startswith('FILE') or ln.startswith('-- IP') or ln.startswith('-- hosts') or '[GAME]' in ln:
            print(ln)


if __name__ == '__main__':
    main()
