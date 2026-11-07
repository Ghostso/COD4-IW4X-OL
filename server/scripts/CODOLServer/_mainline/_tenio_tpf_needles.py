# Exact needle hunt for the Tenio/TPFUI loading path.
import os

TARGETS = [
    r"COD OL\IIPS\Tenio\TenTPF.dll",
    r"COD OL\IIPS\Tenio\TenFact.dll",
    r"COD OL\IIPS\Tenio\June.dll",
    r"COD OL\IIPS\IIPSHostApp.exe",
]

NEEDLES = [
    b"LoadImageFromBuffer",
    b"LoadImage",
    b"TPFFile",
    b"Can't find Component",
    b"Creator From Dll List",
    b"Component(%d)",
    b"TPFUI",
    b"IIPSRes",
    b"TPFProject",
    b"Root.tpf",
    b"SystemSetting.tpf",
    b"SetStyleRootPath",
    b"SetLayoutRootPath",
    b"tprj",
]


def main():
    for path in TARGETS:
        if not os.path.exists(path):
            continue
        blob = open(path, "rb").read()
        print("===== %s =====" % path)
        for needle in NEEDLES:
            start = 0
            hits = []
            while True:
                pos = blob.find(needle, start)
                if pos < 0:
                    break
                hits.append(pos)
                start = pos + 1
            if hits:
                print("  %-28r %d hit(s): %s" % (
                    needle.decode("latin1"),
                    len(hits),
                    " ".join("0x%06X" % h for h in hits[:20])))
        print()


main()
