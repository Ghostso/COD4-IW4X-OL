from pathlib import Path
import pefile, struct, re
path=r'COD OL\WeGameLauncher\launcher.exe'
pe=pefile.PE(path,fast_load=True); data=Path(path).read_bytes(); base=pe.OPTIONAL_HEADER.ImageBase
# Focus on runtime launch/IPC-related strings; print all including their refs.
keys=['LauncherEvent','ResponseZombieSignal','LaunchSession','shared','Shared','Mutex','mutex','Event','event','Mapping','mapping','Pipe','pipe','Session','session','Launcher','launcher','TCLS','tcls','StartGame','start_game','StartFor','GameStart','GameStart','WeGame','wegame','Command','command','Instance','instance','Cmd','cmd','Proc','process']
seen=set(); rows=[]
for m in re.finditer(rb'[\x20-\x7e]{4,}',data):
    s=m.group().decode('latin1')
    if not any(k in s for k in keys): continue
    try:va=base+pe.get_rva_from_offset(m.start())
    except:continue
    if va in seen: continue
    seen.add(va); rows.append((va,s,m.start()))
for va,s,off in sorted(rows):
    refs=[]
    for sec in pe.sections:
        blob=sec.get_data(); sva=base+sec.VirtualAddress
        pos=0
        pat=struct.pack('<I',va)
        while True:
            i=blob.find(pat,pos)
            if i<0:break
            refs.append(sva+i); pos=i+1
    print(f'{va:08X} off={off:08X} refs={len(refs):2d} {s!r}')
    if refs: print('   ',' '.join(hex(x) for x in refs[:20]))
