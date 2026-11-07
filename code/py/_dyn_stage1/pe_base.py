from pathlib import Path
import pefile, hashlib, json
p = Path(r'COD OL\codoMP_client_shipRetailBase.dll')
out = Path(r'_dyn_stage1\base_pe_report.json')
d = p.read_bytes()
pe = pefile.PE(data=d, fast_load=False)
info = {
 'path': str(p.resolve()),
 'size': len(d),
 'sha256': hashlib.sha256(d).hexdigest(),
 'machine': hex(pe.FILE_HEADER.Machine),
 'timestamp': hex(pe.FILE_HEADER.TimeDateStamp),
 'characteristics': hex(pe.FILE_HEADER.Characteristics),
 'magic': hex(pe.OPTIONAL_HEADER.Magic),
 'image_base': hex(pe.OPTIONAL_HEADER.ImageBase),
 'size_of_image': hex(pe.OPTIONAL_HEADER.SizeOfImage),
 'entry_point_rva': hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
 'dll_characteristics': hex(pe.OPTIONAL_HEADER.DllCharacteristics),
 'sections': [],
 'directories': [],
 'imports': [],
 'exports': [],
 'delay_imports': [],
 'debug': [],
 'tls_callbacks': [],
}
for s in pe.sections:
    info['sections'].append({
      'name': s.Name.rstrip(b'\0').decode('latin1'),
      'va': hex(s.VirtualAddress), 'vsize': hex(s.Misc_VirtualSize),
      'raw_ptr': hex(s.PointerToRawData), 'raw_size': hex(s.SizeOfRawData),
      'characteristics': hex(s.Characteristics),
      'entropy': s.get_entropy(),
    })
for i, ent in enumerate(pe.OPTIONAL_HEADER.DATA_DIRECTORY):
    info['directories'].append({'index': i, 'rva': hex(ent.VirtualAddress), 'size': hex(ent.Size)})
if hasattr(pe, 'DIRECTORY_ENTRY_IMPORT'):
    for m in pe.DIRECTORY_ENTRY_IMPORT:
        info['imports'].append({'dll': m.dll.decode('latin1'), 'count': len(m.imports), 'names': [x.name.decode('latin1') if x.name else f'ord:{x.ordinal}' for x in m.imports[:200]]})
if hasattr(pe, 'DIRECTORY_ENTRY_DELAY_IMPORT'):
    for m in pe.DIRECTORY_ENTRY_DELAY_IMPORT:
        info['delay_imports'].append({'dll': m.dll.decode('latin1'), 'count': len(m.imports), 'names': [x.name.decode('latin1') if x.name else f'ord:{x.ordinal}' for x in m.imports[:200]]})
if hasattr(pe, 'DIRECTORY_ENTRY_EXPORT'):
    for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
        info['exports'].append({'ordinal': e.ordinal, 'rva': hex(e.address) if e.address is not None else None, 'name': e.name.decode('latin1') if e.name else None})
if hasattr(pe, 'DIRECTORY_ENTRY_DEBUG'):
    for dbg in pe.DIRECTORY_ENTRY_DEBUG:
        ent = {'type': dbg.struct.Type, 'size': dbg.struct.SizeOfData, 'ptr_raw': dbg.struct.PointerToRawData}
        try:
            if dbg.entry and getattr(dbg.entry, 'PdbFileName', None): ent['pdb'] = dbg.entry.PdbFileName.rstrip(b'\0').decode('latin1')
        except Exception: pass
        info['debug'].append(ent)
try:
    if hasattr(pe, 'DIRECTORY_ENTRY_TLS') and pe.DIRECTORY_ENTRY_TLS:
        td = pe.DIRECTORY_ENTRY_TLS.struct
        info['tls'] = {'start': hex(td.StartAddressOfRawData), 'end': hex(td.EndAddressOfRawData), 'index': hex(td.AddressOfIndex), 'callbacks': hex(td.AddressOfCallBacks)}
except Exception as ex: info['tls_error'] = str(ex)
out.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding='utf-8')
print(json.dumps(info, indent=2, ensure_ascii=False)[:30000])
