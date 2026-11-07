import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read(); BASE=0x400000
lo,hi=0xDC6000,0xDC9000
hits=[]
n=len(d)
for i in range(n-10):
    if d[i]==0xC7:
        m=d[i+1]
        # forms: C7 /0 modrm: mod=00 rm=101 -> [disp32] (5 bytes); mod=01 -> [reg+disp8] (6 bytes)
        if (m & 0xF8)==0x00:
            mod=(m>>6)&3
            if mod==0 and (m&7)==5:
                imm=struct.unpack_from("<I",d,i+6)[0]
                if lo<=imm<hi: hits.append((i+BASE,imm,"[disp32]"))
            elif mod==1:
                imm=struct.unpack_from("<I",d,i+7)[0]
                if lo<=imm<hi: hits.append((i+BASE,imm,"[reg+disp8]"))
print("total:",len(hits))
for a,v,f in hits[:80]:
    print("  %08X  -> %08X   %s" % (a,v,f))
