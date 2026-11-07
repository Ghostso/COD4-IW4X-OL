#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Builds the machine-readable databases for the P0 forensics batch.

Single source of truth for: ISSUE_FORENSICS.json / .csv, EVIDENCE_INDEX.json,
SOURCE_LOCATION_INDEX.json, HYPOTHESIS_MATRIX.csv, FIX_READINESS_MATRIX.csv.

Only the 7 P0 issues are covered in this batch (see 00_INDEX.md for scope).
Run:  python -I build_p0_db.py
"""
import csv
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"


def sha256(p):
    if not os.path.isfile(p):
        return None
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


# ------------------------------------------------------------------ evidence
# Each entry: id, type, path (relative to ROOT), what_it_proves, what_it_does_not,
# independently_rechecked, missing(bool)
EVIDENCE = [
    dict(id="EV-0020-01", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261029_002046\kit\lobby_srv.log",
         loc="00:21:51 mmstart line", issue="CODOL-ISSUE-0020",
         proves="2026-10-29 mmstart has playlist only; map/gametype resolve to '?'",
         does_not_prove="whether the client parsed the reply", rechecked=True, missing=False),
    dict(id="EV-0020-02", type="battle-log", path=r"run_codol_001\runs\ONCE_20261029_002046\kit\_battle_out.txt",
         loc="whole file (358 B / 7 lines)", issue="CODOL-ISSUE-0020",
         proves="zero RX on battle server", does_not_prove="whether client ever tried",
         rechecked=True, missing=False),
    dict(id="EV-0020-03", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261026_220815\kit\lobby_srv.log",
         loc="22:09:15", issue="CODOL-ISSUE-0020",
         proves="last successful mmstart carried map coop_train_mp_firingrange and roomChatChannelID 0",
         does_not_prove="why that map was selected", rechecked=True, missing=False),
    dict(id="EV-0020-04", type="battle-log", path=r"run_codol_001\runs\ONCE_20261026_220815\kit\_battle_out.txt",
         loc="head 40 lines", issue="CODOL-ISSUE-0020",
         proves="full NAT/DTLS/ECDH/getchallenge/connect/stats chain on the success run",
         does_not_prove="whether the client finished map load", rechecked=True, missing=False),
    dict(id="EV-0020-05", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261026_233111\kit\lobby_srv.log",
         loc="23:32:34", issue="CODOL-ISSUE-0020",
         proves="first failing run still carried a map (cargoship) yet got zero RX",
         does_not_prove="root cause", rechecked=True, missing=False),
    dict(id="EV-0020-06", type="battle-log", path=r"run_codol_001\runs\ONCE_20261026_233111\kit\_battle_out.txt",
         loc="whole file (379 B / 7 lines)", issue="CODOL-ISSUE-0020",
         proves="zero RX with a valid map", does_not_prove="root cause",
         rechecked=True, missing=False),
    dict(id="EV-0020-07", type="derived-matrix", path=r"run_codol_001\runs",
         loc="34 runs with lobby_srv.log + _battle_out.txt", issue="CODOL-ISSUE-0020",
         proves="map==coop_train_mp_firingrange AND no-room correlates 100% with RX (8/8 vs 26/26)",
         does_not_prove="causal direction", rechecked=True, missing=False),
    dict(id="EV-0020-08", type="chain-log", path=r"run_codol_001\runs\ONCE_20261026_220815\chain_pos.txt",
         loc="line 1 (--root)", issue="CODOL-ISSUE-0020",
         proves="success runs used sandbox_ifs1_20260923 as game root",
         does_not_prove="whether root matters", rechecked=True, missing=False),
    dict(id="EV-0020-09", type="source", path=r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py",
         loc="lines 1090-1150", issue="CODOL-ISSUE-0020",
         proves="mmstart handling + coop_map self-correction loop",
         does_not_prove="client behaviour", rechecked=True, missing=False),
    dict(id="EV-0020-10", type="source", path=r"CODOL_SERVER_319_20261021\src\battle\battle_service.c",
         loc="lines 1061-1140", issue="CODOL-ISSUE-0020",
         proves="single UDP entry point; logs on every packet",
         does_not_prove="—", rechecked=True, missing=False),
    dict(id="EV-0021-01", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261029_002046\kit\lobby_srv.log",
         loc="00:21:51", issue="CODOL-ISSUE-0021",
         proves="playlist 37 / start_map_rotate_once 7 / roomChatChannelID 1800154382",
         does_not_prove="playlist semantics", rechecked=True, missing=False),
    dict(id="EV-0021-02", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261026_220815\kit\lobby_srv.log",
         loc="22:09:15", issue="CODOL-ISSUE-0021",
         proves="success form: map coop_train_mp_firingrange; g_gametype coop; g_difficulty 1",
         does_not_prove="—", rechecked=True, missing=False),
    dict(id="EV-0021-05", type="source", path=r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py",
         loc="lines 1090-1143", issue="CODOL-ISSUE-0021",
         proves="when map or gametype regex fails, coop_map.txt is silently not written",
         does_not_prove="client semantics", rechecked=True, missing=False),
    dict(id="EV-0021-06", type="data", path=r"run_codol_001\runs\ONCE_20261029_002046\kit\publisher_files\mp_playlists_shipRetail_1.0.0.info",
         loc="112664 B / 123 entries", issue="CODOL-ISSUE-0021",
         proves="official playlist id set has no 37 / no 50",
         does_not_prove="what 37 means", rechecked=True, missing=False),
    dict(id="EV-0074-01", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261027_202345\kit\lobby_srv.log",
         loc="20:24:33 onward, every 5 s", issue="CODOL-ISSUE-0074",
         proves="102/7 answered with 50/50 zero fields (555 B) and the client re-sends every 5 s",
         does_not_prove="why the reply is rejected", rechecked=True, missing=False),
    dict(id="EV-0074-02", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261026_220815\kit\lobby_srv.log",
         loc="whole file", issue="CODOL-ISSUE-0074",
         proves="successful run never sent 102/ (count = 0)",
         does_not_prove="—", rechecked=True, missing=False),
    dict(id="EV-0074-03", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261026_233111\kit\lobby_srv.log",
         loc="whole file", issue="CODOL-ISSUE-0074",
         proves="first failing run also never sent 102/ (count = 0) yet got zero RX",
         does_not_prove="—", rechecked=True, missing=False),
    dict(id="EV-0074-04", type="source", path=r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py",
         loc="lines 1181-1226", issue="CODOL-ISSUE-0074",
         proves="reply implementation hard-codes val = 0; no real-value source exists",
         does_not_prove="client acceptance rule", rechecked=True, missing=False),
    dict(id="EV-0074-05", type="data", path=r"_e1_regression\ol-mod-olfinal\tests\game_server\Fixtures\mp_playerdata.def.1649370.bin",
         loc="22940 B / 153 fields", issue="CODOL-ISSUE-0074",
         proves="field table is for build 1649370 (same build)",
         does_not_prove="how client consumes fields", rechecked=False, missing=False),
    dict(id="EV-0012-01", type="memory-dump", path=r"run_codol_001\runs\EARLIEST_20261027_123806\snap_002.bin",
         loc="1478.5 MB, t=79.7 s, 0 failed blocks", issue="CODOL-ISSUE-0012",
         proves="MyEventHandler vtable 0x00DC78F0 has zero instances (memberCount=0 build)",
         does_not_prove="current state after memberCount=1", rechecked=False, missing=False),
    dict(id="EV-0012-04", type="memory-dump", path=r"run_codol_001\runs\EARLIEST2_20261027_132645\snap_003.bin",
         loc="1630 MB, t=89 s", issue="CODOL-ISSUE-0012",
         proves="dwRoomMatchUber (0x00DC795C) exists after memberCount=1",
         does_not_prove="MyEventHandler instance count (never measured)", rechecked=False, missing=False),
    dict(id="EV-0009-01", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261028_225645\kit\lobby_srv.log",
         loc="22:57:55-22:58:05", issue="CODOL-ISSUE-0009",
         proves="only 4 uplinks that round, none of them a ready",
         does_not_prove="whether the click reached the client internals", rechecked=True, missing=False),
    dict(id="EV-0009-03", type="rtti-inventory", path=r"run_codol_001\runs\RE_FULL_20261029\rtti_full.md",
         loc="AS_* section", issue="CODOL-ISSUE-0009",
         proves="163 AS_* RTTI class names exist in the EXE",
         does_not_prove="whether they are registered at runtime", rechecked=True, missing=False),
    dict(id="EV-0010-03", type="lobby-log", path=r"run_codol_001\runs\ONCE_20261028_224009\kit\lobby_srv.log",
         loc="22:41:03-22:41:13", issue="CODOL-ISSUE-0010",
         proves="first observable behavioural difference (task count 85->71, 11/4 6->4)",
         does_not_prove="that the downlink was parsed correctly", rechecked=True, missing=False),
    dict(id="EV-0041-01", type="report", path=r"CODOL-BATTLE-SERVER-RECEIVE-LINK-050\00_FINDINGS.md",
         loc="whole file", issue="CODOL-ISSUE-0041",
         proves="static analysis converged on one unclosed edge",
         does_not_prove="runtime relationship", rechecked=False, missing=False),
]

# Items referenced by the dossiers but NOT on disk.
MISSING = [
    dict(id="MISS-0020-01", issue="CODOL-ISSUE-0020", what="client memory dump from any 10-26 success run",
         note="nearest dump is EARLIEST2_20261027_132645 (a failure-period run)"),
    dict(id="MISS-0020-02", issue="CODOL-ISSUE-0020", what="network capture (pcap) of any battle session",
         note="never captured; THIRD_ROUND_PREREQUISITES R3-A03 still OPEN"),
    dict(id="MISS-0020-03", issue="CODOL-ISSUE-0020", what="UI entry screenshot per run",
         note="entry path inferred only from mmstart shape"),
    dict(id="MISS-0074-01", issue="CODOL-ISSUE-0074", what="raw 556 B 102/7 request bytes",
         note="no run ever dumped it; structure known only second-hand"),
    dict(id="MISS-0012-02", issue="CODOL-ISSUE-0012", what="MyEventHandler instance count after memberCount=1",
         note="never re-measured; this is the single most important missing item"),
    dict(id="MISS-0009-01", issue="CODOL-ISSUE-0009", what="any client-side UI log",
         note="game writes no UI log; config_mp.cfg encrypted; ui_mp.ff encrypted"),
    dict(id="MISS-0041-01", issue="CODOL-ISSUE-0041", what="runtime dump with an active session",
         note="ACE blocks RPM outside the early window; window does not overlap room creation"),
]

# ------------------------------------------------------------ source locations
# line numbers are verified against the files at the hashes below
SOURCE_LOCATIONS = [
    dict(issue="CODOL-ISSUE-0020", file=r"CODOL_SERVER_319_20261021\src\battle\battle_service.c",
         symbol="codol_battle_service_on_packet", lines="1061-1140", role="UDP entry; logs every packet"),
    dict(issue="CODOL-ISSUE-0020", file=r"CODOL_SERVER_319_20261021\src\main.c",
         symbol="battle_sink / main loop", lines="25-30, 157-175", role="dispatch to battle service"),
    dict(issue="CODOL-ISSUE-0020", file=r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py",
         symbol="reply_objects mmstart branch", lines="1090-1150", role="parses mmstart, writes coop_map.txt"),
    dict(issue="CODOL-ISSUE-0021", file=r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py",
         symbol="reply_objects mmstart regex", lines="1101-1116", role="map/gametype extraction, silent skip"),
    dict(issue="CODOL-ISSUE-0021", file=r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py",
         symbol="reply_objects findSessions", lines="789-849", role="returns session object"),
    dict(issue="CODOL-ISSUE-0074", file=r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py",
         symbol="reply_objects 102/7", lines="1181-1226", role="replies with val=0 for all fields"),
    dict(issue="CODOL-ISSUE-0012", file=r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py",
         symbol="reply_objects 11/13 createRoom", lines="1002-1010", role="sends memberCount=1"),
    dict(issue="CODOL-ISSUE-0009", file=r"CODOL_VERIFIED_GOLDEN_20261019\lobby_server.py",
         symbol="ready_push branch", lines="1048-1068", role="replies only if client already sent 0B/4"),
    dict(issue="CODOL-ISSUE-0010", file=r"CODOL_SERVER_319_20261021\src\battle\battle_service.c",
         symbol="send_gamestate / _gs_adapt_dynamic", lines="302-409", role="gamestate path (unaffected by room push)"),
    dict(issue="CODOL-ISSUE-0041", file=r"CODOL-BATTLE-SERVER-RECEIVE-LINK-050\00_FINDINGS.md",
         symbol="(analysis report)", lines="—", role="static convergence point"),
]

# --------------------------------------------------------------- hypotheses
HYPOTHESES = [
    # issue, id, text, support, against, status, how_to_verify, cost, risk
    ("CODOL-ISSUE-0020", "H1", "selected map not loadable by client => no connect",
     "8/8 successes all coop_train_mp_firingrange; 26/26 failures other maps",
     "regime B/C carried a loadable map name and still failed",
     "HIGH_UNPROVEN", "E2", "1 run", "low"),
    ("CODOL-ISSUE-0020", "H2", "entry path (PvE direct vs room) decides whether client connects",
     "8/8 successes created no room; all failures did",
     "confounded with H1 in all historical data",
     "HIGH_UNPROVEN", "E3", "1 run", "low"),
    ("CODOL-ISSUE-0020", "H3", "102/7 zero reply clears selection",
     "regime C had 102/7 and failed",
     "regime B never sent 102/7 and also failed; regime D disabled it and still failed",
     "EXCLUDED", "E5", "1 run", "low"),
    ("CODOL-ISSUE-0020", "H4", "memberCount affects connection",
     "—", "regime B already had memberCount=1 and failed", "EXCLUDED", "—", "—", "—"),
    ("CODOL-ISSUE-0020", "H5", "mmstart pushing StartGame breaks connect",
     "—", "regime B never pushed StartGame and still failed", "EXCLUDED", "—", "—", "—"),
    ("CODOL-ISSUE-0020", "H6", "battle server not started / port busy",
     "—", "failure-run _battle_out.txt shows listener up", "EXCLUDED", "—", "—", "—"),
    ("CODOL-ISSUE-0020", "H7", "sandbox vs full game root matters",
     "successes used sandbox; 10-27 12:00 onward used COD OL",
     "regime B used the same sandbox and still failed", "EXCLUDED_FOR_B",
     "E1", "1 run", "low"),
    ("CODOL-ISSUE-0021", "H1", "playlist id alone is insufficient to locate a map in this build",
     "regime D entirely this shape", "regime B/C had map and still failed",
     "MEDIUM", "E2/E4", "2-3 runs", "low"),
    ("CODOL-ISSUE-0021", "H2", "37 is a sorted index, not an official playlist id",
     "official table of 123 entries has no 37/50", "not confirmed in client code",
     "MEDIUM", "E4", "2-3 runs", "low"),
    ("CODOL-ISSUE-0074", "H1", "102/7 zero reply causes no connect",
     "regime C had 102/7 and failed",
     "regime B has none and fails; regime D disabled it and fails",
     "EXCLUDED", "E5", "1 run", "low"),
    ("CODOL-ISSUE-0074", "H2", "102/7 reply format itself is rejected by the client",
     "5 s re-send is direct evidence", "clients re-send for other reasons too",
     "OPEN_LOCAL", "—", "—", "—"),
    ("CODOL-ISSUE-0012", "H0", "MyEventHandler actually exists after memberCount=1",
     "dwRoomMatchUber appears after the fix", "never re-measured",
     "MUST_TEST_FIRST", "E6", "1 dump", "low"),
    ("CODOL-ISSUE-0012", "H1", "Init depends on a lobby reply never sent",
     "author hypothesis", "no specific reply identified", "MEDIUM", "E6 + bisect", "several", "med"),
    ("CODOL-ISSUE-0009", "H1", "AS_* classes are not registered with Scaleform",
     "no COL, zero xrefs", "registration may be by hash/ID", "LOW", "E7a", "1 run", "low"),
    ("CODOL-ISSUE-0009", "H2", "room event system not established (Init)",
     "ISSUE-0012", "dwRoomMatchUber eventually appeared", "MEDIUM", "E7a", "1 run", "low"),
    ("CODOL-ISSUE-0010", "H1", "downlink format correct but content insufficient",
     "observable behaviour difference", "not confirmed", "MEDIUM", "E8", "1 run", "low"),
    ("CODOL-ISSUE-0010", "H3", "envelope route key wrong (obj+8 != roomId)",
     "envelope never pinned down", "behaviour difference implies partial handling",
     "HIGH_UNPROVEN", "E8", "1 run", "low"),
    ("CODOL-ISSUE-0010", "H4", "client ignores push because it looks like its own echo",
     "client sends the same body shapes", "not tested", "MEDIUM", "E8", "1 run", "low"),
    ("CODOL-ISSUE-0041", "H1", "[esi+0xA8] is the reader input",
     "natural design", "never observed", "HIGH_UNPROVEN", "E9", "1 dump", "low"),
    ("CODOL-ISSUE-0041", "H2", "an intermediate decrypt/decompress stage exists",
     "Demonsware frames are encrypted", "not observed", "MEDIUM", "E9", "1 dump", "low"),
]

# ---------------------------------------------------------------- fix readiness
# issue, status, root_cause_proven, reproducible, source_located, has_min_experiment,
# has_fix_plan, has_acceptance, can_fix_now, missing
READINESS = [
    ("CODOL-ISSUE-0020", "OPEN", False, True, True, True, False, True, False,
     "E1/E2/E3 differential not run"),
    ("CODOL-ISSUE-0021", "OPEN", False, True, True, True, False, True, False,
     "playlist semantics + E2/E4 not run"),
    ("CODOL-ISSUE-0074", "OPEN", False, True, True, True, False, True, False,
     "recommend downgrade to P2; E5 not run"),
    ("CODOL-ISSUE-0012", "OPEN", False, False, True, True, False, True, False,
     "must re-measure MyEventHandler after memberCount=1 (E6)"),
    ("CODOL-ISSUE-0009", "BLOCKED", False, True, False, True, False, True, False,
     "all reverse-engineering channels blocked (ACE / encrypted ff / no gfx tool)"),
    ("CODOL-ISSUE-0010", "CONTRADICTORY_EVIDENCE", False, True, True, True, False, True, False,
     "E8 malformed-control experiment not run"),
    ("CODOL-ISSUE-0041", "OPEN", False, False, True, True, False, True, False,
     "needs runtime dump with active session (blocked by ISSUE-0045)"),
]


def main():
    # ---- evidence index with hashes
    ev_out = []
    for e in EVIDENCE:
        full = os.path.join(ROOT, e["path"])
        h = sha256(full)
        rec = dict(e)
        rec["abs_path"] = full
        rec["is_dir"] = os.path.isdir(full)
        if rec["is_dir"]:
            rec["sha256"] = None
            rec["exists"] = True
            rec["size"] = sum(os.path.getsize(os.path.join(dp, fn))
                              for dp, _, fns in os.walk(full) for fn in fns)
            rec["note"] = "directory evidence; hash not applicable, contents enumerated in CONNECTION_REGRESSION_DIFFERENTIAL.md §1"
        else:
            rec["sha256"] = h
            rec["exists"] = os.path.isfile(full)
            rec["size"] = os.path.getsize(full) if os.path.isfile(full) else None
        ev_out.append(rec)

    with open(os.path.join(HERE, "EVIDENCE_INDEX.json"), "w", encoding="utf-8") as f:
        json.dump(dict(schema="codol-evidence-index/v1", generated="2026-10-29",
                       evidence=ev_out, missing_primary=MISSING), f, indent=2, ensure_ascii=False)

    # ---- source location index
    with open(os.path.join(HERE, "SOURCE_LOCATION_INDEX.json"), "w", encoding="utf-8") as f:
        json.dump(dict(schema="codol-source-location/v1", generated="2026-10-29",
                       locations=SOURCE_LOCATIONS), f, indent=2, ensure_ascii=False)

    # ---- hypothesis matrix
    with open(os.path.join(HERE, "HYPOTHESIS_MATRIX.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue", "hypothesis_id", "text", "support", "against", "status",
                    "how_to_verify", "cost", "risk"])
        for row in HYPOTHESES:
            w.writerow(row)

    # ---- fix readiness matrix
    with open(os.path.join(HERE, "FIX_READINESS_MATRIX.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue", "current_status", "root_cause_proven", "has_reproduction",
                    "source_located", "has_min_experiment", "has_fix_plan",
                    "has_acceptance", "can_fix_now", "missing_evidence"])
        for row in READINESS:
            w.writerow([str(x).lower() if isinstance(x, bool) else x for x in row])

    # ---- issue forensics json + csv
    issues = []
    for name in sorted(os.listdir(os.path.join(HERE, "ISSUES"))):
        if not name.endswith(".md"):
            continue
        iid = name[:-3]
        issues.append(dict(
            id=iid,
            dossier="ISSUES/" + name,
            evidence=[e["id"] for e in EVIDENCE if e["issue"] == iid],
            missing=[m["id"] for m in MISSING if m["issue"] == iid],
            sources=[s for s in SOURCE_LOCATIONS if s["issue"] == iid],
            hypotheses=[h[1] for h in HYPOTHESES if h[0] == iid],
            readiness=next((r for r in READINESS if r[0] == iid), None),
        ))
    with open(os.path.join(HERE, "ISSUE_FORENSICS.json"), "w", encoding="utf-8") as f:
        json.dump(dict(schema="codol-issue-forensics/v1", generated="2026-10-29",
                       scope="P0 batch (7 issues)", issues=issues), f, indent=2, ensure_ascii=False)

    with open(os.path.join(HERE, "ISSUE_FORENSICS.csv"), "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["issue", "dossier", "evidence_count", "missing_count",
                    "root_cause_proven", "has_min_experiment", "can_fix_now"])
        for it in issues:
            r = it["readiness"]
            w.writerow([it["id"], it["dossier"], len(it["evidence"]), len(it["missing"]),
                        str(r[2]).lower() if r else "?",
                        str(r[5]).lower() if r else "?",
                        str(r[8]).lower() if r else "?"])

    print("evidence entries : %d (exists %d)" % (len(ev_out), sum(1 for e in ev_out if e["exists"])))
    print("missing primary  : %d" % len(MISSING))
    print("source locations : %d" % len(SOURCE_LOCATIONS))
    print("hypotheses       : %d" % len(HYPOTHESES))
    print("readiness rows   : %d" % len(READINESS))
    print("issues           : %d" % len(issues))


if __name__ == "__main__":
    main()
