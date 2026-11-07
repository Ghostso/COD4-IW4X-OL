import pefile,struct,json
DLL=r"D:\\BaiduNetdiskDownload\\使命召唤OL\\COD OL\\codoMP_client_shipRetailBase.dll"
b=open(DLL,'rb').read();pe=pefile.PE(data=b,fast_load=False)
print('=== TLS directory ===')
if hasattr(pe,'DIRECTORY_ENTRY_TLS'):
 t=pe.DIRECTORY_ENTRY_TLS.struct
 for f in ['StartAddressOfRawData','EndAddressOfRawData','AddressOfIndex','AddressOfCallBacks','SizeOfZeroFill','Characteristics']:
  print(' ',f,hex(getattr(t,f)))
else: print(' none')
print('=== RELOCATIONS summary ===')
if hasattr(pe,'DIRECTORY_ENTRY_BASERELOC'):
 from collections import Counter
 c=Counter();rows=[]
 for rb in pe.DIRECTORY_ENTRY_BASERELOC:
  for e in rb.entries:
   # type high nibble
   typ=(e.type if hasattr(e,'type') else (e.data>>12));c[typ]+=1
   if len(rows)<40:rows.append((rb.struct.VirtualAddress,e))
 print(' types',dict(c),'blocks',len(pe.DIRECTORY_ENTRY_BASERELOC),'entries',sum(c.values()))
 for va,e in rows:
  rva=va+e.rva if hasattr(e,'rva') else va+(e.data & 0xfff)
  print('  reloc rva',hex(rva),'type',(e.type if hasattr(e,'type') else (e.data>>12)))
else: print(' none')
print('=== RESOURCE entries ===')
if hasattr(pe,'DIRECTORY_ENTRY_RESOURCE'):
 for t in pe.DIRECTORY_ENTRY_RESOURCE.entries:
  print(' type',t.id,t.name)
  for d in getattr(t,'directory',[]).entries:
   print('  name',d.name,'id',d.id)
print('=== DEBUG directory ===')
if hasattr(pe,'DIRECTORY_ENTRY_DEBUG'):
 for d in pe.DIRECTORY_ENTRY_DEBUG:
  print(' debug',hex(d.struct.AddressOfRawData),hex(d.struct.SizeOfData),d.struct.Type)
