import datetime
import os
import struct

import capstone
import pefile

BASE = r"D:\BaiduNetdiskDownload\使命召唤OL\WeGame"
FACTORY = {"CreateComponent", "GetComponentIDs", "SetDLLRegistry", "SetFactoryHandle"}


def exports(path):
    try:
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
        )
    except Exception:
        return None, set()
    entry = getattr(pe, "DIRECTORY_ENTRY_EXPORT", None)
    names = set()
    if entry is not None and not isinstance(entry, list):
        for e in getattr(entry, "symbols", []):
            if e.name:
                names.add(e.name.decode("ascii", "replace"))
    return pe, names


def main():
    print("=" * 100)
    print("WeGame tree: Tenio factory DLLs and immediate-985 hits")
    print("=" * 100)

    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = True

    scanned = 0
    for dirpath, dirnames, filenames in os.walk(BASE):
        dirnames[:] = [d for d in dirnames if d.lower() not in ("node_modules", ".git")]
        for name in filenames:
            if not name.lower().endswith((".dll", ".exe")):
                continue
            path = os.path.join(dirpath, name)
            try:
                if os.path.getsize(path) > 200 * 1024 * 1024:
                    continue
            except Exception:
                continue
            scanned += 1
            pe, names = exports(path)
            if not names:
                continue
            is_factory = bool(names & FACTORY)
            try:
                data = open(path, "rb").read()
            except Exception:
                continue
            needle = struct.pack("<I", 985)
            offs = []
            s = 0
            while True:
                i = data.find(needle, s)
                if i < 0:
                    break
                offs.append(i)
                s = i + 1
            text_hits = []
            for off in offs:
                try:
                    rva = pe.get_rva_from_offset(off)
                    sec = pe.get_section_by_rva(rva)
                    secname = sec.Name.decode("ascii", "replace").strip("\x00") if sec else "?"
                except Exception:
                    continue
                if secname != ".text":
                    continue
                ins = None
                for insn in md.disasm(data[max(0, off - 16):off + 16], max(0, (rva or 0) - 16)):
                    if (rva or 0) == insn.address:
                        ins = "%s %s" % (insn.mnemonic, insn.op_str)
                        break
                text_hits.append((hex(off), ins))

            if is_factory or text_hits:
                rel = os.path.relpath(path, BASE)
                ts = None
                try:
                    ts = datetime.datetime.utcfromtimestamp(pe.FILE_HEADER.TimeDateStamp)
                except Exception:
                    pass
                print(f"  {rel}")
                print(f"    size={os.path.getsize(path)} pe_ts={ts}")
                print(f"    factory={is_factory} exports={sorted(names & FACTORY)}")
                if text_hits:
                    for off, ins in text_hits[:10]:
                        print(f"    985-immediate off={off}  {ins}")

    print(f"\nscanned={scanned}")


if __name__ == "__main__":
    main()
