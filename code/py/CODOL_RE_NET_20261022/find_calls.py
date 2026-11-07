import struct
p=r'run_codol_001\runs\OMIT_RETEST_20261022\mem\mem_005.bin'
d=open(p,'rb').read(); BASE=0x400000
# code section 0: RVA 0x1000..0x8A689A (dump offsets same as RVA)
start,end=0x1000,0x8A689A
ws2={'WSAStartup':0x779A9CC0,'gethostname':0x779D00A0,'WSAGetLastError':0x779A5D50,'inet_addr':0x779A57E0,'closesocket':0x779AEA60,'socket':0x779AC990,'ioctlsocket':0x779B2520,'ntohs':0x779A56E0,'bind':0x779AD890,'gethostbyname':0x779CFF10,'connect':0x779B5710,'sendto':0x779B6160}
import bisect
# build sorted list of function starts for ws2 known? We only know those.
def find_calls(target):
    res=[]
    for i in range(start,end-5):
        if d[i]==0xE8:
            rel=struct.unpack_from('<i',d,i+1)[0]
            va=BASE+i
            tgt=(va+5+rel)&0xffffffff
            if tgt==target: res.append(va)
    return res
for nm,t in ws2.items():
    r=find_calls(t)
    print('%-16s target=%#010x calls=%d %s'%(nm,t,len(r),[hex(x) for x in r[:20]]))
# FF15 absolute calls into ws2 range
print('\nFF15 calls into ws2 range:')
for i in range(start,end-6):
    if d[i]==0xFF and d[i+1]==0x15:
        ptr=struct.unpack_from('<I',d,i+2)[0]
        if 0x779A0000<=ptr<0x779E0000:
            print('  caller RVA %#x -> [%#x]'%(i,ptr))
