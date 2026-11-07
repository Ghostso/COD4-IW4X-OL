"""Passive C1 camera/local viewmodel capture. Does not establish shadow causation."""
import argparse, ctypes, json, struct

def inspect(pid):
    k=ctypes.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32]
    k.OpenProcess.restype=ctypes.c_void_p
    k.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    k.CloseHandle.argtypes=[ctypes.c_void_p]
    h=k.OpenProcess(0x10,False,pid)
    if not h:raise ctypes.WinError(ctypes.get_last_error())
    def read(a,n):
        b=ctypes.create_string_buffer(n); got=ctypes.c_size_t()
        if not k.ReadProcessMemory(h,a,b,n,ctypes.byref(got)) or got.value!=n:raise OSError('Unreadable '+hex(a))
        return b.raw
    def u(a):return struct.unpack('<I',read(a,4))[0]
    def name(a):
        out=bytearray()
        for i in range(256):
            c=read(a+i,1)
            if c==b'\0':return out.decode('utf-8','replace')
            out+=c
        return '<unterminated>'
    try:
        guard=bytes.fromhex('a1 acd2c306 8b0c85 583b6d01 81f1 0c400b49 d981 5c010000')
        if read(0x429070,len(guard))!=guard:raise ValueError('Wrong C1 build/base')
        ci=u(0x6c3d2ac);vi=u(0x6c3d2bc)
        if ci>1024 or vi>1024:raise ValueError('Invalid pointer table index')
        cg=u(0x16d3b58+4*ci)^0x490b400c
        table=u(0x16d3b58+4*vi)^0x90834eee
        result={'pid':pid,'hasPredictedGameplayState':u(cg)>0,'commandTime':u(cg),'pm_type':u(cg+4),'eFlags':hex(u(cg+0xec)),
                'otherFlags':hex(u(cg+0x10)),'weapon':u(cg+0x33c),
                'arms':u(cg+0x144),'hands':u(cg+0x148),
                'playerOrigin':struct.unpack('<3f',read(cg+0x1c,12)),
                'viewOrigin':struct.unpack('<3f',read(cg+0xb0384,12)),
                'viewAxes':struct.unpack('<9f',read(cg+0xb0390,36)),
                'localDObjs':[],
                'limitation':'Model presence does not prove rendering or shadow casting; render flags not decoded.'}
        for hand in range(2):
            d=u(table+20*hand);entry={'hand':hand,'dobj':hex(d),'models':[]}
            if d:
                count=read(d+9,1)[0]
                if count>32:raise ValueError('Invalid DObj model count')
                models=u(d+0xc0)
                for i in range(count):
                    m=u(models+4*i)
                    entry['models'].append({'address':hex(m),'name':name(u(m))})
            result['localDObjs'].append(entry)
        return result
    finally:k.CloseHandle(h)

if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--pid',type=int,required=True)
    print(json.dumps(inspect(ap.parse_args().pid),indent=2))
