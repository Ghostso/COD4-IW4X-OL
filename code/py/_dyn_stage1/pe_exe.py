from pathlib import Path
import pefile, hashlib, json
p = Path(r'COD OL\codoMP_client_shipRetail.exe')
d = p.read_bytes(); pe = pefile.PE(data=d, fast_load=False)
info={'path':str(p.resolve()),'size':len(d),'sha256':hashlib.sha256(d).hexdigest(),'timestamp':hex(pe.FILE_HEADER.TimeDateStamp),'machine':hex(pe.FILE_HEADER.Machine),'image_base':hex(pe.OPTIONAL_HEADER.ImageBase),'size_of_image':hex(pe.OPTIONAL_HEADER.SizeOfImage),'entry':hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),'sections':[],'directories':[],'imports':[],'exports':[],'delay_imports':[],'debug':[],'version':{}}
for s in pe.sections:
    info['sections'].append({'name':s.Name.rstrip(b'\0').decode('latin1'),'va':hex(s.VirtualAddress),'vsize':hex(s.Misc_VirtualSize),'raw_ptr':hex(s.PointerToRawData),'raw_size':hex(s.SizeOfRawData),'entropy':s.get_entropy()})
for i,e in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY): info['directories'].append({'index':i,'rva':hex(e.VirtualAddress),'size':hex(e.Size)})
if hasattr(pe,'DIRECTORY_ENTRY_IMPORT'):
    for m in pe.DIRECTORY_ENTRY_IMPORT: info['imports'].append({'dll':m.dll.decode('latin1'),'count':len(m.imports),'names':[x.name.decode('latin1') if x.name else f'ord:{x.ordinal}' for x in m.imports[:300]]})
if hasattr(pe,'DIRECTORY_ENTRY_EXPORT'):
    for e in pe.DIRECTORY_ENTRY_EXPORT.symbols: info['exports'].append({'ordinal':e.ordinal,'rva':hex(e.address) if e.address is not None else None,'name':e.name.decode('latin1') if e.name else None})
if hasattr(pe,'DIRECTORY_ENTRY_DEBUG'):
    for d0 in pe.DIRECTORY_ENTRY_DEBUG:
        ent={'type':d0.struct.Type,'size':d0.struct.SizeOfData}
        try:
            if getattr(d0.entry,'PdbFileName',None): ent['pdb']=d0.entry.PdbFileName.rstrip(b'\0').decode('latin1')
        except Exception: pass
        info['debug'].append(ent)
try:
    for fi in pe.FileInfo or []:
        for st in fi:
            if getattr(st,'Key',b'')==b'StringFileInfo':
                for stt in st.StringTable:
                    for k,v in stt.entries.items(): info['version'][k.decode('latin1','replace')]=v.decode('utf-8','replace')
except Exception: pass
Path(r'_dyn_stage1\exe_pe_report.json').write_text(json.dumps(info,indent=2,ensure_ascii=False),encoding='utf-8')
print(json.dumps(info,indent=2,ensure_ascii=False)[:35000])
