import pefile, struct, os, re
from capstone import Cs, CS_ARCH_X86, CS_MODE_32

def va_to_off(pe, va):
    rva=va-pe.OPTIONAL_HEADER.ImageBase
    return pe.get_offset_from_rva(rva)

def search_hits(path, needles):
    pe=pefile.PE(path, fast_load=True)
    data=open(path,'rb').read()
    print('\n###',path,'base',hex(pe.OPTIONAL_HEADER.ImageBase))
    for name, va in needles:
        b=struct.pack('<I',va)
        hits=[]
        start=0
        while True:
            i=data.find(b,start)
            if i<0: break
            try: v=pe.OPTIONAL_HEADER.ImageBase+pe.get_rva_from_offset(i)
            except: v=None
            hits.append((i,v,data[max(0,i-8):i+12]))
            start=i+1
        print(name,hex(va),'raw hits',len(hits))
        for i,v,ctx in hits[:80]:
            print(' ',hex(i),hex(v) if v else '?',ctx.hex())
        if len(hits)>80: print(' ...')

search_hits(r'WeGame\tgp_daemon.exe', [
 ('GetCommandLineW',0x4c6088),('GetCommandLineA',0x4c608c),('CreateProcessW',0x4c6090),
 ('CreateFileW',0x4c6114),('GetPrivateProfileStringW',0x4c611c),('WritePrivateProfileStringW',0x4c6118),
 ('OpenProcess',0x4c60d4),('CreateFileMappingW',0x4c6094),('MapViewOfFile',0x4c60a8),
 ('StartFor',0x4c9b24),('cmd_launcher_info.ini',0x4cbc14),('cmd_launcher_info',0x4cbc2c),('cmd_start_for',0x4cbc40),
])
search_hits(r'WeGame\client_launcher.exe', [
 ('GetCommandLineW',0x432020),('GetCommandLineA',0x432104),('CreateProcessW',0x43201c),
 ('GetEnvironmentVariableW',0x432024),('SetEnvironmentVariableW',0x432028),('CreateFileW',0x432150),
 ('OpenProcess',0x43206c),('OpenEventA',0x432014),('StartFor',0x432b10),('game_id',0x432897),
])
