import pefile, struct, capstone

# KEY FINDING: 0x00CA0000 has 5 references in Base.dll .tvm0!
# This means the VM dispatcher DOES have Engine gap addresses embedded in it.
# These are likely VM bytecode operands that tell the VM interpreter
# to CALL or JMP to these Engine addresses.

# Let's also search for 0x009B9C00 with byte alignment variations
pe = pefile.PE('COD OL/codoMP_client_shipRetailBase.dll')
base = pe.OPTIONAL_HEADER.ImageBase
data = pe.get_memory_mapped_image()

# Search byte-by-byte (not just 4-byte aligned)
print('=== Byte-level search for known Engine addresses in .tvm0 ===')
targets = {
    0x00CA0000: 'code_pre_gfx bootstrap',
    0x009B9C00: 'state accessor (ICH-021 confirmed)',
    0x00B00000: 'virtual dispatch function',
}

tvm0_start = 0x19DD000
tvm0_size = 0x1F5D600

for target_va, desc in targets.items():
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

# Now let's search for the VM dispatcher's CALL/JMP patterns
# The VM dispatcher is at RVA 0x1F27FDC and 0x1F9DFFD
# Let's disassemble around the VM dispatcher to understand how it dispatches

print('=== VM Dispatcher disassembly (RVA 0x1F9DFFD) ===')
md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
# The VM dispatcher at 0x1F9DFFD is inside .tvm0 (encrypted bytecode)
# We can't disassemble it directly because it's VM bytecode, not x86
# The actual x86 VM interpreter is in .text

# Let's look at .text for the VM interpreter
# The interpreter must read .tvm0 data and perform indirect calls
# Search .text for code that reads from .tvm0 address range

print()
print('=== .text references to .tvm0 address range ===')
.text_start = 0x1000
.text_size = 0x742000

# Search for .tvm0 base address (0x119DD000 with base 0x10000000 → VA 0x119DD000)
# The actual VA would be ImageBase + RVA
# .tvm0 VA = 0x10000000 + 0x19DD000 = 0x119DD000
tvm0_va_start = 0x119DD000

# Search for this value in .text
tvm0_le = struct.pack('<I', tvm0_va_start)
count = 0
idx = 0x1000
end = 0x1000 + 0x742000
while idx < end:
    idx = data.find(tvm0_le, idx, end)
    if idx < 0: break
    count += 1
    if count <= 5:
        print(f'  .tvm0 base VA ref at .text RVA {hex(idx)}')
    idx += 1
print(f'  Total .tvm0 base references in .text: {count}')
