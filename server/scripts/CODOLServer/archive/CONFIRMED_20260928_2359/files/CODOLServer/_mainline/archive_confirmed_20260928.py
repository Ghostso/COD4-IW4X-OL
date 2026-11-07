#!/usr/bin/env python3
"""Copy the confirmed CODOL evidence into one dated archive.

Read-only with respect to the live project: every file is copied, never moved.
Produces ARCHIVE/summary.json plus ARCHIVE/CHECKSUMS.txt so the archived set
can be verified later.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(r"D:\BaiduNetdiskDownload\使命召唤OL")
STAMP = "20260928_2359"
ARCHIVE = ROOT / "CODOLServer" / "archive" / f"CONFIRMED_{STAMP}"


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


# ---------------------------------------------------------------- inventory
# Confirmed successful / decisive runs (state CSV + observer log).
RUN_TAGS = [
    "IFS1_ELEVATED_20260928_113239",  # first sub_state=9 / DW_ACCOUNT_LOGIN_COMPLETE
    "IFS1_ELEVATED_20260928_113833",  # cfg_applied=1, objC created, 735 fixed -> 8902
    "IFS1_ELEVATED_20260928_114637",  # stage 32 -> lob1400/lob240 sampled
    "IFS1_ELEVATED_20260928_115639",
    "IFS1_ELEVATED_20260928_115830",
    "IFS1_ELEVATED_20260928_122838",  # objC URL builder fields sampled
    "IFS1_ELEVATED_20260928_123028",
    "IFS1_ELEVATED_20260928_143350",  # objC+0x28 source object sampled
    "IFS1_ELEVATED_20260928_143656",  # fixed host residue reproduced
    "IFS1_ELEVATED_20260928_144416",  # exact official lobby URL captured
    "IFS1_ELEVATED_20260928_150336",  # local redirect, queue PUT begins
    "IFS1_ELEVATED_20260928_150730",  # queue PUT request/response on 8443
    "IFS1_ELEVATED_20260928_151924",
    "IFS1_ELEVATED_20260928_152404",
    "IFS1_ELEVATED_20260928_153244",  # embedded HTTP vtable/status sampled
    "IFS1_ELEVATED_20260928_154132",  # no-poke baseline: official URL, 59 s
    "IFS1_ELEVATED_20260928_161904",
    "IFS1_ELEVATED_20260928_162532",
    "IFS1_ELEVATED_20260928_165118",  # decisive: state 5 / status 200 frame
    "IFS1_ELEVATED_20260928_165646",  # BREAKTHROUGH: lob1400=8900 lob240=2
    "IFS1_ELEVATED_20260928_171011",  # lobby object [..+0x4f4] still null
    "IFS1_ELEVATED_20260928_172524",  # lobby port global [0x81A9780] == 0
    # ---- 20260928 late session: lobby channel protocol cracked ----
    "IFS1_ELEVATED_20260928_174644",  # reqC8 1->4; CSV header/order bug proved
    "IFS1_ELEVATED_20260928_175045",  # tplB garbage IP; [0x81A7F34] empty
    "IFS1_ELEVATED_20260928_175619",  # tplA=127.0.0.1 tplB=236.3.0.0 raw dump
    "IFS1_ELEVATED_20260928_180039",  # reqC8 reaches 2 -> connect made -> tls_fail
    "IFS1_ELEVATED_20260928_180944",  # plain 28-byte probe accepted (sub-state 3)
    "IFS1_ELEVATED_20260928_181236",  # 200-byte padded frame accepted
    "IFS1_ELEVATED_20260928_181603",  # 24-byte frame rejected (len gate)
    "IFS1_ELEVATED_20260928_181937",  # 204-byte frame accepted
    # ---- BREAKTHROUGH: DW_LOBBY_CONNECTED / DWLOBBY_PUMP_SUCCESS ----
    "IFS1_ELEVATED_20260928_182932",  # uA50=4 DW_LOBBY_CONNECTED held 60 s
    "IFS1_ELEVATED_20260928_183320",  # uA50=5 DWLOBBY_PUMP_SUCCESS, TPFUI SystemSetting
    # ---- 20260928 reproduction: 3/3 consecutive successes ----
    "IFS1_ELEVATED_20260928_184705",
    "IFS1_ELEVATED_20260928_184933",
    "IFS1_ELEVATED_20260928_185158",
    # ---- dialog body captured: "与大厅服务失去连接" ----
    "IFS1_ELEVATED_20260928_190708",
    "IFS1_ELEVATED_20260928_191742",
    # ---- type-byte / multi-frame experiments ----
    "IFS1_ELEVATED_20260928_192251",
    "IFS1_ELEVATED_20260928_192553",
    # ---- codec internals sampled ----
    "IFS1_ELEVATED_20260928_193046",
    "IFS1_ELEVATED_20260928_193625",
]

# Log directories (probe transcripts) worth keeping.
LOG_DIRS = [
    "AUTO_LOBBY_20260928_112724_r2",  # iv_seed=0 round trip
    "AUTO_LOBBY_20260928_113511_r1",  # stage 32 request with codo_request
    "AUTO_LOBBY_20260928_113826_r2",  # 749-byte template round trip
    "AUTO_LOBBY_20260928_122831_r5",  # objC no second request on 8443
    "AUTO_LOBBY_20260928_123021_r7",  # second valid run
    "AUTO_LOBBY_20260928_143343_r6",  # objC+0x28 source/URL failure
    "AUTO_LOBBY_20260928_143649_r1",  # second capture
    "AUTO_LOBBY_20260928_150330_r1",  # local redirect queue attempt
    "AUTO_LOBBY_20260928_150723_r3",  # queue PUT + probe response
    "AUTO_LOBBY_20260928_151918_r1",
    "AUTO_LOBBY_20260928_152357_r1",  # queue close-notify
    "AUTO_LOBBY_20260928_153238_r4",  # embedded HTTP object fields
    "AUTO_LOBBY_20260928_154125_r1",  # no-poke probe log
    "AUTO_LOBBY_20260928_161034_r6",
    "AUTO_LOBBY_20260928_162525_r2",
    "AUTO_LOBBY_20260928_165111_r3",
    "AUTO_LOBBY_20260928_165639_r1",
    "AUTO_LOBBY_20260928_171004_r1",
    "AUTO_LOBBY_20260928_172517_r1",
    "AUTO_LOBBY_20260928_180032_r1",  # lobby connect lands on HTTPS probe as plain TCP
    "AUTO_LOBBY_20260928_180413_r2",
    "AUTO_LOBBY_20260928_180938_r2",
    "AUTO_LOBBY_20260928_181229_r2",
    "AUTO_LOBBY_20260928_181556_r3",
    "AUTO_LOBBY_20260928_181930_r4",
]

# Raw plain-TCP lobby channel captures (the decisive protocol evidence).
PLAIN_DIR = "CODOLServer/logs/PLAIN"
PLAIN_LOGS = [
    "plain_20260928_180337.jsonl",   # first 28-byte lobby probe packet
    "echo_20260928_180902.jsonl",    # echo -> client advances to sub-state 3
    "len200_20260928_181151.jsonl",  # 200-byte padded frame accepted
    "frame24_20260928_181453.jsonl", # len=24 frame rejected
    "frame204_20260928_181756.jsonl",
    "frame204b_20260928_181807.jsonl",
]

# Source and config files that define the confirmed chain.
FILES = [
    "CODOLServer/CONFIRMED_RESULTS_20260928.md",
    "CODOLServer/HANDOFF_20260927_IIPS_GATE_RESOLVED.md",
    "CODOLServer/CODOL_SERVER_OPERATIONS_MANUAL.md",
    "CODOLServer/lobby_server/mklobby_response.py",
    "CODOLServer/lobby_server/lobby_response.json",
    "CODOLServer/lobby_server/lobby_probe_server.py",
    "CODOLServer/lobby_server/lobby_socket_server.py",
    "CODOLServer/lobby_server/probe_response.txt",
    "CODOLServer/_mainline/auto_lobby_loop.py",
    "CODOLServer/_mainline/state_query.py",
    "CODOLServer/_mainline/ws_inspect.py",
    "CODOLServer/_mainline/ticket_check.py",
    "CODOLServer/_mainline/_str_at.py",
    "CODOLServer/_mainline/_mem_at.py",
    "CODOLServer/_mainline/ticket_xor_test.py",
    "CODOLServer/_mainline/_curl_probe.py",
    "CODOLServer/_mainline/_find_state5.py",
    "CODOLServer/_mainline/_find_writes.py",
    "CODOLServer/_mainline/_dis_va.py",
    "restore_iips_contract_001/observer2/AboProbe.cs",
    "run_codol_001/elevated_ifs1_observer.ps1",
    "run_codol_001/capture_elevated_network.ps1",
    "run_codol_001/sandbox_ifs1_20260923/iips.ini",
    "run_codol_001/sandbox_ifs1_20260923/dwauth.ini",
    "CODOLServer/_subagents/_tenproxy_shm_fixed.bin",
    # ---- 20260928 late session ----
    "CODOLServer/lobby_server/lobby_plain_probe.py",
    "restore_iips_contract_001/observer2/AboProbe.csproj",
    "CODOLServer/_mainline/_dis_va.py",
    "CODOLServer/_mainline/archive_confirmed_20260928.py",
    "CODOLServer/logs/PLAIN/plain_20260928_180337.jsonl",
    "CODOLServer/logs/PLAIN/echo_20260928_180902.jsonl",
    "CODOLServer/logs/PLAIN/len200_20260928_181151.jsonl",
    "CODOLServer/logs/PLAIN/frame24_20260928_181453.jsonl",
    "CODOLServer/logs/PLAIN/frame204_20260928_181756.jsonl",
    "CODOLServer/logs/PLAIN/frame204b_20260928_181807.jsonl",
    "CODOLServer/logs/PLAIN/hold_20260928_183208.jsonl",
    "run_codol_001/runs/IFS1_ELEVATED_20260928_183320/iips_files/TenioLog/20260928_183329.log",
    "CODOLServer/LOBBY_BREAKTHROUGH_REPRO_20260928.md",
    "CODOLServer/logs/PLAIN/repro_20260928_184532.jsonl",
    "CODOLServer/logs/PLAIN/dlg2_20260928_190535.jsonl",
    "CODOLServer/_mainline/_fatal_dialog_probe.py",
    "CODOLServer/logs/PLAIN/type2_20260928_192230.jsonl",
    "CODOLServer/logs/PLAIN/multi_20260928_192535.jsonl",
    "CODOLServer/logs/PLAIN/codec_20260928_193035.jsonl",
    "CODOLServer/logs/PLAIN/codec2_20260928_193323.jsonl",
    "CODOLServer/archive/CONFIRMED_20260928_2215/CHECKSUMS.txt",
    "CODOLServer/_mainline/frida_lobby_codec.DO_NOT_RUN.py",
    "CODOLServer/archive/CONFIRMED_20260928_2245/CHECKSUMS.txt",
    "CODOLServer/_mainline/_ba0ff0.txt",
]


def copy_file(rel: str, records: list) -> None:
    src = ROOT / rel
    if not src.is_file():
        records.append({"path": rel, "status": "MISSING"})
        return
    dst = ARCHIVE / "files" / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    records.append({"path": rel, "status": "copied",
                    "bytes": src.stat().st_size, "sha256": sha256(src)})


def copy_run(tag: str, records: list) -> None:
    run = ROOT / "CODOLServer" / ".." / "run_codol_001" / "runs" / tag
    run = (ROOT / "run_codol_001" / "runs" / tag).resolve()
    if not run.is_dir():
        records.append({"path": f"runs/{tag}", "status": "MISSING"})
        return
    wanted = [
        ("aboprobe_run", tag + "_state.csv"),
        ("aboprobe_run", tag + "_events.csv"),
        ("aboprobe_run", tag + "_summary.txt"),
        (None, "summary.txt"),
        (None, "launch.txt"),
        (None, "aboprobe.stdout"),
    ]
    for sub, name in wanted:
        src = run / sub / name if sub else run / name
        if not src.is_file():
            records.append({"path": f"runs/{tag}/{sub or ''}/{name}",
                            "status": "MISSING"})
            continue
        rel = Path(sub) / name if sub else Path(name)
        dst = ARCHIVE / "runs" / tag / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        records.append({"path": f"runs/{tag}/{rel}", "status": "copied",
                        "bytes": src.stat().st_size, "sha256": sha256(src)})


def copy_log_dir(name: str, records: list) -> None:
    src_dir = ROOT / "CODOLServer" / "logs" / name
    if not src_dir.is_dir():
        records.append({"path": f"logs/{name}", "status": "MISSING"})
        return
    for child in sorted(src_dir.iterdir()):
        if not child.is_file():
            continue
        dst = ARCHIVE / "logs" / name / child.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(child, dst)
        records.append({"path": f"logs/{name}/{child.name}", "status": "copied",
                        "bytes": child.stat().st_size, "sha256": sha256(child)})


def main() -> int:
    configure_stdio()
    ARCHIVE.mkdir(parents=True, exist_ok=True)
    records: list = []

    for rel in FILES:
        copy_file(rel, records)
    for tag in RUN_TAGS:
        copy_run(tag, records)
    for name in LOG_DIRS:
        copy_log_dir(name, records)

    copied = [r for r in records if r["status"] == "copied"]
    missing = [r for r in records if r["status"] != "copied"]

    (ARCHIVE / "summary.json").write_text(
        json.dumps({"stamp": STAMP, "archive": str(ARCHIVE),
                    "copied": copied, "missing": missing},
                   indent=2, ensure_ascii=False), encoding="utf-8")
    with open(ARCHIVE / "CHECKSUMS.txt", "w", encoding="utf-8") as fh:
        for rec in copied:
            fh.write(f"{rec['sha256']}  {rec['path']}\n")

    print(f"archive : {ARCHIVE}")
    print(f"copied  : {len(copied)} file(s)")
    print(f"missing : {len(missing)}")
    for rec in missing:
        print(f"  MISSING {rec['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
