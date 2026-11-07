import struct
def a(v,A):return (v+A-1)&~(-A)
t=bytearray(b'\xb8\x78\x56\x34\x12\xc3\xc3')
s1=b'GetResourceManagerII\x00'
s2=b'ReleaseResourceManagerII\x00'
r=bytearray()
r+=s1
r+=s2
d=bytearray(struct.pack('<L',0))+b'\x00'*0x410
# DOS header
o=bytearray(64)
o[0:2]=b'MZ'
# NT headers
nt=b'PE\x00\x00'
# File header
mh=struct.pack('<HHIIIHH',0x14c,3,0,0,0,224,0x2000|0x0100)
# Optional header
oh=struct.pack('<LLLLLLLLLLLLLLLLLLLLLLLLLLLLLL',
    0x10b,0,0,len(t),len(r)+len(d),0,0x1000,0x1000,0x3000,0x10000000,0x1000,0x200,4,0,0,0,4,0,0,0,0,0,0,0,0,2,0,0x100000,0x1000,0x100000,0x1000,0,0,16)
# Section headers
sh=bytearray()
# .text
sh+=struct.pack('<8sIIIIIHHII',b'.text\x00\x00\x00',len(t),0,0,0,0,0,0,0,0x60000020)
# .rdata
sh+=struct.pack('<8sIIIIIHHII',b'.rdata\x00\x00\x00',len(r),0,0,0,0,0,0,0,0x40000040)
# .data
sh+=struct.pack('<8sIIIIIHHII',b'.data\x00\x00\x00',len(d),0,0,0,0,0,0,0,0xC0000040)
# PE so far
pe=bytearray()
pe+=o
pe+=nt
pe+=mh
pe+=oh
pe+=sh
# Set e_lfanew
struct.pack_into('<L',o,0x3c,64)
# Set size of headers
szh=len(pe)
szh=a(szh,0x200)
struct.pack_into('<L',pe,64+4+20+60,szh)
# Set sections' virtual addresses and pointers to raw data
cva=0x1000
cfo=szh
for i in range(3):
    o_sh=64+4+20+224+i*40
    struct.pack_into('<L',pe,o_sh+12,cva)
    sz=len([t,r,d][i])
    struct.pack_into('<L',pe,o_sh+4,sz)
    szr=a(sz,0x200)
    struct.pack_into('<L',pe,o_sh+16,szr)
    struct.pack_into('<L',pe,o_sh+20,cfo)
    cva=a(cva+len([t,r,d][i]),0x1000)
    cfo+=szr
# Set size of image
cva=0x1000
for i in range(3):
    o_sh=64+4+20+224+i*40
    sz=struct.unpack_from('<L',pe,o_sh+4)[0]
    cva=a(cva+sz,0x1000)
szim=cva-0x1000
szim=a(szim,0x1000)
struct.pack_into('<L',pe,64+4+20+56,szim)
# Set address of entry point, base of code, base of data
struct.pack_into('<L',pe,64+4+20+16,0x1000)
struct.pack_into('<L',pe,64+4+20+20,0x1000)
struct.pack_into('<L',pe,64+4+20+24,0x3000)
# Set size of code and size of initialized data
struct.pack_into('<L',pe,64+4+20+36,len(t))
struct.pack_into('<L',pe,64+4+20+40,len(r)+len(d))
# Write sections' data
for i in range(3):
    o_sh=64+4+20+224+i*40
    ptr=struct.unpack_from('<L',pe,o_sh+20)[0]
    sec=[t,r,d][i]
    pe[ptr:ptr+len(sec)]=sec
    szr=a(len(sec),0x200)
    if szr>len(sec):
        pe[ptr+len(sec):ptr+szr]=b'\x00'*(szr-len(sec))
# Write file
with open('LocalRM.dll','wb') as f:
    f.write(pe)
print('LocalRM.dll')