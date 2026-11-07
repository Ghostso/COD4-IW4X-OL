from pathlib import Path
import pefile, re
p=Path(r'COD OL\codoMP_client_shipRetailBase.dll')
raw=p.read_bytes(); pe=pefile.PE(data=raw,fast_load=False)
sec_data=[]
for s in pe.sections:
    name=s.Name.rstrip(b'\0').decode('latin1')
    if name.lower()=='.tvm0':
        print('SKIP_SECTION',name,'len',s.SizeOfRawData)
        continue
    sec_data.append((name,s.PointerToRawData,raw[s.PointerToRawData:s.PointerToRawData+s.SizeOfRawData]))
print('EXPORTS')
if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
    for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        print(e.ordinal, hex(e.address) if e.address is not None else None, e.name)
print('TLS')
o=getattr(pe,'DIRECTORY_ENTRY_TLS',None)
if o:
    s=o.struct
    print('tls', {k:hex(getattr(s,k)) for k in ['StartAddressOfRawData','EndAddressOfRawData','AddressOfIndex','AddressOfCallBacks','SizeOfZeroFill','Characteristics']})
print('DEBUG')
if hasattr(pe,'DIRECTORY_ENTRY_DEBUG'):
    for d in pe.DIRECTORY_ENTRY_DEBUG:
        print(d.struct.Type,hex(d.struct.AddressOfRawData),hex(d.struct.PointerToRawData),hex(d.struct.SizeOfData),getattr(d.entry,'PdbFileName',None))
patterns=[b'Client.exe',b'codoMP_client_shipRetailBase.dll',b'TerSafe.dll',b'TCLS',b'TP3Helper',b'tgp_daemon',b'wegame',b'commandline',b'CommandLine',b'GetCommandLine',b'CreateProcess',b'LoadLibrary',b'gameID',b'game_id']
for name,base,data in sec_data:
    for pat in patterns:
        offs=[]; start=0
        while len(offs)<20:
            i=data.find(pat,start)
            if i<0: break
            offs.append(base+i); start=i+1
        if offs: print('PAT',name,pat.decode('latin1'),[hex(x) for x in offs])
print('ASCII selected non-tvm0')
seen=[]
for name,base,data in sec_data:
    for m in re.finditer(rb'[\x20-\x7e]{5,200}',data):
        s=m.group().decode('latin1')
        if re.search(r'Client\.exe|TCLS|TP3|TerSafe|wegame|tgp_|codoMP|GameBaby|command|launch|game\.exe',s,re.I):
            if len(seen)<300: seen.append((name,base+m.start(),s))
for name,off,s in seen: print(name,hex(off),repr(s[:240]))
