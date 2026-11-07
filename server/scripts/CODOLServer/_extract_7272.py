# -*- coding: utf-8 -*-
"""Extract and reassemble the 106.55.191.99:7272 long-lived binary flow."""

import os

from scapy.all import IP, TCP, PcapReader

HERE = os.path.dirname(os.path.abspath(__file__))
PCAP = os.path.join(HERE, '..', 'run_codol_001', 'runs',
                    'ENTRY_CAPTURE_ELEVATED_20260925_013045', 'pktmon.pcapng')
TARGET = '106.55.191.99'
PORT = 7272
OUT = os.path.join(HERE, '_flow_7272.txt')


def ascii_dump(data):
    return ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)


def main():
    c2s = []   # (seq, payload)
    s2c = []
    times = []
    with PcapReader(PCAP) as pr:
        for pkt in pr:
            if IP not in pkt or TCP not in pkt:
                continue
            ip = pkt[IP]
            t = pkt[TCP]
            if TARGET not in (ip.src, ip.dst):
                continue
            if PORT not in (t.sport, t.dport):
                continue
            payload = bytes(t.payload) if t.payload else b''
            if ip.dst == TARGET:
                c2s.append((t.seq, payload))
            else:
                s2c.append((t.seq, payload))
            if payload:
                times.append(float(pkt.time))

    def reassemble(rows):
        rows.sort(key=lambda r: r[0])
        out = bytearray()
        expected = None
        for seq, payload in rows:
            if not payload:
                continue
            if expected is None:
                expected = seq
            if seq > expected:
                out.extend(b'\x00' * (seq - expected))
            elif seq < expected:
                payload = payload[expected - seq:]
                seq = expected
            out.extend(payload)
            expected = seq + len(payload)
        return bytes(out)

    up = reassemble(c2s)
    down = reassemble(s2c)

    lines = []
    lines.append('target %s:%d' % (TARGET, PORT))
    lines.append('packets=%d payload_packets=%d' % (len(c2s) + len(s2c), len(times)))
    if times:
        lines.append('first=%.6f last=%.6f duration=%.3fs' % (
            min(times), max(times), max(times) - min(times)))
    lines.append('client->server bytes=%d' % len(up))
    lines.append('server->client bytes=%d' % len(down))
    lines.append('')
    lines.append('=== client -> server (first 2048) ===')
    for off in range(0, min(len(up), 2048), 32):
        ch = up[off:off + 32]
        lines.append('%06x  %-95s  %s' % (off, ' '.join('%02x' % b for b in ch), ascii_dump(ch)))
    lines.append('')
    lines.append('=== server -> client (first 2048) ===')
    for off in range(0, min(len(down), 2048), 32):
        ch = down[off:off + 32]
        lines.append('%06x  %-95s  %s' % (off, ' '.join('%02x' % b for b in ch), ascii_dump(ch)))
    lines.append('')

    with open(OUT, 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(lines) + '\n')
    with open(os.path.join(HERE, '_flow_7272_c2s.bin'), 'wb') as fh:
        fh.write(up)
    with open(os.path.join(HERE, '_flow_7272_s2c.bin'), 'wb') as fh:
        fh.write(down)
    print('\n'.join(lines[:120]))


if __name__ == '__main__':
    main()
