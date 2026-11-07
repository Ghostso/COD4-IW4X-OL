import re

from scapy.all import IP, TCP, UDP, Raw, PcapReader

PCAP = r"run_codol_001\runs\ENTRY_CAPTURE_ELEVATED_20260924_160326\pktmon.pcapng"


def ascii_dump(data):
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def hexdump(data, width=32):
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        hx = chunk.hex(" ")
        asc = ascii_dump(chunk)
        print("%08x  %-95s  %s" % (off, hx, asc))


def main():
    print("target 42.187.183.162:8080 (UDP) and 42.187.183.203:14309 (TCP)")
    with PcapReader(PCAP) as pr:
        for i, pkt in enumerate(pr, 1):
            if IP not in pkt:
                continue
            ip = pkt[IP]
            hit = False
            proto = ""
            sport = dport = 0
            if UDP in pkt:
                u = pkt[UDP]
                sport, dport = u.sport, u.dport
                if (ip.src == "42.187.183.162" and sport == 8080) or (ip.dst == "42.187.183.162" and dport == 8080):
                    hit = True
                    proto = "UDP"
            if TCP in pkt:
                t = pkt[TCP]
                sport, dport = t.sport, t.dport
                if (ip.src == "42.187.183.203" and sport == 14309) or (ip.dst == "42.187.183.203" and dport == 14309):
                    hit = True
                    proto = "TCP"
            if not hit:
                continue
            data = bytes(pkt[Raw].load) if Raw in pkt else b""
            print("=" * 90)
            print("packet", i, "time", float(pkt.time), proto, ip.src, sport, "->", ip.dst, dport, "payload", len(data))
            if data:
                hexdump(data)


if __name__ == "__main__":
    main()
