import ctypes, ctypes.wintypes as wt, sys, os
sys.path.insert(0,r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline')
import engine_dump as E
h=E.k32.GetCurrentProcess()
m=E.MEMORY_BASIC_INFORMATION()
got=E.k32.VirtualQueryEx(h, ctypes.c_void_p(0x400000), ctypes.byref(m), ctypes.sizeof(m))
print('got',got,'BaseAddress',repr(m.BaseAddress),type(m.BaseAddress),'RegionSize',repr(m.RegionSize),type(m.RegionSize),'State',repr(m.State),type(m.State),'Protect',repr(m.Protect),type(m.Protect))
import json
print(json.dumps([(m.BaseAddress,m.RegionSize,m.State,m.Protect)]))
