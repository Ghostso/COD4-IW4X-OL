import collections

from scapy.all import IP, UDP, Raw, PcapReader

RUN = r"run_codol_001\runs\LOBBY_DEEP_20260924_181441"
PCAP = RUN + r"\pktmon.pcapng"
PEER = "182.50.14.56"
PORT = 8081


def printable(data):
    return "".join(chr(b) if 32 <= b < 127 else "." for b in data)


def main():
    flows = collections.defaultdict(lambda: {"c2s": bytearray(), "s2c": bytearray(), "n": 0})
    first = {}
    with PcapReader(PCAP) as pr:
        for pkt in pr:
            if IP not in pkt or UDP not in pkt:
                continue
            ip = pkt[IP]
            udp = pkt[UDP]
            if (ip.src == PEER and udp.sport == PORT):
                direction = "s2c"
            elif (ip.dst == PEER and udp.dport == PORT):
                direction = "c2s"
            else:
                continue
            data = bytes(pkt[Raw].load) if Raw in pkt else b""
            key = (ip.src, udp.sport, ip.dst, udp.dport, direction)
            flows[key][direction if direction == "c2s" else "s2c"] += data
            flows[key]["n"] += 1
            first.setdefault((direction, data), float(pkt.time))

    print("flows:", len(flows))
    for k, v in flows.items():
        print("=" * 80)
        print("flow", k, "packets", v["n"], "c2s", len(v["c2s"]), "s2c", len(v["s2c"]))
        for label in ("c2s", "s2c"):
            data = bytes(v[label])
            if not data:
                continue
            print(label, "len", len(data))
            print(label, "hex:", data[:600].hex(" "))
            print(label, "txt:", printable(data[:600]))

    print("\n########## unique datagrams ##########")
    seen = set()
    for (direction, data), t0 in sorted(first.items(), key=lambda kv: kv[1]):
        if data in seen:
            continue
        seen.add(data)
        print("-" * 70)
        print("time", t0, "dir", direction, "len", len(data))
        print("hex:", data.hex(" "))
        print("txt:", printable(data))


if __name__ == "__main__":
    main()
