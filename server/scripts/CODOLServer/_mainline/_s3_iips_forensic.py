"""S3: iips.dll tamper forensics.

Determines which iips.dll copies are genuine Tencent originals by checking
Authenticode status, SHA256 and mtime, then byte-diffs the pristine copy
against the currently installed one.

Read-only. Does not modify the game tree.
"""
import hashlib
import os
import struct
import subprocess
import sys

ROOT = r"D:\BaiduNetdiskDownload\使命召唤OL"
CURRENT = os.path.join(ROOT, r"COD OL\IIPS\iips.dll")
PRISTINE = os.path.join(ROOT, r"工具\EX035_DIR\IIPS\iips.dll")

DIRNAMES = [
    "EXPORT", "IMPORT", "RESOURCE", "EXCEPTION", "SECURITY", "BASERELOC",
    "DEBUG", "ARCH", "GLOBALPTR", "TLS", "LOAD_CONFIG", "BOUND_IMPORT",
    "IAT", "DELAY_IMPORT", "COM_DESCRIPTOR", "RESERVED",
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sig_status(path):
    ps = (
        "$s=Get-AuthenticodeSignature -LiteralPath '%s';"
        "Write-Output $s.Status" % path
    )
    try:
        out = subprocess.run(
            ["powershell.exe", "-NoProfile", "-Command", ps],
            capture_output=True, text=True, timeout=60,
        )
        return out.stdout.strip() or "?"
    except Exception as exc:  # pragma: no cover
        return "ERR:%s" % exc


def sections(data):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    n = struct.unpack_from("<H", data, pe + 6)[0]
    opt = pe + 24
    sh = opt + struct.unpack_from("<H", data, pe + 20)[0]
    out = []
    for i in range(n):
        o = sh + i * 40
        name = bytes(data[o:o + 8]).rstrip(b"\x00").decode("latin1")
        vs, va, rs, rp = struct.unpack_from("<IIII", data, o + 8)
        out.append((name, va, vs, rs, rp))
    return out


def data_dirs(data):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    opt = pe + 24
    n = struct.unpack_from("<I", data, opt + 92)[0]
    out = []
    for i in range(n):
        o = opt + 96 + i * 8
        rva, size = struct.unpack_from("<II", data, o)
        out.append((DIRNAMES[i] if i < len(DIRNAMES) else str(i), rva, size))
    return out


def cert_blob(data):
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    opt = pe + 24
    o = opt + 96 + 4 * 8
    rva, size = struct.unpack_from("<II", data, o)
    return rva, size, data[rva:rva + size]


def walk_copies():
    found = {}
    for base, _dirs, files in os.walk(ROOT):
        for fn in files:
            if fn.lower() != "iips.dll":
                continue
            p = os.path.join(base, fn)
            try:
                h = sha256(p)
                st = os.stat(p)
            except OSError:
                continue
            key = (h[:8].upper(), st.st_size)
            found.setdefault(key, []).append((p, st.st_mtime))
    return found


def main():
    print("=" * 74)
    print("iips.dll tamper forensics")
    print("=" * 74)

    for tag, path in (("PRISTINE", PRISTINE), ("CURRENT", CURRENT)):
        if not os.path.exists(path):
            print("%-9s MISSING %s" % (tag, path))
            continue
        data = open(path, "rb").read()
        rva, size, blob = cert_blob(data)
        import datetime
        mt = datetime.datetime.fromtimestamp(os.stat(path).st_mtime)
        print()
        print("%-9s %s" % (tag, path))
        print("  size=%d sha256=%s" % (len(data), sha256(path)))
        print("  mtime=%s" % mt)
        print("  authenticode=%s" % sig_status(path))
        print("  cert blob rva=%X size=%X sha256=%s"
              % (rva, size, hashlib.sha256(blob).hexdigest()))

    print()
    print("--- copies on disk ---")
    for (h, sz), lst in sorted(walk_copies().items(), key=lambda kv: kv[0][1]):
        print("  size=%-7d sha=%s copies=%d" % (sz, h, len(lst)))

    if not (os.path.exists(PRISTINE) and os.path.exists(CURRENT)):
        print("cannot diff: missing file")
        return 0

    a = open(PRISTINE, "rb").read()
    b = open(CURRENT, "rb").read()
    if len(a) != len(b):
        print("sizes differ, section-level compare only")

    print()
    print("--- data directories ---")
    for tag, d in (("PRISTINE", a), ("CURRENT", b)):
        items = [x for x in data_dirs(d) if x[1] or x[2]]
        print("  %-9s %s" % (tag, ", ".join("%s=%X/%X" % i for i in items)))

    diffs = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
    print()
    print("--- byte diff: %d bytes differ ---" % len(diffs))
    if diffs:
        runs = []
        s = p = diffs[0]
        for i in diffs[1:]:
            if i == p + 1:
                p = i
            else:
                runs.append((s, p))
                s = p = i
        runs.append((s, p))
        print("  %d runs; largest 12:" % len(runs))
        for (s, e) in sorted(runs, key=lambda r: r[1] - r[0], reverse=True)[:12]:
            print("    off %08X..%08X len=%d" % (s, e, e - s + 1))
            print("      pristine: %s" % a[s:min(s + 32, e + 1)].hex())
            print("      current : %s" % b[s:min(s + 32, e + 1)].hex())
    return 0


if __name__ == "__main__":
    sys.exit(main())
