import pefile, re

dll_path = r'D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\server2697\client_native_loopback.dll'
pe = pefile.PE(dll_path)
base = pe.OPTIONAL_HEADER.ImageBase
text_sec = [s for s in pe.sections if b'.text' in s.Name][0]
data = pe.__data__[text_sec.PointerToRawData : text_sec.PointerToRawData + text_sec.SizeOfRawData]
rdata_sec = [s for s in pe.sections if b'.rdata' in s.Name][0]
rdata_data = pe.__data__[rdata_sec.PointerToRawData : rdata_sec.PointerToRawData + rdata_sec.SizeOfRawData]

for m in re.finditer(b'([a-zA-Z0-9_%:= ./-]{5,}\x00)', rdata_data):
    s = m.group(1)[:-1].decode('ascii', errors='ignore')
    rdata_va = base + rdata_sec.VirtualAddress + m.start()
    pattern = (rdata_va).to_bytes(4, 'little')
    pos = 0
    refs = []
    while True:
        idx = data.find(pattern, pos)
        if idx == -1: break
        text_va = base + text_sec.VirtualAddress + idx
        refs.append(hex(text_va))
        pos = idx + 1
    if refs and len(s) > 5:
        print(f'{hex(rdata_va)}: "{s}" referenced at {refs}')
