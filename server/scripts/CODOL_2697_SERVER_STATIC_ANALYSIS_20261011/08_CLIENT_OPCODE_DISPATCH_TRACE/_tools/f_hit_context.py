import sys, struct, hashlib
sys.path.insert(0, r'D:\BaiduNetdiskDownload\使命召唤OL\CODOL_2697_SERVER_STATIC_ANALYSIS_20261011\07_PROTOCOL_BIDIRECTIONAL_TRACE\_tools')
import c_common as c
from capstone import Cs, CS_ARCH_X86, CS_MODE_32
md=Cs(CS_ARCH_X86,CS_MODE_32)
im=c.load()
for name, rva in [('A2E50',0xA2E50),('A2D90',0xA2D90)]:
    print('====',name,hex(rva),'====')
    for nm,va,vsz,ptr,rsz in im.sections:
        if va <= rva < va+rsz:
            fo=ptr+rva-va
            print('section',nm,'rva',hex(rva),'file',hex(fo))
    for s in im.pe.sections:
        nm=s.Name.rstrip(b'\\x00').decode('latin1')
        if s.VirtualAddress <= rva < s.VirtualAddress + s.SizeOfRawData:
            print('flags',hex(s.Characteristics),'vsz',hex(s.Misc_VirtualSize),'raw',hex(s.SizeOfRawData),'ptr',hex(s.PointerToRawData))
    code=im.read_rva(rva,512)
    print('bytes',code[:32].hex())
    cnt=0
    for ins in md.disasm(code,im.ib+rva):
        print(hex(ins.address),ins.bytes.hex(),ins.mnemonic,ins.op_str)
        cnt+=1
        if cnt>=40: break
    print()
for label,rva in [('TVM_E50',0xD9D940F),('TVM_D90',0xD97BF7E)]:
    print('====',label,hex(rva),'====')
    for nm,va,vsz,ptr,rsz in im.sections:
        if va <= rva < va+rsz: print('section',nm,'file',hex(ptr+rva-va))
    code=im.read_rva(rva-32,96)
    for ins in md.disasm(code,im.ib+rva-32):
        print(hex(ins.address),ins.bytes.hex(),ins.mnemonic,ins.op_str)
    print()
