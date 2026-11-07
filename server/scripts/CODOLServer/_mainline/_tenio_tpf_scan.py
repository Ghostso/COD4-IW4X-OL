# Locate the TPFUI path-construction bug and the "Can't find Component(985)"
# source inside the Tenio / TenTPF component family.
import os
import re

TARGETS = [
    r"COD OL\IIPS\Tenio\TenTPF.dll",
    r"COD OL\IIPS\Tenio\TenFact.dll",
    r"COD OL\IIPS\Tenio\ScriptManager.dll",
    r"COD OL\IIPS\Tenio\June.dll",
    r"COD OL\IIPS\IIPSHostApp.exe",
]

NEEDLES = (
    "TPFUI", "IIPSRes", "LoadImage", "TPFFile", "Component",
    "Can't find", "tprj", "Tenio.ini", "IIPSHostApp.ini",
    "Style", "Layout", "Localization", "\\TPFUI", "IIPS\\\\",
)


def main():
    for rel in TARGETS:
        if not os.path.exists(rel):
            print("MISSING %s" % rel)
            continue
        blob = open(rel, "rb").read()
        print("===== %s (%d bytes) =====" % (rel, len(blob)))
        shown = 0
        for m in re.finditer(rb"[\x20-\x7e]{4,}", blob):
            text = m.group().decode("latin1")
            if any(k in text for k in NEEDLES):
                print("  +0x%06X  %r" % (m.start(), text[:240]))
                shown += 1
                if shown > 120:
                    print("  ... truncated")
                    break
        print()

    print("===== config files =====")
    for rel in (r"COD OL\IIPS\Tenio.ini",
                r"COD OL\IIPS\TPFUI\TPFUI.tprj",
                r"COD OL\IIPS\IIPSHostApp.ini"):
        print("--- %s ---" % rel)
        try:
            print(open(rel, "rb").read().decode("latin1"))
        except OSError as exc:
            print("  ERR %s" % exc)


main()
