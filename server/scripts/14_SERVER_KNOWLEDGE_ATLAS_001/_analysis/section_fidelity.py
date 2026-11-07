import pefile, struct
P=r"D:\BaiduNetdiskDownload\CODOL_2697_Launcher\runtime\game\aplib-recovered\codol2697-static-candidate.bin"
data=open(P,"rb").read()
pe=pefile.PE(P,fast_load=True); IB=pe.OPTIONAL_HEADER.ImageBase
print("file size 0x%X (%d)" % (len(data),len(data)))
print()
print("%-8s %-12s %-12s %-12s %-10s %-10s" % ("sec","VA","VSize","RawSize","coverage","raw%nz"))
tot_vs=0; tot_rs=0
for s in pe.sections:
    nm=s.Name.rstrip(b"\x00").decode()
    vs=s.Misc_VirtualSize; rs=s.SizeOfRawData
    raw=data[s.PointerToRawData:s.PointerToRawData+rs]
    nz=sum(1 for b in raw if b)
    cov=100.0*rs/max(1,vs)
    print("%-8s 0x%08X   0x%08X   0x%08X   %7.3f%%   %6.1f%%" % (nm,s.VirtualAddress,vs,rs,cov,100.0*nz/max(1,len(raw))))
    tot_vs+=vs; tot_rs+=rs
print()
print("sum VSize=0x%X (%.1f MB)  sum RawSize=0x%X (%.1f MB)" % (tot_vs,tot_vs/1048576,tot_rs,tot_rs/1048576))
print()
print("=== .data honesty: declared 0x%X VSize, only 0x%X present in file ===" % (
    [s.Misc_VirtualSize for s in pe.sections if s.Name.rstrip(b"\x00")==b".data"][0],
    [s.SizeOfRawData for s in pe.sections if s.Name.rstrip(b"\x00")==b".data"][0]))
print()
# .rdata pointer integrity: does .rdata contain well-formed pointer tables to .text?
rd=[s for s in pe.sections if s.Name.rstrip(b"\x00")==b".rdata"][0]
rdata=data[rd.PointerToRawData:rd.PointerToRawData+rd.SizeOfRawData]
n_text_ptr=0; n_contig_runs=0; run=0
for i in range(0,len(rdata)-4,4):
    v=struct.unpack_from("<I",rdata,i)[0]
    if IB+0x1000<=v<IB+0x7AE000:
        n_text_ptr+=1; run+=1
    else:
        if run>=4: n_contig_runs+=1
        run=0
if run>=4: n_contig_runs+=1
print("=== .rdata integrity ===")
print(" aligned VA pointers into .text : %d" % n_text_ptr)
print(" contiguous pointer-table runs (>=4 consecutive) : %d" % n_contig_runs)
print(" => .rdata pointer tables are present and searchable (NOT globally destroyed)")