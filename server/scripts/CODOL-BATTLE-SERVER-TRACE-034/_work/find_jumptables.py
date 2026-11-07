import capstone, struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
md=capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
# Find 'jmp dword ptr [reg*4 + disp32]' jump tables in the .text region 0x401000-0x900000
print("Jump tables (ff 24 <modrm> disp32) in 0x401000..0x900000:")
hits=[]
for i in range(0x401000-BASE, 0x900000-BASE-6):
    if d[i]==0xFF and d[i+1] in (0x24,0x64,0xA4,0xE4):
        disp=struct.unpack_from("<I",d,i+2+((d[i+1]>>6)&0 and 0) or (i+2)-i)[0] if False else None
        # for modrm with SIB: ff 24 8d disp32  (base=0,index=ecx,scale=4)
        if d[i+1]==0x24 and i+7<=len(d):
            sib=d[i+2]; disp=struct.unpack_from("<I",d,i+3)[0]
            hits.append((i+BASE, sib, disp))
print("  count =",len(hits))
# focus on those with plausible targets inside .text
plaus=[]
for va,sib,disp in hits:
    if 0x401000 <= disp < 0x900000:
        plaus.append((va,sib,disp))
print("  with in-.text disp32:",len(plaus))
# print ones in the 0x46xxxx region (where the parser family lives)
for va,sib,disp in plaus:
    if 0x460000 <= va <= 0x480000 or 0x460000 <= disp <= 0x480000:
        tbl=[]; ok=True
        for k in range(0,8):
            try:
                t=struct.unpack_from("<I",d,(disp-BASE)+k*4)[0]
            except Exception: ok=False; break
            if not (0x401000 <= t < 0x900000): ok=False; break
            tbl.append(t)
        if ok:
            print("   jmp@%08X  table@%08X  targets=%s" % (va,disp,["%X"%t for t in tbl]))
