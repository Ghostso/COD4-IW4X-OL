"""Append the full IPv6 DNS aggregate and emit port-named hex files.

This is a one-shot completion pass for the report. Pure ASCII source; the
generated report stays UTF-8.
"""

from __future__ import annotations

import collections
import json
import os
import time


PORTS = ("8000", "8080", "8081", "10009", "3074", "27015")


def fmt_ts(ts):
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) + ".%03d" % int((ts % 1) * 1000)


def hexdump(data: bytes, width: int = 16):
    out = []
    for off in range(0, len(data), width):
        chunk = data[off:off + width]
        hexpart = " ".join("%02x" % b for b in chunk)
        text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        out.append("%06x  %-*s  %s" % (off, width * 3 - 1, hexpart, text))
    return out


def emit_port_files(root: str, sessions: list[dict]) -> int:
    outdir = os.path.join(root, "pcap_payloads")
    os.makedirs(outdir, exist_ok=True)
    count = 0
    for port in PORTS:
        pnum = int(port)
        hits = [s for s in sessions if s["dst_port"] == pnum or s["src_port"] == pnum]
        lines = [
            "# CODOL key-session payload aggregate",
            "# port=%s sessions=%d" % (port, len(hits)),
            "# Each capture/session shows up to 3 distinct payloads, each first 128 bytes.",
            "",
        ]
        if not hits:
            lines.append("(no matching sessions)")
        for s in hits:
            lines.append("## capture=%s proto=%s src=%s dst=%s" % (
                s["capture"], s["proto"], s["src"], s["dst"]))
            lines.append("# packets=%d bytes=%d payload_bytes=%d printable=%.4f entropy=%.3f verdict=%s" % (
                s["packets"], s["bytes"], s["payload_bytes"],
                s["printable_ratio"], s["entropy_bits_per_byte"], s["verdict"]))
            if not s["samples"]:
                lines.append("(no payload samples)")
            for i, smp in enumerate(s["samples"], 1):
                lines.append("# sample %d t=%s len=%d" % (i, fmt_ts(smp["t"]), smp["len"]))
                lines.extend(hexdump(bytes.fromhex(smp["hex"])))
            lines.append("")
        path = os.path.join(outdir, port + ".hex")
        with open(path, "w", encoding="ascii") as fh:
            fh.write("\n".join(lines) + "\n")
        count += 1
    return count


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(root, "pcap_sessions.json"), encoding="utf-8") as fh:
        data = json.load(fh)
    with open(os.path.join(root, "pcap_dns_ipv6.json"), encoding="utf-8") as fh:
        v6 = json.load(fh)

    sessions = []
    for capture in data["captures"]:
        for s in capture["sessions"]:
            row = dict(s)
            row["capture"] = capture["capture"]
            sessions.append(row)
    count = emit_port_files(root, sessions)

    lines = []
    add = lines.append
    add("")
    add("## 11. IPv6 DNS ")
    add("")
    add(" 3  IPv4 DNS `pcap_dns_ipv6.json` "
        " DNS `queries`  PktMon ")
    add("")
    for tag, capture in v6.items():
        queries = collections.Counter()
        answers = collections.defaultdict(set)
        for row in capture["queries"]:
            if row["qr"] == 0:
                queries[row["name"]] += 1
            for ans in row["answers"]:
                if ans["type"] == 1:
                    answers[row["name"]].add(ans["rdata"])
        add("### %s" % tag)
        add("")
        add("|  | queries | A  |")
        add("| --- | ---: | --- |")
        for name in sorted(queries):
            vals = ", ".join(sorted(answers.get(name, set()))) or "( A )"
            add("| `%s` | %d | %s |" % (name, queries[name], vals))
        add("")
    add("### 8081 ")
    add("")
    add(" DNS`tqos.anticheatexpert.com` -> `122.96.96.225`, `182.50.14.56`")
    add(" IP  8081  8081  `tqos.gamesafe.qq.com`")
    add(" `tqos.gamesafe.qq.com`  `tqos.anticheatexpert.com`")
    add("")
    add("###  hex ")
    add("")
    add(" `%d` `%s`" % (
        count, ", ".join("pcap_payloads/%s.hex" % p for p in PORTS)))
    add("")
    with open(os.path.join(root, "pcap_report.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print("wrote %d port files and appended IPv6 DNS aggregate" % count)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
