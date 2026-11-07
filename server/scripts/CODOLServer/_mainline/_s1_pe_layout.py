# -*- coding: utf-8 -*-
"""Print the real PE section/header layout for a PE, using both pefile and raw parse."""
import struct
import sys

import pefile

path = sys.argv[1]
with open(path, "rb") as fh:
    blob = fh.read()

pe = pefile.PE(path, fast_load=True)
oh = pe.OPTIONAL_HEADER
print("path", path, "size", len(blob))
print("Machine 0x%04X NumSections %d" % (pe.FILE_HEADER.Machine, pe.FILE_HEADER.NumberOfSections))
print("SizeOfHeaders 0x%X SizeOfImage 0x%X" % (oh.SizeOfHeaders, oh.SizeOfImage))
print("ImageBase 0x%08X" % oh.ImageBase)
print("EntryPoint 0x%08X (rva)" % oh.AddressOfEntryPoint)
print("SectionAlignment 0x%X FileAlignment 0x%X" % (oh.SectionAlignment, oh.FileAlignment))
print("DllCharacteristics 0x%04X" % oh.DllCharacteristics)
print("Subsystem %d" % oh.Subsystem)
print()
print("%-10s %10s %10s %10s %10s  %s" % ("name", "VirtAddr", "VirtSize", "RawPtr", "RawSize", "chars"))
for s in pe.sections:
    print("%-10s 0x%08X 0x%08X 0x%08X 0x%08X  0x%08X" % (
        s.Name.rstrip(b"\x00").decode("latin-1"),
        s.VirtualAddress, s.Misc_VirtualSize,
        s.PointerToRawData, s.SizeOfRawData, s.Characteristics))

# raw parse of the section table to cross-check pefile's byte-order handling
e_lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
print()
print("raw e_lfanew 0x%X sig %s" % (e_lfanew, blob[e_lfanew:e_lfanew + 4].hex()))
num = struct.unpack_from("<H", blob, e_lfanew + 6)[0]
opt_size = struct.unpack_from("<H", blob, e_lfanew + 20)[0]
print("raw NumSections", num, "SizeOfOptionalHeader 0x%X" % opt_size)
sec_off = e_lfanew + 24 + opt_size

# detect 0x00004550 (little endian 'PE\0\0' written big-endian) anomaly
alt = struct.unpack_from(">I", blob, e_lfanew)[0]
print("raw sig as BE uint32: 0x%08X" % alt)

print()
print("--- raw section entries (as parsed little-endian) ---")
for i in range(num):
    base = sec_off + i * 40
    if base + 40 > len(blob):
        break
    name = blob[base:base + 8].rstrip(b"\x00")
    if b"\x00\x00" in name:
        name = name.split(b"\x00")[0]
    vsize, vaddr, rawsize, rawptr = struct.unpack_from("<IIII", blob, base + 8)
    chars = struct.unpack_from("<I", blob, base + 36)[0]
    print("[%d] name=%r vsize=0x%X vaddr=0x%X rawsize=0x%X rawptr=0x%X chars=0x%08X" % (
        i, name.decode("latin-1"), vsize, vaddr, rawsize, rawptr, chars))

print()
print("--- raw section entries (as parsed big-endian, for comparison) ---")
for i in range(num):
    base = sec_off + i * 40
    if base + 40 > len(blob):
        break
    name = blob[base:base + 8].rstrip(b"\x00")
    if b"\x00\x00" in name:
        name = name.split(b"\x00")[0]
    vsize, vaddr, rawsize, rawptr = struct.unpack_from(">IIII", blob, base + 8)
    print("[%d] name=%r vsize=0x%X vaddr=0x%X rawsize=0x%X rawptr=0x%X" % (
        i, name.decode("latin-1"), vsize, vaddr, rawsize, rawptr))
