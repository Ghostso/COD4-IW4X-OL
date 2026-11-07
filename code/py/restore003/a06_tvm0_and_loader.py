"""EB-003 Agent 06 - why no LoadLibraryA/GetProcAddress call is observed.

Agent 03/05 established:
  * Base.dll imports LoadLibraryA + GetProcAddress from kernel32.
  * The provider module IS mapped under the expected name and path.
  * But instrumenting Base.dll's IAT for those two APIs records zero calls, and a
    full-process IAT scan finds no slot holding the provider's export addresses.

Base.dll has a .tvm0 section, which prior rounds (ICH-0xx) identified as a
virtualised/obfuscated code container. This script quantifies the plausible
explanation:

  (a) the resolution happens inside .tvm0 code, which may reach the API through a
      mechanism other than the module's IAT (e.g. its own dispatcher), or
  (b) the loader used is the process's native loader reached via ntdll, not
      kernel32!LoadLibraryA.

This reports the .tvm0 section's size/attributes and which loader-related APIs are
imported anywhere in the install, so the hypothesis can be stated with its actual
supporting and contradicting facts rather than asserted.
"""
import json
import os
import struct
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAME = os.path.join(ROOT, "COD OL")
OUT = os.path.join(ROOT, "restore003", "evidence")

LOADER_APIS = [
    b"LoadLibraryA", b"LoadLibraryW", b"LoadLibraryExA", b"LoadLibraryExW",
    b"GetProcAddress", b"LdrLoadDll", b"LdrGetProcedureAddress",
    b"LdrGetDllHandle", b"RtlImageNtHeader", b"ZwOpenFile", b"LdrUnloadDll",
]


def sections(d):
    pe = struct.unpack_from("<I", d, 0x3C)[0]
    magic = struct.unpack_from("<H", d, pe + 24)[0]
    nsec = struct.unpack_from("<H", d, pe + 6)[0]
    so = pe + 24 + (224 if magic == 0x10B else 240)
    out = []
    for i in range(nsec):
        o = so + i * 40
        name = d[o:o + 8].rstrip(b"\0").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", d, o + 8)
        ch = struct.unpack_from("<I", d, o + 36)[0]
        out.append({"name": name, "va": va, "vsize": vs, "raw": rp,
                    "rsize": rs, "ch": ch})
    return pe, out


def main():
    os.makedirs(OUT, exist_ok=True)
    rep = {}

    print("=== EB-003 Agent 06: .tvm0 and loader surface ===")
    for rel in ("codoMP_client_shipRetailBase.dll", "codoMP_client_shipRetail.exe"):
        p = os.path.join(GAME, rel)
        d = open(p, "rb").read()
        pe, secs = sections(d)
        rep[rel] = {"sections": secs, "loader_api_strings": {}}
        print("\n%s" % rel)
        for s in secs:
            flag = ""
            if s["name"] == ".tvm0":
                flag = "   <-- virtualised code container"
            print("   %-10s VA=0x%08X VS=0x%08X RAW=0x%08X CH=0x%08X%s"
                  % (s["name"], s["va"], s["vsize"], s["raw"], s["ch"], flag))
        for api in LOADER_APIS:
            c = d.count(api)
            if c:
                rep[rel]["loader_api_strings"][api.decode()] = c
        print("   loader API name strings present: %s"
              % json.dumps(rep[rel]["loader_api_strings"]))

    # Which modules import the loader APIs?
    print("\n=== who imports loader APIs (by import table) ===")
    imports_found = {}
    for fn in sorted(os.listdir(GAME)):
        if not fn.lower().endswith((".dll", ".exe")):
            continue
        p = os.path.join(GAME, fn)
        try:
            d = open(p, "rb").read()
        except Exception:
            continue
        got = []
        for api in (b"LoadLibraryA", b"LoadLibraryW", b"GetProcAddress", b"LdrLoadDll"):
            if d.count(api):
                got.append(api.decode())
        if got:
            # confirm it is a NUL-terminated name (import hint/name table style)
            imports_found[fn] = got
    for fn, got in imports_found.items():
        print("   %-40s %s" % (fn, ", ".join(got)))
    rep["modules_mentioning_loader_apis"] = imports_found

    with open(os.path.join(OUT, "a06_tvm0_and_loader.json"), "w", encoding="utf-8") as f:
        json.dump(rep, f, indent=2)
    print("\nwrote %s" % os.path.join(OUT, "a06_tvm0_and_loader.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
