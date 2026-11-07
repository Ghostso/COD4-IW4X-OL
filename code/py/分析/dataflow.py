"""Focused dataflow checks for the AUTH -> ticket -> LSG chain."""
import re
import sys

import capstone

sys.stdout.reconfigure(encoding="utf-8")

BASE = 0x400000


def disasm(blob, start, end):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    md.detail = False
    return list(md.disasm(blob[start - BASE:end - BASE], start))


def show(title, blob, start, end):
    print("=== %s  0x%08X..0x%08X ===" % (title, start, end))
    for ins in disasm(blob, start, end):
        print("0x%08X  %-20s %s %s" % (ins.address, ins.bytes.hex(),
                                       ins.mnemonic, ins.op_str))
    print()


def main():
    path = sys.argv[1]
    blob = open(path, "rb").read()

    # AUTH stage: parse lsg_server_ticket + size from the /auth/ response.
    show("AUTH ticket parse site", blob, 0xB984D8, 0xB98580)
    # Where the ticket name/size are consumed after parsing.
    show("AUTH ticket consumer", blob, 0xB9851A, 0xB985C0)
    # Second AUTH parser (other stage) for comparison.
    show("AUTH parser 2 ticket site", blob, 0xB99B80, 0xB99C30)

    # Lobby connect: uses HOST/PORT/hex5 and the TLS wrapper object.
    show("DW lobby connect", blob, 0x7F2BA0, 0x7F2C50)
    # Lobby worker that decides success/error and drives state.
    show("DW lobby worker", blob, 0x7F31A0, 0x7F3210)

    print("=== string refs to DW-* headers / ticket names ===")
    for name, va in (
        ("DW-Server-Ticket", 0xD5A1AC),
        ("DW-Client-Ticket", 0xD5A180),
        ("DW-Ticket-Seed", 0xD5A158),
        ("lsg_server_ticket", 0xD5A0E8),
        ("lsg_server_ticket_size", 0xD5A0FC),
    ):
        pat = va.to_bytes(4, "little")
        hits = [m.start() for m in re.finditer(re.escape(pat), blob)]
        code = [BASE + h for h in hits if 0x401000 <= BASE + h < 0xCA8000]
        print("  %-24s VA 0x%08X  all_refs=%d code_refs=%d %s"
              % (name, va, len(hits), len(code), ["0x%08X" % c for c in code[:8]]))


if __name__ == "__main__":
    main()
