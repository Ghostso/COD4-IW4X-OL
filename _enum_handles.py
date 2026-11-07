
import ctypes, ctypes.wintypes as w, sys, time
ntdll=ctypes.WinDLL('ntdll')
k32=ctypes.WinDLL('kernel32',use_last_error=True)
PROCESS_DUP_HANDLE=0x0040; PROCESS_QUERY_LIMITED_INFORMATION=0x1000
class UNICODE_STRING(ctypes.Structure):
    _fields_=[('Length',w.USHORT),('MaximumLength',w.USHORT),('Buffer',w.LPWSTR)]
class SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX(ctypes.Structure):
    _fields_=[('Object',ctypes.c_void_p),('UniqueProcessId',ctypes.c_void_p),('HandleValue',ctypes.c_void_p),('GrantedAccess',ctypes.c_ulong),('CreatorBackTraceIndex',ctypes.c_ushort),('ObjectTypeIndex',ctypes.c_ushort),('HandleAttributes',ctypes.c_ulong),('Reserved',ctypes.c_ulong)]
pid=int(sys.argv[1])
h=k32.OpenProcess(PROCESS_DUP_HANDLE|PROCESS_QUERY_LIMITED_INFORMATION,False,pid)
print('OpenProcess',hex(h or 0),'err',ctypes.get_last_error(),flush=True)
if h:
    size=1<<24; buf=ctypes.create_string_buffer(size); ret=w.ULONG()
    NQSI=ntdll.NtQuerySystemInformation; NQSI.restype=ctypes.c_long
    st=NQSI(64,buf,size,ctypes.byref(ret))
    print('NQSI',hex(st&0xffffffff),'len',ret.value,flush=True)
    if st>=0:
        cnt=ctypes.c_ulong.from_buffer(buf,0).value
        arr=(SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX*(cnt)).from_buffer(buf,16)
        targets=[]
        for i in range(cnt):
            r=arr[i]
            if r.UniqueProcessId==pid and r.HandleValue:
                targets.append((int(r.HandleValue),int(r.ObjectTypeIndex),int(r.GrantedAccess)))
        print('target handles',len(targets),flush=True)
        NQO=ntdll.NtQueryObject; NQO.restype=ctypes.c_long
        hits=[]; errs={}
        for hv,ti,ga in targets:
            dh=w.HANDLE()
            ok=k32.DuplicateHandle(h, w.HANDLE(hv), k32.GetCurrentProcess(), ctypes.byref(dh), 0, False, 2)
            if not ok: continue
            nb=ctypes.create_string_buffer(8192); rl=w.ULONG()
            q=NQO(dh,1,nb,len(nb),ctypes.byref(rl))
            if q>=0 and rl.value>=ctypes.sizeof(UNICODE_STRING):
                us=UNICODE_STRING.from_buffer(nb)
                if us.Buffer and us.Length:
                    s=ctypes.wstring_at(us.Buffer,us.Length//2)
                    if any(x in s.upper() for x in ('TCLS','SHARED','XTDL','MUTEX','SEMAPHORE')):
                        hits.append((hv,ti,ga,s))
            else:
                errs[q]=errs.get(q,0)+1
            k32.CloseHandle(dh)
        print('named hits',len(hits),flush=True)
        for x in hits: print(hex(x[0]),x[1],hex(x[2]),repr(x[3]),flush=True)
        print('query errs',errs,flush=True)
    k32.CloseHandle(h)
