p="_gate.py"
s=open(p,encoding="utf-8").read()
old = """        for k in range(5):
            r=wrb(h,0x849B61F,1)
            print("POKE gate61F=1 -> %s"%r,flush=True); time.sleep(0.5)
        print("INJECTED at t=%.1f"%el,flush=True)"""
new = """        for k in range(5):
            r=wrb(h,0x849B61F,1)
            print("POKE gate61F=1 -> %s"%r,flush=True); time.sleep(0.5)
        # 同时填 host 槽（之前证明需要的）
        def wrbN(va, data):
            oldp=wt.DWORD()
            if not k32.VirtualProtectEx(h,ctypes.c_void_p(va),len(data),0x40,ctypes.byref(oldp)): return False
            w=ctypes.c_size_t(0)
            ok=k32.WriteProcessMemory(h,ctypes.c_void_p(va),data,len(data),ctypes.byref(w))
            k32.VirtualProtectEx(h,ctypes.c_void_p(va),len(data),oldp.value,ctypes.byref(oldp))
            return bool(ok)
        for va in (0x81A76A8,0x81A7F34,0x81A9784):
            print("  poke host 0x%08X -> %s"%(va, wrbN(va, b"tqos.gamesafe.qq.com\\x00")),flush=True)
        for va in (0x81A9780,0xE513D4):
            print("  poke port 0x%08X -> %s"%(va, wrbN(va, struct.pack("<H",8081)+b"\\x00\\x00")),flush=True)
        print("INJECTED at t=%.1f"%el,flush=True)"""
assert old in s
open(p,"w",encoding="utf-8").write(s.replace(old,new))
print("patched")
