import pefile, struct

# Base.dll .tvm0 is 32MB of encrypted/VM bytecode
# It's fully raw-backed (not virtual-only like the Engine gap)
# The VM interpreter in .text decrypts and executes .tvm0 bytecode

# Key addresses from ICH-008:
# Base.dll ordinal-1 stub: RVA 0x1D6582C
# VM dispatcher: RVA 0x1F27FDC → 0x1F9DFFD
# These are all inside .tvm0 section

# The VM dispatcher must have code that:
# 1. Reads VM bytecode from .tvm0
# 2. Interprets instructions
# 3. CALLs into Engine gap addresses
# 4. Reads return values

# Let's search .tvm0 for references to Engine gap addresses
pe = pefile.PE('COD OL/codoMP_client_shipRetailBase.dll')
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()

# Engine gap VA range: 0x00994000..0x00CA789A
# In .tvm0 these addresses would be stored as DWORDs

engine_start = 0x00994000
engine_end = 0x00CA789A

# Search .tvm0 section for absolute references to Engine gap
tvm0_start_rva = 0x19DD000
tvm0_size = 0x1F5D600

print('=== Searching .tvm0 for Engine gap address references ===')
refs = []
idx = tvm0_start_rva
end_rva = tvm0_start_rva + tvm0_size

# Search for 4-byte patterns that fall in Engine gap VA range
for i in range(0, tvm0_size - 4, 4):
    rva = tvm0_start_rva + i
    val = struct.unpack_from('<I', data, rva)[0]
    if engine_start <= val <= engine_end:
        refs.append((rva, val))

print(f'Total Engine VA references in .tvm0: {len(refs)}')
print()

# Show first 30
for rva, val in refs[:30]:
    print(f'  .tvm0 RVA {hex(rva)}: value {hex(val)} (Engine gap)')

# Also search for known Engine function addresses
known_engine_funcs = [0x00CA0000, 0x009B9C00, 0x00B00000, 0x009B9D30, 0x009C1310]
print()
print('=== Known Engine function addresses in .tvm0 ===')
for func_va in known_engine_funcs:
    func_le = struct.pack('<I', func_va)
    idx = data.find(func_le, tvm0_start_rva, end_rva)
    count = 0
    while idx >= 0 and idx < end_rva:
        count += 1
        if count <= 3:
            print(f'  {hex(func_va)} found at .tvm0 RVA {hex(idx)}')
        idx = data.find(func_le, idx+1, end_rva)
    print(f'  {hex(func_va)}: {count} references')
