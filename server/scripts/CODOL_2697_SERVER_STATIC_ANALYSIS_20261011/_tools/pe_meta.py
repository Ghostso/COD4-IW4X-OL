import sys, json, hashlib, datetime, pefile

def ts(v):
    if not v: return None
    try: return datetime.datetime.utcfromtimestamp(v).strftime('%Y-%m-%d %H:%M:%S UTC')
    except Exception: return str(v)

def res_strings(pe):
    out={}
    try:
        if hasattr(pe,'FileInfo') and pe.FileInfo:
            for fi in pe.FileInfo:
                for entry in fi:
                    if getattr(entry,'Key',b'')==b'StringFileInfo':
                        for st in entry.StringTable:
                            for k,v in st.entries.items():
                                out[k.decode('utf-8','replace')]=v.decode('utf-8','replace')
    except Exception as e:
        out['_error']=str(e)
    return out

def analyze(p):
    d=open(p,'rb').read()
    sha=hashlib.sha256(d).hexdigest()
    pe=pefile.PE(data=d, fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],
                                           pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXPORT'],
                                           pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE'],
                                           pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DEBUG']])
    oh=pe.OPTIONAL_HEADER
    imports={}
    for entry in getattr(pe,'DIRECTORY_ENTRY_IMPORT',[]) or []:
        dll=entry.dll.decode('ascii','replace')
        fns=[imp.name.decode('ascii','replace') if imp.name else ('ord#%s'%imp.ordinal) for imp in entry.imports]
        imports[dll]=fns
    exports=[]
    if hasattr(pe,'DIRECTORY_ENTRY_EXPORT') and pe.DIRECTORY_ENTRY_EXPORT:
        for e in pe.DIRECTORY_ENTRY_EXPORT.symbols:
            exports.append(e.name.decode('ascii','replace') if e.name else 'ord#%s'%e.ordinal)
    sections=[]
    for s in pe.sections:
        sections.append({'name':s.Name.rstrip(b'\x00').decode('ascii','replace'),
            'VA':hex(s.VirtualAddress),'VSize':hex(s.Misc_VirtualSize),'RawSize':hex(s.SizeOfRawData),
            'RawPtr':hex(s.PointerToRawData),'Entropy':round(s.get_entropy(),4),
            'Chars':hex(s.Characteristics),'md5':s.get_hash_md5()})
    dbg=[]
    for dd in getattr(pe,'DIRECTORY_ENTRY_DEBUG',[]) or []:
        try:
            dbg.append({'type':dd.struct.Type,'size':dd.struct.SizeOfData,'ptr':hex(dd.struct.PointerToRawData),'addr':hex(dd.struct.AddressOfRawData)})
        except Exception: pass
    return {'path':p,'size':len(d),'sha256':sha,
        'machine':hex(pe.FILE_HEADER.Machine),'machine_name':str(pefile.MACHINE_TYPE.get(pe.FILE_HEADER.Machine)),
        'subsystem':str(pefile.SUBSYSTEM_TYPE.get(oh.Subsystem)),'subsystem_val':oh.Subsystem,
        'timestamp':pe.FILE_HEADER.TimeDateStamp,'timestamp_str':ts(pe.FILE_HEADER.TimeDateStamp),
        'image_base':hex(oh.ImageBase),'entry_point':hex(oh.AddressOfEntryPoint),'size_of_image':hex(oh.SizeOfImage),
        'dll_characteristics':hex(oh.DllCharacteristics),'characteristics':hex(pe.FILE_HEADER.Characteristics),
        'linker_ver':'%d.%d'%(oh.MajorLinkerVersion,oh.MinorLinkerVersion),
        'os_ver':'%d.%d'%(oh.MajorOperatingSystemVersion,oh.MinorOperatingSystemVersion),
        'num_sections':pe.FILE_HEADER.NumberOfSections,'num_imports':sum(len(v) for v in imports.values()),
        'import_dlls':sorted(imports.keys()),'import_count_per_dll':{k:len(v) for k,v in sorted(imports.items())},
        'imports':imports,'exports':exports,'imphash':pe.get_imphash(),
        'sections':sections,'version_strings':res_strings(pe),'debug':dbg}

if __name__=='__main__':
    out=[analyze(p) for p in sys.argv[2:]]
    json.dump(out, open(sys.argv[1],'w',encoding='utf-8'), indent=1, ensure_ascii=False)
    print('ok', sys.argv[1], len(out))

