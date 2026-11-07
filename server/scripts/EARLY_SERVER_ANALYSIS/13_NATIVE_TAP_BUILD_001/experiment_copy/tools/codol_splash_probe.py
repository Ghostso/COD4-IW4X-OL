"""Guarded passive C1 splash slots and UI gates; no process writes or input."""
import argparse
import ctypes
import json
import struct


def inspect(pid):
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.OpenProcess.argtypes = [ctypes.c_uint32, ctypes.c_int, ctypes.c_uint32]
    k.OpenProcess.restype = ctypes.c_void_p
    k.ReadProcessMemory.argtypes = [ctypes.c_void_p, ctypes.c_void_p,
                                   ctypes.c_void_p, ctypes.c_size_t,
                                   ctypes.POINTER(ctypes.c_size_t)]
    k.CloseHandle.argtypes = [ctypes.c_void_p]
    h = k.OpenProcess(0x10, False, pid)
    if not h:
        raise ctypes.WinError(ctypes.get_last_error())

    def read(address, size):
        b = ctypes.create_string_buffer(size)
        got = ctypes.c_size_t()
        if not k.ReadProcessMemory(h, address, b, size, ctypes.byref(got)) or got.value != size:
            raise OSError(f'Unreadable {address:#x}')
        return b.raw

    def u(address):
        return struct.unpack('<I', read(address, 4))[0]

    try:
        if read(0x469140, 9) != bytes.fromhex('558bec51a168806f01'):
            raise ValueError('Wrong C1 image/base')
        index = u(0x6c3d2ac)
        if index > 1024:
            raise ValueError('Invalid cg pointer index')
        cg = u(0x16d3b58 + index * 4) ^ 0x490b400c
        command = u(cg)
        result = dict(pid=pid, commandTime=command,
                      status='captured' if command else 'inactive; slots skipped')
        result['uiInitializedGate16fc2da'] = read(0x16fc2da, 1)[0]
        result['uiFlags16fc2e0'] = read(0x16fc2e0, 1)[0]
        result['hudGates'] = dict(
            hudDrawHudBF090=u(cg + 0xbf090),
            localDvar952=read(u(0x16f8064) + 12, 1)[0],
            uiFlag16fc2e4=read(0x16fc2e4, 1)[0])
        result['killcam'] = dict(deltaTime=struct.unpack('<i', read(cg + 0xa50, 4))[0],
                                 entity=u(cg + 0xa54), inKillcam=u(cg + 0xc8b60))
        if not command:
            result['limitation'] = ('Inactive cg values are retained storage only, '
                                    'not proof of last-match state or a visible HUD gate.')
            return result
        data = read(cg + 0x174384, 80)
        result['slots'] = [dict(slot=i, row=r, startMilliseconds=t,
                                durationMilliseconds=d, optionalNumber=n)
                           for i, (r, t, d, n) in enumerate(struct.iter_unpack('<4i', data))]
        result['showSplashMenuGate'] = read(u(0x16d44d4) + 12, 1)[0]
        result['slotsUnchangedAcrossReads'] = data == read(cg + 0x174384, 80)
        result['commandTimeAfter'] = u(cg)
        result['limitation'] = 'Slot presence proves receipt, not visible menu/icon/text rendering; reads are not atomic.'
        return result
    finally:
        k.CloseHandle(h)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pid', type=int, required=True)
    print(json.dumps(inspect(p.parse_args().pid), indent=2))
