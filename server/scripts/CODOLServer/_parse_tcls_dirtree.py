import argparse
import os
import re

from scapy.all import IP, TCP, Raw, PcapReader

TARGET_IP = '116.130.229.168'
TARGET_PORT = 10009


def extract_unique_payload(pcapng, want_len=774):
    seen = []
    with PcapReader(pcapng) as pr:
        for pkt in pr:
            if IP not in pkt or TCP not in pkt or Raw not in pkt:
                continue
            ip = pkt[IP]
            tcp = pkt[TCP]
            if ip.src != TARGET_IP or tcp.sport != TARGET_PORT:
                continue
            data = bytes(pkt[Raw].load)
            if len(data) == want_len and data not in seen:
                seen.append(data)
    return seen


def decode_gbk(data):
    try:
        return data.decode('gbk')
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('pcapng')
    ap.add_argument('--out', default='CODOLServer/tcls_dirtree_response.bin')
    args = ap.parse_args()

    payloads = extract_unique_payload(args.pcapng)
    print('unique %d-byte payloads: %d' % (774, len(payloads)))
    if not payloads:
        return

    data = payloads[0]
    with open(args.out, 'wb') as f:
        f.write(data)
    print('wrote', args.out, len(data))
    print('hex head:', data[:64].hex(' '))

    print('\n===== length-prefixed strings (u32 BE) =====')
    found = []
    for i in range(0, len(data) - 4):
        n = int.from_bytes(data[i:i + 4], 'big')
        if 1 <= n <= 200 and i + 4 + n <= len(data):
            raw = data[i + 4:i + 4 + n]
            # accept mostly printable ASCII or valid GBK
            ascii_ok = all(32 <= b < 127 for b in raw)
            gbk = decode_gbk(raw)
            if ascii_ok or (gbk and all(ch.isprintable() or ch in '\r\n\t' for ch in gbk)):
                found.append((i, n, gbk if gbk else raw.decode('ascii', 'replace')))

    for off, n, text in found:
        if n >= 3:
            print('  off=0x%04x len=%-4d %r' % (off, n, text))

    print('\n===== IPv4-looking octets =====')
    text_all = data.decode('latin1', 'ignore')
    for ip in sorted(set(re.findall(r'\b(?:\d{1,3}\.){3}\d{1,3}\b', text_all))):
        print(' ', ip)

    print('\n===== URLs / host:port =====')
    for u in sorted(set(re.findall(rb'[A-Za-z0-9._-]+(?::\d+)?(?:;\d+)?', data))):
        s = u.decode('ascii', 'replace')
        if '.' in s and len(s) >= 6:
            print(' ', s)


if __name__ == '__main__':
    main()
