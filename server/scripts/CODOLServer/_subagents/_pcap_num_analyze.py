"""Streaming numeric analysis of PktMon pcapng captures.

Read-only. Uses scapy's PcapNgReader one packet at a time so multi-hundred
megabyte captures do not blow up memory. Emits:

  pcap_sessions.json          per-capture session table + dns + rst/icmp
  pcap_report.md              Chinese report
  pcap_payloads/<port>.hex    hexdumps of the first packets of key sessions

All source is pure ASCII. Chinese only appears in generated output files.
"""

from __future__ import annotations

import argparse
import collections
import hashlib
import json
import math
import os
import struct
import sys
import time

from scapy.utils import PcapNgReader
from scapy.layers.inet import ICMP, IP, TCP, UDP
from scapy.layers.dns import DNS, DNSQR, DNSRR
from scapy.packet import Raw


CAPTURES = [
    ("ENTRY_20260925_013045", "run_codol_001/runs/ENTRY_CAPTURE_ELEVATED_20260925_013045/pktmon.pcapng"),
    ("TCLS_DIR_20260924_220810", "run_codol_001/runs/TCLS_DIR_20260924_220810/pktmon.pcapng"),
    ("LOBBY_DEEP_20260924_181441", "run_codol_001/runs/LOBBY_DEEP_20260924_181441/pktmon.pcapng"),
    ("ENTRY_20260924_160326", "run_codol_001/runs/ENTRY_CAPTURE_ELEVATED_20260924_160326/pktmon.pcapng"),
]

HOT_PORTS = {8000, 8080, 8081, 10009, 3074, 27015}

MAX_PAYLOAD_SAMPLES = 3
MAX_SAMPLE_BYTES = 128

NOW = "2026-09-25T00:00:00+08:00"


def printable_ratio(data: bytes) -> float:
    if not data:
        return 0.0
    good = sum(1 for b in data if 32 <= b < 127 or b in (9, 10, 13))
    return good / len(data)


def shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    counts = collections.Counter(data)
    total = len(data)
    acc = 0.0
    for c in counts.values():
        p = c / total
        acc -= p * math.log2(p)
    return acc


def classify(payloads: list[bytes]) -> str:
    joined = b"".join(payloads)
    if not joined:
        return "no-payload"
    pr = printable_ratio(joined)
    ent = shannon_entropy(joined[:4096])
    if pr >= 0.90:
        return "text/ascii"
    if pr >= 0.70:
        return "mostly-text"
    if ent >= 7.5:
        return "high-entropy(binary/compressed/encrypted)"
    return "binary-structured"


def hexdump(data: bytes, width: int = 16) -> list[str]:
    out = []
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        hexpart = " ".join("%02x" % b for b in chunk)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append("%06x  %-*s  %s" % (off, width * 3 - 1, hexpart, text))
    return out


def dns_name(name) -> str:
    if name is None:
        return ""
    if isinstance(name, bytes):
        return name.decode("ascii", "replace").rstrip(".")
    return str(name).rstrip(".")


