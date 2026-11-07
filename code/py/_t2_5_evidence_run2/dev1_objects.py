"""T-2.5 DEV-1: verify the link-input closure of the rebuilt test binary.

Reads the xmake build metadata for ol_transport_lifecycle_tests.exe, confirms every
object file exists and was produced inside the recorded rebuild window, and that each
linked project source/header still hashes to the frozen T-1 value where applicable.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = Path("F:/桌面/ol/ol-mod-olfinal")
META = ROOT / "build/deps/release/ol_transport_lifecycle_tests/windows/x86/release/ol_transport_lifecycle_tests.exe.d"
TZ = timezone(timedelta(hours=8))
BUILD_START = datetime(2026, 10, 10, 14, 49, 33, tzinfo=TZ).timestamp()
BUILD_END = datetime(2026, 10, 10, 14, 50, 8, tzinfo=TZ).timestamp()

T1 = {
    "src/game_server/server_mp/sv_network_mp.cpp": "EF4E209BDD9EFDCD5A1F7F69B3789E77852FD98C1371D7C1154677EEBFF19B60",
    "src/game_server/server_mp/sv_network_mp.hpp": "53E5907AE4AFD9251A2192DB2634D88223F6037DB57D772DCC7A081D4E8612C1",
    "src/game_server/win32/win_net.cpp": "3A34D953D2A7A4830D99FF77988A2C791AAB36F968049906F06B832EABAA9A14",
    "src/game_server/win32/win_net.hpp": "8F0FF3189887660DEBB968C6CFF1E055CF065951E82E72F2E2ECF71451F5FBC1",
    "tests/game_server/TransportLifecycleTests.cpp": "FA67AE5B9C6D222CB3B8630D0EEA3D143A860A5E4C55753EB0951A7650A4C8AD",
    "src/game_server/EngineBindings.hpp": "9ACE87313419DB58DC41EE6F4F38612A0970525BAF24CBF924462AD1BA88C72E",
    "src/game_server/ClientProcessPatches.cpp": "E81D760A6B362076C346471EAC89F6841BF43B369BDA360E5E9180378C09B885",
    "src/game_server/Appmain.cpp": "407B6F9896A5F0354625B9D0724A3519BA4ACEDDFC36BA34CE879F79100BE7B1",
    "xmake.lua": "5C54E3585817E908AD32F7D2A36FD69A6130B8964591C25775A48A23605B6FE8",
}
OBJ_PREFIX = "build\\obj\\release\\ol_transport_lifecycle_tests\\windows\\x86\\release\\"


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    text = META.read_text(encoding="utf-8", errors="replace")
    doc: dict = {"collectedAt": iso(datetime.now(TZ).timestamp()), "metadata": str(META)}

    linker = re.search(r"\[\[(.*?link\.exe)\]\]", text)
    doc["linker"] = linker.group(1) if linker else None
    doc["linkFlags"] = re.findall(r'"(-[a-z][^"]*|/[a-z][^"]*)"', text)
    doc["libraries"] = re.findall(r'"((?:lib|ws2_32|user32|advapi32|crypt32)[^"]*\.lib)"', text)
    doc["libPaths"] = re.findall(r"\[\[(-libpath:[^\]]+)\]\]", text)

    obj_rels = re.findall(r"\[\[(build\\obj\\[^\]]+\.obj)\]\]", text)
    doc["objectCount"] = len(obj_rels)
    outside, missing, mtimes = [], [], []
    rows = []
    for rel in obj_rels:
        path = ROOT / rel.replace("\\", "/")
        row = {"object": rel}
        if not path.is_file():
            missing.append(rel)
            row["exists"] = False
        else:
            m = path.stat().st_mtime
            mtimes.append(m)
            row.update(exists=True, size=path.stat().st_size, mtime=iso(m),
                       createdAt=iso(path.stat().st_ctime),
                       insideWindow=bool(BUILD_START - 300 <= m <= BUILD_END + 5))
            if not row["insideWindow"]:
                outside.append(rel)
        rows.append(row)
    doc["objects"] = rows
    doc["missingObjects"] = missing
    doc["objectsOutsideWindow"] = outside
    doc["objectMtimeRange"] = {"earliest": iso(min(mtimes)) if mtimes else None,
                               "latest": iso(max(mtimes)) if mtimes else None}

    # derive source paths from object paths and check they exist + hash
    sources = []
    for rel in obj_rels:
        src = rel[len(OBJ_PREFIX):-4].replace("\\", "/")
        p = ROOT / src
        entry = {"source": src, "exists": p.is_file()}
        if p.is_file():
            entry["mtime"] = iso(p.stat().st_mtime)
            entry["sha256"] = sha256(p)
            entry["unchangedFromT1"] = (T1[src] == entry["sha256"]) if src in T1 else None
        sources.append(entry)
    doc["linkedSources"] = sources
    doc["linkedSourceMissing"] = [s["source"] for s in sources if not s["exists"]]
    doc["t1SourcesInClosure"] = [s for s in sources if s["source"] in T1]

    # any project file under src/ or tests/ newer than the build start?
    newer = []
    for base in (ROOT / "src", ROOT / "tests"):
        if base.is_dir():
            for p in base.rglob("*"):
                if p.is_file() and p.stat().st_mtime > BUILD_END:
                    newer.append({"path": str(p.relative_to(ROOT)).replace("\\", "/"),
                                  "mtime": iso(p.stat().st_mtime)})
    doc["projectSourcesNewerThanBuildEnd"] = newer

    doc["frozenT1"] = {rel: {"expected": exp, "actual": sha256(ROOT / rel) if (ROOT / rel).is_file() else None,
                             "unchanged": (sha256(ROOT / rel) if (ROOT / rel).is_file() else None) == exp}
                       for rel, exp in T1.items()}

    ok = (not missing and not outside and not doc["linkedSourceMissing"] and not newer
          and all(v["unchanged"] for v in doc["frozenT1"].values())
          and all(s.get("unchangedFromT1") is not False for s in sources))
    doc["verdict"] = "CONSISTENT_WITH_FROZEN_SOURCES" if ok else "NEEDS_ATTENTION"
    (EVIDENCE / "dev1_objects.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print("linker:", doc["linker"])
    print("flags:", doc["linkFlags"])
    print("libs:", doc["libraries"])
    print("libPaths:", doc["libPaths"])
    print("objects:", doc["objectCount"], "missing:", missing, "outsideWindow:", outside)
    print("objectMtimeRange:", doc["objectMtimeRange"])
    print("linkedSources missing:", doc["linkedSourceMissing"])
    print("projectSourcesNewerThanBuildEnd:", json.dumps(newer, ensure_ascii=False))
    print("T-1 in closure:")
    for s in doc["t1SourcesInClosure"]:
        print("  ", s["source"], "unchanged=" + str(s["unchangedFromT1"]))
    print("frozenT1 all unchanged:", all(v["unchanged"] for v in doc["frozenT1"].values()))
    print("VERDICT:", doc["verdict"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
