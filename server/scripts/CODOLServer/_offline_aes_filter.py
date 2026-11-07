#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Filter offline AES hits by how many of the 9 packets they satisfy."""

import json
import os


def main():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     '_offline_aes_hits.jsonl')
    rows = [json.loads(l) for l in open(p, encoding='utf-8')]
    rows.sort(key=lambda r: -r.get('confirmed', 0))
    print('total', len(rows))
    from collections import Counter
    print('confirmed histogram', Counter(r.get('confirmed', 0) for r in rows))
    for r in rows[:30]:
        print(r)


if __name__ == '__main__':
    main()
