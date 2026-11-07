import ctypes
import sys
dll_path = 'D:\\BaiduNetdiskDownload\\使命召唤OL\\LocalRM.dll'
try:
    dll = ctypes.WinDLL(dll_path)
except Exception as e:
    print('Failed to load DLL:', e)
    sys.exit(1)
# Get function addresses
GetResourceManagerII = dll.GetResourceManagerII
ReleaseResourceManagerII = dll.ReleaseResourceManagerII
# Set return types and argument types
GetResourceManagerII.restype = ctypes.c_void_p
GetResourceManagerII.argtypes = []
ReleaseResourceManagerII.restype = None
ReleaseResourceManagerII.argtypes = []
# Call GetResourceManagerII
ptr1 = GetResourceManagerII()
print('GetResourceManagerII() returned:', hex(ptr1) if ptr1 else 'NULL')
# Call again to see if it returns the same pointer (our implementation returns fixed value)
ptr2 = GetResourceManagerII()
print('Second call returned:', hex(ptr2) if ptr2 else 'NULL')
# Call ReleaseResourceManagerII
ReleaseResourceManagerII(ptr1)
# Call again after release
ptr3 = GetResourceManagerII()
print('After release, Get returned:', hex(ptr3) if ptr3 else 'NULL')
# Check if the pointer is non-zero (our fixed value is 0x12345678)
if ptr1 == 0x12345678:
    print('Pointer matches expected fixed value')
else:
    print('Pointer does not match expected fixed value')