def analyze_capture(tag: str, path: str) -> dict:
    sessions = {}
    dns_queries = []
    dns_answers = collections.defaultdict(set)
    rst_list = []
    icmp_list = []
    total_packets = 0
    ipv4_packets = 0
    tcp_packets = 0
    udp_packets = 0
    other_packets = 0
    first_ts = None
    last_ts = None
    distinct_frames = set()
    duplicate_frames = 0
    malformed = 0

    reader = PcapNgReader(path)
    try:
        for pkt in reader:
            total_packets += 1
            ts = float(pkt.time)
            if first_ts is None or ts < first_ts:
                first_ts = ts
            if last_ts is None or ts > last_ts:
                last_ts = ts
            raw = bytes(pkt)
            digest = hashlib.blake2b(raw, digest_size=16).digest()
            key_dup = (digest, round(ts, 6))
            if key_dup in distinct_frames:
                duplicate_frames += 1
            else:
                distinct_frames.add(key_dup)
            if IP not in pkt:
                other_packets += 1
                continue
            ip = pkt[IP]
            if ip.version != 4:
                other_packets += 1
                continue
            ipv4_packets += 1
            if UDP in pkt:
                udp_packets += 1
                u = pkt[UDP]
                payload = bytes(pkt[Raw].load) if Raw in pkt else b""
                proto = "udp"
                sport, dport = int(u.sport), int(u.dport)
            elif TCP in pkt:
                tcp_packets += 1
                t = pkt[TCP]
                payload = bytes(t.payload) if t.payload else b""
                proto = "tcp"
                sport, dport = int(t.sport), int(t.dport)
            else:
                other_packets += 1
                continue

            src = "%s:%d" % (ip.src, sport)
            dst = "%s:%d" % (ip.dst, dport)
            key = "%s|%s|%s" % (proto, src, dst)
            s = sessions.get(key)
            if s is None:
                s = {
                    "capture": tag,
                    "proto": proto,
                    "src": src,
                    "dst": dst,
                    "src_ip": ip.src,
                    "src_port": sport,
                    "dst_ip": ip.dst,
                    "dst_port": dport,
                    "packets": 0,
                    "bytes": 0,
                    "payload_bytes": 0,
                    "first": ts,
                    "last": ts,
                    "hot_port": dport in HOT_PORTS or sport in HOT_PORTS,
                    "samples": [],
                    "sample_hashes": set(),
                }
                sessions[key] = s
            s["packets"] += 1
            s["bytes"] += len(raw)
            s["payload_bytes"] += len(payload)
            if ts < s["first"]:
                s["first"] = ts
            if ts > s["last"]:
                s["last"] = ts
            if payload and len(s["samples"]) < MAX_PAYLOAD_SAMPLES:
                h = hashlib.sha1(payload).hexdigest()
                if h not in s["sample_hashes"]:
                    s["sample_hashes"].add(h)
                    s["samples"].append({
                        "t": ts,
                        "len": len(payload),
                        "hex": payload[:MAX_SAMPLE_BYTES].hex(),
                    })

            if proto == "udp" and (sport == 53 or dport == 53) and DNS in pkt:
                try:
                    d = pkt[DNS]
                    if d.qd is not None:
                        q = d.qd
                        name = dns_name(q.qname)
                        qtype = int(q.qtype) if q.qtype is not None else 0
                        rec = {
                            "t": ts,
                            "src": src,
                            "dst": dst,
                            "name": name,
                            "qtype": qtype,
                            "answers": [],
                        }
                        an = d.an
                        while an is not None:
                            try:
                                rdata = an.rdata
                            except Exception:
                                rdata = None
                            rec["answers"].append({
                                "type": int(an.type) if an.type is not None else 0,
                                "rdata": str(rdata),
                            })
                            dns_answers[name].add(str(rdata))
                            an = an.payload if isinstance(an.payload, DNSRR) else None
                        dns_queries.append(rec)
                except Exception:
                    malformed += 1

            if proto == "tcp" and TCP in pkt and (pkt[TCP].flags & 0x04):
                rst_list.append({
                    "t": ts,
                    "src": src,
                    "dst": dst,
                    "flags": str(pkt[TCP].flags),
                })

            if ICMP in pkt:
                ic = pkt[ICMP]
                icmp_list.append({
                    "t": ts,
                    "src": "%s" % ip.src,
                    "dst": "%s" % ip.dst,
                    "type": int(ic.type),
                    "code": int(ic.code),
                })

    finally:
        reader.close()

    for s in sessions.values():
        joined = b""
        for sample in s["samples"]:
            joined += bytes.fromhex(sample["hex"])
        s["printable_ratio"] = round(printable_ratio(joined), 4)
        s["entropy_bits_per_byte"] = round(shannon_entropy(joined), 3)
        s["verdict"] = classify([bytes.fromhex(x["hex"]) for x in s["samples"]])
        s.pop("sample_hashes", None)

    ordered = sorted(sessions.values(), key=lambda x: (x["proto"], x["src"], x["dst"]))
    return {
        "capture": tag,
        "path": path,
        "size_bytes": os.path.getsize(path),
        "packets_total": total_packets,
        "frames_distinct_by_time": len(distinct_frames),
        "frames_duplicate_by_time": duplicate_frames,
        "ipv4_packets": ipv4_packets,
        "tcp_packets": tcp_packets,
        "udp_packets": udp_packets,
        "other_packets": other_packets,
        "first_timestamp": first_ts,
        "last_timestamp": last_ts,
        "sessions": ordered,
        "dns_queries": dns_queries,
        "rst_count": len(rst_list),
        "rst": rst_list,
        "icmp_unreachable_count": len(icmp_list),
        "icmp": icmp_list,
        "malformed": malformed,
    }


def fmt_ts(ts):
    if ts is None:
        return "n/a"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) + ".%03d" % int((ts % 1) * 1000)


