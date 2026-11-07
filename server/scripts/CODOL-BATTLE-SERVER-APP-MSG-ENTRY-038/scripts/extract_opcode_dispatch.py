import struct,capstone,json
IMG=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOLServer\\_mainline\\_dyn100_run_20260925_182324\\live\\image_best.bin"
b=open(IMG,'rb').read();IB=0x400000
def dis(rva,n=64):
 md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
 return list(md.disasm(b[rva:rva+n],IB+rva))
def fmt(i):return f"{i.address-IB:08X} {i.bytes.hex():<20s} {i.mnemonic} {i.op_str}".rstrip()
idx_tbl_rva=0x20077c;jmp_tbl_rva=0x200744
print('=== opcode dispatch table (correct RVA base) ===')
rows=[]
for op in range(26):
 slot=b[idx_tbl_rva+op]
 va=struct.unpack_from('<I',b,jmp_tbl_rva+slot*4)[0]
 tgt=va-IB
 rows.append((op,slot,tgt))
 print(f'opcode={op:2d} slot={slot:3d} target_rva={tgt:#010x} target_va={va:#010x} bytes={b[tgt:tgt+8].hex()}')
print('\n=== unique targets with first instructions ===')
seen=[]
for op,slot,tgt in rows:
 if tgt not in [x[0] for x in seen]: seen.append((tgt,op))
for tgt,op in seen:
 print(f'--- target RVA {tgt:#x} first-opcode {op} ---')
 for i in dis(tgt,48): print(fmt(i))
print('\n=== dispatcher boundary and nearby callers probe ===')
md=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_32);md.detail=True
# find rel32 calls to dispatcher entry
entry=0x2000a0
calls=[]
for rva in range(0x1000,0x8a6000-5):
 if b[rva]==0xe8:
  rel=struct.unpack_from('<i',b,rva+1)[0]
  if (rva+5+rel)==entry:
   calls.append(rva)
print('direct call sites to 0x2000A0:',[hex(x) for x in calls])
# int3/prologue boundaries around caller sites
for c in calls[:20]:
 print(f'--- call site {c:#x} ---')
 for i in dis(max(0,c-64),128): print(fmt(i))
json.dump(rows,open(r'D:\\BaiduNetdiskDownload\\使命召唤OL\\CODOL-BATTLE-SERVER-APP-MSG-ENTRY-038\\evidence\\opcode_rows.json','w'),indent=2)
