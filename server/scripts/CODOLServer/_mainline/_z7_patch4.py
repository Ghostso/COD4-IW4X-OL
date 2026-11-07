"""Verify the four compatibility patches from the working document against
the runtime image, and locate them by PATTERN (the document itself notes the
exact offsets drift, and that the bytes only exist AFTER unpacking).

Document spec:
  #1  0xB9A78C-16 .. +40   pattern 84 C0 (74|75) B2 B0 01   act 74->75
  #2  0xB9A7B0    .. +64   pattern 84 C0 (75|EB) 2A E8      act 75->EB
  #3  same region         call + 8D 8D 38FD FFFF C7 85 68FD FFFF
                          act: call -> E9 jump 0xB9A7F1
  #4  0xBA3C1A            pattern 85 C0 75 44              act 90 90 at +2

Known traps from the document:
  * decimal 12205082 == 0xBA3C1A (not 0xBA41DA)
  * patch #3 turns 0xB9A7C7's E8 into E9, after which pattern #2 no longer
    matches -- latch on success, do not retry every round
"""
import re
import struct
import sys

IMG = r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
BASE = 0x400000


def load():
    return open(IMG, "rb").read()


def at(d, va, n):
    o = va - BASE
    return d[o:o + n]


def hexs(b):
    return " ".join("%02x" % x for x in b)


def scan(d, pat, lo, hi, limit=8):
    rx = re.compile(pat)
    out = []
    for m in rx.finditer(d, lo - BASE, hi - BASE):
        out.append(BASE + m.start())
        if len(out) >= limit:
            break
    return out


def main():
    d = load()
    print("=== PATCH #4 : 0xBA3C1A  (LSG nonce check) ===")
    got = at(d, 0xBA3C1A, 6)
    print("  at 0xBA3C1A :", hexs(got))
    print("  expect      : 85 c0 75 44")
    print("  match       :", got[:4] == b"\x85\xc0\x75\x44")
    print("  action would be: write 90 90 at 0xBA3C1C  (now %s)"
          % hexs(at(d, 0xBA3C1C, 2)))

    print()
    print("=== PATCH #1 : pattern 84 C0 (74|75) B2 B0 01 near 0xB9A78C ===")
    hits = scan(d, rb"\x84\xc0[\x74\x75]\xb2\xb0\x01",
                0xB9A700, 0xB9A900)
    print("  hits:", ["0x%08X" % h for h in hits])
    for h in hits:
        print("     0x%08X : %s" % (h, hexs(at(d, h, 7))))

    print()
    print("=== PATCH #2 : pattern 84 C0 (75|EB) 2A E8 near 0xB9A7B0 ===")
    hits2 = scan(d, rb"\x84\xc0[\x75\xeb]\x2a\xe8", 0xB9A700, 0xB9A900)
    print("  hits:", ["0x%08X" % h for h in hits2])
    for h in hits2:
        print("     0x%08X : %s" % (h, hexs(at(d, h, 6))))

    print()
    print("=== PATCH #3 : pattern near 0xB9A7B0 ===")
    hits3 = scan(d, rb"\x8d\x8d\x38\xfd\xff\xff\xc7\x85\x68\xfd\xff\xff",
                 0xB9A700, 0xB9A900)
    print("  hits:", ["0x%08X" % h for h in hits3])
    for h in hits3:
        # the call is a few bytes before
        print("     ref 0x%08X : %s" % (h, hexs(at(d, h - 8, 22))))
        cb = at(d, h - 8, 1)
        print("     byte before = %s" % hexs(cb))

    print()
    print("=== what we had been patching instead ===")
    for va in (0xBA3A2A, 0xBA3AE6, 0xBA3AE9, 0xBA3B02):
        print("  0x%08X : %s" % (va, hexs(at(d, va, 6))))
    print("  -> these are ~0x200 bytes BEFORE 0xBA3C1A (different site)")


if __name__ == "__main__":
    main()
