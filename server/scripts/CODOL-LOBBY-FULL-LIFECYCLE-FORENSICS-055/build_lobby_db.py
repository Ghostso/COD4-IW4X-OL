#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build the machine-readable deliverables for 055 by parsing the real lobby logs."""
import csv
import hashlib
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RUNS = os.path.join(ROOT, "run_codol_001", "runs")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def parse_runs():
    RE = re.compile(r"解密成功 #(\d+) seq=(\d+) .*?service=(\d+) ver=0x(\w+) task=(\d+) declared=(\d+)")
    out = {}
    for d in sorted(os.listdir(RUNS)):
        lg = os.path.join(RUNS, d, "kit", "lobby_srv.log")
        if not os.path.isfile(lg):
            continue
        reqs, ev = [], []
        for ln in open(lg, encoding="utf-8", errors="replace"):
            m = RE.search(ln)
            if m:
                reqs.append({"seq": int(m.group(2)), "service": int(m.group(3)),
                             "task": int(m.group(5)), "declared": int(m.group(6))})
                continue
            t = re.match(r"\[(\d\d:\d\d:\d\d)\]\s*(.*)", ln)
            if t:
                ev.append({"t": t.group(1), "line": t.group(2).strip()})
        out[d] = {"log": lg, "sha256": sha(lg), "requests": reqs, "events": ev}
    return out


