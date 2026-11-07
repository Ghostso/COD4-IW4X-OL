"""Merge the IPv6 DNS pass and the AFD-derived process attribution into the
final pcap_report.md / pcap_sessions.json. Pure ASCII source.

Attribution facts below are quoted from per-run AFD ETW logs that already
exist in the repository (file paths are listed in the report).
"""

from __future__ import annotations

import json
import os
import sys


def fmt_ts(ts):
    import time
    if ts is None:
        return "n/a"
    return time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) + ".%03d" % int((ts % 1) * 1000)


ATTRIBUTION = [
    {
        "capture": "ENTRY_20260925_013045",
        "pid": 14220,
        "process": "codoMP_client_shipRetail.exe (game client; from the run's game_etw.jsonl)",
        "endpoint": "116.130.224.66:8000/udp",
        "local_port": 60904,
        "evidence": "run_codol_001/runs/ENTRY_CAPTURE_ELEVATED_20260925_013045/game_etw.jsonl",
        "connect_wall": "2026-09-25T01:31:05.924014500+08:00",
        "pktmon_first_packet": "2026-09-25 01:31:05.924",
        "packets": 8,
        "bytes": 528,
        "payload_bytes": 192,
        "request_hex": "75720010000800030000000b000008220000006400180000",
        "request_len": 24,
        "response_len": 73,
    },
    {
        "capture": "TCLS_DIR_20260924_220810",
        "pid": 18076,
        "process": "TCLS chain (tcls_core/tclshost family; from all_etw.jsonl and afd_tcls.xml)",
        "endpoint": "116.130.224.66:8000/udp",
        "local_port": 58301,
        "evidence": "run_codol_001/runs/TCLS_DIR_20260924_220810/all_etw.jsonl",
        "connect_wall": "2026-09-24T22:08:11.459383500+08:00",
        "pktmon_first_packet": "2026-09-24 22:08:11.480",
        "packets": 88,
        "bytes": 35808,
        "payload_bytes": 32112,
        "request_hex": "7572001001aa00050000000b00006cd600000000000000010000000001000000000100000b5900000000000000020000001000060006000123f184214dd80000241000000b59ffffffff0000000000000000000000000000001d0000000000000001000000000000000000003d6c000020210000000a00000043643439333930",
        "request_len": 442,
        "response_len": 73,
    },
    {
        "capture": "LOBBY_DEEP_20260924_181441",
        "pid": 12696,
        "process": "codoMP_client_shipRetail.exe (game client; from the run's game_etw.jsonl)",
        "endpoint": "116.130.224.66:8000/udp",
        "local_port": 52053,
        "evidence": "run_codol_001/runs/LOBBY_DEEP_20260924_181441/game_etw.jsonl",
        "connect_wall": "2026-09-24T18:15:03.411337800+08:00",
        "pktmon_first_packet": "2026-09-24 18:15:03.411",
        "packets": 8,
        "bytes": 528,
        "payload_bytes": 192,
        "request_hex": "75720010000800030000000b00003a680000006400180000",
        "request_len": 24,
        "response_len": 73,
    },
    {
        "capture": "ENTRY_20260924_160326",
        "pid": 19040,
        "process": "codoMP_client_shipRetail.exe (game client; from the run's game_etw.jsonl)",
        "endpoint": "116.130.224.66:8000/udp",
        "local_port": 58504,
        "evidence": "run_codol_001/runs/ENTRY_CAPTURE_ELEVATED_20260924_160326/game_etw.jsonl",
        "connect_wall": "2026-09-24T16:03:46.113234200+08:00",
        "pktmon_first_packet": "2026-09-24 16:03:46.113",
        "packets": 8,
        "bytes": 528,
        "payload_bytes": 192,
        "request_hex": "75720010000800030000000b000055ed0000006400180000",
        "request_len": 24,
        "response_len": 73,
    },
]

ATTRIBUTION_NOTE = (
    "pid  AFD ETW bind 0.0.0.0:<local_port>  connect "
    "116.130.224.66:8000  Endpoint pcapng  pcapng "
)


