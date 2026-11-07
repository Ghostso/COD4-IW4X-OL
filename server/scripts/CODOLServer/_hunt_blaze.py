# -*- coding: utf-8 -*-
"""Hunt for Blaze/Demonware lobby endpoints in the 92 MB PktMon capture.

Looks for:
  - every DNS query/answer (names -> IPs)
  - every TCP flow that is NOT loopback and NOT the known CDN/ACE set
  - flows whose payload is not HTTP/TLS-looking (Blaze is a binary protocol
    with its own framing), so raw payload bytes are dumped
"""

import collections
import os

from scapy.all import DNS, DNSRR, IP, TCP, UDP, Raw, PcapReader

HERE = os.path.dirname(os.path.abspath(__file__))
PCAP = os.path.join(HERE, '..', 'run_codol_001', 'runs',
                    'ENTRY_CAPTURE_ELEVATED_20260925_013045', 'pktmon.pcapng')
OUT = os.path.join(HERE, '_blaze_hunt.txt')

KNOWN = {
    '101.72.248.61',    # down.qq.com
    '121.29.3.105',     # intldlgs.qq.com
    '61.241.53.221',    # dump.gamesafe.qq.com
    '116.130.224.66',   # ied-tqos.qq.com
    '182.50.14.56',     # tqos
}


def is_local(ip):
    return (ip.startswith('192.168.') or ip.startswith('127.')
            or ip.startswith('10.') or ip.startswith('239.')
            or ip == '0.0.0.0' or ip.startswith('224.'))


def ascii_dump(data):
    return ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)


def main():
    dns_pairs = []
    tcp_flows = collections.defaultdict(list)
    udp_flows = collections.defaultdict(list)
    total = 0

    with PcapReader(PCAP) as pr:
        for pkt in pr:
            total += 1
            if IP not in pkt:
                continue
            ip = pkt[IP]
            if UDP in pkt and DNS in pkt:
                try:
                    d = pkt[DNS]
                    if d.qr == 0 and d.qd is not None and d.qd.qname:
                        dns_pairs.append(('Q', d.qd.qname.decode('ascii', 'replace'), None))
                    if d.qr == 1 and d.an is not None and d.ancount:
                        ans = d.an
                        for i in range(d.ancount):
                            try:
                                rr = ans[i]
                                if isinstance(rr, DNSRR):
                                    nm = rr.rrname.decode('ascii', 'replace')
                                    rd = rr.rdata
                                    if isinstance(rd, bytes):
                                        rd = rd.decode('ascii', 'replace')
                                    dns_pairs.append(('A', nm, str(rd)))
                            except Exception:
                                pass
                except Exception:
                    pass
            if TCP in pkt:
                t = pkt[TCP]
                a, b = ip.src, ip.dst
                if is_local(a) and is_local(b):
                    k = ('loopback', a, t.sport, b, t.dport)
                else:
                    remote = b if is_local(a) else a
                    rport = t.dport if is_local(a) else t.sport
                    k = ('tcp', remote, rport)
                payload = bytes(pkt[Raw].load) if Raw in pkt else b''
                tcp_flows[k].append((a, t.sport, b, t.dport, payload))
            elif UDP in pkt:
                u = pkt[UDP]
                a, b = ip.src, ip.dst
                remote = b if is_local(a) else a
                rport = u.dport if is_local(a) else u.sport
                k = ('udp', remote, rport)
                payload = bytes(pkt[Raw].load) if Raw in pkt else b''
                udp_flows[k].append((a, u.sport, b, u.dport, payload))

    lines = []
    lines.append('packets scanned: %d' % total)
    lines.append('')
    lines.append('== DNS ==')
    seen = set()
    for kind, name, rdata in dns_pairs:
        key = (kind, name, rdata)
        if key in seen:
            continue
        seen.add(key)
        if kind == 'Q':
            lines.append('  Q  %s' % name)
        else:
            lines.append('  A  %-45s -> %s' % (name, rdata))
    lines.append('')

    lines.append('== TCP flows (remote) ==')
    for k in sorted(tcp_flows, key=lambda x: str(x)):
        rows = tcp_flows[k]
        if k[0] == 'loopback':
            continue
        remote, rport = k[1], k[2]
        bob = sum(1 for r in rows if r[4])
        lines.append('')
        lines.append('### %s:%s  packets=%d  payload_pkts=%d  %s' % (
            remote, rport, len(rows), bob, 'KNOWN' if remote in KNOWN else '*** NEW ***'))
        seenp = []
        for src, sport, dst, dport, p in rows:
            if not p:
                continue
            if p in seenp:
                continue
            seenp.append(p)
            lines.append('  %s:%s -> %s:%s len=%d' % (src, sport, dst, dport, len(p)))
            for off in range(0, min(len(p), 384), 32):
                ch = p[off:off + 32]
                lines.append('    %04x  %-95s  %s' % (
                    off, ' '.join('%02x' % b for b in ch), ascii_dump(ch)))
            if len(seenp) >= 6:
                break
    lines.append('')

    lines.append('== UDP flows (remote, non-DNS) ==')
    for k in sorted(udp_flows, key=lambda x: str(x)):
        if k[1] == '0.0.0.0' or k[2] in (53, 1900):
            continue
        rows = udp_flows[k]
        lines.append('  %s:%s packets=%d %s' % (
            k[1], k[2], len(rows), '' if k[1] in KNOWN else '*** NEW ***'))
    lines.append('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    print(OUT)
    print('\n'.join(lines[:150]))


if __name__ == '__main__':
    main()
