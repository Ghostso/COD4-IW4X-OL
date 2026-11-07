from pathlib import Path
p=Path('scripts/_tmp_high_reuse_deep.py')
s=p.read_text(encoding='utf-8')
s=s.replace("for i,(r,slot,opc) in enumerate(allr):", "for i,x in enumerate(allr):\n    r=x['rva']")
s=s.replace("if i==0 or r-allr[i-1][0]>0x10000: cid=r\n    clusters[r]=cid", "if i==0 or r-allr[i-1]['rva']>0x10000: cid=r\n    clusters[r]=cid")
s=s.replace("for r,slot,opc in allr:\n    cands", "for x in allr:\n    r=x['rva']; slot=x['slot']; opc=x['opcode']\n    cands")
s=s.replace("nearby=[(rr,ss) for rr,ss,oo in allr if rr!=r and abs(rr-r)<=64]", "nearby=[(y['rva'],y['slot']) for y in allr if y['rva']!=r and abs(y['rva']-r)<=64]")
p.write_text(s,encoding='utf-8')
print('patched')
