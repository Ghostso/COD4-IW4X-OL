from capstone import *
p=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); md=Cs(CS_ARCH_X86,CS_MODE_32)
for s,e in [(0xae9000,0xaea000),(0xaf0000,0xaf3000),(0x49c000,0x49d000)]:
    print('\n===',hex(s),hex(e),'===')
    n=0
    for ins in md.disasm(d[s-0x400000:e-0x400000],s):
        print(f'{ins.address:08x} {ins.bytes.hex():<18} {ins.mnemonic:<8} {ins.op_str}')
        n+=1
        if n>1200: break
    print('shown',n)
