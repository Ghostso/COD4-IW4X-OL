import ctypes, ctypes.wintypes as wt, time
k32=ctypes.WinDLL('kernel32',use_last_error=True)
adv=ctypes.WinDLL('advapi32',use_last_error=True)
PROCESS_QUERY_INFORMATION=0x0400
PROCESS_VM_READ=0x0010
h=k32.OpenProcess(PROCESS_QUERY_INFORMATION|PROCESS_VM_READ,False,8788)
print('agent reachable:',bool(h))
if h: k32.CloseHandle(h)
# is our own session able to read the agent state file?
import json,os
p=r'D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\logs\elevated_agent.json'
print('state readable:',os.path.isfile(p))
print(json.load(open(p,encoding='utf-8')) if os.path.isfile(p) else '')
