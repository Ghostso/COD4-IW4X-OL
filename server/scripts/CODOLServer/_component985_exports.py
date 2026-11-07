import os

import pefile

IIPS = r"run_codol_001\sandbox_ifs1_20260923\IIPS"
ORIG = r"COD OL\IIPS"


def dump_exports(path):
    print("=" * 80)
    print(path)
    try:
        pe = pefile.PE(path, fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_EXPORT"]])
    except Exception as e:
        print("  pe error:", e)
        return
    if not hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
        print("  (no exports)")
        return
    for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        name = exp.name.decode("ascii", "replace") if exp.name else "(ordinal %d)" % exp.ordinal
        print("  ", exp.ordinal, name)


def dump_985_context(path):
    data = open(path, "rb").read()
    pos = data.find(b"985")
    print("=" * 80)
    print("985 context in", path, "at", hex(pos) if pos >= 0 else "none")
    if pos < 0:
        return
    start = max(0, pos - 600)
    end = min(len(data), pos + 900)
    chunk = data[start:end]
    text = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
    print(text)
    for s in (b"985", b"P2P", b"p2p", b"Component"):
        idx = data.find(s)
        print(" ", s, hex(idx) if idx >= 0 else "none")


def main():
    for name in sorted(os.listdir(IIPS)):
        if name.lower().endswith(".dll"):
            dump_exports(os.path.join(IIPS, name))
    dump_985_context(os.path.join(IIPS, "p2papp.dll"))

    print("\n########## Tenio.ini comparison ##########")
    for p in (os.path.join(IIPS, "Tenio.ini"), os.path.join(ORIG, "Tenio.ini")):
        print("-" * 60, p)
        print(open(p, "rb").read().decode("utf-8", "replace"))


if __name__ == "__main__":
    main()
