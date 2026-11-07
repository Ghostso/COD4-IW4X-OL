# -*- coding: utf-8 -*-
"""Check whether the WKNet IP pool appears in the lobby capture."""

import collections
import os

from scapy.all import IP, TCP, UDP, PcapReader

HERE = os.path.dirname(os.path.abspath(__file__))
PCAP = os.path.join(HERE, '..', 'run_codol_001', 'runs',
                    'ENTRY_CAPTURE_ELEVATED_20260925_013045', 'pktmon.pcapng')

WK_IPS = {
    '111.13.35.103', '183.192.199.244', '183.232.94.120', '123.151.72.72',
    '101.91.5.226', '183.57.48.31', '111.161.111.175', '116.128.160.92',
    '163.177.89.187', '211.147.81.116', '3.1.47.178', '183.60.58.99',
}


def main():
    hits = collections.Counter()
    ports = collections.Counter()
    with PcapReader(PCAP) as pr:
        for pkt in pr:
            if IP not in pkt:
                continue
            ip = pkt[IP]
            other = None
            if ip.src in WK_IPS:
                other = ip.src
            elif ip.dst in WK_IPS:
                other = ip.dst
            if other is None:
                continue
            if TCP in pkt:
                port = pkt[TCP].dport if ip.dst == other else pkt[TCP].sport
                hits[(other, port, 'tcp')] += 1
            elif UDP in pkt:
                port = pkt[UDP].dport if ip.dst == other else pkt[UDP].sport
                hits[(other, port, 'udp')] += 1
    if not hits:
        print('NO traffic with the WKNet IP pool in this capture')
        return
    for k, v in hits.most_common():
        print(k, v)


if __name__ == '__main__':
    main()
