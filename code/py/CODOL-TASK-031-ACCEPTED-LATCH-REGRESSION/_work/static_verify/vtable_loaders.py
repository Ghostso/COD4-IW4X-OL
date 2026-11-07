import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
# absolute-address loading forms: 
#  B8+r imm32 (mov r32, imm32) ; 68 imm32 (push) ; 8D 05/0D/15/1D/25/2D/35/3D disp32 (lea r, [disp32]) ; A1 imm32 (mov eax,[m]) etc
def find_abs(addr):
    tb=struct.pack("<I",addr); s=0; out=[]
    while True:
        i=d.find(tb,s)
        if i<0: break
        out.append(i+BASE); s=i+1
    return out
for a in (0xDC73A0,0xDC7840,0xDC73B0,0xDC7850):
    r=find_abs(a)
    print("%08X: %s" % (a, ", ".join("%08X"%x for x in r) or "NONE"))
print()
# Explicitly: lea reg,[disp32]  = 8D modrm=00 reg 101
for a in (0xDC73A0,0xDC7840):
    tb=struct.pack("<I",a)
    for modrm in range(0x05,0x3E,8):
        pat=bytes([0x8D,modrm])+tb
        s=0
        while True:
            i=d.find(pat,s)
            if i<0: break
            print("lea %02X -> %08X : %08X" % (modrm,a,i+BASE)); s=i+1
