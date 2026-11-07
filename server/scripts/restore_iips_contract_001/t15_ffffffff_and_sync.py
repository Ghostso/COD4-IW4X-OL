"""RESTORE-IIPS-CONTRACT-001 / Task 11 - the 0xFFFFFFFF termination path and the
synchronisation/named-object contract.

Part A: 0xFFFFFFFF.
  Condition B self-terminated with exit code 0xFFFFFFFF in 4 of 5 EB-003 runs.
  This part enumerates every in-image producer of the literal 0xFFFFFFFF in the
  EXE, Base.dll and both providers, so the value's origin is located rather than
  guessed from its shape.

Part B: the synchronisation / named-object surface the provider contract needs.
  From the static contract (Task 06) the provider must, before it can report
  ready:
      * create a window (IIPSWndMsgProcessor)
      * LoadLibrary IFS.dll
      * launch IIPSHostApp.exe
      * open a named pipe to it (m_iipsClient)
      * open shared state (m_iipsShareState / m_sharedSpaces)
  This part enumerates the named-object and pipe string literals that those steps
  would use, so a runtime observer knows exactly what to look for.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore_iips_contract_001", "evidence")
FILES = {
    "EXE": os.path.join(GAME, "codoMP_client_shipRetail.exe"),
    "Base.dll": os.path.join(GAME, "codoMP_client_shipRetailBase.dll"),
    "iips.dll": os.path.join(GAME, "IIPS", "iips.dll"),
    "LocalRM_v3.dll": os.path.join(ROOT, "LocalRM_v3.dll"),
}


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


def secname(secs, off):
    for s in secs:
        if s["raw"] <= off < s["raw"] + s["rsize"]:
            return s["name"]
    return None


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}
    print("=== Task 11: 0xFFFFFFFF producer + sync/named-object contract ===")
    print()

    # ---- Part A: literal 0xFFFFFFFF producers ----
    print("Part A - literal 0xFFFFFFFF occurrences")
    needle = struct.pack("<I", 0xFFFFFFFF)
    rep["ffffffff"] = {}
    for label, path in FILES.items():
        d = open(path, "rb").read()
        pe, secs = sections(d)
        offs = []
        p = 0
        while True:
            i = d.find(needle, p)
            if i < 0:
                break
            offs.append(i)
            p = i + 1
        in_code = []
        for o in offs:
            s = secname(secs, o)
            if s in (".text", ".tp3", ".tvm0", ".localrm"):
                in_code.append((o, s))
        rep["ffffffff"][label] = {
            "total": len(offs),
            "in_executable_sections": len(in_code),
            "sample": ["0x%X(%s)" % (o, s) for o, s in in_code[:8]],
        }
        print("   %-16s total=%-6d in-exec=%-6d %s"
              % (label, len(offs), len(in_code),
                 ", ".join("0x%X(%s)" % (o, s) for o, s in in_code[:4])))

    # ---- Part B: the sync / named-object surface ----
    print()
    print("Part B - named-object / pipe / dependency strings")
    patterns = [b"\\\\.\\pipe\\", b"IIPSHostApp", b"IFS.dll", b"iips.dll",
                b"Global\\", b"Local\\", b"_iips", b"ShareInfo", b"SharedInfo",
                b"FileMapping", b"m_iipsClient", b"m_iipsShareState"]
    rep["named_object_strings"] = {}
    for label, path in FILES.items():
        d = open(path, "rb").read()
        pe, secs = sections(d)
        found = {}
        for pat in patterns:
            c = d.count(pat)
            if c:
                first = d.find(pat)
                e = d.find(b"\0", first, first + 200)
                txt = d[first:e].decode("latin1", "replace") if e > 0 else None
                found[pat.decode("latin1", "replace")] = {
                    "count": c,
                    "first_off": "0x%X" % first,
                    "first_section": secname(secs, first),
                    "first_text": txt,
                }
        rep["named_object_strings"][label] = found
        if found:
            print("   %s:" % label)
            for k, v in found.items():
                print("      %-16s x%-4d %-8s %r"
                      % (k, v["count"], v["first_section"], v["first_text"]))

    # The provider's import surface tells which sync primitives it can use.
    print()
    print("   pipe/sync imports in iips.dll:")
    d = open(FILES["iips.dll"], "rb").read()
    for api in (b"CreateFileA", b"CreateFileW", b"CreateNamedPipeA", b"CreateNamedPipeW",
                b"ConnectNamedPipe", b"WaitNamedPipeA", b"ReadFile", b"WriteFile",
                b"CreateEventA", b"CreateEventW", b"OpenEventA", b"OpenEventW",
                b"SetEvent", b"WaitForSingleObject", b"WaitForMultipleObjects",
                b"CreateMutexA", b"OpenMutexA", b"CreateFileMappingA",
                b"OpenFileMappingA", b"MapViewOfFile", b"CreateThread",
                b"PostMessageA", b"CreateWindowExA", b"ShellExecuteA"):
        c = d.count(api)
        if c:
            print("      %-22s %d" % (api.decode(), c))
    rep["iips_sync_imports_present"] = [
        a.decode() for a in (b"CreateFileA", b"CreateFileW", b"CreateNamedPipeA",
                             b"CreateNamedPipeW", b"ConnectNamedPipe",
                             b"WaitNamedPipeA", b"ReadFile", b"WriteFile",
                             b"CreateEventA", b"CreateEventW", b"OpenEventA",
                             b"OpenEventW", b"SetEvent", b"WaitForSingleObject",
                             b"WaitForMultipleObjects", b"CreateMutexA",
                             b"OpenMutexA", b"CreateFileMappingA",
                             b"OpenFileMappingA", b"MapViewOfFile", b"CreateThread",
                             b"PostMessageA", b"CreateWindowExA", b"ShellExecuteA")
        if d.count(a)]

    with open(os.path.join(OUT, "t15_ffffffff_and_sync.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print()
    print("wrote %s" % os.path.join(OUT, "t15_ffffffff_and_sync.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
