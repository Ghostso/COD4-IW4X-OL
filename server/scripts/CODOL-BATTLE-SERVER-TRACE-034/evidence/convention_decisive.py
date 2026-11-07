import struct
IMG = r"D:\BaiduNetdiskDownload\使命召唤OL\CODOLServer\_mainline\_dyn100_run_20260925_182324\live\image_best.bin"
d=open(IMG,'rb').read()
# locate the 'mmbook' string
i=d.find(b'mmbook\x00')
print("'mmbook' string file offset = 0x%X" % i)
# under the hypothesis 'file_offset == VA', the VA of this string is i
# under 'offset = VA-0x400000', the VA is i+0x400000
for label, sva in (("offset==VA  -> string VA", i), ("offset==VA-0x400000 -> string VA", i+0x400000)):
    pat = b"\x68" + struct.pack("<I", sva)          # push imm32
    pat2= b"\xb8" + struct.pack("<I", sva)          # mov eax, imm32
    pat3= b"\xb9" + struct.pack("<I", sva)
    pat4= b"\xba" + struct.pack("<I", sva)
    hits=[]
    for ptag,p in (("push",pat),("mov eax",pat2),("mov ecx",pat3),("mov edx",pat4)):
        st=0
        while True:
            j=d.find(p,st)
            if j<0: break
            hits.append((ptag,j)); st=j+1
    print("  %-36s VA=%08X  refs=%d  %s" % (label, sva, len(hits), [(t,"%X"%o) for t,o in hits[:8]]))
print()
print("Sanity: which file offset does the probe's playerStateFields table live at?")
for off in (0x855F70, 0xC55F70):
    if off < len(d):
        print("  off 0x%X first48: %s" % (off, d[off:off+48].hex()))
    else:
        print("  off 0x%X OUT OF FILE (size 0x%X)" % (off,len(d)))
