import collections, csv, os
d=r'D:\BaiduNetdiskDownload\使命召唤OL\run_codol_001\runs\ENGINE_DUMP_20260925_114204\engine'
rows=list(csv.DictReader(open(os.path.join(d,'runtime_code_analysis.csv'),encoding='utf-8')))
imm=collections.Counter(); direct=collections.Counter(); slot=collections.Counter()
for r in rows:
    m=r['mnemonic']; ops=r['operands'] or ''
    if m in ('call','jmp'):
        if ops.startswith('0x'):
            try: direct[int(ops,16)]+=1
            except: pass
        elif 'dword ptr [0x' in ops:
            try: slot[int(ops.split('[0x')[1].rstrip(']'),16)]+=1
            except: pass
    for tok in ops.replace(',',' ').split():
        if tok.startswith('0x'):
            try:
                v=int(tok,16)
                if 0x00400000<=v<=0x14000000 and v!=0x10C58000:
                    imm[v]+=1
            except: pass
print('== direct targets (non-local, top) ==')
for v,n in direct.most_common(50):
    tag='IMAGE' if 0x00400000<=v<0x00F00000 else ('RUNTIME' if 0x10C00000<=v<0x11000000 else '')
    print('  %08x x%-3d %s'%(v,n,tag))
print('\n== abs immediates (top) ==')
for v,n in imm.most_common(90):
    tag='IMAGE' if 0x00400000<=v<0x00F00000 else ('RUNTIME' if 0x10C00000<=v<0x11000000 else '')
    print('  %08x x%-3d %s'%(v,n,tag))
print('\n== slot refs ==')
for v,n in slot.most_common(40): print('  %08x x%d'%(v,n))
