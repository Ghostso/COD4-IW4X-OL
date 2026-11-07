import collections
import re

from scapy.all import IP, TCP, Raw, PcapReader

PCAP = r"run_codol_001\runs\ENTRY_CAPTURE_ELEVATED_20260924_160326\pktmon.pcapng"


def printable(data):
    return "".join(chr(b) if 32 <= b < 127 or b in (9, 10, 13) else "." for b in data)


def main():
    flows = collections.defaultdict(lambda: {"c2s": bytearray(), "s2c": bytearray(), "packets": 0})
    with PcapReader(PCAP) as pr:
        for pkt in pr:
            if IP not in pkt or TCP not in pkt:
                continue
            ip = pkt[IP]
            tcp = pkt[TCP]
            payload = bytes(pkt[Raw].load) if Raw in pkt else b""
            k = (ip.src, tcp.sport, ip.dst, tcp.dport)
            rev = (ip.dst, tcp.dport, ip.src, tcp.sport)
            if k in flows:
                flows[k]["c2s"] += payload
                flows[k]["packets"] += 1
            elif rev in flows:
                flows[rev]["s2c"] += payload
                flows[rev]["packets"] += 1
            else:
                flows[k]["c2s"] += payload
                flows[k]["packets"] += 1

    interesting = []
    for k, v in flows.items():
        blob = bytes(v["c2s"] + v["s2c"])
        score = sum(1 for b in blob if 32 <= b < 127 or b in (9, 10, 13))
        interesting.append((score, k, v))
    interesting.sort(reverse=True)

    print("tcp flows:", len(flows))
    for score, k, v in interesting[:30]:
        print("=" * 70)
        print("flow", k, "packets", v["packets"], "c2s", len(v["c2s"]), "s2c", len(v["s2c"]), "score", score)
        for label in ("c2s", "s2c"):
            data = bytes(v[label])
            if not data:
                continue
            print(label, "hex:", data[:200].hex(" "))
            print(label, "txt:")
            print(printable(data[:4000]))

    print("\n########## target 42.187.183.203:14309 ##########")
    for score, k, v in interesting:
        if "42.187.183.203" in k or 14309 in k:
            print("=" * 70)
            print("flow", k, "packets", v["packets"], "c2s", len(v["c2s"]), "s2c", len(v["s2c"]))
            print("c2s hex:", bytes(v["c2s"]).hex(" "))
            print("c2s txt:\n" + printable(bytes(v["c2s"])))
            print("s2c hex:", bytes(v["s2c"])[:1000].hex(" "))
            print("s2c txt:\n" + printable(bytes(v["s2c"])))


if __name__ == "__main__":
    main()
