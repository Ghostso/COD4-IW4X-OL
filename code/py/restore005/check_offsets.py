"""Verify IMAGE_OPTIONAL_HEADER32 field offsets by parsing the original template
and cross-checking byte positions against pefile's parsed values."""
import struct

import pefile

ORIG = r"COD OL\IIPS\iips.dll"
pe = pefile.PE(ORIG, fast_load=True)
base = pe.OPTIONAL_HEADER.get_file_offset()
print("OptionalHeader file offset = 0x%X" % base)
print("DOS e_lfanew = 0x%X" % pe.DOS_HEADER.e_lfanew)
print("section table offset = 0x%X" % (base + pe.FILE_HEADER.SizeOfOptionalHeader))

with open(ORIG, "rb") as f:
    d = f.read()

FIELDS = [
    (0,  "Magic", "<H"),
    (2,  "MajorLinkerVersion", "<B"),
    (3,  "MinorLinkerVersion", "<B"),
    (4,  "SizeOfCode", "<I"),
    (8,  "SizeOfInitializedData", "<I"),
    (12, "SizeOfUninitializedData", "<I"),
    (16, "AddressOfEntryPoint", "<I"),
    (20, "BaseOfCode", "<I"),
    (24, "BaseOfData", "<I"),
    (28, "ImageBase", "<I"),
    (32, "SectionAlignment", "<I"),
    (36, "FileAlignment", "<I"),
    (40, "MajorOperatingSystemVersion", "<H"),
    (42, "MinorOperatingSystemVersion", "<H"),
    (44, "MajorImageVersion", "<H"),
    (46, "MinorImageVersion", "<H"),
    (48, "MajorSubsystemVersion", "<H"),
    (50, "MinorSubsystemVersion", "<H"),
    (52, "Win32VersionValue", "<I"),
    (56, "SizeOfImage", "<I"),
    (60, "SizeOfHeaders", "<I"),
    (64, "CheckSum", "<I"),
    (68, "Subsystem", "<H"),
    (70, "DllCharacteristics", "<H"),
    (72, "SizeOfStackReserve", "<I"),
    (76, "SizeOfStackCommit", "<I"),
    (80, "SizeOfHeapReserve", "<I"),
    (84, "SizeOfHeapCommit", "<I"),
    (88, "LoaderFlags", "<I"),
    (92, "NumberOfRvaAndSizes", "<I"),
]

print()
print("%-6s %-30s %14s %14s %s" % ("off", "field", "bytes-value", "pefile", "match"))
ALIAS = {"Win32VersionValue": "Reserved1"}
for off, name, fmt in FIELDS:
    raw = struct.unpack_from(fmt, d, base + off)[0]
    key = ALIAS.get(name, name)
    ref = getattr(pe.OPTIONAL_HEADER, key, None)
    ok = "OK" if raw == ref else ("**MISMATCH**" if ref is not None else "n/a")
    print("%-6d %-30s %14s %14s %s"
          % (off, name, "0x%X" % raw if fmt != "<B" else raw,
             "0x%X" % ref if (ref is not None and fmt != "<B") else ref,
             ok))

print()
print("Section table offset (file) = 0x%X" % (base + 224))
print("First section header bytes: %s" % d[base + 224: base + 224 + 40].hex())
pe.close()
