import pefile
p=pefile.PE('COD OL/codoMP_client_shipRetail.exe')
for name,idx in [('EXPORT',0),('IMPORT',1),('RESOURCE',2),('EXCEPTION',3),('SECURITY',4),('BASERELOC',5),('DEBUG',6),('TLS',9),('LOAD_CONFIG',10),('IAT',12)]:
 d=p.OPTIONAL_HEADER.DATA_DIRECTORY[idx]
 print(name,'RVA',hex(d.VirtualAddress),'size',hex(d.Size))
if hasattr(p,'DIRECTORY_ENTRY_DEBUG'):
 for d in p.DIRECTORY_ENTRY_DEBUG:
  print('debug',d.struct.Type,hex(d.struct.AddressOfRawData),hex(d.struct.SizeOfData),hex(d.struct.PointerToRawData))
if hasattr(p,'DIRECTORY_ENTRY_TLS'):
 print('tls raw',hex(p.DIRECTORY_ENTRY_TLS.struct.AddressOfRawData),hex(p.DIRECTORY_ENTRY_TLS.struct.SizeOfTemplate),hex(p.DIRECTORY_ENTRY_TLS.struct.AddressOfCallBacks))
