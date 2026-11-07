import pefile, re
from capstone import *
p=r"COD OL\IIPS\iips.dll"
pe=pefile.PE(p); ib=pe.OPTIONAL_HEADER.ImageBase
d=open(p,"rb").read()
md=Cs(CS_ARCH_X86, CS_MODE_32)
# Find the IIPSClient::Start function: locate string ref '[IIPSClient::Start()][failed to conncet pipe]'
# Search for the pattern that builds pipe name: '\\\\.\\Pipe\\' + name
# First find all string VAs of interest
strs = {}
for key in [b"failed to conncet pipe", b"\\\\.\\Pipe\\", b"[IIPSClientListenThread()][pipe thread start while(true)]",
            b"asynchronous connect succeed", b"error of pipe handle,thread exit",
            b"[IIPSClient::SendMsg()][SendMsg Error]", b"IIPSClient.ini", b"HostPid"]:
    i = d.find(key)
    if i>=0:
        strs[key]= ib + pe.get_rva_from_offset(i)
print("string VAs:")
for k,v in strs.items(): print("  0x%08X %r"%(v,k[:50]))
print()
# For each string VA, find code refs in .text
text=[s for s in pe.sections if b".text" in s.Name][0]
blob=d[text.PointerToRawData:text.PointerToRawData+text.SizeOfRawData]
code_va=ib+text.VirtualAddress
want=set(strs.values())
hits={}
for ins in md.disasm(blob, code_va):
    if ins.mnemonic in ("push","mov","lea") and ins.op_str:
        for v in want:
            if ("0x%x"%v) in ins.op_str:
                hits.setdefault(v,[]).append((ins.address, ins.bytes.hex(), ins.mnemonic+" "+ins.op_str))
for v in sorted(hits):
    name=[k for k,val in strs.items() if val==v][0]
    print("0x%08X  %r  -> %d refs" % (v, name[:60], len(hits[v])))
    for a,b,t in hits[v][:6]:
        print("     %08X %-24s %s"%(a,b,t))
