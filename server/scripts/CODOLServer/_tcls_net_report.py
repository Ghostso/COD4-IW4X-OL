"""Summarize TCLS-side network activity from an AFD ETW JSONL capture.

Focus: which remote endpoints the TCLS chain talks to, in what order, and with
what byte counts. That identifies the directory servers we must emulate.
"""

import argparse
import collections
import json
import os

TCLS_NAMES = (
    'tcls_core.exe', 'tclshost.exe', 'client.exe', 'clientbase',
    'tgp_daemon.exe', 'rail.exe', 'wegameservice', 'tclshostapp',
)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('jsonl')
    ap.add_argument('--out')
    args = ap.parse_args()

    pid_to_name = {}
    events = []
    with open(args.jsonl, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            pid = rec.get('pid')
            name = rec.get('process') or rec.get('name')
            if pid is not None and name:
                pid_to_name[str(pid)] = name
            events.append(rec)

    out = []

    def emit(text=''):
        out.append(text)

    emit('capture: %s' % args.jsonl)
    emit('events: %d' % len(events))
    emit('')
    emit('=' * 96)
    emit('processes seen with network events')
    emit('=' * 96)
    by_pid = collections.Counter()
    for rec in events:
        if rec.get('pid') is not None:
            by_pid[str(rec['pid'])] += 1
    for pid, count in by_pid.most_common(60):
        emit('  pid=%-8s events=%-7d name=%s' % (pid, count, pid_to_name.get(pid, '?')))

    emit('')
    emit('=' * 96)
    emit('TCLS-chain remote endpoints (connect / sendto / recvfrom)')
    emit('=' * 96)

    def is_tcls(name):
        if not name:
            return False
        low = name.lower()
        return any(k in low for k in TCLS_NAMES)

    flows = collections.defaultdict(lambda: {'n': 0, 'bytes': 0, 'first': None, 'last': None})
    for rec in events:
        pid = rec.get('pid')
        name = pid_to_name.get(str(pid)) if pid is not None else None
        if not is_tcls(name):
            continue
        addr = rec.get('addr') or {}
        ip = addr.get('ip') if isinstance(addr, dict) else None
        port = addr.get('port') if isinstance(addr, dict) else None
        if not ip:
            continue
        if ip.startswith('127.') or ip in ('0.0.0.0', '::', '::1'):
            continue
        api = rec.get('api') or rec.get('op') or ''
        key = (ip, port, api)
        f = flows[key]
        f['n'] += 1
        f['bytes'] += int(rec.get('len') or rec.get('length') or 0)
        ts = rec.get('wall') or rec.get('t')
        if ts is not None:
            if f['first'] is None:
                f['first'] = ts
            f['last'] = ts

    if not flows:
        emit('  (no TCLS-chain external endpoints matched)')
    for (ip, port, api), f in sorted(flows.items(), key=lambda kv: kv[1]['n'], reverse=True):
        emit('  %-18s %-6s %-10s n=%-5d bytes=%-8d first=%s last=%s' % (
            ip, port, api, f['n'], f['bytes'], f['first'], f['last']))

    emit('')
    emit('=' * 96)
    emit('all external endpoints (any process), top 80')
    emit('=' * 96)
    allflows = collections.Counter()
    for rec in events:
        addr = rec.get('addr') or {}
        ip = addr.get('ip') if isinstance(addr, dict) else None
        port = addr.get('port') if isinstance(addr, dict) else None
        if not ip or ip.startswith('127.') or ip in ('0.0.0.0', '::', '::1'):
            continue
        allflows[(ip, port)] += 1
    for (ip, port), n in allflows.most_common(80):
        emit('  %-18s %-6s n=%d' % (ip, port, n))

    text = '\n'.join(out)
    print(text)
    if args.out:
        os.makedirs(os.path.dirname(args.out) or '.', exist_ok=True)
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(text)
        print('\n[written] %s' % args.out)


if __name__ == '__main__':
    main()
