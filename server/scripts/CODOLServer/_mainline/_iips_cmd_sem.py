# cmd=1 / cmd=2 semantics: resolve the format strings used by the two
# reply-construction branches in ResourceManagerII::OnRecvMsg @ 0x100153B0.
#
# Evidence chain (static disassembly of COD OL\IIPS\iips.dll):
#   0x100153CE  sub eax,1 ; je 0x1001544B     -> cmd == 1
#   0x100153D6  sub eax,1 ; je 0x100153FA     -> cmd == 2
#   0x100153DB  default: push 0x57; push 0x10037194 -> "unknown cmd" log
# Each branch builds a 0x315-byte reply buffer and formats it with a
# printf-style string pushed right before the FormatMsg call.
import re

PIPE = r"COD OL\IIPS\iips.dll"
IMAGE_BASE = 0x10000000


def cstr(blob, va):
    off = va - IMAGE_BASE
    return blob[off:off + 512].split(b"\x00")[0]


def main():
    blob = open(PIPE, "rb").read()

    targets = [
        (0x10037110, "cmd==1 branch  (je 0x1001544B)"),
        (0x10037150, "cmd==2 branch  (je 0x100153FA)"),
        (0x10037194, "default        (unknown cmd log)"),
    ]
    for va, label in targets:
        raw = cstr(blob, va)
        print("%-34s VA 0x%08X off 0x%06X" % (label, va, va - IMAGE_BASE))
        print("    ascii = %r" % raw.decode("latin1"))
        print()

    print("=== all format-ish strings near the dispatch (0x10037000..0x10037300) ===")
    lo, hi = 0x10037000 - IMAGE_BASE, 0x10037300 - IMAGE_BASE
    for m in re.finditer(rb"[\x20-\x7e]{4,}", blob[lo:hi]):
        print("  +0x%06X VA 0x%08X  %r" % (
            lo + m.start(), IMAGE_BASE + lo + m.start(), m.group().decode("latin1")))


main()
