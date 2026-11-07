# Dump *every* string near the TenTPF LoadImage hit and around any occurrence
# of "ss" / "LoadImage" style tokens; also scan for wide (UTF-16LE) variants
# since Tenio logs are likely compiled with both char and wchar messages.
import os
import re

paths = [
    r"COD OL\IIPS\Tenio\TenTPF.dll",
    r"COD OL\IIPS\IIPSHostApp.exe",
]


def ascii_strings(blob, lo, hi):
    region = blob[lo:hi]
    for m in re.finditer(rb"[\x20-\x7e]{4,}", region):
        yield lo + m.start(), "A", m.group().decode("latin1")
    # UTF-16LE
    for m in re.finditer(rb"(?:[\x20-\x7e]\x00){4,}", region):
        yield lo + m.start(), "W", m.group().decode("utf-16-le")


def main():
    for path in paths:
        if not os.path.exists(path):
            continue
        blob = open(path, "rb").read()
        print("===== %s =====" % path)
        key = blob.find(b"LoadImage")
        while key >= 0:
            lo = max(0, key - 0x600)
            hi = min(len(blob), key + 0xA00)
            print("--- around 0x%06X ---" % key)
            for off, kind, text in ascii_strings(blob, lo, hi):
                print("  [%s] +0x%06X  %r" % (kind, off, text[:200]))
            key = blob.find(b"LoadImage", key + 1)
            if key > 0x1000000:
                break
        print()


main()
