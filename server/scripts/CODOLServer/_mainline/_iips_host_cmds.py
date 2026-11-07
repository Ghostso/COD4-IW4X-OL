# Scan IIPSHost.dll / IIPSHostApp.exe for the host side of the 791-byte
# pipe protocol and print context strings around the known client-side
# SetHostAction commands (cmd=1 -> WriteBitmap, cmd=2 -> show ui).
import re

TARGETS = [
    r"COD OL\IIPS\IIPSHost.dll",
    r"COD OL\IIPS\IIPSHostApp.exe",
]

NEEDLES = [
    "OnRecv", "SendMsg", "SetHostAction", "WriteBitmap", "show ui",
    "MSG_", "CMD", "pipe", "Pipe", "HostAction", "userdata",
    "ListenThread", "CreateNamedPipe",
]


def main():
    for path in TARGETS:
        print("===== %s =====" % path)
        blob = open(path, "rb").read()
        for m in re.finditer(rb"[\x20-\x7e]{4,}", blob):
            text = m.group().decode("latin1")
            if any(needle in text for needle in NEEDLES):
                print("+0x%06X  %r" % (m.start(), text[:220]))
        print()


main()
