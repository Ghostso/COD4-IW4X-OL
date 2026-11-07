import pefile

exe = r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\native\bin2697\codol_dedrun.exe"
pe = pefile.PE(exe)
print("Sections:")
for s in pe.sections:
    print(f"  {s.Name.decode().strip(chr(0))} VA=0x{s.VirtualAddress:X} Size=0x{s.SizeOfRawData:X}")

print("\nSubsystem:", pe.OPTIONAL_HEADER.Subsystem)
print("ImageBase: 0x%X" % pe.OPTIONAL_HEADER.ImageBase)
print("EntryPoint: 0x%X" % (pe.OPTIONAL_HEADER.ImageBase + pe.OPTIONAL_HEADER.AddressOfEntryPoint))

if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
    print("\nImports:")
    for entry in pe.DIRECTORY_ENTRY_IMPORT:
        print(f"  {entry.dll.decode()}: {len(entry.imports)} imports")
