import ctypes
from ctypes import wintypes
class US(ctypes.Structure):
    _fields_=[('Length',wintypes.USHORT),('MaximumLength',wintypes.USHORT),('Buffer',ctypes.c_void_p)]
class OA(ctypes.Structure):
    _fields_=[('Length',wintypes.ULONG),('RootDirectory',wintypes.HANDLE),('ObjectName',ctypes.POINTER(US)),('Attributes',wintypes.ULONG),('SecurityDescriptor',ctypes.c_void_p),('SecurityQualityOfService',ctypes.c_void_p)]
nt=ctypes.WinDLL('ntdll',use_last_error=True); k=ctypes.WinDLL('kernel32',use_last_error=True)
nt.NtOpenDirectoryObject.argtypes=[ctypes.POINTER(wintypes.HANDLE),wintypes.DWORD,ctypes.POINTER(OA)];nt.NtOpenDirectoryObject.restype=ctypes.c_long
nt.NtQueryDirectoryObject.argtypes=[wintypes.HANDLE,ctypes.c_void_p,wintypes.ULONG,wintypes.BOOLEAN,wintypes.BOOLEAN,ctypes.POINTER(wintypes.ULONG),ctypes.POINTER(wintypes.ULONG)];nt.NtQueryDirectoryObject.restype=ctypes.c_long
for path in (r'\BaseNamedObjects',r'\Sessions\1\BaseNamedObjects'):
    buf=ctypes.create_unicode_buffer(path); us=US(len(path)*2,(len(path)+1)*2,ctypes.cast(buf,ctypes.c_void_p)); oa=OA(ctypes.sizeof(OA),None,ctypes.pointer(us),0,None,None); h=wintypes.HANDLE(); st=nt.NtOpenDirectoryObject(ctypes.byref(h),1,ctypes.byref(oa))
    print('NAMESPACE',path,'OPEN',hex(st & 0xffffffff))
    if st<0: continue
    arr=ctypes.create_string_buffer(65536); ctx=wintypes.ULONG(0); ret=wintypes.ULONG(0); first=True; found=[]
    while True:
        st=nt.NtQueryDirectoryObject(h,arr,65536,True,first,ctypes.byref(ctx),ctypes.byref(ret)); first=False
        if st==0x8000001a: break
        if st<0: print(' QUERY_ERR',hex(st & 0xffffffff)); break
        base=ctypes.sizeof(US); n=US.from_buffer_copy(arr.raw[:base]); t=US.from_buffer_copy(arr.raw[base:base*2])
        if not n.Length: break
        name=ctypes.wstring_at(n.Buffer,n.Length//2); typ=ctypes.wstring_at(t.Buffer,t.Length//2) if t.Length else ''
        if any(x in name.upper() for x in ('TCLS','XTDL2','TEN','TP','ACE','COD','SHIP','TQM')): found.append((name,typ))
    k.CloseHandle(h); print(' MATCHES',len(found))
    for name,typ in found: print(' ',typ,name)
