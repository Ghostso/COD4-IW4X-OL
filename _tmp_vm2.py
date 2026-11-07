import pefile, struct

pe = pefile.PE('COD OL/codoMP_client_shipRetailBase.dll')
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()

# Search byte-level for Engine addresses in .tvm0
targets = [
    (0x00CA0000, 'code_pre_gfx bootstrap'),
    (0x009B9C00, 'state accessor'),
    (0x00B00000, 'virtual dispatch'),
]

tvm0_start = 0x19DD000
tvm0_size = 0x1F5D600

print('=== Byte-level search for Engine addresses in .tvm0 ===')
for target_va, desc in targets:
    target_le = struct.pack('<I', target_va)
    count = 0
    idx = tvm0_start
    end = tvm0_start + tvm0_size
    positions = []
    while idx < end:
        idx = data.find(target_le, idx, end)
        if idx < 0: break
        count += 1
        positions.append(idx)
        idx += 1
    print(f'  {hex(target_va)} ({desc}): {count} refs')
    for p in positions[:5]:
        print(f'    at .tvm0 RVA {hex(p)}')

print()

# Search .text for .tvm0 base address references
tvm0_va = 0x119DD000
tvm0_le = struct.pack('<I', tvm0_va)
count = 0
idx = 0x1000
end = 0x1000 + 0x742000
positions = []
while idx < end:
    idx = data.find(tvm0_le, idx, end)
    if idx < 0: break
    count += 1
    positions.append(idx)
    idx += 1
print(f'=== .tvm0 base VA ({hex(tvm0_va)}) refs in .text: {count} ===')
for p in positions[:10]:
    print(f'  .text RVA {hex(p)}')

print()

# The .tls section is also executable and large (0xED3000)
# Check if VM interpreter might be in .tls
tls_start = 0x10B0A000
tls_size = 0xED2600
print(f'=== .tls section: {hex(base+tls_start)}..{hex(base+tls_start+0xED3000)} ({tls_size:,} bytes) ===')
# Search .tls for Engine addresses too
for target_va, desc in targets:
    target_le = struct.pack('<I', target_va)
    idx = tls_start
    end = tls_start + tls_size
    count = 0
    while idx < end:
        idx = data.find(target_le, idx, end)
        if idx < 0: break
        count += 1
        idx += 1
    if count > 0:
        print(f'  {hex(target_va)} in .tls: {count} refs')
