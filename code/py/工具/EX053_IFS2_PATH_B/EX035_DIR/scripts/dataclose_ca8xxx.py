from pathlib import Path
import struct, csv, json
from collections import Counter, defaultdict, deque
from capstone import Cs, CS_ARCH_X86, CS_MODE_32, CS_OP_IMM, CS_OP_MEM, CS_OP_REG

EXE = Path(r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\codoMP_client_shipRetail.exe')
OUT = Path(r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts\_out')
TMP = Path(r'D:\BaiduNetdiskDownload\使命召唤OL\COD OL\scripts\_tmp')
OUT.mkdir(parents=True, exist_ok=True); TMP.mkdir(parents=True, exist_ok=True)
IB = 0x400000
SLOTS = {0x00CA8114:0x00A13726,0x00CA8194:0x00A1397A,0x00CA812C:0x00A1378C,0x00CA819C:0x00A139A0,0x00CA8164:0x00A1389E}
ENTRY_RVA = 0x0E5DC690
ENTRY_SLOT = 0x0E9DC665
D = EXE.read_bytes()

# Parse PE metadata only; section payloads are accessed exclusively through file_off/read.
pe = struct.unpack_from('<I', D, 0x3c)[0]
assert D[pe:pe+4] == b'PE\0\0'
nsec = struct.unpack_from('<H', D, pe+6)[0]
opt = pe+24
optsz = struct.unpack_from('<H', D, pe+20)[0]
secoff = opt+optsz
SECS=[]
for i in range(nsec):
    h=secoff+40*i
    name=D[h:h+8].split(b'\0',1)[0].decode('latin1','replace')
    vs,va,rs,pr=struct.unpack_from('<IIII',D,h+8)
    ch=struct.unpack_from('<I',D,h+36)[0]
    SECS.append(dict(i=i,name=name,va=va,vs=vs,rs=rs,pr=pr,ch=ch))

def sec(rva):
    for s in SECS:
        if s['va'] <= rva < s['va']+max(s['vs'],s['rs']): return s
    return None

def off(rva):
    s=sec(rva)
    if not s or s['name'].lower()=='.tvm0': return None
    q=rva-s['va']
    return s['pr']+q if 0 <= q < s['rs'] else None

def read(rva,n):
    o=off(rva)
    if o is None or o+n>len(D): return None
    return D[o:o+n]

def u32(rva):
    b=read(rva,4)
    return struct.unpack('<I',b)[0] if b else None

def is_exec(rva):
    s=sec(rva)
    return bool(s and s['name'].lower()!='.tvm0' and (s['ch']&0x20000000) and off(rva) is not None)

md=Cs(CS_ARCH_X86,CS_MODE_32); md.detail=True

def dec(rva,max_len=0x2000,count=0):
    o=off(rva); s=sec(rva)
    if o is None or not s or s['name'].lower()=='.tvm0': return []
    lim=min(max_len,len(D)-o,s['rs']-(rva-s['va']))
    if lim<=0: return []
    return list(md.disasm(D[o:o+lim],IB+rva,count=count))

def text(i): return f'{i.mnemonic} {i.op_str}'.strip()

# Exact absolute-memory references, and exact mov reg,[slot] / call reg pairs.
refs=[]; movpairs=[]
for s in SECS:
    if s['name'].lower()=='.tvm0': continue
    b=D[s['pr']:s['pr']+s['rs']]
    for j in range(max(0,len(b)-5)):
        rva=s['va']+j
        if b[j]==0xff and b[j+1] in (0x15,0x25):
            slot=struct.unpack_from('<I',b,j+2)[0]
            if slot in SLOTS:
                ins=dec(rva,16,1)
                refs.append(dict(rva=rva,slot=slot,opcode='FF%02X'%b[j+1],raw=b[j:j+6].hex(),self=text(ins[0]) if ins else '',size=ins[0].size if ins else 0))
    # boundary-independent byte search for mov reg,[absolute slot]
    for slot in SLOTS:
        pat=b'\x8b'
        # mov r32, [disp32]: 8B modrm 05/0D/15/1D/25/2D/35/3D
        mods=b'\x05\x0d\x15\x1d\x25\x2d\x35\x3d'
        for p in mods:
            q=0
            while True:
                q=b.find(pat+bytes([p])+struct.pack('<I',slot),q)
                if q<0: break
                rva=s['va']+q
                ins=dec(rva,16,1)
                if ins and ins[0].address-IB==rva and ins[0].mnemonic=='mov':
                    # Find an immediate next call reg at the exact next instruction boundary.
                    nxt=dec(rva+ins[0].size,32,3)
                    call=None
                    for z in nxt:
                        if z.mnemonic=='call': call=z; break
                        if z.mnemonic not in ('nop','mov','push','lea','xor','test'): break
                    if call and call.operands and call.operands[0].type==CS_OP_REG:
                        movpairs.append(dict(load_rva=rva,load=text(ins[0]),call_rva=call.address-IB,call=text(call),size=ins[0].size))
                q+=1

# Deduplicate refs and mov pairs.
refs=sorted({(r['rva'],r['slot']):r for r in refs}.values(),key=lambda x:(x['slot'],x['rva']))
movpairs=sorted({(m['load_rva'],m['call_rva']):m for m in movpairs}.values(),key=lambda x:(x['load_rva'],x['call_rva']))

# Exact direct branch/call incoming edges using only exact instruction decodes from candidate starts.
# We use byte-relative rel32/rel8 scans as candidates, then validate the source by self-decode.
direct=[]
for s in SECS:
    if s['name'].lower()=='.tvm0' or not (s['ch']&0x20000000): continue
    b=D[s['pr']:s['pr']+s['rs']]
    for j in range(len(b)-5):
        op=b[j]
        if op not in (0xe8,0xe9,0x0f): continue
        if op in (0xe8,0xe9):
            size=5; tgt=s['va']+j+5+struct.unpack_from('<i',b,j+1)[0]; kind='CALL' if op==0xe8 else 'JMP'
        else:
            if j+6>len(b) or not (0x80<=b[j+1]<=0x8f): continue
            size=6; tgt=s['va']+j+6+struct.unpack_from('<i',b,j+2)[0]; kind='JCC'
        src=s['va']+j
        ins=dec(src,16,1)
        if not ins or ins[0].address-IB!=src or ins[0].size!=size: continue
        if tgt in SLOTS or tgt in [x['rva'] for x in refs] or tgt==0x004853A8 or tgt==0x004853AE:
            direct.append(dict(src=src,target=tgt,kind=kind))
# byte searches for 2-byte Jcc and near Jcc/Jmp, validated by self-decode
for s in SECS:
    if s['name'].lower()=='.tvm0' or not (s['ch']&0x20000000): continue
    b=D[s['pr']:s['pr']+s['rs']]
    for op in range(0x70,0x80):
        for j in range(len(b)-2):
            if b[j]!=op: continue
            src=s['va']+j; tgt=src+2+struct.unpack_from('<b',b,j+1)[0]
            ins=dec(src,8,1)
            if ins and ins[0].address-IB==src and ins[0].size==2 and tgt in (0x004853A8,0x004853AE):
                direct.append(dict(src=src,target=tgt,kind='JCC_SHORT'))

# Exact bound for the FF25 local home: find all validated instruction starts and control edges in +/- 256 bytes.
def local_map(lo,hi):
    out={}
    # seed every offset, validate only self-consistent single instructions; still a candidate map
    for r in range(lo,hi):
        if not is_exec(r): continue
        i=dec(r,16,1)
        if i and i[0].address-IB==r: out[r]=i[0]
    return out

# Post-use extraction from exact next instruction.  This is a local exact-decode claim,
# not a whole-function CFG claim.
def post_use(ref):
    r=ref['rva']+ref['size']
    xs=dec(r,96,8)
    out=[]
    for i in xs:
        rr=i.address-IB
        out.append(dict(rva=rr,bytes=i.bytes.hex(),text=text(i),reads_eax=any(o.type==CS_OP_REG and o.reg==0 for o in i.operands)))
        if any(o.type==CS_OP_IMM and o.imm in (0x7886e68,0x7886e6c) for o in i.operands): out[-1]['compare_const']=hex(next(o.imm for o in i.operands if o.type==CS_OP_IMM and o.imm in (0x7886e68,0x7886e6c)))
        if i.mnemonic in ('ret','retn','jmp','ud2','int3'): break
    return out

for r in refs: r['post']=post_use(r)
for m in movpairs:
    ins=dec(m['call_rva'],16,1)
    m['post']=post_use(dict(rva=m['call_rva'],size=ins[0].size if ins else 0)) if ins else []

# CA8164 3-load summary: exact byte windows and branch incoming.
for m in movpairs:
    lo=m['load_rva']-64; hi=m['call_rva']+80
    m['window']=[dict(rva=i.address-IB,bytes=i.bytes.hex(),text=text(i)) for i in dec(lo,hi-lo)]
    m['incoming']=[d for d in direct if d['target'] in (m['load_rva'],m['call_rva'])]

# Entry local exact layout and sentinel family.
entry=dict(rva=ENTRY_RVA,slot=ENTRY_SLOT,slot_value=u32(ENTRY_SLOT-IB),slot_minus8=u32(ENTRY_SLOT-IB-8),slot_plus4=u32(ENTRY_SLOT-IB+4),refs=[r for r in refs if r['rva']==ENTRY_RVA])
entry['bytes_around']=read(ENTRY_SLOT-IB-16,48).hex() if read(ENTRY_SLOT-IB-16,48) else None

# Table-level sentinel scan inside CA8000..CA8800 only; file-backed permitted section.
tbl_base=0x00CA8000; tbl=[]
for idx in range(512):
    va=tbl_base+4*idx; v=u32(va-IB); tbl.append(dict(index=idx,va=va,value=v))
sent=[x for x in tbl if x['value'] is not None and 0x80000000<=x['value']<=0x8fffffff]
entry['sentinel_rows']=sent
entry['same_80000001']=[x for x in tbl if x['value']==0x80000001]

# CA819C immediate cluster: exact byte scan for preceding push imm32 in permitted sections.
imm=[]
for s in SECS:
    if s['name'].lower()=='.tvm0': continue
    b=D[s['pr']:s['pr']+s['rs']]
    for rva in [x['rva'] for x in refs if x['slot']==0x00CA819C]:
        j=rva-s['va']
        if j>=5 and b[j-5]==0x68:
            v=struct.unpack_from('<I',b,j-4)[0]
            if 0x081A5200<=v<=0x081A5700:
                imm.append(dict(ref=rva,push_rva=rva-5,value=v))
imm=sorted({x['ref']:x for x in imm}.values(),key=lambda x:x['ref'])
vals=[x['value'] for x in imm]
uniq=sorted(set(vals)); diffs=[uniq[i+1]-uniq[i] for i in range(len(uniq)-1)]
imm_summary=dict(count=len(vals),unique=len(uniq),values=['0x%08X'%v for v in uniq],duplicates=[[hex(k),v] for k,v in Counter(vals).items() if v>1],diffs=diffs,diff_counter=Counter(diffs))

# Save a compact JSON for audit; no tvm0 bytes.
(TMP/'dataclose_ca8xxx.json').write_text(json.dumps(dict(sections=SECS,refs=refs,movpairs=movpairs,direct=direct,entry=entry,imm=imm_summary),indent=2),encoding='utf-8')

lines=['DATACLOSE CA8xxx STRUCTURAL AUDIT','sections='+','.join('%d:%s'%(s['i'],s['name']) for s in SECS),'refs=%d movpairs=%d'%(len(refs),len(movpairs)),'']
for slot in SLOTS:
    rs=[r for r in refs if r['slot']==slot]
    lines.append('SLOT 0x%08X value=0x%08X refs=%d'%(slot,SLOTS[slot],len(rs)))
    for r in rs:
        lines.append(' REF 0x%08X %s %s'%(r['rva'],r['opcode'],r['self']))
        for p in r['post'][:6]: lines.append('   +0x%X %s%s'%(p['rva']-r['rva'],p['text'],' [EAX]' if p['reads_eax'] else ''))
    lines.append('')
lines.append('CA8164 MOV/CALL REG PAIRS')
for m in movpairs:
    lines.append(' 0x%08X %s ; 0x%08X %s'%(m['load_rva'],m['load'],m['call_rva'],m['call']))
    for x in m['window']: lines.append('   %08X %-20s %s'%(x['rva'],x['bytes'],x['text']))
    lines.append(' incoming='+repr(m['incoming']))
lines.append('')
lines.append('DIRECT EDGES TO FF25/NEARBY')
for d in direct:
    if d['target'] in (0x004853A8,0x004853AE): lines.append(' %s 0x%08X -> 0x%08X'%(d['kind'],d['src'],d['target']))
lines.append('')
lines.append('ENTRY SENTINEL')
lines.append(' value=0x%08X slot-8=0x%08X slot+4=0x%08X refs=%r'%(entry['slot_value'],entry['slot_minus8'],entry['slot_plus4'],entry['refs']))
lines.append(' same_80000001='+repr(entry['same_80000001']))
lines.append(' sentinel_count=%d'%len(entry['sentinel_rows']))
lines.append('')
lines.append('CA819C IMMEDIATE CLUSTER')
lines.append(json.dumps(imm_summary,indent=2))
(OUT/'dataclose_ca8xxx_audit.txt').write_text('\n'.join(lines),encoding='utf-8')
print('refs',len(refs),'movpairs',len(movpairs),'direct',len(direct),'sent',len(sent),'imm',len(vals))
print('movpairs',[(hex(m['load_rva']),m['load'],hex(m['call_rva']),m['call']) for m in movpairs])
print('entry',entry['slot_value'],hex(entry['slot_minus8']),entry['same_80000001'])
print('imm summary',imm_summary)
print('wrote',OUT/'dataclose_ca8xxx_audit.txt')
