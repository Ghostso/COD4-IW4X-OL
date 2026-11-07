"""Extract TCP payloads for the TCLS directory flow from a PktMon pcapng."""

import argparse
import collections

from scapy.all import IP, TCP, Raw, PcapReader

TARGET_IP = '116.130.229.168'
TARGET_PORT = 10009


def ascii_dump(data):
    return ''.join(chr(b) if 32 <= b < 127 else '.' for b in data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pcapng')
    ap.add_argument('--out')
    args = ap.parse_args()

    pkts = []
    with PcapReader(args.pcapng) as pr:
        for pkt in pr:
            if IP not in pkt or TCP not in pkt:
                continue
            ip = pkt[IP]
            tcp = pkt[TCP]
            hit = ((ip.dst == TARGET_IP and tcp.dport == TARGET_PORT) or
                   (ip.src == TARGET_IP and tcp.sport == TARGET_PORT))
            if not hit:
                continue
            payload = bytes(pkt[Raw].load) if Raw in pkt else b''
            pkts.append({
                'time': float(pkt.time),
                'src': ip.src,
                'sport': int(tcp.sport),
                'dst': ip.dst,
                'dport': int(tcp.dport),
                'seq': int(tcp.seq),
                'ack': int(tcp.ack),
                'flags': str(tcp.flags),
                'payload': payload,
            })

    out = []

    def emit(line=''):
        out.append(line)

    emit('target flow: %s:%d' % (TARGET_IP, TARGET_PORT))
    emit('packets: %d' % len(pkts))
    emit('')

    by_flow = collections.defaultdict(list)
    for p in pkts:
        key = (p['src'], p['sport'], p['dst'], p['dport'])
        by_flow[key].append(p)

    for key, rows in sorted(by_flow.items()):
        emit('=' * 96)
        emit('flow %s:%d -> %s:%d  packets=%d' % (
            key[0], key[1], key[2], key[3], len(rows)))
        for p in rows:
            if not p['payload']:
                continue
            emit('-' * 90)
            emit('t=%.6f seq=%u ack=%u flags=%s len=%d' % (
                p['time'], p['seq'], p['ack'], p['flags'], len(p['payload'])))
            data = p['payload']
            for off in range(0, len(data), 32):
                chunk = data[off:off + 32]
                hx = ' '.join('%02x' % b for b in chunk)
                emit('  %04x  %-95s  %s' % (off, hx, ascii_dump(chunk)))

        # Best-effort reassembly by TCP sequence number.
        payload = b''
        for p in sorted(rows, key=lambda r: (r['seq'], r['time'])):
            if p['payload']:
                payload += p['payload']
        if payload:
            emit('')
            emit('reassembled bytes: %d' % len(payload))
            emit('hex: %s' % payload.hex(' '))
            emit('txt: %s' % ascii_dump(payload))

    text = '\n'.join(out)
    print(text)
    if args.out:
        with open(args.out, 'w', encoding='utf-8') as fh:
            fh.write(text)
        print('\n[written] %s' % args.out)


if __name__ == '__main__':
    main()
