"""Passive native helicopter flight/ownership capture. No debugger or writes.
Offsets describe retained native structs, NOT C1 structs. COFF addresses come
from the exact built exe; runtime code bytes are checked before data reads.
"""
import argparse, ctypes, hashlib, json, struct, time
from pathlib import Path
import pefile

def symbols(pe, data):
    off=pe.FILE_HEADER.PointerToSymbolTable; count=pe.FILE_HEADER.NumberOfSymbols
    strings=off+18*count; result={}; i=0
    while i<count:
        raw=data[off+18*i:off+18*(i+1)]
        if len(raw)!=18: raise ValueError('truncated COFF table')
        first,second=struct.unpack_from('<II',raw)
        name=(data[strings+second:].split(b'\0',1)[0] if not first else raw[:8].split(b'\0',1)[0]).decode('ascii','replace')
        value,section=struct.unpack_from('<Ih',raw,8)
        if section>0: result[name]=pe.OPTIONAL_HEADER.ImageBase+pe.sections[section-1].VirtualAddress+value
        i+=1+raw[17]
    return result

def inspect(args):
    data=Path(args.exe).read_bytes(); pe=pefile.PE(data=data); sy=symbols(pe,data)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.OpenProcess.argtypes=[ctypes.c_uint32,ctypes.c_int,ctypes.c_uint32];kernel.OpenProcess.restype=ctypes.c_void_p
    kernel.ReadProcessMemory.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_size_t)]
    kernel.CloseHandle.argtypes=[ctypes.c_void_p]
    class Module(ctypes.Structure):
        _fields_=[('size',ctypes.c_uint32),('id',ctypes.c_uint32),('pid',ctypes.c_uint32),('globalUsage',ctypes.c_uint32),('processUsage',ctypes.c_uint32),('base',ctypes.c_void_p),('imageSize',ctypes.c_uint32),('module',ctypes.c_void_p),('name',ctypes.c_wchar*256),('path',ctypes.c_wchar*260)]
    kernel.CreateToolhelp32Snapshot.argtypes=[ctypes.c_uint32,ctypes.c_uint32];kernel.CreateToolhelp32Snapshot.restype=ctypes.c_void_p
    kernel.Module32FirstW.argtypes=[ctypes.c_void_p,ctypes.POINTER(Module)]
    snapshot=kernel.CreateToolhelp32Snapshot(0x18,args.pid)
    if snapshot==ctypes.c_void_p(-1).value:raise ctypes.WinError(ctypes.get_last_error())
    module=Module();module.size=ctypes.sizeof(module)
    try:
        if not kernel.Module32FirstW(snapshot,ctypes.byref(module)):raise ctypes.WinError(ctypes.get_last_error())
    finally:kernel.CloseHandle(snapshot)
    preferred=pe.OPTIONAL_HEADER.ImageBase; delta=module.base-preferred
    sy={name:address+delta for name,address in sy.items()}
    mapped=pe.get_memory_mapped_image(ImageBase=module.base)
    handle=kernel.OpenProcess(0x10,False,args.pid)
    if not handle: raise ctypes.WinError(ctypes.get_last_error())
    def read(address,size):
        b=ctypes.create_string_buffer(size); got=ctypes.c_size_t()
        if not kernel.ReadProcessMemory(handle,address,b,size,ctypes.byref(got)) or got.value!=size: raise OSError(f'read failed at {address:#x}')
        return b.raw
    def unpack(buf,off,fmt='i'): return struct.unpack_from('<'+fmt,buf,off)[0]
    def vec(buf,off): return list(struct.unpack_from('<3f',buf,off))
    try:
        for name in ('_Scr_Vehicle_Think','_G_EntUnlink'):
            addr=sy[name]; rva=addr-module.base;expected=mapped[rva:rva+48]
            if read(addr,48)!=expected: raise ValueError(f'running code differs from exe: {name}')
        print(json.dumps({'pid':args.pid,'exeSha256':hashlib.sha256(data).hexdigest(),'readOnly':True}),flush=True)
        for sample in range(args.samples):
            now=unpack(read(sy['_level']+0x1ec,4),0)
            vehicle_pool=unpack(read(sy['_level']+0x2e68,4),0,'I')
            pool=read(sy['_g_entities'],2048*0x274); result=[]
            # entity.h: r.inuse100, scr_vehicle164, handler16e, nextthink19c.
            for number in range(2048):
                e=pool[number*0x274:(number+1)*0x274]
                pointer=unpack(e,0x164,'I')
                if not e[0x100] or not pointer: continue
                v=read(pointer,0x354)
                if unpack(v,0x1b8)!=number: raise ValueError('vehicle/entity identity mismatch')
                index=unpack(v,0x1bc,'h')
                if not 0<=index<32: raise ValueError('invalid native vehicle definition index')
                definition=read(sy['_s_vehicleInfos']+index*0x270,0x270)
                owner=unpack(e,0x154,'H')
                tag=unpack(e,0x218,'I'); parent=None
                if tag:
                    parent_ptr=unpack(read(tag,4),0,'I')
                    parent=(parent_ptr-sy['_g_entities'])//0x274
                riders=[unpack(v,0x2ec+i*12+8) for i in range(3)]
                rider_states=[]
                for rider in riders:
                    if not 0<=rider<32: continue
                    re=pool[rider*0x274:(rider+1)*0x274];client=unpack(re,0x15c,'I')
                    if client:
                        ps=read(client,0x18)
                        rider_states.append({'entity':rider,'pmType':unpack(ps,4),'pmFlags':hex(unpack(ps,12,'I')),'ownerHandle':unpack(re,0x154,'H'),'tagLinked':bool(unpack(re,0x218,'I'))})
                controller=None
                if '_turret_control_owner' in sy:
                    slot,rem=divmod(pointer-vehicle_pool,0x354)
                    if rem or not 0<=slot<8:raise ValueError('vehicle pointer outside native pool')
                    controller=unpack(read(sy['_turret_control_owner']+slot*4,4),0)-1
                result.append({'entity':number,'type':unpack(e,4),'handler':e[0x16e],'nextthink':unpack(e,0x19c),'linked':bool(e[0xf4]),'origin':vec(e,0x13c),'angles':vec(e,0x148),'parent':parent,'ownerHandle':owner,'definition':definition[:64].split(b'\0',1)[0].decode(errors='replace'),'definitionType':unpack(definition,0x40,'H'),'flags':hex(unpack(v,0x1c0,'I')),'moveState':unpack(v,0x1c8),'manualMode':unpack(v,0x248),'manualSpeed':unpack(v,0x24c,'f'),'acceleration':unpack(v,0x250,'f'),'deceleration':unpack(v,0x254,'f'),'speed':unpack(v,0x25c,'f'),'goal':vec(v,0x2a0),'stopAtGoal':unpack(v,0x274),'stopping':unpack(v,0x278),'velocity':vec(v,0x138),'riders':riders,'riderStates':rider_states,'turretController':controller})
            print(json.dumps({'sample':sample,'serverTime':now,'vehicleFrametime':unpack(read(sy['_vehicle_frametime'],4),0,'f'),'helicopterThinktime':unpack(read(sy['_helicopter_thinktime'],4),0),'vehicles':result},allow_nan=False),flush=True)
            if sample+1<args.samples:time.sleep(args.interval)
    finally:kernel.CloseHandle(handle)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--pid',type=int,required=True);p.add_argument('--exe',default='bin/codol_dedrun_next.exe');p.add_argument('--samples',type=int,default=1);p.add_argument('--interval',type=float,default=.5);args=p.parse_args()
    if not 1<=args.samples<=120 or not .25<=args.interval<=2:p.error('samples1..120; interval.25..2')
    inspect(args)

