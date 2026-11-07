# EX-060: recover the exact LoadLibraryW path construction in initIfsLib.
import struct

from ex060_iips_cfg import Image, DLL
from ex060_cfg_engine import Function


def main():
    img = Image(DLL)
    md = __import__("capstone").Cs(
        __import__("capstone").CS_ARCH_X86, __import__("capstone").CS_MODE_32)

    fi = Function(img, 0x9570, "initIfsLib").run().build_bbs()

    print("=== The three string pieces feeding the path build ===")
    for rva, note in ((0x34904, "pushed at 0x95E4 -> std::string ctor (narrow)"),
                      (0x34908, "pushed at 0x96A1 -> wide operator+ RHS")):
        # narrow
        n = img.cstr(rva, 64)
        print("  RVA 0x%05X (narrow) %r   [%s]" % (rva, n, note))
        # wide
        w = img.read(rva, 128)
        try:
            ws = w.decode("utf-16-le")
            # cut at first NUL pair
            cut = ws.find("\x00")
            ws = ws[:cut] if cut >= 0 else ws
            print("  RVA 0x%05X (utf16)  %r" % (rva, ws))
        except Exception as e:
            print("     utf16 decode failed: %r" % e)

    print()
    print("=== bytes at 0x34900..0x34920 ===")
    print("  hex:", img.read(0x34900, 0x20).hex())
    print("  raw:", repr(img.read(0x34900, 0x20)))

    print()
    print("=== wide-string view with proper 2-byte stride ===")
    blob = img.read(0x348F0, 0x40)
    print("  hex:", blob.hex())
    for start in range(0, 16):
        try:
            ws = blob[start:].decode("utf-16-le")
            cut = ws.find("\x00")
            ws = ws[:cut] if cut >= 0 else ws
            if ws and all(32 <= ord(c) < 0x3000 for c in ws):
                print("  stride16 off=%d : %r" % (start, ws))
        except Exception:
            pass


if __name__ == "__main__":
    main()
