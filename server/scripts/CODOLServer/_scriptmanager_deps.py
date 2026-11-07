import os

import pefile

IIPS = r"run_codol_001\sandbox_ifs1_20260923\IIPS"
ORIG = r"COD OL\IIPS"


def dump(path, label):
    print("=" * 88)
    print(label, path)
    if not os.path.exists(path):
        print("  MISSING")
        return
    try:
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
        ])
    except Exception as e:
        print("  pe error:", e)
        return

    print("  size:", os.path.getsize(path))
    print("  --- static imports ---")
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        dll = entry.dll.decode("ascii", "replace")
        names = []
        for imp in getattr(entry, "imports", [])[:14]:
            names.append(imp.name.decode("ascii", "replace") if imp.name else str(imp.ordinal))
        print(f"    {dll}: {', '.join(names)}")

    print("  --- delay imports ---")
    for entry in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []):
        dll = entry.dll.decode("ascii", "replace")
        names = []
        for imp in getattr(entry, "imports", [])[:14]:
            names.append(imp.name.decode("ascii", "replace") if imp.name else str(imp.ordinal))
        print(f"    {dll}: {', '.join(names)}")


def check_availability(dll_names, roots):
    print("\n  --- availability of referenced DLLs ---")
    for d in dll_names:
        found = []
        for root in roots:
            if not os.path.isdir(root):
                continue
            for dp, _, fs in os.walk(root):
                for f in fs:
                    if f.lower() == d.lower():
                        found.append(os.path.join(dp, f))
        print(f"    {d}: {'FOUND ' + str(found[:2]) if found else 'NOT FOUND under IIPS'}")


def main():
    for label, root in (("SANDBOX", IIPS), ("ORIGINAL", ORIG)):
        for name in ("ScriptManager.dll", "MemoryAlloctor.dll"):
            p = os.path.join(root, "Tenio", name)
            dump(p, label)

    print("\n" + "=" * 88)
    print("ScriptManager.dll referenced DLLs vs IIPS tree")
    p = os.path.join(IIPS, "Tenio", "ScriptManager.dll")
    if os.path.exists(p):
        pe = pefile.PE(p, fast_load=True)
        pe.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT"],
        ])
        names = []
        for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
            names.append(entry.dll.decode("ascii", "replace"))
        for entry in getattr(pe, "DIRECTORY_ENTRY_DELAY_IMPORT", []):
            names.append(entry.dll.decode("ascii", "replace"))
        check_availability(names, [IIPS, r"COD OL\IIPS"])


if __name__ == "__main__":
    main()
