
import ctypes
import ctypes.wintypes as wt
import struct

k32 = ctypes.WinDLL('kernel32', use_last_error=True)
k32.OpenProcess.restype = wt.HANDLE
k32.ReadProcessMemory.restype = wt.BOOL
k32.ReadProcessMemory.argtypes = [wt.HANDLE, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t, ctypes.POINTER(ctypes.c_size_t)]

pid = 14968
h = k32.OpenProcess(0x400 | 0x10, False, pid)
print('OpenProcess handle:', hex(h) if h else f'ERR {k32.GetLastError()}')
if h:
    def read_va(va, n):
        buf = ctypes.create_string_buffer(n)
        got = ctypes.c_size_t(0)
        if k32.ReadProcessMemory(h, ctypes.c_void_p(va), buf, n, ctypes.byref(got)):
            return buf.raw[:got.value]
        return None

    ca_state = struct.unpack('<I', read_va(0x76446b0, 4))[0] if read_va(0x76446b0, 4) else None
    start_flag = read_va(0x849b61c, 1)[0] if read_va(0x849b61c, 1) else None
    dw_room_imp = struct.unpack('<I', read_va(0x82e13fc, 4))[0] if read_va(0x82e13fc, 4) else None
    dw_uber = struct.unpack('<I', read_va(0x82e1518, 4))[0] if read_va(0x82e1518, 4) else None

    print(f'CA connection state [0x76446b0]: {ca_state}')
    print(f'Start flag [0x849b61c]: {start_flag}')
    print(f'dwRoomImp: {hex(dw_room_imp) if dw_room_imp else None}')
    print(f'dwRoomMatchUber: {hex(dw_uber) if dw_uber else None}')

    if dw_room_imp:
        f278 = read_va(dw_room_imp + 0x278, 1)[0]
        f288 = read_va(dw_room_imp + 0x288, 1)[0]
        f289 = read_va(dw_room_imp + 0x289, 1)[0]
        f10614 = read_va(dw_room_imp + 0x10614, 1)[0]
        scnt = struct.unpack('<I', read_va(dw_room_imp + 0x7230, 4))[0]
        print(f'  dwRoomImp: +0x278={f278}, +0x288={f288}, +0x289={f289}, GateB(+0x10614)={f10614}, server_count={scnt}')

    if dw_uber:
        state = struct.unpack('<I', read_va(dw_uber + 0x20, 4))[0]
        print(f'  dwRoomMatchUber: state={state}')