def render_report(results: list[dict]) -> str:
    lines = []
    add = lines.append
    add("# CODOL ")
    add("")
    add(": `CODOLServer/_subagents/_pcap_num_analyze.py`scapy 2.7.0 + PcapNgReader  rdpcap")
    add("")
    add(":")
    add("")
    add("- PktMon `frames_duplicate_by_time`  ( BLAKE2b, ) ")
    add("-  (, IP:, IP:) ")
    add("- :  3  128 ")
    add("- Asia/Shanghai")
    add("")

    add("## 1. ")
    add("")
    add("|  |  |  |  |  | IPv4 | TCP | UDP |  |  |  |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- | --- |")
    for r in results:
        add("| `%s` | %d | %d | %d | %d | %d | %d | %d | %d | %s | %s |" % (
            r["capture"], r["size_bytes"], r["packets_total"], r["frames_distinct_by_time"],
            r["frames_duplicate_by_time"], r["ipv4_packets"], r["tcp_packets"], r["udp_packets"],
            r["other_packets"], fmt_ts(r["first_timestamp"]), fmt_ts(r["last_timestamp"])))
    add("")

    for r in results:
        add("## 2.%s  `%s`" % ("", r["capture"]))
        add("")
        if not r["sessions"]:
            add("( IPv4 TCP/UDP )")
            add("")
            continue
        add("| # | proto |  |  |  |  |  |  |  |  |  |  |  |")
        add("| ---: | --- | --- | --- | ---: | ---: | ---: | --- | --- | --- | ---: | ---: | --- |")
        for i, s in enumerate(r["sessions"], 1):
            add("| %d | %s | `%s` | `%s` | %d | %d | %d | %s | %s | %s | %.3f | %.3f | %s |" % (
                i, s["proto"], s["src"], s["dst"], s["packets"], s["bytes"], s["payload_bytes"],
                fmt_ts(s["first"]), fmt_ts(s["last"]),
                "YES" if s["hot_port"] else "", s["printable_ratio"],
                s["entropy_bits_per_byte"], s["verdict"]))
        add("")
        hot = [s for s in r["sessions"] if s["hot_port"]]
        add(" (%s):" % (", ".join(str(p) for p in sorted(HOT_PORTS))))
        add("")
        if not hot:
            add("- ")
        for s in hot:
            add("- `%s -> %s` %s =%d =%d =%d =%s =%s =%s" % (
                s["src"], s["dst"], s["proto"], s["packets"], s["bytes"],
                s["payload_bytes"], fmt_ts(s["first"]), fmt_ts(s["last"]), s["verdict"]))
        add("")

    add("## 3. DNS ")
    add("")
    for r in results:
        add("### %s" % r["capture"])
        add("")
        if not r["dns_queries"]:
            add("( DNS )")
            add("")
            continue
        add("|  |  |  |  |  |  |")
        add("| --- | --- | --- | --- | ---: | --- |")
        for q in r["dns_queries"]:
            answers = "; ".join("%s/%s" % (a["type"], a["rdata"]) for a in q["answers"]) or "()"
            add("| %s | `%s` | `%s` | `%s` | %d | %s |" % (
                fmt_ts(q["t"]), q["src"], q["dst"], q["name"], q["qtype"], answers))
        add("")

    add("## 4. TCP RST / ICMP ")
    add("")
    add("|  | TCP RST  | ICMP  |")
    add("| --- | ---: | ---: |")
    for r in results:
        add("| `%s` | %d | %d |" % (r["capture"], r["rst_count"], r["icmp_unreachable_count"]))
    add("")
    for r in results:
        add("### %s" % r["capture"])
        add("")
        add("TCP RST :")
        add("")
        if not r["rst"]:
            add("- ")
        for x in r["rst"]:
            add("- %s `%s -> %s` flags=%s" % (fmt_ts(x["t"]), x["src"], x["dst"], x["flags"]))
        add("")
        add("ICMP :")
        add("")
        if not r["icmp"]:
            add("- ")
        for x in r["icmp"]:
            add("- %s `%s -> %s` type=%d code=%d" % (
                fmt_ts(x["t"]), x["src"], x["dst"], x["type"], x["code"]))
        add("")

    add("## 5. ")
    add("")
    targets = {
        "116.130.224.66:8000": lambda s: s["dst_ip"] == "116.130.224.66" and s["dst_port"] == 8000,
        " IP:8081": lambda s: s["dst_port"] == 8081 or s["src_port"] == 8081,
        " IP:8000": lambda s: s["dst_port"] == 8000 or s["src_port"] == 8000,
        " IP:10009": lambda s: s["dst_port"] == 10009 or s["src_port"] == 10009,
        " IP:3074": lambda s: s["dst_port"] == 3074 or s["src_port"] == 3074,
        " IP:27015": lambda s: s["dst_port"] == 27015 or s["src_port"] == 27015,
    }
    add("|  |  |  |  |  |")
    add("| --- | --- | ---: | ---: | --- |")
    for r in results:
        for label, pred in targets.items():
            matched = [s for s in r["sessions"] if pred(s)]
            pkts = sum(s["packets"] for s in matched)
            note = "" if not matched else "; ".join(
                "%s->%s n=%d first=%s" % (s["src"], s["dst"], s["packets"], fmt_ts(s["first"]))
                for s in matched[:6])
            add("| `%s` | %s | %d | %d | %s |" % (r["capture"], label, len(matched), pkts, note))
    add("")
    add(" ied-tqos.qq.com / tqos.gamesafe.qq.com / stun*.codol.qq.com  DNS :")
    add("")
    for r in results:
        names = sorted({q["name"] for q in r["dns_queries"]})
        hits = [n for n in names if any(k in n.lower() for k in ("tqos", "codol", "gamesafe", "stun"))]
        add("- `%s`: DNS  %d : %s" % (
            r["capture"], len(names), ", ".join(hits) if hits else ""))
    add("")

    add("## 6.  / ")
    add("")
    add("|  |  |  | text/ascii | mostly-text | binary-structured | high-entropy | no-payload |")
    add("| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |")
    for r in results:
        c = collections.Counter(s["verdict"] for s in r["sessions"])
        add("| `%s` | () | %d | %d | %d | %d | %d | %d |" % (
            r["capture"], len(r["sessions"]), c.get("text/ascii", 0), c.get("mostly-text", 0),
            c.get("binary-structured", 0),
            c.get("high-entropy(binary/compressed/encrypted)", 0), c.get("no-payload", 0)))
    add("")
    add("## 7.  3 ")
    add("")
    for r in results:
        add("### %s" % r["capture"])
        add("")
        for s in r["sessions"]:
            if not s["samples"]:
                continue
            add("#### `%s -> %s` (%s)" % (s["src"], s["dst"], s["proto"]))
            add("")
            add("```")
            add("packets=%d bytes=%d payload_bytes=%d printable=%.4f entropy=%.3f verdict=%s" % (
                s["packets"], s["bytes"], s["payload_bytes"], s["printable_ratio"],
                s["entropy_bits_per_byte"], s["verdict"]))
            for i, smp in enumerate(s["samples"], 1):
                add("-- sample %d  t=%s  len=%d --" % (i, fmt_ts(smp["t"]), smp["len"]))
                for hl in hexdump(bytes.fromhex(smp["hex"])):
                    add(hl)
            add("```")
            add("")
    return "\n".join(lines) + "\n"


