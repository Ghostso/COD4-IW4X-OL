"""IPv6 DNS pass for the PktMon captures.

The main analyzer only reads IPv4; this pass covers IPv6 DNS (link-local
resolver traffic seen on the capture interface) and writes a JSON fragment.
Pure ASCII source.
"""

from __future__ import annotations

import json
import math
import os
import sys
import hashlib

from scapy.utils import PcapNgReader
from scapy.layers.inet6 import IPv6
from scapy.layers.inet import TCP, UDP
from scapy.layers.dns import DNS, DNSRR
from scapy.packet import Raw


CAPTURES = [
    ("ENTRY_20260925_013045", "run_codol_001/runs/ENTRY_CAPTURE_ELEVATED_20260925_013045/pktmon.pcapng"),
    ("TCLS_DIR_20260924_220810", "run_codol_001/runs/TCLS_DIR_20260924_220810/pktmon.pcapng"),
    ("LOBBY_DEEP_20260924_181441", "run_codol_001/runs/LOBBY_DEEP_20260924_181441/pktmon.pcapng"),
    ("ENTRY_20260924_160326", "run_codol_001/runs/ENTRY_CAPTURE_ELEVATED_20260924_160326/pktmon.pcapng"),
]


def name_of(qname) -> str:
    if qname is None:
        return ""
    if isinstance(qname, bytes):
        return qname.decode("ascii", "replace").rstrip(".")
    return str(qname).rstrip(".")


def rdata_of(rr) -> str:
    try:
        value = rr.rdata
    except Exception:
        return ""
    if isinstance(value, bytes):
        try:
            return value.decode("ascii")
        except Exception:
            return value.hex()
    return str(value)


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    return sum(1 for b in data if 32 <= b < 127 or b in (9, 10, 13)) / len(data)


def entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = {}
    for b in data:
        counts[b] = counts.get(b, 0) + 1
    acc = 0.0
    n = len(data)
    for c in counts.values():
        p = c / n
        acc -= p * math.log2(p)
    return acc


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    repo = os.path.dirname(os.path.dirname(root))
    out = {}
    for tag, rel in CAPTURES:
        path = os.path.normpath(os.path.join(repo, rel))
        ipv6_packets = 0
        dns_packets = 0
        dns_queries_only = 0
        dns_responses_only = 0
        queries = []
        sessions = {}
        reader = PcapNgReader(path)
        try:
            for pkt in reader:
                if IPv6 not in pkt:
                    continue
                ipv6_packets += 1
                if UDP in pkt or TCP in pkt:
                    if UDP in pkt:
                        proto = "udp"
                        sport, dport = int(pkt[UDP].sport), int(pkt[UDP].dport)
                        payload = bytes(pkt[Raw].load) if Raw in pkt else b""
                    else:
                        proto = "tcp"
                        sport, dport = int(pkt[TCP].sport), int(pkt[TCP].dport)
                        payload = bytes(pkt[TCP].payload) if pkt[TCP].payload else b""
                    src = "%s:%d" % (pkt[IPv6].src, sport)
                    dst = "%s:%d" % (pkt[IPv6].dst, dport)
                    key = "%s|%s|%s" % (proto, src, dst)
                    s = sessions.get(key)
                    if s is None:
                        s = {
                            "proto": proto, "src": src, "dst": dst,
                            "packets": 0, "bytes": 0, "payload_bytes": 0,
                            "first": float(pkt.time), "last": float(pkt.time),
                            "samples": [], "sample_hashes": set(),
                        }
                        sessions[key] = s
                    s["packets"] += 1
                    s["bytes"] += len(bytes(pkt))
                    s["payload_bytes"] += len(payload)
                    s["first"] = min(s["first"], float(pkt.time))
                    s["last"] = max(s["last"], float(pkt.time))
                    if payload and len(s["samples"]) < 3:
                        h = hashlib.sha1(payload).hexdigest()
                        if h not in s["sample_hashes"]:
                            s["sample_hashes"].add(h)
                            s["samples"].append({
                                "t": float(pkt.time),
                                "len": len(payload),
                                "hex": payload[:128].hex(),
                            })
                if UDP not in pkt or DNS not in pkt:
                    continue
                dns = pkt[DNS]
                if not int(dns.qdcount or 0):
                    continue
                try:
                    qname = dns.qd.qname
                    qtype = dns.qd.qtype
                except Exception:
                    continue
                dns_packets += 1
                if int(dns.qr or 0):
                    dns_responses_only += 1
                else:
                    dns_queries_only += 1
                answers = []
                if dns.ancount:
                    try:
                        for i in range(int(dns.ancount)):
                            rr = dns.an[i]
                            if isinstance(rr, DNSRR):
                                answers.append({
                                    "type": int(rr.type),
                                    "name": name_of(rr.rrname),
                                    "rdata": rdata_of(rr),
                                })
                    except Exception:
                        pass
                queries.append({
                    "t": float(pkt.time),
                    "src": "%s:%d" % (pkt[IPv6].src, int(pkt[UDP].sport)),
                    "dst": "%s:%d" % (pkt[IPv6].dst, int(pkt[UDP].dport)),
                    "transaction_id": int(dns.id),
                    "qr": int(dns.qr or 0),
                    "name": name_of(qname),
                    "qtype": int(qtype) if qtype is not None else 0,
                    "answers": answers,
                })
        finally:
            reader.close()
        ordered = []
        for s in sessions.values():
            s.pop("sample_hashes", None)
            joined = b"".join(bytes.fromhex(x["hex"]) for x in s["samples"])
            s["printable_ratio"] = round(printable_ratio(joined), 4)
            s["entropy_bits_per_byte"] = round(entropy(joined), 3)
            s["verdict"] = "text/ascii" if s["printable_ratio"] >= 0.9 else (
                "mostly-text" if s["printable_ratio"] >= 0.7 else "binary-structured")
            ordered.append(s)
        ordered.sort(key=lambda x: (x["proto"], x["src"], x["dst"]))
        out[tag] = {
            "ipv6_packets": ipv6_packets,
            "ipv6_dns_packets": dns_packets,
            "ipv6_dns_queries_only": dns_queries_only,
            "ipv6_dns_responses_only": dns_responses_only,
            "queries": queries,
            "sessions": ordered,
        }
        sys.stderr.write("%s ipv6=%d dns=%d\n" % (tag, ipv6_packets, dns_packets))
        sys.stderr.flush()
    path = os.path.join(root, "pcap_dns_ipv6.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)
    sys.stderr.write("wrote %s\n" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
