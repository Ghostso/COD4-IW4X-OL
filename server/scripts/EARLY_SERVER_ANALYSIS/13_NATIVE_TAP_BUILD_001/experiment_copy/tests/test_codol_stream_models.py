"""Exercise the native streamed-model decoder; optional arguments are model IWD ZIPs."""
import ctypes as C
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import zipfile
import pathlib as _codol_pl
_codol_src=_codol_pl.Path(__file__).resolve().parents[1]/'src'
CODOL_INCLUDE=['-I'+str(_codol_src)]+['-I'+str(d) for d in sorted((_codol_src/'codol').iterdir()) if d.is_dir()]

class Block(C.Structure):
    _fields_=[('data',C.c_void_p),('size',C.c_size_t)]
class Model(C.Structure):
    _fields_=[('storage',C.c_void_p*3),('blocks',Block*8)]

root=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
    dll=Path(tmp)/('models.dll' if os.name=='nt' else 'models.so')
    subprocess.run([os.environ.get('CC', 'gcc'), *CODOL_INCLUDE,'-shared','-fPIC','-O1','-I'+str(root/'src'),
                    str(root/'src/codol/assets/codol_stream_model.c'),'-o',str(dll)],check=True)
    lib=C.CDLL(str(dll))
    lib.CODOL_ReadStreamModel.argtypes=[C.c_void_p,C.c_size_t,C.POINTER(Model)]
    lib.CODOL_FreeStreamModel.argtypes=[C.POINTER(Model)]

    def verify(data):
        buf=C.create_string_buffer(data); result=Model()
        assert lib.CODOL_ReadStreamModel(buf,len(data),C.byref(result))
        try:
            desc=[struct.unpack_from('<5I',data,8+20*i) for i in range(4)]
            for i,block in enumerate((3,6,7)):
                size,offset,start,count,_=desc[i]
                expected=bytearray(data[offset:offset+size])
                for k in range(start,start+count):
                    fix=struct.unpack_from('<I',data,desc[3][1]+4*k)[0]
                    location,target=fix>>3,fix&7
                    value=struct.unpack_from('<I',data,offset+location)[0]
                    struct.pack_into('<I',expected,location,((3,6,7)[target]<<28)+value+1)
                assert result.blocks[block].size==size
                assert C.string_at(result.blocks[block].data,size)==expected
            assert C.string_at(buf,len(data))==data
        finally:
            lib.CODOL_FreeStreamModel(C.byref(result))
            assert bytes(result)==bytes(Model())

    data=bytearray(156)
    struct.pack_into('<2I',data,0,1,0xe9c9c447)
    for i,d in enumerate(((48,88,0,3,0),(4,136,3,0,0),(4,140,3,0,0),(12,144,0,0,0))):
        struct.pack_into('<5I',data,8+20*i,*d)
    struct.pack_into('<I',data,88,12)
    struct.pack_into('<3I',data,144,0,33,66)
    verify(bytes(data))
    def reject(data,length=None):
        result=Model();result.storage[0]=1234
        before=bytes(result);buf=C.create_string_buffer(bytes(data))
        assert not lib.CODOL_ReadStreamModel(buf,len(data) if length is None else length,C.byref(result))
        assert bytes(result)==before
    for length in range(len(data)):
        reject(data,length)
    for offset,value in ((0,2),(4,0),(12,87),(32,90),(16,4),(20,4),(144,3),(148,0xfffffff8),(88,48),(92,4)):
        bad=data.copy();struct.pack_into('<I',bad,offset,value);reject(bad)
    count=0
    for path in sys.argv[1:]:
        with zipfile.ZipFile(path) as z:
            for name in z.namelist():
                if name.endswith('/'):continue
                verify(z.read(name));count+=1
    print(f'PASS: streamed model relocation fixtures and {count} archive models')
    if os.name=='nt':
        import _ctypes
        _ctypes.FreeLibrary(lib._handle)
