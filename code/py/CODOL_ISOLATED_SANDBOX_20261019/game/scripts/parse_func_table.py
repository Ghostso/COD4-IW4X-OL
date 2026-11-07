import struct, sys
sys.stdout.reconfigure(encoding='utf-8')

dll_path = r'd:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetailBase.dll'
with open(dll_path, 'rb') as f:
    data = f.read()

# DOS header
dos_magic = data[:2]
dos = struct.unpack_from('<4sIIIIIIHHHHHH', data, 0)
pe_offset = dos[1]
print(f"DOS magic: {dos_magic}")
print(f"PE offset: 0x{pe_offset:08x}")

# PE signature
pe_sig = data[pe_offset:pe_offset+4]
print(f"PE signature: {pe_sig.hex()}")

# At PE+4: 64-byte extended header
ext = struct.unpack_from('<I', data, pe_offset+4)[0]
print(f"Extended header field: 0x{ext:08x}")

# Try standard COFF at PE+4
coff_machine, coff_sections, coff_timedate, coff_sym, coff_nsym, coff_opt_size = struct.unpack_from('<HHIIII', data, pe_offset+4)
print(f"Coff: machine=0x{coff_machine:04x}, sections={coff_sections}, opt_size={coff_opt_size}")

# Section headers
sec_start = pe_offset + 4 + coff_opt_size
print(f"Section table starts at: 0x{sec_start:08x}")
print(f"File size: 0x{len(data):08x}")

sections = []
for i in range(min(coff_sections, 50)):
    off = sec_start + i * 40
    if off + 40 > len(data):
        break
    raw = data[off:off+40]
    name = raw[:8].rstrip(b'\x00')
    vsize, rawsize, vaddr, rawaddr, reloc, line, nreloc, nline, flags = struct.unpack_from('<IIIIIIIHH', raw, 8)
    name_str = name.decode('latin1', errors='replace')
    sections.append({
        'name': name_str,
        'vsize': vsize,
        'rawsize': rawsize,
        'vaddr': vaddr,
        'rawaddr': rawaddr,
        'flags': flags,
    })
    print(f"  [{i}] {name_str:20s} va=0x{vaddr:08x} vsize=0x{vsize:08x} rawaddr=0x{rawaddr:08x} rawsize=0x{rawsize:08x} flags=0x{flags:08x}")

def file_offset(va):
    for s in sections:
        if s['vaddr'] <= va < s['vaddr'] + s['vsize']:
            delta = va - s['vaddr']
            if delta < s['rawsize']:
                return s['rawaddr'] + delta
    return None

# Find function table at 0x9abb18
func_table_va = 0x9abb18
func_table_off = file_offset(func_table_va)
print(f"\nFunction table VA: 0x{func_table_va:08x}")
print(f"Function table file offset: 0x{func_table_off:08x}")

if func_table_off:
    print("\nFirst 120 entries:")
    for i in range(120):
        p_va = struct.unpack_from('<I', data, func_table_off + i*4)[0]
        p_off = file_offset(p_va)
        name = ""
        if p_off and p_off < len(data):
            end = p_off
            while end < len(data) and data[end] != 0:
                end += 1
            name = data[p_off:end].decode('utf-8', errors='replace')[:80]
        print(f"  [{i:3d}] 0x{p_va:08x} -> {name}")
