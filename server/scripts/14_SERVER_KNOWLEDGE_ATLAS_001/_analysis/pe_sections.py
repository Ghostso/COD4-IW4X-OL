import pefile
p = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
pe = pefile.PE(p, fast_load=True)
pe.parse_data_directories()
print("ImageBase 0x%X" % pe.OPTIONAL_HEADER.ImageBase)
print("EntryPoint RVA 0x%X" % pe.OPTIONAL_HEADER.AddressOfEntryPoint)
print("SizeOfImage 0x%X" % pe.OPTIONAL_HEADER.SizeOfImage)
print("NumberOfSections %d" % pe.FILE_HEADER.NumberOfSections)
print("Sections:")
for s in pe.sections:
    nm = s.Name.rstrip(b"\x00").decode("latin1")
    print("  %-10s VA=0x%08X VSize=0x%08X RawPtr=0x%08X RawSize=0x%08X Ch=%08X" % (
        nm, s.VirtualAddress, s.Misc_VirtualSize, s.PointerToRawData, s.SizeOfRawData, s.Characteristics))