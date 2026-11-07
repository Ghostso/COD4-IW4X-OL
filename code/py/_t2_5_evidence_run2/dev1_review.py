"""T-2.5 DEV-1: read-only provenance review of the rebuilt T-1 test binary.

Answers: was build/bin/release/ol_transport_lifecycle_tests.exe produced by the local
toolchain from the frozen T-1 sources, inside the recorded 14:49:33-14:50:08 window,
with no source newer than the build? No rebuild is performed.
"""
from __future__ import annotations

import hashlib
import json
import re
import struct
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = Path("F:/桌面/ol/ol-mod-olfinal")
EXE = ROOT / "build/bin/release/ol_transport_lifecycle_tests.exe"
DEPS = ROOT / "build/deps/release/ol_transport_lifecycle_tests/windows/x86/release"
DEP_FILE = DEPS / "ol_transport_lifecycle_tests.exe.d"
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
OTHER = {
    "build/bin/release/ol_game_server_tests.exe": "706CAE920707DA8976F047E14878BB3CCC546915C566B9BAFDF66DE68D09CCEB",
    "build/bin/release/ol_lua_runtime_tests.exe": "9205E4BBE39EB9F5C5B24D483ED2245E8C93B0168385312D27560743D7DEC151",
}


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, TZ).strftime("%Y-%m-%dT%H:%M:%S%z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def parse_pe(path: Path) -> dict:
    data = path.read_bytes()
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    info: dict = {}
    machine, sections, timestamp, _, _, opt_size, characteristics = struct.unpack_from("<HHIIIHH", data, pe + 4)
    opt = pe + 24
    magic = struct.unpack_from("<H", data, opt)[0]
    is64 = magic == 0x20B
    info["machine"] = hex(machine)
    info["sectionCount"] = sections
    info["timeDateStamp"] = timestamp
    info["timeDateStampISO"] = iso(timestamp) if timestamp else None
    info["characteristics"] = hex(characteristics)
    info["linkerVersion"] = "%d.%d" % struct.unpack_from("<BB", data, opt + 2)
    info["sizeOfImage"] = struct.unpack_from("<I", data, opt + 56)[0]
    info["imageBase"] = struct.unpack_from("<Q", data, opt + 24)[0] if is64 else struct.unpack_from("<I", data, opt + 28)[0]
    info["checksum"] = struct.unpack_from("<I", data, opt + 64)[0]
    info["subsystem"] = struct.unpack_from("<H", data, opt + 68)[0]
    info["dllCharacteristics"] = hex(struct.unpack_from("<H", data, opt + 70)[0])
    info["sizeOfHeaders"] = struct.unpack_from("<I", data, opt + 60)[0]
    dirs = opt + (0x70 if is64 else 0x60)
    dirs_count = struct.unpack_from("<I", data, opt + (0x6C if is64 else 0x5C))[0]
    info["numberOfRvaAndSizes"] = dirs_count
    rva_dirs = [struct.unpack_from("<II", data, dirs + 8 * i) for i in range(min(dirs_count, 16))]
    info["importDirectory"] = {"rva": hex(rva_dirs[1][0]), "size": rva_dirs[1][1]}
    info["debugDirectory"] = {"rva": hex(rva_dirs[6][0]), "size": rva_dirs[6][1]}

    secs = []
    sec_start = opt + opt_size
    for i in range(sections):
        base = sec_start + i * 40
        name = data[base:base + 8].rstrip(b"\0").decode("ascii", "replace")
        vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", data, base + 8)
        secs.append((name, vaddr, vsize, rawptr, rawsize))

    def rva2off(rva):
        for _n, vaddr, vsize, rawptr, rawsize in secs:
            if vaddr <= rva < vaddr + max(vsize, rawsize):
                return rawptr + (rva - vaddr)
        return None

    # imports: DLL names only
    dlls = []
    off = rva2off(rva_dirs[1][0])
    if off:
        while True:
            entry = struct.unpack_from("<IIIII", data, off)
            if entry == (0, 0, 0, 0, 0):
                break
            name_off = rva2off(entry[3])
            if name_off is None:
                break
            end = data.index(b"\0", name_off)
            dlls.append(data[name_off:end].decode("ascii", "replace"))
            off += 20
    info["importedDlls"] = sorted(set(dlls))
    info["importedDllCount"] = len(set(dlls))

    # debug directory -> PDB
    dbg_off = rva2off(rva_dirs[6][0])
    info["debugEntries"] = []
    if dbg_off and rva_dirs[6][1]:
        for i in range(rva_dirs[6][1] // 28):
            base = dbg_off + i * 28
            typ, size, rva_raw, ptr_raw = struct.unpack_from("<IIII", data, base)
            entry = {"type": typ, "size": size}
            if typ == 2:
                codeview_off = rva2off(rva_raw)
                if codeview_off is None:
                    codeview_off = ptr_raw
                sig = data[codeview_off:codeview_off + 4]
                entry["signature"] = sig.decode("ascii", "replace").strip("\0")
                guid = data[codeview_off + 4:codeview_off + 20]
                age = struct.unpack_from("<I", data, codeview_off + 20)[0]
                name_end = data.index(b"\0", codeview_off + 24)
                entry["pdbGuid"] = "-".join([
                    guid[:4].hex(), guid[4:6].hex(), guid[6:8].hex(),
                    guid[8:10].hex(), guid[10:].hex()]).upper()
                entry["pdbAge"] = age
                entry["pdbPath"] = data[codeview_off + 24:name_end].decode("ascii", "replace")
            info["debugEntries"].append(entry)

    # rich header
    rich_off = data.find(b"Rich", 0x80, min(pe, 0x400))
    info["richHeader"] = None
    if rich_off != -1:
        dans_off = data.rfind(b"DanS", 0x80, rich_off)
        info["richHeader"] = {"richOffset": rich_off, "dansOffset": dans_off,
                              "productIds": sorted({struct.unpack_from("<H", data, rich_off - 4 - i * 8)[0]
                                                    for i in range((rich_off - dans_off - 8) // 8)})}
    return info


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    doc: dict = {"reviewedAt": iso(datetime.now(TZ).timestamp()),
                 "scope": "read-only provenance review of DEV-1; no rebuild, no replace, no revert"}
    st = EXE.stat()
    doc["binary"] = {"path": str(EXE), "sha256": sha256(EXE), "size": st.st_size,
                     "mtime": iso(st.st_mtime), "ctime": iso(st.st_ctime)}
    doc["binary"]["builtInsideRecordedWindow"] = bool(BUILD_START - 30 <= st.st_mtime <= BUILD_END + 30)
    doc["pe"] = parse_pe(EXE)

    pdb = next((d.get("pdbPath") for d in doc["pe"]["debugEntries"] if d.get("pdbPath")), None)
    doc["pdbOnDisk"] = None
    if pdb:
        candidates = [Path(pdb), EXE.with_suffix(".pdb"), DEPS / Path(pdb).name]
        for cand in candidates:
            if cand.is_file():
                doc["pdbOnDisk"] = {"path": str(cand), "size": cand.stat().st_size,
                                    "sha256": sha256(cand), "mtime": iso(cand.stat().st_mtime)}
                break

    # dependency closure
    text = DEP_FILE.read_text(encoding="utf-8", errors="replace") if DEP_FILE.is_file() else ""
    tokens = sorted({t for t in re.findall(r"[A-Za-z]:[^\s\\/][^\s]*", text)})
    doc["dependencyFile"] = {"path": str(DEP_FILE), "exists": DEP_FILE.is_file(),
                             "size": DEP_FILE.stat().st_size if DEP_FILE.is_file() else None,
                             "mtime": iso(DEP_FILE.stat().st_mtime) if DEP_FILE.is_file() else None,
                             "tokenCount": len(tokens)}
    project, external = [], []
    for t in tokens:
        p = Path(t.replace("\\\\", "/"))
        (project if str(p).lower().startswith(str(ROOT).lower().replace("\\", "/")) else external).append(t)
    doc["dependencyFile"]["projectSources"] = project
    doc["dependencyFile"]["externalDependencies"] = external
    doc["dependencyFile"]["projectSourceCount"] = len(project)
    doc["dependencyFile"]["externalCount"] = len(external)

    post = []
    for t in project:
        p = Path(t)
        if p.is_file():
            m = p.stat().st_mtime
            if m > BUILD_END:
                post.append({"path": t, "mtime": iso(m)})
    doc["projectSourcesNewerThanBuild"] = post

    frozen = {}
    for rel, expected in T1.items():
        p = ROOT / rel
        actual = sha256(p) if p.is_file() else None
        frozen[rel] = {"expected": expected, "actual": actual, "unchanged": actual == expected}
    doc["frozenT1Recheck"] = frozen
    doc["frozenT1AllUnchanged"] = all(v["unchanged"] for v in frozen.values())

    others = {}
    for rel, expected in OTHER.items():
        p = ROOT / rel
        actual = sha256(p) if p.is_file() else None
        others[rel] = {"expected": expected, "actual": actual, "unchanged": actual == expected,
                       "mtime": iso(p.stat().st_mtime) if p.is_file() else None}
    doc["siblingBinaries"] = others

    objs = []
    for p in DEPS.rglob("*.obj"):
        objs.append({"name": p.name, "mtime": iso(p.stat().st_mtime), "size": p.stat().st_size})
    doc["objectFiles"] = {"count": len(objs), "earliest": min((o["mtime"] for o in objs), default=None),
                          "latest": max((o["mtime"] for o in objs), default=None)}
    outside = [o for o in objs if not (iso(BUILD_START - 300) <= o["mtime"] <= iso(BUILD_END + 300))]
    doc["objectFiles"]["outsideBuildWindow"] = outside

    # copies elsewhere
    copies = []
    for base in (ROOT / "build/stage", ROOT / "distribution"):
        if base.is_dir():
            for p in base.rglob("ol_transport_lifecycle_tests.exe"):
                copies.append({"path": str(p), "sha256": sha256(p), "size": p.stat().st_size})
    doc["otherCopies"] = copies

    (EVIDENCE / "dev1_binary_review.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")

    print("hash:", doc["binary"]["sha256"], doc["binary"]["size"])
    print("mtime:", doc["binary"]["mtime"], "insideWindow:", doc["binary"]["builtInsideRecordedWindow"])
    print("ctime:", doc["binary"]["ctime"])
    print("linkerTimeDateStamp:", doc["pe"]["timeDateStampISO"], "linker:", doc["pe"]["linkerVersion"],
          "machine:", doc["pe"]["machine"], "subsystem:", doc["pe"]["subsystem"])
    print("imports:", doc["pe"]["importedDllCount"], doc["pe"]["importedDlls"])
    print("debugEntries:", json.dumps(doc["pe"]["debugEntries"], ensure_ascii=False))
    print("pdbOnDisk:", json.dumps(doc["pdbOnDisk"], ensure_ascii=False))
    print("rich:", json.dumps(doc["pe"]["richHeader"], ensure_ascii=False))
    print("depfile tokens project/external:", doc["dependencyFile"]["projectSourceCount"], "/", doc["dependencyFile"]["externalCount"])
    print("projectSourcesNewerThanBuild:", json.dumps(post, ensure_ascii=False))
    print("frozenT1AllUnchanged:", doc["frozenT1AllUnchanged"])
    print("siblings:", json.dumps(others, ensure_ascii=False))
    print("objects:", json.dumps(doc["objectFiles"], ensure_ascii=False)[:600])
    print("otherCopies:", json.dumps(copies, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
