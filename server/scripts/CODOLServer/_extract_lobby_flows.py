# -*- coding: utf-8 -*-
"""Extract candidate lobby-related flows from the big PktMon pcapng."""

import collections
import os
import struct

from scapy.all import DNS, DNSQR, IP, TCP, UDP, Raw, PcapReader

HERE = os.path.dirname(os.path.abspath(__file__))
PCAP = os.path.join(HERE, '..', 'run_codol_001', 'runs',
                    'ENTRY_CAPTURE_ELEVATED_20260925_013045', 'pktmon.pcapng')
OUT = os.path.join(HERE, '_lobby_flows.txt')

INTEREST = {
    ('101.72.248.61', 80),
    ('101.72.248.61', 443),
    ('121.29.3.105', 443),
    ('116.130.224.66', 8000),
    ('61.241.53.221', 80),
}


def ascii_dump(data):
    return ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)


def main():
    conv = collections.Counter()
    dns = []
    flows = collections.defaultdict(list)   # key -> [(src,sport,dst,dport,payload)]
    total = 0

    with PcapReader(PCAP) as pr:
        for pkt in pr:
            total += 1
            if IP not in pkt:
                continue
            ip = pkt[IP]
            if UDP in pkt:
                u = pkt[UDP]
                if (u.sport == 53 or u.dport == 53) and DNS in pkt:
                    try:
                        d = pkt[DNS]
                        if d.qd is not None and d.qd.qname:
                            dns.append((ip.src, ip.dst, d.qd.qname.decode('ascii', 'replace')))
                    except Exception:
                        pass
                key = (ip.src, ip.dst, 'udp', u.sport, u.dport)
                conv[key] += 1
                # normalise key to remote endpoint for interest matching
                other = ip.dst if ip.src != '192.168.5.11' else ip.src
                port = u.dport if ip.dst != '192.168.5.11' else u.sport
                if (other, port) in INTEREST:
                    payload = bytes(pkt[Raw].load) if Raw in pkt else b''
                    flows[('udp', other, port)].append(
                        (ip.src, u.sport, ip.dst, u.dport, payload))
            elif TCP in pkt:
                t = pkt[TCP]
                key = (ip.src, ip.dst, 'tcp', t.sport, t.dport)
                conv[key] += 1
                other = ip.dst if ip.src != '192.168.5.11' else ip.src
                port = t.dport if ip.dst != '192.168.5.11' else t.sport
                if (other, port) in INTEREST:
                    payload = bytes(pkt[Raw].load) if Raw in pkt else b''
                    flows[('tcp', other, port)].append(
                        (ip.src, t.sport, ip.dst, t.dport, payload))

    lines = []
    lines.append('packets total: %d' % total)
    lines.append('')
    lines.append('== DNS queries (first 200) ==')
    seen = set()
    for src, dst, name in dns:
        if name in seen:
            continue
        seen.add(name)
        lines.append('  %s -> %s  %s' % (src, dst, name))
    lines.append('')
    lines.append('== interesting flows ==')
    for key in sorted(flows):
        rows = flows[key]
        lines.append('')
        lines.append('### %s %s:%s  packets=%d' % (key[0], key[1], key[2], len(rows)))
        # unique payloads
        uniq = []
        for row in rows:
            p = row[4]
            if p and p not in [x[4] for x in uniq]:
                uniq.append(row)
        for src, sport, dst, dport, p in uniq[:12]:
            lines.append('  %s:%s -> %s:%s len=%d' % (src, sport, dst, dport, len(p)))
            for off in range(0, min(len(p), 320), 32):
                chunk = p[off:off + 32]
                lines.append('    %04x  %-95s  %s' % (
                    off, ' '.join('%02x' % b for b in chunk), ascii_dump(chunk)))
    lines.append('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(OUT)
    print('\n'.join(lines[:120]))


if __name__ == '__main__':
    main()
