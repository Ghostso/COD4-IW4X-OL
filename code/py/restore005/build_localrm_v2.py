"""Agent 06 - Loader-only repair.

Builds LocalRM_v2.dll: a NEW, self-consistent PE32 DLL scaffold.

Design rationale (from Agent 01-05 evidence):

  * The original iips.dll template has FileAlignment == SectionAlignment == 0x1000
    and section VirtualAddress == PointerToRawData for every section.  All measured
    loader facts come from that ROM-image layout.  We keep it.

  * The previous LocalRM.dll kept the original section table but rewrote the
    OptionalHeader with values derived from a different (0x200-aligned) scaffold:
      SizeOfHeaders = 0xFFF, SizeOfImage = 0x481, .rdata VA = 0x1006, .data VA = 0x106F
    That layout is internally inconsistent: SizeOfImage (0x481) is smaller than
    every remaining data directory RVA (import 0x3EE3C, IAT 0x33000, reloc 0x50000),
    so the loader invalidates the image -> ERROR_BAD_EXE_FORMAT.

  * We therefore REBUILD the header from the original template's own constants and
    keep the ORIGINAL bytes of the loader-critical directories (import descriptors,
    thunks, IAT, .reloc, resources) at their original RVAs.  Only the entrypoint and
    the export directory are written by us, and the export directory is placed in a
    fresh section rather than on top of the original .rdata.

Read-only w.r.t. the original: COD OL\\IIPS\\iips.dll is only opened for reading.
"""
import hashlib
import os
import struct

import pefile

ORIG = r"COD OL\IIPS\iips.dll"
OUT = "LocalRM_v2.dll"

IMAGE_FILE_MACHINE_I386 = 0x014C
IMAGE_FILE_EXECUTABLE_IMAGE = 0x0002
IMAGE_FILE_LINE_NUMS_STRIPPED = 0x0004
IMAGE_FILE_LOCAL_SYMS_STRIPPED = 0x0008
IMAGE_FILE_32BIT_MACHINE = 0x0100
IMAGE_FILE_DLL = 0x2000

IMAGE_SCN_CNT_CODE = 0x00000020
IMAGE_SCN_CNT_INITIALIZED_DATA = 0x00000040
IMAGE_SCN_MEM_EXECUTE = 0x20000000
IMAGE_SCN_MEM_READ = 0x40000000
IMAGE_SCN_MEM_WRITE = 0x80000000

ALIGN = 0x1000


def align(v, a):
    return (v + a - 1) & ~(a - 1)


def gather_layout():
    """Read the original template's layout constants (read-only)."""
    pe = pefile.PE(ORIG, fast_load=True)
    info = {
        "image_base": pe.OPTIONAL_HEADER.ImageBase,
        "sect_align": pe.OPTIONAL_HEADER.SectionAlignment,
        "file_align": pe.OPTIONAL_HEADER.FileAlignment,
        "subsystem": pe.OPTIONAL_HEADER.Subsystem,
        "dllchars": pe.OPTIONAL_HEADER.DllCharacteristics,
        "stack_res": pe.OPTIONAL_HEADER.SizeOfStackReserve,
        "stack_commit": pe.OPTIONAL_HEADER.SizeOfStackCommit,
        "heap_res": pe.OPTIONAL_HEADER.SizeOfHeapReserve,
        "heap_commit": pe.OPTIONAL_HEADER.SizeOfHeapCommit,
        "os_major": pe.OPTIONAL_HEADER.MajorOperatingSystemVersion,
        "os_minor": pe.OPTIONAL_HEADER.MinorOperatingSystemVersion,
        "subsys_major": pe.OPTIONAL_HEADER.MajorSubsystemVersion,
        "subsys_minor": pe.OPTIONAL_HEADER.MinorSubsystemVersion,
        "coff_chars": pe.FILE_HEADER.Characteristics,
        "timedate": pe.FILE_HEADER.TimeDateStamp,
        "dirs": [(d.VirtualAddress, d.Size) for d in pe.OPTIONAL_HEADER.DATA_DIRECTORY[:16]],
        "orig_ep": pe.OPTIONAL_HEADER.AddressOfEntryPoint,
        "sections": [
            {
                "Name": s.Name.rstrip(b"\x00"),
                "VirtualSize": s.Misc_VirtualSize,
                "VirtualAddress": s.VirtualAddress,
                "SizeOfRawData": s.SizeOfRawData,
                "PointerToRawData": s.PointerToRawData,
                "Characteristics": s.Characteristics,
            }
            for s in pe.sections
        ],
    }
    pe.close()
    return info