def summarize(capture: dict, v6: dict) -> dict:
    sessions = capture["sessions"]
    hot = {}
    for port in (8000, 8080, 8081, 10009, 3074, 27015):
        hits = [s for s in sessions if s["dst_port"] == port or s["src_port"] == port]
        hot[str(port)] = {
            "sessions": len(hits),
            "packets": sum(s["packets"] for s in hits),
            "bytes": sum(s["bytes"] for s in hits),
            "payload_bytes": sum(s["payload_bytes"] for s in hits),
            "verdicts": sorted({s["verdict"] for s in hits}),
            "peers": sorted({(s["src"], s["dst"]) for s in hits})[:20],
        }
    internal = {"dst_ip": "116.130.224.66", "dst_port": 8000}
    tqos = [s for s in sessions if s["dst_ip"] == internal["dst_ip"] and s["dst_port"] == internal["dst_port"]]
    return {
        "hot_ports": hot,
        "tqos_8000": {
            "sessions": len(tqos),
            "packets": sum(s["packets"] for s in tqos),
            "bytes": sum(s["bytes"] for s in tqos),
            "samples": [
                {"src": s["src"], "dst": s["dst"], "packets": s["packets"],
                 "first": s["first"], "samples": s["samples"]}
                for s in tqos
            ],
        },
        "ipv6_dns": {
            "ipv6_packets": v6.get("ipv6_packets"),
            "dns_packets": v6.get("ipv6_dns_packets"),
            "queries_only": v6.get("ipv6_dns_queries_only"),
            "responses_only": v6.get("ipv6_dns_responses_only"),
            "queries_in_file": "pcap_dns_ipv6.json",
        },
    }


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    json_path = os.path.join(root, "pcap_sessions.json")
    v6_path = os.path.join(root, "pcap_dns_ipv6.json")
    with open(json_path, encoding="utf-8") as fh:
        data = json.load(fh)
    with open(v6_path, encoding="utf-8") as fh:
        v6 = json.load(fh)
    for capture in data["captures"]:
        capture["summary"] = summarize(capture, v6.get(capture["capture"], {}))
        capture["ipv6_dns_file"] = "pcap_dns_ipv6.json"
    data["target_attribution"] = ATTRIBUTION
    data["target_attribution_note"] = ATTRIBUTION_NOTE
    data["dns_domain_targets"] = {
        "ied-tqos.qq.com": "seen in ipv6 DNS (capture pcap_dns_ipv6.json), A -> 116.130.224.66",
        "ied-tqos-tgp.qq.com": "seen in ipv6 DNS, A -> 60.29.240.113, 116.130.229.94, 140.207.176.18",
        "tqos.gamesafe.qq.com": "NOT seen as a DNS query in these four captures; the port-8081 peer 122.96.96.225:8081 was labelled tqos.gamesafe.qq.com by the run's own rt_summary_console.txt",
        "stun*.codol.qq.com": "NOT seen; A records present in these captures are for stun.qqlive.qq.com only",
    }
    with open(json_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)

    lines = []
    add = lines.append
    add("")
    add("## 8. /")
    add("")
    add("### 8.1 116.130.224.66:8000")
    add("")
    add(" **UDP** `192.168.5.11` ")
    add("")
    add("|  |  |  |  |  |  | (24B) |")
    add("| --- | ---: | ---: | ---: | ---: | --- | --- |")
    for a in ATTRIBUTION:
        add("| `%s` | %d | %d | %d | %d | %s | `%s` |" % (
            a["capture"], a["local_port"], a["packets"], a["bytes"], a["payload_bytes"],
            a["pktmon_first_packet"], a["request_hex"]))
    add("")
    add(" AFD ETW  pcapng ")
    add("")
    add("|  |  | PID |  | connect  |  |")
    add("| --- | --- | ---: | ---: | --- | --- |")
    for a in ATTRIBUTION:
        add("| `%s` | %s | %d | %d | %s | `%s` |" % (
            a["capture"], a["process"], a["pid"], a["local_port"], a["connect_wall"], a["evidence"]))
    add("")
    add("%s" % ATTRIBUTION_NOTE)
    add("")
    add("`75 72` = `ur` magic `00 10` 2 "
        "`00 05``00 00 00 0b`=11/"
        "EN/LOBBY  24 TCLS  88  UDP  442/371/476/300/259/468 ")
    add("")
    add(" 824B  673B`116.130.224.66:8000 -> 192.168.5.11:<port>`"
        "****/")
    add("")
    add("### 8.2 ied-tqos.qq.com")
    add("")
    add("** IPv6/ DNS **scapy IPv4 ")
    add("")
    add("|  | IPv6  | IPv6 DNS  |  |  |  |")
    add("| --- | ---: | ---: | ---: | --- | --- |")
    for capture in data["captures"]:
        tag = capture["capture"]
        v = v6.get(tag, {})
        add("| `%s` | %s | %s | %s | ied-tqos.qq.com / ied-tqos-tgp.qq.com | A 116.130.224.66 / A 60.29.240.113, 116.130.229.94, 140.207.176.18 |" % (
            tag, v.get("ipv6_packets"), v.get("ipv6_dns_packets"),
            v.get("ipv6_dns_queries_only")))
    add("")
    add("`ied-tqos.qq.com`  `116.130.224.66` 8.1  8000  UDP ")
    add("")
    add("### 8.3 tqos.gamesafe.qq.com")
    add("")
    add(" pcapng  ** tqos.gamesafe.qq.com  DNS **")
    add(" `rt_summary_console.txt`  `122.96.96.225:8081` ")
    add("")
    add("|  | 8081  | 8081  | 8081  |  8081 DNS  |")
    add("| --- | ---: | ---: | ---: | --- |")
    for capture in data["captures"]:
        s = capture["summary"]["hot_ports"]["8081"]
        add("| `%s` | %d | %d | %d |  DNS  |" % (
            capture["capture"], s["sessions"], s["packets"], s["bytes"]))
    add("")
    add("### 8.4 stun*.codol.qq.com")
    add("")
    add("**** STUN  `stun.qqlive.qq.com`IPv6 DNSCNAME  stun-a1.qq.com")
    add(" `stun.au/jp/eu/us.demonware.net` EARLY_HANDLE_SCAN/hits.jsonl")
    add("`stun*.codol.qq.com`  DNS  IP ")
    add("")
    add("## 9. ")
    add("")
    add("|  |  |  |  |  |  |  |")
    add("| --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for capture in data["captures"]:
        for port in ("8000", "8080", "8081", "10009", "3074", "27015"):
            s = capture["summary"]["hot_ports"][port]
            if not s["sessions"]:
                continue
            add("| `%s` | %s | %d | %d | %d | %d | %s |" % (
                capture["capture"], port, s["sessions"], s["packets"], s["bytes"],
                s["payload_bytes"], ", ".join(s["verdicts"])))
    add("")
    add("## 10. IPv6 DNS ")
    add("")
    add("IPv6/ DNS  RR `pcap_dns_ipv6.json`")
    add(" `queries[]`  `qr`0=, 1=`name``answers[]`")
    add("")
    with open(os.path.join(root, "pcap_report.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    sys.stderr.write("report/json finalized\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
