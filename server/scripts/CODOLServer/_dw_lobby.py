import re

EXE = r"run_codol_001\sandbox\codoMP_client_shipRetail.exe"


def dump_around(data, off, before=1500, after=2500):
    s = max(0, off - before)
    e = min(len(data), off + after)
    chunk = data[s:e]
    return "".join(chr(b) if 32 <= b < 127 else ("\n" if b == 0 else ".") for b in chunk)


def main():
    data = open(EXE, "rb").read()
    print("size", len(data))

    families = {
        "DW_LOBBY": rb"DW_LOBBY[A-Z_]*",
        "DWLOGON": rb"DWLOGON[A-Z_]*",
        "DW_ACCOUNT": rb"DW_ACCOUNT[A-Z_]*",
        "DW_DNS": rb"DW_DNS[A-Z_]*",
        "BD_LOBBY": rb"BD_LOBBY[A-Z_]*",
    }
    for name, pat in families.items():
        hits = sorted(set(m.group(0).decode() for m in re.finditer(pat, data)))
        print(f"\n===== {name}: {len(hits)} unique =====")
        for h in hits:
            print("  ", h)

    print("\n########## 100-ish numeric strings near lobby names ##########")
    for m in re.finditer(rb"DW_LOBBY_ERROR", data):
        print("-" * 70, "off", hex(m.start()))
        print(dump_around(data, m.start()))

    print("\n########## search for mensagem / MENU_ strings mentioning 100 ##########")
    for m in re.finditer(rb"MENU_[A-Z0-9_]{3,60}", data):
        s = m.group(0).decode()
        if "LOBBY" in s or "SERVER" in s or "CONNECT" in s:
            print("  ", s)


if __name__ == "__main__":
    main()
