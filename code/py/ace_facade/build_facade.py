"""Build a minimal PE32 (x86) DLL facade with hand-assembled code.

No compiler/toolchain needed -- we emit the PE ourselves. The resulting DLL
exports the exact names the game resolves from the protection modules and
returns inert objects, so the startup contract is satisfied without any
enforcement running.

Usage:  python build_facade.py <export1,export2,...> <outfile.dll>

Every export becomes a stdcall stub that returns 0 (S_OK) and performs no
cleanup of caller arguments (ret 0), which is the safest default for a
facade: it cannot corrupt the caller's stack, and callers of these
factory-style entry points do not rely on callee cleanup for correctness of
their own frame (they use their own epilogue after `call`).
"""
import struct
import sys

IMAGE_BASE = 0x10000000
SECTOR = 0x200


def align(v, a):
    return (v + a - 1) // a * a


def build(exports, out_path):
    n = len(exports)

    # ---- layout ---------------------------------------------------------
    # .text : code (stubs) ; .edata : export tables ; .rdata : names/strings
    text_rva = 0x1000

    # code: for each export a stub `xor eax,eax; ret`
    stub = b"\x33\xC0\xC3"            # xor eax,eax ; ret   (3 bytes)
    code = b""
    func_rvas = []
    for _ in range(n):
        func_rvas.append(text_rva + len(code))
        code += stub
    # pad with int3
    code += b"\xCC" * 8

    text_size = align(len(code), SECTOR)

    edata_rva = text_rva + text_size
    # export directory (40 bytes) + function RVA array + name RVA array +
    # ordinal array + name strings
    dir_size = 40
    fun_arr = edata_rva + dir_size
    nam_arr = fun_arr + 4 * n
    ord_arr = nam_arr + 4 * n
    str_rva = ord_arr + 2 * n

    name_blob = b""
    name_rvas = []
    for e in exports:
        name_rvas.append(str_rva + len(name_blob))
        name_blob += e.encode("ascii") + b"\x00"

    edata = bytearray()
    edata += struct.pack("<IIHHIIIIIII",
                         0,          # Characteristics
                         0,          # TimeDateStamp
                         0,          # Major/MinorVersion
                         0,
                         str_rva,    # Name RVA (dll name) - fill later
                         1,          # Base
                         n,          # NumberOfFunctions
                         n,          # NumberOfNames
                         fun_arr,    # AddressOfFunctions
                         nam_arr,    # AddressOfNames
                         ord_arr)    # AddressOfNameOrdinals
    edata += struct.pack("<" + "I" * n, *func_rvas)
    edata += struct.pack("<" + "I" * n, *name_rvas)
    edata += struct.pack("<" + "H" * n, *range(n))
    edata += name_blob
    dll_name_rva = str_rva + len(name_blob)
    dll_name = b"VSDDrvDll.dll\x00"
    edata += dll_name
    edata = bytes(edata)
    # patch Name RVA now that we know it
    edata = edata[:12] + struct.pack("<I", dll_name_rva) + edata[16:]

    edata_size = align(len(edata), SECTOR)
    edata_rva_end = edata_rva + edata_size

    raw_text = code.ljust(text_size, b"\x00")
    raw_edata = edata.ljust(edata_size, b"\x00")

    # ---- headers --------------------------------------------------------
    sect_align = 0x1000
    file_align = SECTOR
    size_of_image = align(edata_rva_end, sect_align)

    dos = bytearray(0x40)
    dos[0:2] = b"MZ"
    struct.pack_into("<I", dos, 0x3C, 0x40)

    num_sections = 2
    opt_size = 224

    nt = bytearray()
    nt += b"PE\x00\x00"
    nt += struct.pack("<HHIIIHH",
                      0x014C,          # Machine i386
                      num_sections,
                      0, 0, 0,
                      opt_size,
                      0x0102)          # IMAGE_FILE_DLL | EXECUTABLE

    opt = bytearray()
    opt += struct.pack("<H", 0x010B)          # PE32 magic
    opt += b"\x00" * 2
    # SizeOfCode is the RAW size of the code section(s), not the live byte
    # count.  A real DLL sets it to the section's SizeOfRawData (verified
    # against SysWOW64\version.dll: .text raw 0x2A00 -> SizeOfCode 0x2A00).
    opt += struct.pack("<III", text_size, edata_size, 0)
    opt += struct.pack("<I", text_rva)        # AddressOfEntryPoint
    opt += struct.pack("<I", text_rva)        # BaseOfCode
    opt += struct.pack("<I", edata_rva)       # BaseOfData
    opt += struct.pack("<I", IMAGE_BASE)
    opt += struct.pack("<II", sect_align, file_align)
    # MajorOperatingSystemVersion, MinorOperatingSystemVersion,
    # MajorImageVersion, MinorImageVersion,
    # MajorSubsystemVersion, MinorSubsystemVersion
    opt += struct.pack("<HHHHHH", 6, 0, 0, 0, 6, 0)
    opt += struct.pack("<I", 0)
    opt += struct.pack("<I", size_of_image)
    # SizeOfHeaders MUST be file-aligned: the loader maps the headers as a
    # whole number of FileAlignment sectors, and the first section's raw
    # pointer must equal it.  Writing a merely 8-aligned value here makes
    # LoadLibrary fail with Error 193 ("not a valid Win32 application").
    headers_size = align(0x40 + 4 + 20 + opt_size, sect_align if False else file_align)
    opt += struct.pack("<I", headers_size)
    opt += struct.pack("<I", 0)               # checksum
    # Subsystem MUST be 2 (IMAGE_SUBSYSTEM_WINDOWS_GUI) for a DLL.
    # Writing 3 (CONSOLE) makes the loader reject the image with
    # ERROR_BAD_EXE_FORMAT (193) -- which is exactly what we hit.
    # Verified against the real VSDDrvDll.dll: Subsystem=2, DllChars=0x140.
    opt += struct.pack("<HH", 2, 0x0140)      # subsystem + dll characteristics
    opt += struct.pack("<IIII", 0x100000, 0x1000, 0x100000, 0x1000)
    opt += struct.pack("<II", 0, 16)          # NumberOfRvaAndSizes
    # 16 data directories
    dirs = [(0, 0)] * 16
    dirs[0] = (edata_rva, len(edata))          # export
    for d in dirs:
        opt += struct.pack("<II", d[0], d[1])

    assert len(opt) == opt_size, len(opt)

    def section(name, vsize, vaddr, rawsize, rawptr, chars):
        s = name.ljust(8, b"\x00")
        s += struct.pack("<IIII", vsize, vaddr, rawsize, rawptr)
        s += struct.pack("<II", 0, 0)
        s += struct.pack("<HH", 0, 0)
        s += struct.pack("<I", chars)
        return s

    # raw pointers must start at SizeOfHeaders (file-aligned)
    headers_size = align(0x40 + len(nt) + opt_size, file_align)
    sec_text = section(b".text", text_size, text_rva, text_size,
                       headers_size,
                       0x60000020)  # code|execute|read
    sec_edata = section(b".edata", edata_size, edata_rva, edata_size,
                        sec_text_get_rawptr(sec_text) + text_size,
                        0xC0000040)  # initialized data|read|write

    hdr = bytes(dos) + bytes(nt) + bytes(opt) + sec_text + sec_edata
    hdr = hdr.ljust(headers_size, b"\x00")

    img = bytearray(hdr)
    img += raw_text
    img += raw_edata

    open(out_path, "wb").write(bytes(img))
    print("wrote %s (%d bytes) exports=%s" % (out_path, len(img), exports))


def sec_text_get_rawptr(sec_text):
    return struct.unpack_from("<I", sec_text, 20)[0]


if __name__ == "__main__":
    names = sys.argv[1].split(",")
    out = sys.argv[2]
    build(names, out)