def main():
    runs = parse_runs()

    # ---------- LOBBY_PROTOCOLS.json
    info = defaultdict(lambda: {"runs": 0, "sizes": set(), "count": 0})
    for r, d in runs.items():
        seen = set()
        for q in d["requests"]:
            k = (q["service"], q["task"])
            info[k]["sizes"].add(q["declared"])
            info[k]["count"] += 1
            seen.add(k)
        for k in seen:
            info[k]["runs"] += 1
    protos = [{"service": s, "task": t,
               "runs_present": v["runs"], "requests_total": v["count"],
               "declared_sizes": sorted(v["sizes"])}
              for (s, t), v in sorted(info.items())]
    with open(os.path.join(HERE, "LOBBY_PROTOCOLS.json"), "w", encoding="utf-8") as f:
        json.dump({"schema": "codol-lobby-protocols/v1", "generated": "2026-10-29",
                   "runs_scanned": len(runs), "protocols": protos}, f, indent=1, ensure_ascii=False)

    # ---------- LOBBY_BREAKPOINTS.json
    BP = [
        dict(id="BP-01", issue="CODOL-ISSUE-0009", stage="ready_button", type="NOT_IMPLEMENTED",
             last_ok="room created (11/13 answered)", first_unproven="click -> 11/4 ready batch",
             protocol="11/4", blocks_followup=True, next="E7a: click a non-ready room button",
             evidence=["run_codol_001/runs/ONCE_20261028_225645/kit/lobby_srv.log"]),
        dict(id="BP-02", issue="CODOL-ISSUE-0010", stage="downlink_dispatch", type="BLOCKED",
             last_ok="server push sent (bytes logged)", first_unproven="client parses the push",
             protocol="instant_push(kind=11)+bitstream", blocks_followup=True,
             next="E8: malformed-control (truncate field, observe behaviour)",
             evidence=["run_codol_001/runs/E1_20261029_103001/DUMP_FORENSICS.md"]),
        dict(id="BP-03", issue="CODOL-ISSUE-0012", stage="member_sync", type="NOT_IMPLEMENTED",
             last_ok="server returns memberCount scalar", first_unproven="client builds member objects",
             protocol="none (no member list protocol exists)", blocks_followup=True,
             next="decode the 11/4 batch blob (103-245 B)",
             evidence=["03_LOBBY_PROTOCOL_INVENTORY.md"]),
        dict(id="BP-04", issue="CODOL-ISSUE-0012", stage="event_handler_register", type="UNKNOWN",
             last_ok="dwRoomMatchUber exists at memberCount=1", first_unproven="MyEventHandler registered",
             protocol="none", blocks_followup=True,
             next="E6: dump with memberCount=1 kit, count vtable 0x00DC78F0",
             evidence=["run_codol_001/runs/EARLIEST2_20261027_132645/"]),
        dict(id="BP-05", issue="CODOL-ISSUE-0013", stage="autostart_sm", type="BLOCKED",
             last_ok="state machine field [U+0x20] set", first_unproven="state 1 -> 2",
             protocol="none", blocks_followup=False,
             next="disassemble 0x63C350 / 0x63C550",
             evidence=["docs/AB_MEMBERCOUNT_RESULT_20261027.md"]),
        dict(id="BP-06", issue="CODOL-ISSUE-0020", stage="mmstart_to_battle", type="BLOCKED",
             last_ok="client sent mmstart (server received)", first_unproven="client creates UDP socket",
             protocol="UDP 28960", blocks_followup=True,
             next="E2 (PvE + different map) / E3 (room + map in mmstart)",
             evidence=["run_codol_001/runs/E1_20261029_103001/e1.pcapng"]),
        dict(id="BP-07", issue="CODOL-ISSUE-0017", stage="event_push", type="NOT_IMPLEMENTED",
             last_ok="client subscribed 20 events (6/5)", first_unproven="server pushes first event",
             protocol="room event push", blocks_followup=True,
             next="decode the 20 event ids in the 6/5 request",
             evidence=["docs/LOBBY_TRAFFIC_GAP_20261027.md"]),
        dict(id="BP-08", issue="CODOL-ISSUE-0016", stage="bootstrap", type="UNKNOWN",
             last_ok="12 unmapped requests answered with empty ACK", first_unproven="their semantics",
             protocol="12/6 9/14 3/53 29/10 10/20 68/3 28/4 71/18 3/46 3/48 9/5 4/4",
             blocks_followup=False, next="add minimal legal replies one at a time",
             evidence=["03_LOBBY_PROTOCOL_INVENTORY.md"]),
    ]
    with open(os.path.join(HERE, "LOBBY_BREAKPOINTS.json"), "w", encoding="utf-8") as f:
        json.dump({"schema": "codol-lobby-breakpoints/v1", "generated": "2026-10-29",
                   "breakpoints": BP}, f, indent=1, ensure_ascii=False)

    # ---------- LOBBY_COMPLETENESS_MATRIX.csv
    rows = [
        ["bootstrap_handshake", "VERIFIED_COMPLETE", "56/56 runs, 0x81/0x82/0x83 + KDF", "all lobby_srv.log"],
        ["bootstrap_35_requests", "PARTIALLY_IMPLEMENTED", "56/56 but 12 of them are empty-ACK unknowns", "03_LOBBY_PROTOCOL_INVENTORY.md#A"],
        ["player_profile", "VERIFIED_COMPLETE", "8/1 + 8/2 return 33KB/32KB, 8/3 upload accepted", "lobby_srv.log"],
        ["publisher_config", "VERIFIED_COMPLETE", "10/21 x10 incl 21412B playlists", "lobby_srv.log"],
        ["channel_subscribe", "VERIFIED_COMPLETE", "102/1 returns 7B object", "lobby_server.py:1228"],
        ["find_sessions", "VERIFIED_COMPLETE", "21/5 returns 280B incl 67B address block", "lobby_srv.log"],
        ["create_room", "VERIFIED_COMPLETE", "11/13 returns 37B, client continues", "32 runs"],
        ["room_initialization", "PARTIALLY_IMPLEMENTED", "dwRoomMatchUber created at memberCount=1 but SM stuck state1", "AB_MEMBERCOUNT_RESULT"],
        ["room_member_sync", "NOT_IMPLEMENTED", "no member-list protocol exists; only memberCount u32", "03_LOBBY_PROTOCOL_INVENTORY.md#A"],
        ["room_ui_update", "BLOCKED", "downlink sent but never proven parsed", "07_ROOM_EVENT_DISPATCH.md"],
        ["room_ready", "BLOCKED", "button produces no uplink at all", "CODOL-ISSUE-0009"],
        ["event_push_20", "NOT_IMPLEMENTED", "zero events pushed for 20 subscriptions", "LOBBY_TRAFFIC_GAP"],
        ["mmbook", "VERIFIED_COMPLETE", "46 runs, accepted->mmstart proven", "lobby_srv.log"],
        ["mmstart_send", "VERIFIED_COMPLETE", "client sends it, server parses it", "lobby_srv.log"],
        ["mmstart_to_battle_connect", "BLOCKED", "PvE path once worked (8 runs 10-26); room path never", "CONNECTION_REGRESSION_DIFFERENTIAL"],
        ["battle_handoff_address", "VERIFIED_COMPLETE", "67B address block present in 21/5 reply", "lobby_server.py:840"],
        ["battle_udp_connect", "BLOCKED", "zero RX; pcap 0 packets", "e1.pcapng"],
        ["exit_to_lobby", "UNKNOWN", "no run observed returning to lobby after a match", "-"],
    ]
    with open(os.path.join(HERE, "LOBBY_COMPLETENESS_MATRIX.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["stage", "status", "note", "evidence"])
        w.writerows(rows)

    # ---------- LOBBY_EVIDENCE_INDEX.json
    ev = []
    for r, d in runs.items():
        ev.append(dict(id="RUN-" + r, type="lobby-log", run=r,
                       path=os.path.relpath(d["log"], ROOT).replace("\\", "/"),
                       sha256=d["sha256"], requests=len(d["requests"]),
                       events=len(d["events"])))
    for extra in ["docs/ROOM_PROTOCOL_COMPLETE_20261028.md",
                  "docs/ROOM_DIRECTION_SPLIT_20261028.md",
                  "docs/ROOM_PUSH_ROUTE_KEY_SLOT_20261028.md",
                  "docs/LOBBY_TRAFFIC_GAP_20261027.md",
                  "docs/AB_MEMBERCOUNT_RESULT_20261027.md",
                  "docs/GATE_B_INIT_PATH_20261027.md",
                  "run_codol_001/runs/E1_20261029_103001/DUMP_FORENSICS.md",
                  "run_codol_001/runs/E1_20261029_103001/e1.pcapng",
                  "CODOL_VERIFIED_GOLDEN_20261019/lobby_server.py",
                  "CODOL-PROJECT-DEEP-ISSUE-FORENSICS-053/CONNECTION_REGRESSION_DIFFERENTIAL.md"]:
        p = os.path.join(ROOT, extra.replace("/", os.sep))
        if os.path.isfile(p):
            ev.append(dict(id="DOC-" + os.path.basename(p), type="document", path=extra,
                           sha256=sha(p), size=os.path.getsize(p)))
        else:
            ev.append(dict(id="DOC-" + os.path.basename(p), type="document", path=extra,
                           sha256=None, missing=True))
    with open(os.path.join(HERE, "LOBBY_EVIDENCE_INDEX.json"), "w", encoding="utf-8") as f:
        json.dump({"schema": "codol-lobby-evidence/v1", "generated": "2026-10-29",
                   "runs_scanned": len(runs), "evidence": ev}, f, indent=1, ensure_ascii=False)

    print("protocols:", len(protos))
    print("breakpoints:", len(BP))
    print("completeness rows:", len(rows))
    print("evidence entries:", len(ev), "missing:", sum(1 for e in ev if e.get("missing")))


if __name__ == "__main__":
    main()
