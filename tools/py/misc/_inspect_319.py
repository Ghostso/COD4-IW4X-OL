import pefile

exe = r"D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\sandbox_datafix_20260929\codoMP_client_shipRetail.exe"
pe = pefile.PE(exe, fast_load=True)
print("TimeDateStamp: 0x%X" % pe.FILE_HEADER.TimeDateStamp)
print("SizeOfImage: 0x%X" % pe.OPTIONAL_HEADER.SizeOfImage)
print("NumberOfSections:", len(pe.sections))
for s in pe.sections:
    print("  %-8s VA=0x%08X RawSize=0x%08X" % (s.Name.decode(errors='ignore').strip('\x00'), s.VirtualAddress, s.SizeOfRawData))
