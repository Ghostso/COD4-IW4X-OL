import pefile, re

dll_path = r"D:\BaiduNetdiskDownload\CODOL-AlphaBuild_By_Antia(20261006)\CODOL-AlphaBuild By Antia\CODOL_Client\Kernel33.dll"
pe = pefile.PE(dll_path)
print("Sections:")
for s in pe.sections:
    print(f"  {s.Name.decode().strip(chr(0))} VA=0x{s.VirtualAddress:X} Size=0x{s.SizeOfRawData:X}")

with open(dll_path, "rb") as f:
    data = f.read()

print("\n--- Trainer & Command references in Kernel33.dll ---")
strings = re.findall(b'[\x20-\x7e]{5,}', data)
for s in strings:
    s_str = s.decode('ascii', errors='ignore')
    for kw in ['trainer', 'map', 'sv_', 'devmap', 'console', 'cbuf', 'cmd', 'dedicated', 'loopback', 'match']:
        if kw in s_str.lower():
            if len(s_str) < 100:
                print(f"  {s_str}")
            break
