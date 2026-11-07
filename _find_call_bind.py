import pefile, capstone

dll_path = r"E:\CODOL_SANDBOX\RUN001\Ayria\Plugins\CodolGameServer.Localnet32"
pe = pefile.PE(dll_path)
base = pe.OPTIONAL_HEADER.ImageBase
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)

target_va = 0x1020AB90 # Bindings.bind()

text_sec = [s for s in pe.sections if b'.text' in s.Name][0]
data = pe.__data__[text_sec.PointerToRawData : text_sec.PointerToRawData + text_sec.SizeOfRawData]
sec_va = base + text_sec.VirtualAddress

# Search for E8 relative calls
import struct
calls = []
for i in range(len(data) - 5):
    if data[i] == 0xE8:
        rel = struct.unpack("<i", data[i+1:i+5])[0]
        call_target = sec_va + i + 5 + rel
        if call_target == target_va:
            file_off = text_sec.PointerToRawData + i
            call_va = sec_va + i
            calls.append((file_off, call_va))

print(f"Found {len(calls)} calls to Bindings.bind() (VA 0x{target_va:X}):")
for f_off, c_va in calls:
    print(f"  File offset 0x{f_off:06X} (VA 0x{c_va:08X})")
    # disassemble 30 bytes before and 30 bytes after
    start = max(0, f_off - text_sec.PointerToRawData - 20)
    chunk = data[start:start + 45]
    for ins in md.disasm(chunk, sec_va + start):
        mark = "  <-- CALL BIND()" if ins.address == c_va else ""
        print(f"    0x{ins.address:08X}: {ins.mnemonic:8} {ins.op_str}{mark}")
