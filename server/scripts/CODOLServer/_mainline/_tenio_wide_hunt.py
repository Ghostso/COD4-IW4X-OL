import os
import re

PATHS = [
    r"COD OL\IIPS\Tenio\TenTPF.dll",
    r"COD OL\IIPS\Tenio\TenFact.dll",
    r"COD OL\IIPS\Tenio\June.dll",
    r"COD OL\IIPS\IIPSHostApp.exe",
]

NEEDLES = [
    "LoadImage",
    "LoadImageFromBuffer",
    "GetBuffer",
    "CTPFImageCreator",
    "TPFFile",
    "Can't find Component",
    "Creator From Dll List",
    "Component",
    "TPFUI",
    "IIPSRes",
    "back",
]


def wide(needle):
    return "".join(ch + "\x00" for ch in needle).encode("latin1")


def main():
    for path in PATHS:
        if not os.path.exists(path):
            continue
        blob = open(path, "rb").read()
        print("===== %s =====" % path)
        for needle in NEEDLES:
            for kind, seq in (
                    ("A", needle.encode("latin1")),
                    ("W", wide(needle))):
                hits = []
                start = 0
                while True:
                    pos = blob.find(seq, start)
                    if pos < 0:
                        break
                    hits.append(pos)
                    start = pos + 1
                if hits:
                    print("  [%s] %-28s %d hit(s): %s" % (
                        kind, needle, len(hits),
                        " ".join("0x%06X" % h for h in hits[:16])))
        print()


main()
