# -*- coding: utf-8 -*-
"""List every connect() target for one PID from an rt_etw JSONL dump."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, '..', 'run_codol_001', 'runs',
                       'ENTRY_CAPTURE_ELEVATED_20260925_013045', 'all_etw3.jsonl')


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    pid = int(sys.argv[2]) if len(sys.argv) > 2 else 14220
    rows = []
    with open(path, encoding='utf-8', errors='replace') as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except ValueError:
                pass

    targets = []
    sends = []
    for r in rows:
        if r.get('pid') != pid:
            continue
        api = r.get('api')
        addr = r.get('addr') or {}
        if api == 'connect':
            t = (addr.get('addr') or addr.get('ip'), addr.get('port'))
            targets.append((r.get('wall'), t))
        elif api in ('send', 'sendto'):
            sends.append((r.get('wall'), r.get('len'), (addr.get('addr'), addr.get('port')),
                          r.get('hex') or r.get('data')))

    print('pid %d  connect count = %d' % (pid, len(targets)))
    seen = []
    for wall, t in targets:
        if t not in seen:
            seen.append(t)
            print('  %s  %s:%s' % (wall, t[0], t[1]))
    print()
    print('send count = %d' % len(sends))
    for wall, ln, tgt, data in sends[:40]:
        head = ''
        if isinstance(data, str):
            head = data[:64]
        print('  %s len=%s -> %s:%s %s' % (wall, ln, tgt[0], tgt[1], head))


if __name__ == '__main__':
    main()
