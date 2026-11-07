#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Probe 2: exact byte layout of the ticket/iv_seed constant cluster and the
qos_cs / qos_ss compact tables (read-only, from hits.jsonl).
"""

import json
import os
import struct

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HITS = os.path.join(ROOT, 'run_codol_001', 'runs', 'EARLY_HANDLE_SCAN',
                    'hits.jsonl')


def load():
    out = []
    for line in open(HITS, encoding='utf-8', errors='replace'):
        try:
            out.append(json.loads(line))
        except ValueError:
            pass
    return out


def hexwin(h, va, text, pre=32, post=48):
    """Reconstruct absolute hex around a hit without needing the live process."""
    return None


def main():
    hs = load()
    print('total hits', len(hs))

    # The ticket cluster: VAs 0x00D5A0EC .. 0x00D5A333. Extend 96 bytes back.
    print('')
    print('=== ticket / iv_seed / cd_key cluster (0x00D5A0EC .. 0x00D5A333) ===')
    for h in hs:
        va = h.get('va', 0)
        if 0x00D5A000 <= va <= 0x00D5A400:
            print('VA 0x%08X kw=%-8s protect=%s' % (va, h.get('kw'), h.get('protect')))
            print('   %r' % h.get('text'))
            print('   asc: %s' % ''.join(
                c if 32 <= ord(c) < 127 else '.' for c in h.get('text', '')))

    # Look for the DW-Ti... continuation right after iv_seed block
    print('')
    print('=== hits mentioning DW-Ti / demonware / blaze near that VA range ===')
    for h in hs:
        t = h.get('text', '')
        if 'DW-' in t or 'demonware' in t.lower() or 'blaze' in t.lower():
            print('VA 0x%08X %r' % (h.get('va', 0), t[:160]))

    # qos_cs / qos_ss compact tables
    print('')
    print('=== qos_cs / qos_ss tables ===')
    for h in hs:
        t = h.get('text', '')
        if 'qos_cs' in t or 'qos_ss' in t:
            va = h.get('va', 0)
            print('VA 0x%08X protect=%s' % (va, h.get('protect')))
            print('   %r' % t)
            # find offset of the literal inside
            i = t.find('qos_cs')
            if i < 0:
                i = t.find('qos_ss')
            print('   literal at +%d ; preceding bytes = %s'
                  % (i, t[max(0, i - 40):i].encode('utf-8', 'replace').hex()))
            print('   following 64 bytes = %r' % t[i:i + 64])

    # Any other small hex constants near the QoS area (protect=8 / 2 blobs)
    print('')
    print('=== hits with protect=8 (module-blob style) ===')
    for h in hs:
        if h.get('protect') == 8:
            print('VA 0x%08X kw=%-10s %r' % (h.get('va', 0), h.get('kw'),
                                             h.get('text', '')[:120]))


if __name__ == '__main__':
    main()
