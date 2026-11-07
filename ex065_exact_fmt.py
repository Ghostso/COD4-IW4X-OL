# EX-065 PHASE 3: exact raw bytes of the TCLS shared-memory / message
# format strings in tcls_core.exe and TenProxy.dll.
import os
import re


def dump_around(path, needle, label, before=24, after=140):
    data = open(path, "rb").read()
    print("=" * 78)
    print("%s  in %s" % (label, path))
    print("=" * 78)
    st = 0
    cnt = 0
    while cnt < 12:
        i = data.find(needle, st)
        if i < 0:
            break
        cnt += 1
        seg = data[max(0, i - before): i + after]
        # split into utf16 strings
        out = []
        cur = []
        for j in range(0, len(seg) - 1, 2):
            ch = seg[j]
            if seg[j + 1] == 0 and 32 <= ch < 127:
                cur.append(chr(ch))
            else:
                if len(cur) >= 3:
                    out.append("".join(cur))
                cur = []
        if len(cur) >= 3:
            out.append("".join(cur))
        print("  @0x%06X: %s" % (i, out))
        st = i + 1


def main():
    dump_around(r"WeGame\tcls\tcls_core.exe", b"T\0C\0L\0S\0_\0S\0H\0A\0R\0E\0D\0",
                "TCLS_SHAREDMEMEMORY (utf16)")
    dump_around(r"WeGame\tcls\tcls_core.exe", b"T\0C\0L\0S\0_\0C\0O\0R\0E\0_\0S\0H\0A\0R\0E\0",
                "TCLS_CORE_SHARE (utf16)")
    dump_around(r"WeGame\tcls\tcls_core.exe", b"T\0C\0L\0S\0_\0C\0O\0R\0E\0_\0M\0U\0T\0E\0X\0",
                "TCLS_CORE_MUTEX (utf16)")
    dump_around(r"WeGame\tcls\tcls_core.exe", b"T\0C\0L\0S\0_\0E\0X\0I\0T\0_\0E\0V\0E\0N\0T\0",
                "TCLS_EXIT_EVENT (utf16)")
    dump_around(r"WeGame\tcls\tcls_core.exe", b"T\0C\0L\0S\0_\0C\0O\0R\0E\0_\0W\0N\0D\0",
                "TCLS_CORE_WND (utf16)")
    dump_around(r"工具\EX035_DIR\TenProxy.dll", b"T\0C\0L\0S\0_\0S\0H\0A\0R\0E\0D\0",
                "TCLS_SHAREDMEMEMORY (utf16)")


if __name__ == "__main__":
    main()
