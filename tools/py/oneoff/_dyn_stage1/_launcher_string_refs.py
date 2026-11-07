from pathlib import Path
import pefile, struct, re, collections
path=r'COD OL\WeGameLauncher\launcher.exe'
pe=pefile.PE(path,fast_load=True); data=Path(path).read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
# extract ASCII and wide strings, then index pointers to them in all sections
strings=[]
for m in re.finditer(rb'[\x20-\x7e]{4,}',data):
    s=m.group().decode('latin1')
    if any(k in s.lower() for k in ['mutex','event','mapping','pipe','tcls','wegame','launcher','session','context','platform','token','auth','ticket','instance','ipc','common','stage','process']):
        try: va=base+pe.get_rva_from_offset(m.start())
        except Exception: continue
        strings.append((va,s,m.start()))
for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}',data):
    try:s=m.group().decode('utf-16le','ignore')
    except:continue
    if any(k in s.lower() for k in ['mutex','event','mapping','pipe','tcls','wegame','launcher','session','context','platform','token','auth','ticket','instance','ipc','common','stage','process']):
        try: va=base+pe.get_rva_from_offset(m.start())
        except Exception: continue
        strings.append((va,s,m.start()))
print('STRINGS',len(strings))
for va,s,off in sorted(strings):
    refs=[]
    for sec in pe.sections:
        blob=sec.get_data(); sva=base+sec.VirtualAddress
        for pat in (struct.pack('<I',va), struct.pack('<I',va+2)):
            pos=0
            while True:
                i=blob.find(pat,pos)
                if i<0: break
                refs.append(sva+i); pos=i+1
    if refs:
        print(f'VA={va:08X} OFF={off:08X} STR={s!r}')
        print('  refs',' '.join(hex(x) for x in refs[:64]), 'count',len(refs))
