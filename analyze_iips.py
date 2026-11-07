import pefile
import sys

def main():
    if len(sys.argv) < 2:
        print("Usage: python analyze_iips.py <dll>")
        sys.exit(1)
    dll_path = sys.argv[1]
    pe = pefile.PE(dll_path)
    print(f"Machine: {pe.FILE_HEADER.Machine:#x} ({'I386' if pe.FILE_HEADER.Machine == 0x14c else 'unknown'})")
    print(f"Number of sections: {pe.FILE_HEADER.NumberOfSections}")
    print(f"EntryPoint: {pe.OPTIONAL_HEADER.AddressOfEntryPoint:#x}")
    print(f"ImageBase: {pe.OPTIONAL_HEADER.ImageBase:#x}")
    
    if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
        print("\nExport table:")
        print(f"  Characteristics: {pe.DIRECTORY_ENTRY_EXPORT.struct.Characteristics:#x}")
        print(f"  TimeDateStamp: {pe.DIRECTORY_ENTRY_EXPORT.struct.TimeDateStamp:#x}")
        print(f"  MajorVersion: {pe.DIRECTORY_ENTRY_EXPORT.struct.MajorVersion}")
        print(f"  MinorVersion: {pe.DIRECTORY_ENTRY_EXPORT.struct.MinorVersion}")
        try:
            export_name = pe.DIRECTORY_ENTRY_EXPORT.name.decode('utf-8')
            print(f"  Name: {export_name}")
        except:
            print(f"  Name RVA: {pe.DIRECTORY_ENTRY_EXPORT.struct.Name:#x}")
        print(f"  Base: {pe.DIRECTORY_ENTRY_EXPORT.struct.Base:#x}")
        print(f"  NumberOfFunctions: {pe.DIRECTORY_ENTRY_EXPORT.struct.NumberOfFunctions}")
        print(f"  NumberOfNames: {pe.DIRECTORY_ENTRY_EXPORT.struct.NumberOfNames}")
        print(f"  AddressOfFunctions RVA: {pe.DIRECTORY_ENTRY_EXPORT.struct.AddressOfFunctions:#x}")
        print(f"  AddressOfNames RVA: {pe.DIRECTORY_ENTRY_EXPORT.struct.AddressOfNames:#x}")
        print(f"  AddressOfNameOrdinals RVA: {pe.DIRECTORY_ENTRY_EXPORT.struct.AddressOfNameOrdinals:#x}")
        
        print("\nExported functions:")
        for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            if exp.name:
                try:
                    name = exp.name.decode('utf-8')
                except:
                    name = str(exp.name)
                print(f"  {name} (ordinal {exp.ordinal}) at RVA {exp.address:#x}")
    else:
        print("No export directory found.")

if __name__ == '__main__':
    main()