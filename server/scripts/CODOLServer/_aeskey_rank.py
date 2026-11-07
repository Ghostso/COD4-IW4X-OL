#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rank AES key candidates by how many of the 9 packets they satisfy."""

import glob
import json
import os
import sys


def main():
    n_expected = None
    rows = []
    targets = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            targets += glob.glob(os.path.join(a, 'aes_key_candidates.jsonl'))
        else:
            targets += glob.glob(a)
    print('targets:', targets)
    for p in targets:
        if True:
            for line in open(p, encoding='utf-8', errors='replace'):
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except ValueError:
                    continue
                conf = r.get('confirmed', r.get('confirmed_packets', 0))
                rows.append((conf, p, r))
                n_expected = max(n_expected or 0, r.get('n_packets', 0) or 0)
    rows.sort(key=lambda x: -x[0])
    print('files scanned, total candidates=%d' % len(rows))
    from collections import Counter
    print('confirmed histogram:', Counter(c for c, _, _ in rows))
    full = [r for c, _, r in rows if c >= 9]
    print('')
    print('candidates decrypting ALL packets:', len(full))
    for r in full[:20]:
        print(r)
    print('')
    print('top 5 by confirmed:')
    for c, p, r in rows[:5]:
        print('  confirmed=%s/%s key=%s va=0x%X src=%s'
              % (c, r.get('n_packets'), r.get('key'), r.get('va', 0),
                 os.path.basename(p)))


if __name__ == '__main__':
    main()
