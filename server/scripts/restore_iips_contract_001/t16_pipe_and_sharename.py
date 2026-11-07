"""RESTORE-IIPS-CONTRACT-001 / Task 12 - exact named-pipe and shared-memory names.

Task 11 found the string families but not the final names. The provider:
  * connects to its host via a pipe (log: "m_iipsClient connect",
    "synchronous pipe connect failed"), but does NOT import CreateNamedPipe/
    ConnectNamedPipe -- so it must open the pipe with CreateFileA/CreateFileW;
  * opens shared state via OpenFileMappingA (log: "m_iipsShareState open",
    "OpenFileMapping()failed") using "Global\\SharedSpaceName_...".

This script extracts the exact literal names, since a runtime observer needs them
verbatim to detect whether the contract was satisfied.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
IIPS = os.path.join(GAME, "IIPS", "iips.dll")
EXE = os.path.join(GAME, "codoMP_client_shipRetail.exe")
BASE = os.path.join(GAME, "codoMP_client_shipRetailBase.dll")


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    so = pe + 24 + 224
    secs = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        secs.append({"name": name, "va": va, "vsize": vs, "raw": rp, "rsize": rs})
    return pe, secs


def cstrings_containing(d, needle, minlen=3):
    """Return NUL-terminated strings containing needle, with their offsets."""
    out = []
    p = 0
    while True:
        i = d.find(needle, p)
        if i < 0:
            break
        # walk back to start of the string
        s = i
        while s > 0 and 0x20 <= d[s - 1] < 0x7F:
            s -= 1
        e = d.find(b"\0", i)
        if e > 0 and e - s >= minlen:
            txt = d[s:e].decode("latin1", "replace")
            if all(0x20 <= c < 0x7F for c in d[s:e]):
                out.append({"off": "0x%X" % s, "text": txt})
        p = i + 1
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 12: exact pipe / shared-memory names ===")
    print()

    d = open(IIPS, "rb").read()
    pe, secs = sections(d)

    for label, needle in (("SharedSpaceName", b"SharedSpaceName"),
                          ("Global\\", b"Global\\"),
                          ("pipe", b"pipe"),
                          ("Pipe", b"Pipe"),
                          ("IIPSHostApp", b"IIPSHostApp"),
                          ("_iips", b"_iips"),
                          ("iips", b"iips")):
        hits = cstrings_containing(d, needle)
        # dedupe
        seen, uniq = set(), []
        for h in hits:
            if h["text"] in seen:
                continue
            seen.add(h["text"])
            uniq.append(h)
        rep[label] = uniq
        if uniq:
            print("  iips.dll strings containing %r:" % needle.decode("latin1"))
            for h in uniq[:25]:
                print("     %-10s %r" % (h["off"], h["text"]))
            print()

    # The EXE's GUID-style global name.
    de = open(EXE, "rb").read()
    print("  EXE strings containing 'Global\\':")
    for h in cstrings_containing(de, b"Global\\"):
        print("     %-10s %r" % (h["off"], h["text"]))
        rep.setdefault("exe_global", []).append(h)

    db = open(BASE, "rb").read()
    print()
    print("  Base.dll strings containing 'Global\\' / 'SharedInfo':")
    for pat in (b"Global\\", b"SharedInfo"):
        for h in cstrings_containing(db, pat):
            print("     %-10s %r" % (h["off"], h["text"]))
            rep.setdefault("base_global", []).append(h)

    rep["contract_named_objects"] = {
        "shared_memory_prefix": "Global\\SharedSpaceName_",
        "opened_with": "OpenFileMappingA + MapViewOfFile",
        "pipe_transport": "CreateFileA/CreateFileW on a pipe path "
                          "(CreateNamedPipe/ConnectNamedPipe are NOT imported)",
        "host_process": "IIPSHostApp.exe",
        "ifs_library": "IFS.dll",
        "note": "The provider opens these; it does not create the pipe server side "
                "in-process, which is consistent with IIPSHostApp.exe being a "
                "separate process (see LaunchIIPSHostApp in the log table).",
    }
    print()
    print("  CONTRACT NAMED OBJECTS")
    for k, v in rep["contract_named_objects"].items():
        print("     %-22s %s" % (k, v))

    with open(os.path.join(OUT, "t16_pipe_and_sharename.json"), "w",
              encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t16_pipe_and_sharename.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
