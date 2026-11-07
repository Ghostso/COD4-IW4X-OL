import pefile

pe = pefile.PE('COD OL/codoMP_client_shipRetailBase.dll')
base = pe.OPTIONAL_HEADER.ImageBase
print('Base.dll ImageBase:', hex(base))
print('Base.dll size:', len(pe.__data__))
for s in pe.sections:
    name = s.Name.decode().rstrip(chr(0))
    is_exec = bool(s.Characteristics & 0x20000000)
    print(f'  {name}: VA={hex(base+s.VirtualAddress)} VSize={hex(s.Misc_VirtualSize)} Raw={hex(s.SizeOfRawData)} Exec={is_exec}')
    if name == '.tvm0':
        print(f'    .tvm0: VA={hex(base+s.VirtualAddress)}..{hex(base+s.VirtualAddress+s.Misc_VirtualSize)}')
        print(f'    Raw data: {s.SizeOfRawData} bytes')
        data = pe.get_memory_mapped_image()
        tvm0 = data[s.VirtualAddress:s.VirtualAddress+min(64, s.SizeOfRawData)]
        h = tvm0.hex(' ')
        print(f'    First 64: {h}')
        nz = sum(1 for b in tvm0 if b != 0)
        print(f'    Non-zero: {nz}/{len(tvm0)}')
