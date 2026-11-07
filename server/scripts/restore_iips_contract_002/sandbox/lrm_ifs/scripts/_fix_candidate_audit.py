from pathlib import Path
p=Path('scripts/_tmp_candidate_audit.py')
s=p.read_text(encoding='utf-8')
s=s.replace("f=off(st); xx=list(md.disasm(D[f:f+40],IB+st,count=12))\n print('\\n%s kind=%s refs=%s context=%s'%(fn,next(r['candidate_kind'] for r in rows if r['candidate_func']==fn),' '.join(r['ref_rva'] for r in rows if r['candidate_func']==fn),D[max(0,f-8):f+24].hex()))\n for x in xx: print('  %08X %-20s %s %s'%(x.address-IB,x.bytes.hex(),x.mnemonic,x.op_str))",
"f=off(st); ref=int(next(r['ref_rva'] for r in rows if r['candidate_func']==fn),16); xx=list(md.disasm(D[max(0,f-64):off(ref)+16],IB+max(st-64,0)))\n print('\\n%s kind=%s refs=%s context=%s'%(fn,next(r['candidate_kind'] for r in rows if r['candidate_func']==fn),' '.join(r['ref_rva'] for r in rows if r['candidate_func']==fn),D[max(0,f-8):f+24].hex()))\n for x in xx:\n  if ref-64 <= x.address-IB <= ref+16: print('  %08X %-20s %s %s%s'%(x.address-IB,x.bytes.hex(),x.mnemonic,x.op_str,' <== REF' if x.address-IB==ref else ''))")
p.write_text(s,encoding='utf-8')
