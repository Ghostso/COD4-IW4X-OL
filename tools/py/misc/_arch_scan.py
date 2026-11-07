"""CODOL component / protocol static scanner (READ-ONLY).

Produces address-level artifacts from the decrypted runtime image so that
xrefs are meaningful (the on-disk .tp3 code section is encrypted, so xref
scanning there yields nothing).

Usage:
  python -X utf8 _arch_scan.py modules
  python -X utf8 _arch_scan.py imports
  python -X utf8 _arch_scan.py endpoints
  python -X utf8 _arch_scan.py xref <hexva>

Outputs (written next to this script):
  arch_modules.csv, arch_imports.csv, arch_endpoints.csv

Constraints: no game run, no process memory access, no modification of
existing files (only new files are created).
"""
import hashlib
import os
import re
import struct
import sys

import pefile

ROOT = os.path.dirname(os.path.abspath(__file__))
IMAGE = os.path.join(ROOT, "CODOLServer", "_mainline",
                     "_dyn100_run_20260925_182324", "live", "image_best.bin")
GAMEDIR = os.path.join(ROOT, "COD OL")
BASE = 0x400000


def load():
    with open(IMAGE, "rb") as f:
        return f.read()


def pe_of(path):
    return pefile.PE(path, fast_load=True)


# ---------------------------------------------------------------- modules
PROTECT_MARK = {
    b".tp3": "TenProtect TP3",
    b".tvm0": "TenProtect VM0",
    b".tvm40": "TenProtect VM4.0",
    b".tvm41": "TenProtect VM4.1",
    b".vmp0": "VMProtect",
    b".vmp1": "VMProtect",
}


