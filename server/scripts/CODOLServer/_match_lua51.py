import os

import pefile

SCRIPT = r"run_codol_001\sandbox_ifs1_20260923\IIPS\Tenio\ScriptManager.dll"
LUA_CANDIDATES = [
    r"COD OL\Cross\Lua51.dll",
    r"COD OL\Cross\LiveUpdate\Lua51.dll",
    r"COD OL\TCLS\Lua51.dll",
    r"WeGame\Lua51.dll",
    r"WeGame\apps\Rail\Lua51.dll",
]


def imports_from(pe, dll_name):
    names = set()
    for entry in getattr(pe, "DIRECTORY_ENTRY_IMPORT", []):
        if entry.dll.decode("ascii", "replace").lower() == dll_name.lower():
            for imp in entry.imports:
                if imp.name:
                    names.add(imp.name.decode("ascii", "replace"))
                else:
                    names.add("#%d" % imp.ordinal)
    return names


def exports_of(path):
    pe = pefile.PE(path, fast_load=True)
    pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]]
    )
    names = set()
    for exp in getattr(pe, "DIRECTORY_ENTRY_EXPORT", []).symbols:
        if exp.name:
            names.add(exp.name.decode("ascii", "replace"))
    return names, pe


def main():
    script_pe = pefile.PE(SCRIPT, fast_load=True)
    script_pe.parse_data_directories(
        directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"]]
    )
    needed = imports_from(script_pe, "Lua51.dll")
    print("ScriptManager needs", len(needed), "Lua51 imports")
    print("  sample:", sorted(needed)[:20])

    for path in LUA_CANDIDATES:
        print("=" * 80)
        if not os.path.exists(path):
            print(path, "MISSING")
            continue
        try:
            exports, pe = exports_of(path)
        except Exception as e:
            print(path, "parse error", e)
            continue
        missing = sorted(needed - exports)
        print(path)
        print("  size:", os.path.getsize(path))
        print("  exports:", len(exports), "missing:", len(missing))
        if missing:
            print("  first missing:", missing[:20])
        else:
            print("  MATCH: all ScriptManager Lua imports are exported")


if __name__ == "__main__":
    main()
