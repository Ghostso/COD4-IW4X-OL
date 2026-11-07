# -*- coding: utf-8 -*-
"""Dump UDP port 8081 payloads (the long-lived server interaction)."""

import collections
import os

from scapy.all import IP, UDP, Raw, PcapReader

HERE = os.path.dirname(os.path.abspath(__file__))
PCAP = os.path.join(HERE, '..', 'run_codol_001', 'runs',
                    'ENTRY_CAPTURE_ELEVATED_20260925_013045', 'pktmon.pcapng')
OUT = os.path.join(HERE, '_flow_8081.txt')


def ascii_dump(data):
    return ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)


def main():
    rows = []
    with PcapReader(PCAP) as pr:
        for pkt in pr:
            if IP not in pkt or UDP not in pkt:
                continue
            ip = pkt[IP]
            u = pkt[UDP]
            if 8081 not in (u.sport, u.dport):
                continue
            if u.sport != 8081 and u.dport != 8081:
                continue
            payload = bytes(pkt[Raw].load) if Raw in pkt else b''
            rows.append((float(pkt.time), ip.src, u.sport, ip.dst, u.dport, payload))

    # group by remote endpoint
    groups = collections.defaultdict(list)
    for row in rows:
        _, src, sport, dst, dport, payload = row
        remote = (dst, dport) if dport == 8081 else (src, sport)
        groups[remote].append(row)

    lines = []
    lines.append('udp/8081 packets=%d endpoints=%d' % (len(rows), len(groups)))
    lines.append('')
    for remote, grows in sorted(groups.items(), key=lambda kv: -len(kv[1])):
        up = [r for r in grows if r[4] == 8081]
        down = [r for r in grows if r[2] == 8081]
        lines.append('=== %s:%s  total=%d  c2s=%d  s2c=%d ===' % (
            remote[0], remote[1], len(grows), len(up), len(down)))
        lines.append('client -> server (unique payloads):')
        seen = []
        for t, src, sport, dst, dport, p in up:
            if not p or p in seen:
                continue
            seen.append(p)
            lines.append('  t=%.3f len=%d' % (t, len(p)))
            for off in range(0, min(len(p), 256), 32):
                ch = p[off:off + 32]
                lines.append('    %04x  %-95s  %s' % (
                    off, ' '.join('%02x' % b for b in ch), ascii_dump(ch)))
            if len(seen) >= 4:
                break
        lines.append('server -> client (unique payloads):')
        seen = []
        for t, src, sport, dst, dport, p in down:
            if not p or p in seen:
                continue
            seen.append(p)
            lines.append('  t=%.3f len=%d' % (t, len(p)))
            for off in range(0, min(len(p), 256), 32):
                ch = p[off:off + 32]
                lines.append('    %04x  %-95s  %s' % (
                    off, ' '.join('%02x' % b for b in ch), ascii_dump(ch)))
            if len(seen) >= 4:
                break
        lines.append('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print('\n'.join(lines[:160]))


if __name__ == '__main__':
    main()