def cmd_modules():
    rows = []
    for name in sorted(os.listdir(GAMEDIR)):
        p = os.path.join(GAMEDIR, name)
        if not os.path.isfile(p):
            continue
        low = name.lower()
        if not (low.endswith(".dll") or low.endswith(".exe")):
            continue
        size = os.path.getsize(p)
        h = hashlib.sha256()
        with open(p, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        protect = ""
        machine = ""
        try:
            pe = pe_of(p)
            machine = "x64" if pe.FILE_HEADER.Machine == 0x8664 else "x86"
            marks = set()
            for s in pe.sections:
                nm = s.Name.rstrip(b"\x00")
                if nm in PROTECT_MARK:
                    marks.add(PROTECT_MARK[nm])
            protect = ";".join(sorted(marks))
            pe.close()
        except Exception as exc:  # noqa: BLE001
            protect = "parse-error:%s" % exc.__class__.__name__
        rows.append((name, machine, size, protect, h.hexdigest()))
    out = os.path.join(ROOT, "arch_modules.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("module|arch|size|protection|sha256\n")
        for r in rows:
            f.write("%s|%s|%d|%s|%s\n" % r)
    print("wrote %s (%d rows)" % (out, len(rows)))
    for r in rows:
        print("  %-42s %-4s %10d  %s" % (r[0], r[1], r[2], r[3]))
    return 0


# ---------------------------------------------------------------- imports
NET_DLLS = ("ws2_32", "wininet", "winhttp", "urlmon", "wsock32", "iphlpapi",
            "dnsapi", "secur32", "crypt32", "ncrypt", "schannel", "mswsock")


IAT_DUMP = os.path.join(GAMEDIR, "scratch_iat.txt")


def _iat_rows_from_dump(path):
    """Parse the resolved runtime IAT dump (addr | DLL:FUNC | DLL:FUNC ...)."""
    rows = []
    with open(path, "r", encoding="latin-1") as f:
        for line in f:
            parts = [p.strip() for p in line.split("|")]
            if not parts:
                continue
            m = re.match(r"^(0x[0-9a-fA-F]+)\s+(\S+)$", parts[0])
            if m:
                parts = [m.group(2)] + parts[1:]
                slot = m.group(1)
            else:
                slot = ""
            for tok in parts:
                if ":" in tok:
                    dll, func = tok.split(":", 1)
                    rows.append((dll, func, slot))
    return rows


def cmd_imports():
    rows = []
    src = ""
    try:
        pe = pe_of(IMAGE)
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]])
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            dll = entry.dll.decode("latin-1")
            for imp in entry.imports:
                fname = imp.name.decode("latin-1") if imp.name else "ord#%d" % imp.ordinal
                rows.append((dll, fname, "%08X" % (imp.address or 0)))
        src = "image_best.bin"
    except Exception:  # noqa: BLE001
        rows = []
    if os.path.isfile(IAT_DUMP):
        rows = _iat_rows_from_dump(IAT_DUMP)
        src = "scratch_iat.txt (runtime resolved IAT)"
    out = os.path.join(ROOT, "arch_imports.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("dll|func|iat_slot\n")
        for r in rows:
            f.write("%s|%s|%s\n" % r)
    print("wrote %s (%d rows) [source: %s]" % (out, len(rows), src))
    seen = {}
    for dll, _, _ in rows:
        seen[dll] = seen.get(dll, 0) + 1
    for dll in sorted(seen):
        flag = "  <-- network" if dll.lower().split(".")[0] in NET_DLLS else ""
        print("  %-24s %4d%s" % (dll, seen[dll], flag))
    return 0



# ---------------------------------------------------------------- endpoints
HOST_RE = re.compile(r"^[a-z0-9][a-z0-9\.\-]{3,80}\.(com|net|org|cn|qq\.com)$",
                     re.I)
PATH_RE = re.compile(r"^/[a-z0-9_\.\-/]*(auth|queue|title|member|gateway|"
                     r"login|lobby|storage|profile)[a-z0-9_\.\-/]*$", re.I)


def kind_of(s):
    low = s.lower()
    if "http://" in low or "https://" in low:
        return "url"
    if s.startswith("DW-") or s.startswith("dw_"):
        return "dw-header/var"
    if "demonware" in low or "stun" in low:
        return "stun"
    if low.endswith(".ini") or low.endswith(".pem") or low.endswith(".tdr"):
        return "config-file"
    if low.startswith("bd_") or low.startswith("bdlobby"):
        return "dw-code"
    if low.startswith("dwlobby") or (s.startswith("DW_") and "_" in s):
        return "dw-event"
    if HOST_RE.match(s):
        return "host"
    if PATH_RE.match(s):
        return "path"
    return ""


def find_strings(data, minlen=4):
    for m in re.finditer(rb"[\x20-\x7e]{%d,300}" % minlen, data):
        yield BASE + m.start(), m.group(0).decode("ascii", "ignore")


def xref_abs4(data, target):
    pat = struct.pack("<I", target)
    res, i = [], data.find(pat)
    while i != -1:
        res.append(BASE + i)
        i = data.find(pat, i + 1)
    return res


def xref_push(data, target):
    pat = b"\x68" + struct.pack("<I", target)
    res, i = [], data.find(pat)
    while i != -1:
        res.append(BASE + i)
        i = data.find(pat, i + 1)
    return res


def cmd_endpoints():
    data = load()
    rows = []
    for va, s in find_strings(data):
        k = kind_of(s)
        if not k:
            continue
        a = xref_abs4(data, va)
        p = xref_push(data, va)
        rows.append((k, s, "%08X" % va,
                     ";".join("%08X" % x for x in a),
                     ";".join("%08X" % x for x in p)))
    rows.sort(key=lambda r: (r[0], r[1]))
    out = os.path.join(ROOT, "arch_endpoints.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("kind|value|va|abs4_refs|push_refs\n")
        for r in rows:
            f.write("%s|%s|%s|%s|%s\n" % r)
    print("wrote %s (%d rows)" % (out, len(rows)))
    for r in rows:
        if r[0] in ("url", "host", "stun", "config-file"):
            print("  %-12s %-46s %s push=%s" % (r[0], r[1][:46], r[2],
                                                (r[4] or r[3])[:44]))
    return 0


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "modules":
        return cmd_modules()
    if cmd == "imports":
        return cmd_imports()
    if cmd == "endpoints":
        return cmd_endpoints()
    if cmd == "xref":
        data = load()
        t = int(argv[1], 16)
        print("abs4:", ["%08X" % x for x in xref_abs4(data, t)])
        print("push:", ["%08X" % x for x in xref_push(data, t)])
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