def write_payload_files(results, root: str) -> list[str]:
    outdir = os.path.join(root, "pcap_payloads")
    os.makedirs(outdir, exist_ok=True)
    written = []
    for r in results:
        base = r["capture"]
        for s in r["sessions"]:
            if not s["samples"]:
                continue
            port = s["dst_port"]
            if not s["hot_port"] and port not in (53, 80, 443):
                continue
            name = "%s_p%d_%s_to_%s.hex" % (base, port, s["src"].replace(":", "-"),
                                            s["dst"].replace(":", "-"))
            path = os.path.join(outdir, name)
            lines = [
                "# capture=%s proto=%s src=%s dst=%s" % (base, s["proto"], s["src"], s["dst"]),
                "# packets=%d bytes=%d payload_bytes=%d printable=%.4f entropy=%.3f verdict=%s" % (
                    s["packets"], s["bytes"], s["payload_bytes"], s["printable_ratio"],
                    s["entropy_bits_per_byte"], s["verdict"]),
            ]
            for i, smp in enumerate(s["samples"], 1):
                lines.append("# sample %d t=%s len=%d" % (i, fmt_ts(smp["t"]), smp["len"]))
                lines.extend(hexdump(bytes.fromhex(smp["hex"])))
            with open(path, "w", encoding="ascii") as fh:
                fh.write("\n".join(lines) + "\n")
            written.append(path)
    return written


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=os.path.dirname(os.path.abspath(__file__)))
    args = ap.parse_args()
    root = args.root
    os.makedirs(root, exist_ok=True)

    results = []
    for tag, rel in CAPTURES:
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), rel)
        path = os.path.normpath(path)
        sys.stderr.write("analyzing %s ...\n" % path)
        sys.stderr.flush()
        results.append(analyze_capture(tag, path))

    payload = {
        "generated": NOW,
        "tool": "scapy 2.7.0 PcapNgReader streaming",
        "captures": results,
    }
    with open(os.path.join(root, "pcap_sessions.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(root, "pcap_report.md"), "w", encoding="utf-8") as fh:
        fh.write(render_report(results))
    written = write_payload_files(results, root)
    sys.stderr.write("wrote %d payload files\n" % len(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
