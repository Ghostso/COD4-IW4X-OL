"""Merge the IPv6 session aggregates into pcap_sessions.json and append a
short note to the report. Pure ASCII source.
"""

from __future__ import annotations

import json
import os


NOTE = [
    "",
    "## 12. IPv6 会话表说明",
    "",
    "第 2 节的会话表只统计 IPv4（抓包链路层为 IPv4/IPv6 混合）。",
    "IPv6 侧的完整会话表（含包数/字节/载荷样本/熵/判定）在 `pcap_dns_ipv6.json` 的 `sessions[]` 中，",
    "键为抓包名。IPv6 会话全部是 UDP，且绝大多数目标端口是 53（DNS），",
    "另有少量 5353/5355 组播 DNS 与临时端口；IPv6 侧没有任何 TCP 会话。",
    "",
]


def main() -> int:
    root = os.path.dirname(os.path.abspath(__file__))
    jpath = os.path.join(root, "pcap_sessions.json")
    vpath = os.path.join(root, "pcap_dns_ipv6.json")
    with open(jpath, encoding="utf-8") as fh:
        data = json.load(fh)
    with open(vpath, encoding="utf-8") as fh:
        v6 = json.load(fh)
    for capture in data["captures"]:
        entry = v6.get(capture["capture"], {})
        capture["ipv6_sessions_file"] = "pcap_dns_ipv6.json"
        capture["ipv6_session_count"] = len(entry.get("sessions", []))
    data["ipv6_note"] = ("IPv6 sessions are stored in pcap_dns_ipv6.json under sessions[]; "
                         "all are UDP, mostly dst port 53.")
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=1)
    with open(os.path.join(root, "pcap_report.md"), "a", encoding="utf-8") as fh:
        fh.write("\n".join(NOTE) + "\n")
    print("merged ipv6 session counts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
