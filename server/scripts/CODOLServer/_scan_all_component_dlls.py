import datetime
import hashlib
import os
import struct

import capstone
import pefile

BASE = r"D:\BaiduNetdiskDownload\使命召唤OL"
EXCLUDE_DIRS = {
    "backups", "runs", "__pycache__", "vodcache", "iipsdownload",
    ".git", "logs", "node_modules",
}
FACTORY = {"CreateComponent", "GetComponentIDs", "SetDLLRegistry", "SetFactoryHandle"}


def sha256(path, limit=200 * 1024 * 1024):
    h = hashlib.sha256()
    read = 0
    with open(path, "rb") as f:
        while True:
            chunk = f.read(1024 * 1024)
            if not chunk:
                break
            h.update(chunk)
            read += len(chunk)
            if read > limit:
                break
    return h.hexdigest()


def exports(path):
    try:
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
        )
    except Exception as e:
        return None, None, str(e)

    entry = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    if entry is None or isinstance(entry, list):
        return pe, set(), None
    names = set()
    for exp in getattr(entry, "symbols", []):
        if exp.name:
            names.add(exp.name.decode("ascii", "replace"))
    return pe, names, None


def scan_immediate_985(path, pe):
    try:
        data = open(path, "rb").read()
    except Exception:
        return [], None
    needle = struct.pack("<I", 985)
    hits = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        hits.append(i)
        start = i + 1

    results = []
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    for off in hits:
        try:
            rva = pe.get_rva_from_offset(off)
            sec = pe.get_section_by_rva(rva)
            secname = sec.Name.decode("ascii", "replace").strip("\x00") if sec else "?"
        except Exception:
            rva, secname = None, "?"
        # Decode the instruction that contains this immediate.
        text = None
        try:
            for insn in md.disasm(data[off - 16:off + 16], (rva or 0) - 16):
                if insn.address <= (rva or 0) < insn.address + insn.size:
                    text = "%s %s" % (insn.mnemonic, insn.op_str)
                    break
        except Exception:
            pass
        results.append((off, rva, secname, text))
    return results, data


def main():
    factory_dlls = []
    immediate_985 = []
    scanned = 0

    for dirpath, dirnames, filenames in os.walk(BASE):
        dirnames[:] = [d for d in dirnames if d.lower() not in EXCLUDE_DIRS]
        for name in filenames:
            if not name.lower().endswith((".dll", ".exe")):
                continue
            path = os.path.join(dirpath, name)
            try:
                size = os.path.getsize(path)
                if size > 200 * 1024 * 1024:
                    continue
            except Exception:
                continue
            scanned += 1
            pe, names, err = exports(path)
            if names is not None and (names & FACTORY):
                rel = os.path.relpath(path, BASE)
                st = os.stat(path)
                ts = None
                try:
                    ts = pe.FILE_HEADER.TimeDateStamp
                except Exception:
                    pass
                factory_dlls.append({
                    "path": rel,
                    "size": size,
                    "exports": sorted(names & FACTORY),
                    "pe_timestamp": ts,
                    "mtime": datetime.datetime.fromtimestamp(st.st_mtime).isoformat(),
                    "sha256": sha256(path),
                })

            hits, data = scan_immediate_985(path, pe) if pe else ([], None)
            exact = [h for h in hits if h[1] is not None and h[2] == ".text"]
            if exact:
                immediate_985.append({
                    "path": os.path.relpath(path, BASE),
                    "hits": [
                        {
                            "file_off": hex(off),
                            "rva": "0x%X" % rva,
                            "instruction": instruction,
                        }
                        for off, rva, sec, instruction in exact
                    ],
                    "has_factory": bool(names and (names & FACTORY)),
                })

    print("scanned files:", scanned)
    print()
    print("=" * 100)
    print("DLLs with Tenio component factory exports")
    print("=" * 100)
    for row in sorted(factory_dlls, key=lambda r: r["path"]):
        print(f"  {row['path']}")
        print(f"    size={row['size']} pe_ts={row['pe_timestamp']} mtime={row['mtime']}")
        print(f"    exports={row['exports']}")
        print(f"    sha256={row['sha256']}")

    print()
    print("=" * 100)
    print("Files with an immediate 985 in .text")
    print("=" * 100)
    for row in sorted(immediate_985, key=lambda r: r["path"]):
        print(f"  {row['path']}  has_factory={row['has_factory']}")
        for h in row["hits"][:12]:
            print(f"    off={h['file_off']} rva={h['rva']}  {h['instruction']}")


if __name__ == "__main__":
    main()
