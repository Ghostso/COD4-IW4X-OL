import re
import sys

AFD = r"run_codol_001\runs\ENTRY_CAPTURE_ELEVATED_20260924_160326\afd.xml"
TARGET = "42.187.183.203:14309"


def main():
    data = open(AFD, "rb").read().decode("utf-8", "replace")
    print("afd chars:", len(data))

    idx = [m.start() for m in re.finditer(re.escape(TARGET), data)]
    print("hits for", TARGET, ":", len(idx))
    for i in idx:
        s = max(0, i - 3000)
        e = min(len(data), i + 6000)
        print("=" * 60, "at", i)
        print(data[s:e])

    print("\n########## printable INI-ish blobs ##########")
    for m in re.finditer(r"(?i)PsIps", data):
        s = max(0, m.start() - 1200)
        e = min(len(data), m.end() + 2500)
        print("=" * 60, "PsIps at", m.start())
        print(data[s:e])


if __name__ == "__main__":
    main()