STUB_GRMII = bytes([
    0xB8, 0x00, 0x00, 0x00, 0x00,   # mov eax, <imm32>  (patched below)
    0xC3,                            # ret
])
STUB_REL = bytes([
    0xB8, 0x00, 0x00, 0x00, 0x00,   # mov eax, 0
    0xC3,                            # ret
])

ENTRYPOINT_CODE = bytes([
    0xB8, 0x01, 0x00, 0x00, 0x00,   # mov eax, 1        (TRUE)
    0xC2, 0x0C, 0x00,                # ret 0x0C          (stdcall DllMain: callee pops 3 args)
])


def build():
    info = gather_layout()
    with open(ORIG, "rb") as f:
        orig = f.read()

    sa = info["sect_align"]
    fa = info["file_align"]
    assert sa == fa == ALIGN, "template alignment assumption changed: sa=0x%X fa=0x%X" % (sa, fa)

    orig_sections = info["sections"]

    # ---------------------------------------------------------------- new section
    # .localrm : entrypoint + export descriptors + names + our data
    b = bytearray()
    off_ep = 0
    b[0:0] = ENTRYPOINT_CODE
    off_grmii = align(len(b), 16)
    b.extend(b"\x00" * (off_grmii - len(b)))
    off_grmii = len(b)
    b.extend(STUB_GRMII)
    off_rel = align(len(b), 16)
    b.extend(b"\x00" * (off_rel - len(b)))
    off_rel = len(b)
    b.extend(STUB_REL)

    off_expdir = align(len(b), 4)
    b.extend(b"\x00" * (off_expdir - len(b)))
    off_expdir = len(b)
    b.extend(b"\x00" * 40)                 # IMAGE_EXPORT_DIRECTORY
    off_name = align(len(b), 4)
    b.extend(b"\x00" * (off_name - len(b)))
    off_name = len(b)
    b.extend(b"LocalRM_v2.dll\x00")
    off_n1 = align(len(b), 4)
    b.extend(b"\x00" * (off_n1 - len(b)))
    off_n1 = len(b)
    b.extend(b"GetResourceManagerII\x00")
    off_n2 = align(len(b), 4)
    b.extend(b"\x00" * (off_n2 - len(b)))
    off_n2 = len(b)
    b.extend(b"ReleaseResourceManagerII\x00")
    off_funcs = align(len(b), 4)
    b.extend(b"\x00" * (off_funcs - len(b)))
    off_funcs = len(b)
    b.extend(b"\x00" * 8)                  # 2 RVAs
    off_names = align(len(b), 4)
    b.extend(b"\x00" * (off_names - len(b)))
    off_names = len(b)
    b.extend(b"\x00" * 8)                  # 2 name RVAs
    off_ords = align(len(b), 4)
    b.extend(b"\x00" * (off_ords - len(b)))
    off_ords = len(b)
    b.extend(b"\x00" * 4)                  # 2 ordinals
    payload_sz = align(len(b), 4)

    new_va = align(max(s["VirtualAddress"] + max(s["VirtualSize"], s["SizeOfRawData"])
                       for s in orig_sections), sa)
    patch = lambda off, val: struct.pack_into("<I", b, off, val)
    patch(off_grmii + 1, new_va + 0x400)          # RM handle sentinel
    patch(off_rel + 1, 0)
    patch(off_expdir + 12, new_va + off_name)     # Name
    patch(off_expdir + 16, 1)                     # Base
    patch(off_expdir + 20, 2)                     # NumberOfFunctions
    patch(off_expdir + 24, 2)                     # NumberOfNames
    patch(off_expdir + 28, new_va + off_funcs)    # AddressOfFunctions
    patch(off_expdir + 32, new_va + off_names)    # AddressOfNames
    patch(off_expdir + 36, new_va + off_ords)     # AddressOfNameOrdinals
    patch(off_funcs + 0, new_va + off_grmii)
    patch(off_funcs + 4, new_va + off_rel)
    patch(off_names + 0, new_va + off_n1)
    patch(off_names + 4, new_va + off_n2)
    struct.pack_into("<HH", b, off_ords, 0, 1)
    assert len(b) <= payload_sz + 16, "payload bookkeeping"
    while len(b) < ALIGN:
        b.append(0)

    sections = []
    for s in orig_sections:
        sections.append({
            "name": s["Name"],
            "va": s["VirtualAddress"],
            "vs": s["VirtualSize"],
            "rs": s["SizeOfRawData"],
            "rp": s["PointerToRawData"],
            "ch": s["Characteristics"],
            "raw": orig[s["PointerToRawData"]:s["PointerToRawData"] + s["SizeOfRawData"]],
        })
    sections.append({
        "name": b".localrm",
        "va": new_va,
        "vs": len(b),
        "rs": len(b),
        "rp": new_va,                       # ROM-image rule: raw offset == VA
        "ch": (IMAGE_SCN_CNT_CODE | IMAGE_SCN_CNT_INITIALIZED_DATA
               | IMAGE_SCN_MEM_EXECUTE | IMAGE_SCN_MEM_READ),
        "raw": bytes(b),
    })

    nsec = len(sections)
    size_headers = 0x200 + 4 + 20 + 224 + nsec * 40
    size_headers = align(size_headers, ALIGN)
    size_image = align(sections[-1]["va"] + sections[-1]["vs"], sa)

    # ------------------------------------------------------------- DOS + NT header
    out = bytearray()
    out.extend(b"\x00" * 0x200)
    struct.pack_into("<H", out, 0, 0x5A4D)     # e_magic
    struct.pack_into("<H", out, 2, 0x0090)     # e_cblp
    struct.pack_into("<H", out, 4, 0x0003)     # e_cp
    struct.pack_into("<H", out, 8, 0x0004)     # e_cparhdr
    struct.pack_into("<H", out, 0x0C, 0xFFFF)  # e_maxalloc
    struct.pack_into("<H", out, 0x10, 0x00B8)  # e_sp
    struct.pack_into("<H", out, 0x18, 0x0040)  # e_lfarlc
    struct.pack_into("<I", out, 0x3C, 0x200)   # e_lfanew
    out.extend(b"PE\x00\x00")

    coff_chars = info["coff_chars"]
    # IMAGE_FILE_HEADER = Machine, NumberOfSections, TimeDateStamp,
    #                    PointerToSymbolTable, NumberOfSymbols,
    #                    SizeOfOptionalHeader, Characteristics
    out.extend(struct.pack("<HHIIIHH",
                           IMAGE_FILE_MACHINE_I386,   # Machine
                           nsec,                      # NumberOfSections
                           info["timedate"],          # TimeDateStamp
                           0,                         # PointerToSymbolTable
                           0,                         # NumberOfSymbols
                           224,                       # SizeOfOptionalHeader
                           coff_chars))               # Characteristics
    assert len(out) == 0x200 + 4 + 20, ("COFF header size", len(out))
    # IMAGE_OPTIONAL_HEADER32 field order (31 fields, 224 bytes):
    #   Magic, MajorLinkerVersion, MinorLinkerVersion,
    #   SizeOfCode, SizeOfInitializedData, SizeOfUninitializedData,
    #   AddressOfEntryPoint, BaseOfCode, BaseOfData, ImageBase,
    #   SectionAlignment, FileAlignment,
    #   MajorOperatingSystemVersion, MinorOperatingSystemVersion,
    #   MajorImageVersion, MinorImageVersion,
    #   MajorSubsystemVersion, MinorSubsystemVersion,
    #   Win32VersionValue, SizeOfImage, SizeOfHeaders, CheckSum,
    #   Subsystem, DllCharacteristics,
    #   SizeOfStackReserve, SizeOfStackCommit,
    #   SizeOfHeapReserve, SizeOfHeapCommit,
    #   LoaderFlags, NumberOfRvaAndSizes
    # IMAGE_OPTIONAL_HEADER32 = 30 fields, exactly 224 bytes:
    #   H  Magic
    #   B  MajorLinkerVersion
    #   B  MinorLinkerVersion
    #   I  SizeOfCode
    #   I  SizeOfInitializedData
    #   I  SizeOfUninitializedData
    #   I  AddressOfEntryPoint
    #   I  BaseOfCode
    #   I  BaseOfData
    #   I  ImageBase
    #   I  SectionAlignment
    #   I  FileAlignment
    #   H  MajorOperatingSystemVersion
    #   H  MinorOperatingSystemVersion
    #   H  MajorImageVersion
    #   H  MinorImageVersion
    #   H  MajorSubsystemVersion
    #   H  MinorSubsystemVersion
    #   I  Win32VersionValue
    #   I  SizeOfImage
    #   I  SizeOfHeaders
    #   I  CheckSum
    #   H  Subsystem
    #   H  DllCharacteristics
    #   I  SizeOfStackReserve
    #   I  SizeOfStackCommit
    #   I  SizeOfHeapReserve
    #   I  SizeOfHeapCommit
    #   I  LoaderFlags
    #   I  NumberOfRvaAndSizes
    # --- optional header (224 bytes), built from pefile's own field offsets ---
    size_of_code = sum(s["rs"] for s in sections if s["ch"] & IMAGE_SCN_CNT_CODE)
    size_of_idata = sum(s["rs"] for s in sections if s["ch"] & IMAGE_SCN_CNT_INITIALIZED_DATA)

    dirs = list(info["dirs"])
    dirs[0] = (new_va + off_expdir, 40)      # EXPORT -> our new section
    dirs[8] = (0, 0)                          # GLOBALPTR

    # Build the 224-byte IMAGE_OPTIONAL_HEADER32 by writing each field at the
    # exact offset pefile reports for the ORIGINAL header, then overriding the
    # fields we must change.  This avoids hand-written struct format strings:
    # a previous round shipped a wrong-length format and produced
    # SizeOfImage = 0x481 instead of 0x55000.
    oh_buf = bytearray(224)
    OVERRIDES = {
        "Magic": 0x010B,
        "MajorLinkerVersion": 6,
        "MinorLinkerVersion": 0,
        "SizeOfCode": size_of_code,
        "SizeOfInitializedData": size_of_idata,
        "SizeOfUninitializedData": 0,
        "AddressOfEntryPoint": new_va + off_ep,
        "BaseOfCode": sections[0]["va"],
        "BaseOfData": sections[1]["va"],
        "ImageBase": info["image_base"],
        "SectionAlignment": sa,
        "FileAlignment": fa,
        "MajorOperatingSystemVersion": info["os_major"],
        "MinorOperatingSystemVersion": info["os_minor"],
        "MajorImageVersion": 0,
        "MinorImageVersion": 0,
        "MajorSubsystemVersion": info["subsys_major"],
        "MinorSubsystemVersion": info["subsys_minor"],
        "Reserved1": 0,                 # Win32VersionValue
        "SizeOfImage": size_image,
        "SizeOfHeaders": size_headers,
        "CheckSum": 0,
        "Subsystem": info["subsystem"],
        "DllCharacteristics": info["dllchars"],
        "SizeOfStackReserve": info["stack_res"],
        "SizeOfStackCommit": info["stack_commit"],
        "SizeOfHeapReserve": info["heap_res"],
        "SizeOfHeapCommit": info["heap_commit"],
        "LoaderFlags": 0,
        "NumberOfRvaAndSizes": 16,
    }
    SHORT = {"Magic", "Subsystem", "DllCharacteristics"}
    PE_OPT = pefile.PE(ORIG, fast_load=True)
    oh_ex = PE_OPT.OPTIONAL_HEADER
    for name, val in OVERRIDES.items():
        if not hasattr(oh_ex, name):
            raise SystemExit("optional-header field %r not found in template" % name)
        off_f = oh_ex.get_field_relative_offset(name)
        struct.pack_into("<H" if name in SHORT else "<I", oh_buf, off_f, val)
    PE_OPT.close()
    # The 16 data directories are the LAST 128 bytes of IMAGE_OPTIONAL_HEADER32
    # (offsets 96..223 relative to the optional header).  Writing them again
    # after `oh` would shift the section table by 0x80 and corrupt the image --
    # that is exactly the defect that made the first LocalRM_v2 build unloadable.
    DIRS_REL_OFF = 96
    for i, (rva, sz) in enumerate(dirs[:16]):
        struct.pack_into("<II", oh_buf, DIRS_REL_OFF + i * 8, rva, sz)
    oh = bytes(oh_buf)
    assert len(oh) == 224, len(oh)
    out.extend(oh)          # optional header incl. its 16 data directories

    for s in sections:
        nm = (s["name"] + b"\x00" * 8)[:8]
        # IMAGE_SECTION_HEADER = Name[8], VirtualSize, VirtualAddress,
        #   SizeOfRawData, PointerToRawData, PointerToRelocations,
        #   PointerToLinenumbers, NumberOfRelocations, NumberOfLinenumbers,
        #   Characteristics
        blob = struct.pack("<8sIIIIIIHHI",
                           nm,
                           s["vs"],      # Misc.VirtualSize
                           s["va"],      # VirtualAddress
                           s["rs"],      # SizeOfRawData
                           s["rp"],      # PointerToRawData
                           0,            # PointerToRelocations
                           0,            # PointerToLinenumbers
                           0,            # NumberOfRelocations
                           0,            # NumberOfLinenumbers
                           s["ch"])      # Characteristics
        assert len(blob) == 40, len(blob)
        out.extend(blob)

    assert len(out) <= size_headers, (len(out), size_headers)
    out.extend(b"\x00" * (size_headers - len(out)))

    for s in sections:
        if len(out) < s["rp"]:
            out.extend(b"\x00" * (s["rp"] - len(out)))
        assert len(out) == s["rp"], (s["name"], len(out), s["rp"])
        out.extend(s["raw"])

    with open(OUT, "wb") as f:
        f.write(bytes(out))

    print("ORIGINAL     %s  (%d bytes)  sha256 %s" % (ORIG, len(orig), hashlib.sha256(orig).hexdigest()))
    print("OUTPUT       %s  (%d bytes)  sha256 %s" % (OUT, len(out), hashlib.sha256(bytes(out)).hexdigest()))
    print("sections     %d   SizeOfImage=0x%X  SizeOfHeaders=0x%X" % (nsec, size_image, size_headers))
    print("entrypoint   RVA 0x%X   (mov eax,1 ; ret 0x0C)" % (new_va + off_ep))
    print("export dir   RVA 0x%X  funcs=0x%X names=0x%X ords=0x%X"
          % (new_va + off_expdir, new_va + off_funcs, new_va + off_names, new_va + off_ords))
    print("GetResourceManagerII  RVA 0x%X" % (new_va + off_grmii))
    print("ReleaseResourceManagerII RVA 0x%X" % (new_va + off_rel))
    for i, (rva, sz) in enumerate(dirs):
        if rva or sz:
            print("   dir[%2d] 0x%08X size 0x%X" % (i, rva, sz))


if __name__ == "__main__":
    build()
