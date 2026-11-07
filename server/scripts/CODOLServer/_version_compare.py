import datetime
import os

import pefile

ROOTS = {
    "sandbox": r"run_codol_001\sandbox_ifs1_20260923\IIPS",
    "original": r"COD OL\IIPS",
}

TARGETS = [
    ("IIPSHostApp.exe", ""),
    ("Tenio\\June.dll", ""),
    ("Tenio\\TenTPF.dll", ""),
    ("Tenio\\TenFact.dll", ""),
    ("Tenio\\ScriptManager.dll", ""),
    ("Tenio\\MemoryAlloctor.dll", ""),
]


def version_info(path):
    # Read the resource version block without pywin32.
    try:
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(
            directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_RESOURCE"]]
        )
    except Exception as e:
        return {"error": str(e)}

    def walk(entries):
        for entry in entries:
            if hasattr(entry, "directory"):
                yield from walk(entry.directory.entries)
            elif hasattr(entry, "data"):
                yield entry

    out = {}
    try:
        if hasattr(pe, "DIRECTORY_ENTRY_RESOURCE"):
            for entry in walk(pe.DIRECTORY_ENTRY_RESOURCE.entries):
                if entry.id != pefile.RESOURCE_TYPE["RT_VERSION"]:
                    continue
                data_rva = entry.data.struct.OffsetToData
                size = entry.data.struct.Size
                data = pe.get_memory_mapped_image()[data_rva:data_rva + size]
                # Parse the version resource minimally.
                import struct
                # UTF-16 key/value pairs appear after the fixed header.
                text = data.decode("utf-16-le", "ignore")
                for key in ("FileVersion", "ProductVersion", "CompanyName",
                            "FileDescription", "ProductName", "OriginalFilename"):
                    idx = text.find(key)
                    if idx >= 0:
                        tail = text[idx + len(key):idx + len(key) + 60]
                        value = tail.replace("\x00", " ").strip()
                        out[key] = value.split("  ")[0].strip()
    except Exception as e:
        out["parse_error"] = str(e)
    return out


def main():
    for label, root in ROOTS.items():
        print("=" * 100)
        print(label, root)
        for rel, _ in TARGETS:
            path = os.path.join(root, rel)
            if not os.path.exists(path):
                print(f"  {rel}: MISSING")
                continue
            st = os.stat(path)
            print("-" * 90)
            print(f"  {rel}")
            print(f"    size={st.st_size}  mtime={datetime.datetime.fromtimestamp(st.st_mtime)}")
            print(f"    ctime={datetime.datetime.fromtimestamp(st.st_ctime)}")
            vi = version_info(path)
            for k in ("FileVersion", "ProductVersion", "CompanyName",
                      "FileDescription", "ProductName", "OriginalFilename"):
                if k in vi:
                    print(f"    {k}={vi[k]}")
            for k, v in vi.items():
                if k not in ("FileVersion", "ProductVersion", "CompanyName",
                             "FileDescription", "ProductName", "OriginalFilename"):
                    print(f"    {k}={v}")

            # PE timestamp is the linker build timestamp.
            try:
                pe = pefile.PE(path, fast_load=True)
                ts = pe.FILE_HEADER.TimeDateStamp
                print(f"    PE_TimeDateStamp={ts} ({datetime.datetime.utcfromtimestamp(ts)} UTC)")
                print(f"    Machine=0x{pe.FILE_HEADER.Machine:04X}")
                print(f"    SizeOfImage=0x{pe.OPTIONAL_HEADER.SizeOfImage:X}")
            except Exception as e:
                print(f"    PE parse error: {e}")


if __name__ == "__main__":
    main()
