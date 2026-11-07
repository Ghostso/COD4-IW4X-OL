import sys, json, struct
import pefile

def coff_symbols(path):
    d=open(path,'rb').read()
    pe=pefile.PE(data=d, fast_load=True)
    fh=pe.FILE_HEADER
    ptr=fh.PointerToSymbolTable; n=fh.NumberOfSymbols
    secs=pe.sections
    out=[]
    if not ptr or not n: return out, pe
    strtab_off = ptr + 18*n
    def cname(off):
        # off: 8-byte name field
        if off[:4]==b'\x00\x00\x00\x00':
            so=struct.unpack('<I',off[4:8])[0]
            end=d.index(b'\x00', strtab_off+so)
            return d[strtab_off+so:end].decode('latin1','replace')
        return off.rstrip(b'\x00').decode('latin1','replace')
    i=0
    while i<n:
        base=ptr+18*i
        name=cname(d[base:base+8])
        value,secnum,typ,storage,naux=struct.unpack('<IhHBB', d[base+8:base+18])
        if secnum>0 and secnum<=len(secs):
            s=secs[secnum-1]
            rva=s.VirtualAddress+value
            out.append({'name':name,'section':s.Name.rstrip(b'\x00').decode('latin1','replace'),
                        'value':value,'rva':rva,'va':pe.OPTIONAL_HEADER.ImageBase+rva,
                        'type':typ,'storage':storage})
        i+=1+naux
    return out, pe

if __name__=='__main__':
    path=sys.argv[1]; dst=sys.argv[2]
    syms,pe=coff_symbols(path)
    json.dump({'path':path,'n_symbols':len(syms),'symbols':syms}, open(dst,'w',encoding='utf-8'), ensure_ascii=False, indent=1)
    print('symbols',len(syms),'->',dst)
