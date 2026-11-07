import ctypes, ctypes.wintypes as wt
k32=ctypes.WinDLL('kernel32',use_last_error=True)
adv=ctypes.WinDLL('advapi32',use_last_error=True)
PROCESS_QUERY_INFORMATION=0x0400
h=k32.OpenProcess(PROCESS_QUERY_INFORMATION,False,4)  # System process
print('OpenProcess(pid=4) ->',h,'err',ctypes.get_last_error())
h2=k32.OpenProcess(PROCESS_QUERY_INFORMATION,False,12164)
print('OpenProcess(pid=12164) ->',h2,'err',ctypes.get_last_error())
