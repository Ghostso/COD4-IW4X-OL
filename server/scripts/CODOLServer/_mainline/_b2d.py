from capstone import *
import struct
p=r"CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(p,"rb").read(); base=0x400000
def s(va):
    o=va-base
    if o<0 or o>=len(d): return None
    e=d.find(b"\x00",o)
    if e<0: return None
    return d[o:e].decode("latin1","replace")
print("=== 0x82E1580 处的值（配置对象指针）===")
v=struct.unpack_from("<I",d,0x82E1580-base)[0]
print("   [0x82E1580] = 0x%08X"%v)
print()
print("=== 谁写 0x82E1580 ===")
le=struct.pack("<I",0x82E1580)
hits=[];o=0
while True:
    j=d.find(le,o)
    if j<0: break
    hits.append(base+j); o=j+1
print("   引用:",[hex(x) for x in hits])
md=Cs(CS_ARCH_X86, CS_MODE_32)
for va in hits[:4]:
    st=max(0,va-base-20)
    print("--- 0x%08X ---"%va)
    for ins in md.disasm(d[st:va-base+10], base+st):
        m="  <<<" if ins.address<=va<ins.address+ins.size else ""
        print("    %08X  %-20s %s %s%s"%(ins.address,ins.bytes.hex(),ins.mnemonic,ins.op_str,m))
print()
print("=== 附近字符串（找密钥/键名）===")
o2=0x82E1500-base
if 0<=o2<len(d):
    for m in __import__("re").finditer(rb"[\x20-\x7e]{4,}", d[o2:o2+0x200]):
        print("   0x%08X %r"%(0x82E1500+m.start(), m.group().decode("latin1")[:90]))
